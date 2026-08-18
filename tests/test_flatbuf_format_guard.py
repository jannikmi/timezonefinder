"""Guard against silently reading packaged data written by an incompatible version.

Both packaged binary kinds can change what they *mean* inside an unchanged container:
the per-axis coordinate layout changed with the same file name, the same schema, the
same vector lengths and values still plausible ``int32``; a hybrid shortcut file holds
zone ids one byte wide in one schema and two in the other, and either width parses under
either schema. Such a file parses cleanly and yields wrong timezones with no error, which
no existing failure mode catches. The file identifier and ``layout_version`` exist to
turn that into a startup error, so the rejection paths are what these tests cover.
"""

import flatbuffers
import numpy as np
import pytest

from timezonefinder import TimezoneFinder
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.generated.polygons.Polygon import (
    PolygonAddCoords,
    PolygonEnd,
    PolygonStart,
    PolygonStartCoordsVector,
)
from timezonefinder.flatbuf.generated.polygons.PolygonCollection import (
    PolygonCollection,
    PolygonCollectionAddLayoutVersion,
    PolygonCollectionAddPolygons,
    PolygonCollectionEnd,
    PolygonCollectionStart,
    PolygonCollectionStartPolygonsVector,
)
from timezonefinder.flatbuf.io.polygons import (
    POLYGON_FILE_IDENTIFIER,
    POLYGON_LAYOUT_VERSION,
    flatten_polygon_coords,
    get_coordinate_path,
    get_polygon_collection,
    write_polygon_collection_flatbuffer,
)
from timezonefinder.flatbuf.io.hybrid_shortcuts import (
    SHORTCUT_LAYOUT_VERSION,
    SHORTCUT_SCHEMAS,
    ShortcutSchema,
    get_hybrid_shortcut_file_path,
    read_hybrid_shortcuts_binary,
    write_hybrid_shortcuts_flatbuffers,
)
from timezonefinder.utils import get_boundaries_dir, get_holes_dir
from scripts.data_integrity import validate_shipped_schemas

POLYGONS = [
    np.array([[0, 1, 2], [3, 4, 5]]),
    np.array([[100, 200], [300, 400]]),
]

SCHEMA_IDS = [schema.dtype_name for schema in SHORTCUT_SCHEMAS]


def build_collection(
    polygons=POLYGONS,
    *,
    with_identifier: bool = True,
    layout_version: int | None = POLYGON_LAYOUT_VERSION,
) -> bytes:
    """Build a polygon buffer, optionally omitting or faking the layout markers.

    ``with_identifier=False, layout_version=None`` reproduces a pre-guard file: the
    identifier did not exist and the field was absent, so it reads back as 0. Built here
    rather than committed as a binary fixture - a handful of builder calls stays readable
    and cannot rot.
    """
    builder = flatbuffers.Builder(0)
    polygon_offsets = []
    for polygon in polygons:
        coords = flatten_polygon_coords(polygon)
        PolygonStartCoordsVector(builder, len(coords))
        for coord in reversed(coords):
            builder.PrependInt32(int(coord))
        coords_offset = builder.EndVector()
        PolygonStart(builder)
        PolygonAddCoords(builder, coords_offset)
        polygon_offsets.append(PolygonEnd(builder))

    PolygonCollectionStartPolygonsVector(builder, len(polygon_offsets))
    for offset in reversed(polygon_offsets):
        builder.PrependUOffsetTRelative(offset)
    polygons_offset = builder.EndVector()

    PolygonCollectionStart(builder)
    PolygonCollectionAddPolygons(builder, polygons_offset)
    if layout_version is not None:
        PolygonCollectionAddLayoutVersion(builder, layout_version)
    collection_offset = PolygonCollectionEnd(builder)

    if with_identifier:
        builder.Finish(collection_offset, file_identifier=POLYGON_FILE_IDENTIFIER)
    else:
        builder.Finish(collection_offset)
    return bytes(builder.Output())


@pytest.mark.unit
def test_written_file_carries_layout_markers(tmp_path):
    """A file this version writes is one this version accepts."""
    output_file = tmp_path / "coordinates.bin"
    write_polygon_collection_flatbuffer(output_file, POLYGONS)
    with open(output_file, "rb") as f:
        buffer = f.read()

    assert PolygonCollection.PolygonCollectionBufferHasIdentifier(buffer, 0) is True
    collection = get_polygon_collection(buffer, output_file)
    assert collection.LayoutVersion() == POLYGON_LAYOUT_VERSION


@pytest.mark.unit
def test_pre_guard_buffer_is_rejected(tmp_path):
    """A file written before the markers existed must not be read as if it were current."""
    buffer = build_collection(with_identifier=False, layout_version=None)
    assert PolygonCollection.PolygonCollectionBufferHasIdentifier(buffer, 0) is False
    # would parse cleanly and return wrong coordinates without the guard
    assert PolygonCollection.GetRootAs(buffer, 0).LayoutVersion() == 0

    path = tmp_path / "coordinates.bin"
    with pytest.raises(ValueError) as excinfo:
        get_polygon_collection(buffer, path)

    message = str(excinfo.value)
    assert "file_converter.py" in message, "error must name the way to regenerate"
    assert str(path) in message, "error must name the offending file"
    assert "layout version 0" in message, (
        "a pre-guard file is layout version 0, not corrupt"
    )


@pytest.mark.unit
def test_newer_layout_version_is_rejected():
    """Old code, newer data - the direction the identifier alone cannot catch."""
    buffer = build_collection(layout_version=POLYGON_LAYOUT_VERSION + 1)
    assert PolygonCollection.PolygonCollectionBufferHasIdentifier(buffer, 0) is True

    with pytest.raises(ValueError) as excinfo:
        get_polygon_collection(buffer)

    message = str(excinfo.value)
    assert "file_converter.py" in message
    assert f"layout version {POLYGON_LAYOUT_VERSION + 1}" in message


@pytest.mark.unit
def test_the_packaged_data_ships_the_schemas_describing_it():
    """The committed data directory must carry the format definition it was written by.

    The copy under ``<data>/schemas/`` is what lets a data directory be read back
    without the package that wrote it - a hand-built ``bin_file_location``, a directory
    copied out of site-packages - and it is generated, so it goes stale silently: edit
    a schema, regenerate the bindings, and the shipped copy still describes the
    previous format with nothing to say so. The converter runs this same check over
    what it just wrote; this one covers what the repository ships.
    """
    validate_shipped_schemas(DEFAULT_DATA_DIR)


@pytest.mark.unit
@pytest.mark.parametrize("get_dir", [get_boundaries_dir, get_holes_dir])
def test_packaged_data_passes_guard(get_dir):
    """The shipped data must satisfy the guard its own writer stamps."""
    path = get_coordinate_path(get_dir())
    with open(path, "rb") as f:
        buffer = f.read()
    collection = get_polygon_collection(buffer, path)
    assert collection.LayoutVersion() == POLYGON_LAYOUT_VERSION


@pytest.mark.unit
@pytest.mark.parametrize("in_memory", [False, True])
def test_guard_keeps_coordinates_zero_copy(in_memory):
    """Checking the markers must not turn the coordinate views into copies."""
    tf = TimezoneFinder(in_memory=in_memory)
    try:
        coords = tf.coords_of(boundary_id=0)
        assert coords.flags["OWNDATA"] is False
    finally:
        del coords
        del tf


# --- hybrid shortcuts -------------------------------------------------------------

SHORTCUT_MAPPING: dict[int, int | list[int]] = {
    0x85283473FFFFFFF: 42,
    0x85283447FFFFFFF: [1, 2, 3],
}


def build_shortcut_collection(
    schema: ShortcutSchema,
    *,
    with_identifier: bool = True,
    layout_version: int | None = SHORTCUT_LAYOUT_VERSION,
) -> bytes:
    """Build a shortcut buffer, optionally omitting or faking the layout markers.

    ``with_identifier=False, layout_version=None`` reproduces a pre-guard file, back
    when the zone id width was inferred from the file name.
    """
    builder = flatbuffers.Builder(0)
    schema.unique_zone.UniqueZoneStart(builder)
    schema.unique_zone.UniqueZoneAddZoneId(builder, 42)
    unique_zone_offset = schema.unique_zone.UniqueZoneEnd(builder)

    schema.entry.HybridShortcutEntryStart(builder)
    schema.entry.HybridShortcutEntryAddHexId(builder, 0x85283473FFFFFFF)
    schema.entry.HybridShortcutEntryAddValueType(builder, schema.unique_zone_tag)
    schema.entry.HybridShortcutEntryAddValue(builder, unique_zone_offset)
    entry_offset = schema.entry.HybridShortcutEntryEnd(builder)

    schema.collection.HybridShortcutCollectionStartEntriesVector(builder, 1)
    builder.PrependUOffsetTRelative(entry_offset)
    entries_vector = builder.EndVector()

    schema.collection.HybridShortcutCollectionStart(builder)
    schema.collection.HybridShortcutCollectionAddEntries(builder, entries_vector)
    if layout_version is not None:
        schema.collection.HybridShortcutCollectionAddLayoutVersion(
            builder, layout_version
        )
    collection_offset = schema.collection.HybridShortcutCollectionEnd(builder)

    if with_identifier:
        builder.Finish(collection_offset, file_identifier=schema.file_identifier)
    else:
        builder.Finish(collection_offset)
    return bytes(builder.Output())


@pytest.mark.unit
def test_shortcut_identifiers_are_distinct():
    """The whole point of the identifier: it must tell the zone id widths apart.

    Sharing one would leave a uint8 buffer readable as uint16, which is silently wrong
    rather than an error - ``UniqueZone.zone_id`` simply decodes at the wrong width.
    """
    identifiers = [schema.file_identifier for schema in SHORTCUT_SCHEMAS]
    assert len(set(identifiers)) == len(identifiers)
    assert all(len(identifier) == 4 for identifier in identifiers), (
        "a FlatBuffers file identifier occupies exactly bytes 4-8"
    )


@pytest.mark.unit
@pytest.mark.parametrize("schema", SHORTCUT_SCHEMAS, ids=SCHEMA_IDS)
def test_written_shortcut_file_carries_layout_markers(schema, tmp_path):
    """A file this version writes is one this version accepts."""
    output_file = tmp_path / schema.file_name
    write_hybrid_shortcuts_flatbuffers(
        SHORTCUT_MAPPING, schema.zone_id_dtype, output_file
    )
    buffer = output_file.read_bytes()

    assert buffer[4:8] == schema.file_identifier
    collection = schema.collection.HybridShortcutCollection.GetRootAs(buffer, 0)
    assert collection.LayoutVersion() == SHORTCUT_LAYOUT_VERSION


@pytest.mark.unit
@pytest.mark.parametrize("schema", SHORTCUT_SCHEMAS, ids=SCHEMA_IDS)
def test_wrong_shortcut_identifier_is_rejected(schema, tmp_path):
    """A buffer carrying another kind's identifier is not a shortcut file.

    Stamped with the polygon identifier, everything else about it is a valid shortcut
    collection - so nothing but the identifier separates it from one that would parse.
    """
    buffer = bytearray(build_shortcut_collection(schema))
    buffer[4:8] = POLYGON_FILE_IDENTIFIER
    path = tmp_path / schema.file_name
    path.write_bytes(bytes(buffer))

    with pytest.raises(ValueError) as excinfo:
        read_hybrid_shortcuts_binary(path)

    message = str(excinfo.value)
    assert str(path) in message, "error must name the offending file"
    assert "file_converter.py" in message, "error must name the way to regenerate"


@pytest.mark.unit
@pytest.mark.parametrize("schema", SHORTCUT_SCHEMAS, ids=SCHEMA_IDS)
def test_pre_guard_shortcut_buffer_is_rejected(schema, tmp_path):
    """A file written before the markers existed carries no identifier at all."""
    path = tmp_path / schema.file_name
    path.write_bytes(
        build_shortcut_collection(schema, with_identifier=False, layout_version=None)
    )

    with pytest.raises(ValueError) as excinfo:
        read_hybrid_shortcuts_binary(path)

    assert "layout version 0" in str(excinfo.value), (
        "a pre-guard file is layout version 0, not corrupt"
    )


@pytest.mark.unit
@pytest.mark.parametrize("schema", SHORTCUT_SCHEMAS, ids=SCHEMA_IDS)
def test_newer_shortcut_layout_version_is_rejected(schema, tmp_path):
    """Old code, newer data - the direction the identifier alone cannot catch."""
    path = tmp_path / schema.file_name
    path.write_bytes(
        build_shortcut_collection(schema, layout_version=SHORTCUT_LAYOUT_VERSION + 1)
    )

    with pytest.raises(ValueError) as excinfo:
        read_hybrid_shortcuts_binary(path)

    assert f"layout version {SHORTCUT_LAYOUT_VERSION + 1}" in str(excinfo.value)


@pytest.mark.unit
@pytest.mark.parametrize("schema", SHORTCUT_SCHEMAS, ids=SCHEMA_IDS)
def test_shortcut_schema_follows_the_identifier_not_the_file_name(schema, tmp_path):
    """The reason the marker moved into the buffer: names lie, identifiers travel.

    Written under the *other* width's file name, the file still decodes at its own
    width. Before the identifier the name picked the schema, so this file silently
    returned zone ids read at the wrong width.
    """
    other = next(s for s in SHORTCUT_SCHEMAS if s is not schema)
    path = tmp_path / other.file_name
    write_hybrid_shortcuts_flatbuffers(SHORTCUT_MAPPING, schema.zone_id_dtype, path)

    read_back = read_hybrid_shortcuts_binary(path)
    assert read_back[0x85283473FFFFFFF] == 42
    assert list(read_back[0x85283447FFFFFFF]) == [1, 2, 3]


@pytest.mark.unit
@pytest.mark.parametrize("schema", SHORTCUT_SCHEMAS, ids=SCHEMA_IDS)
def test_packaged_shortcut_data_passes_guard(schema):
    """The shipped shortcut binary must satisfy the guard its own writer stamps."""
    path = get_hybrid_shortcut_file_path(schema.zone_id_dtype)
    if not path.exists():
        pytest.skip(f"no packaged shortcut binary for {schema.dtype_name}")
    buffer = path.read_bytes()
    assert buffer[4:8] == schema.file_identifier
    collection = schema.collection.HybridShortcutCollection.GetRootAs(buffer, 0)
    assert collection.LayoutVersion() == SHORTCUT_LAYOUT_VERSION


if __name__ == "__main__":
    pytest.main([__file__])
