"""Guard against silently reading packaged coordinates written by an incompatible version.

The polygon binary can change what it *means* inside an unchanged container: the
per-axis coordinate layout changed once with the same file name, the same schema, the
same vector lengths and values still plausible ``int32``. Such a file parses cleanly and
yields wrong timezones with no error, which no existing failure mode catches. The file
identifier and ``layout_version`` exist to turn that into a startup error, so the
rejection paths are what these tests cover.

The shortcut index carries the same pair of markers and is covered in
``tests/test_shortcut_index.py``, next to the rest of that format.
"""

import flatbuffers
import numpy as np
import pytest

from timezonefinder import TimezoneFinder
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.generated.polygons.Polygon import (
    PolygonAddPayload,
    PolygonEnd,
    PolygonStart,
    PolygonStartPayloadVector,
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
    get_coordinate_path,
    get_polygon_collection,
    write_polygon_collection_flatbuffer,
)
from timezonefinder.utils import get_boundaries_dir, get_holes_dir
from timezonefinder._data_integrity import validate_shipped_schemas

#: Payloads, not rings: this module tests the container and the markers on it, so what
#: the words mean is beside the point and anything decodable would only add a dependency
#: on the encoding these tests are not about.
PAYLOADS = [
    np.array([0, 1, 2, 3, 4, 5], dtype=np.uint32),
    np.array([100, 200, 300, 400], dtype=np.uint32),
]


def build_collection(
    payloads=PAYLOADS,
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
    for payload in payloads:
        PolygonStartPayloadVector(builder, len(payload))
        for word in reversed(payload):
            builder.PrependUint32(int(word))
        payload_offset = builder.EndVector()
        PolygonStart(builder)
        PolygonAddPayload(builder, payload_offset)
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
    write_polygon_collection_flatbuffer(output_file, PAYLOADS)
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
def test_guard_keeps_the_payload_zero_copy(in_memory):
    """Checking the markers must not turn the payload views into copies.

    ``coords_of`` itself owns its data since polygon layout 3 - it decodes a ring
    rather than viewing one - so what has to stay zero-copy is the payload underneath
    it, which is what the point-in-polygon kernels are handed and what would otherwise
    be copied per lookup.
    """
    tf = TimezoneFinder(in_memory=in_memory)
    try:
        payload = tf.boundaries.coordinates[0]
        assert payload.flags["OWNDATA"] is False
        assert tf.boundaries.coordinates.words.flags["OWNDATA"] is False
    finally:
        del payload
        del tf


if __name__ == "__main__":
    pytest.main([__file__])
