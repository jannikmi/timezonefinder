"""Guard against silently reading coordinate data written by an incompatible version.

The per-axis coordinate layout changed inside an unchanged container: same file name,
same schema, same vector lengths, values still plausible ``int32``. A file written by an
older version parses cleanly and yields wrong timezones with no error, which no existing
failure mode catches. The file identifier and ``layout_version`` exist to turn that into
a startup error, so the rejection paths are what these tests cover.
"""

import flatbuffers
import numpy as np
import pytest

from timezonefinder import TimezoneFinder
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
from timezonefinder.utils import get_boundaries_dir, get_holes_dir

POLYGONS = [
    np.array([[0, 1, 2], [3, 4, 5]]),
    np.array([[100, 200], [300, 400]]),
]


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
    output_file = tmp_path / "coordinates.fbs"
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

    path = tmp_path / "coordinates.fbs"
    with pytest.raises(ValueError) as excinfo:
        get_polygon_collection(buffer, path)

    message = str(excinfo.value)
    assert "file_converter.py" in message, "error must name the way to regenerate"
    assert str(path) in message, "error must name the offending file"
    assert f"found {0}" in message, "a pre-guard file is layout version 0, not corrupt"


@pytest.mark.unit
def test_newer_layout_version_is_rejected():
    """Old code, newer data - the direction the identifier alone cannot catch."""
    buffer = build_collection(layout_version=POLYGON_LAYOUT_VERSION + 1)
    assert PolygonCollection.PolygonCollectionBufferHasIdentifier(buffer, 0) is True

    with pytest.raises(ValueError) as excinfo:
        get_polygon_collection(buffer)

    message = str(excinfo.value)
    assert "file_converter.py" in message
    assert f"found {POLYGON_LAYOUT_VERSION + 1}" in message


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


if __name__ == "__main__":
    pytest.main([__file__])
