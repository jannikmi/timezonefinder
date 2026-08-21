"""The offset table the coordinate accessors address polygons through.

The lookup path does not walk the FlatBuffers structure per candidate polygon. It
resolves every polygon's ``(byte offset, length)`` once and afterwards slices
coordinates straight out of the buffer, so what used to be a guarantee of the reader is
now an assumption of arithmetic. These tests pin down the three things that assumption
rests on: that the table addresses the same bytes the reader does, that it holds nothing
but integers - the property that lets a memory map be released while the table lives -
and that a ``TimezoneFinder`` built on it answers identically.
"""

import mmap

import numpy as np
import pytest

from scripts.data_integrity import DataIntegrityError, validate_coordinate_offset_table
from timezonefinder import TimezoneFinder
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.coord_accessors import FileCoordAccessor, MemoryCoordAccessor
from timezonefinder.flatbuf.io.polygons import (
    derive_coord_offset_table,
    get_coordinate_path,
    get_polygon_collection,
    read_polygon_array_at,
    read_polygon_array_from_binary,
    write_polygon_collection_flatbuffer,
)
from timezonefinder.utils import get_boundaries_dir, get_holes_dir

# Deliberately uneven: a single-vertex polygon, an odd length and a long one, so a
# derivation that quietly assumed a uniform stride would not survive.
POLYGONS = [
    np.array([[0, 1, 2], [3, 4, 5]], dtype=np.int32),
    np.array([[1000], [-2000]], dtype=np.int32),
    np.array([list(range(50)), list(range(-50, 0))], dtype=np.int32),
    np.array([[-10, -20, -30, -40], [60, 70, 80, 90]], dtype=np.int32),
]


@pytest.fixture
def written_collection(tmp_path):
    path = tmp_path / "coordinates.bin"
    write_polygon_collection_flatbuffer(path, POLYGONS)
    with open(path, "rb") as file:
        buffer = file.read()
    return buffer, get_polygon_collection(buffer, path)


@pytest.mark.unit
def test_table_addresses_what_was_written(written_collection):
    buffer, collection = written_collection
    offsets, lengths = derive_coord_offset_table(collection)

    assert len(offsets) == len(POLYGONS)
    for idx, original in enumerate(POLYGONS):
        np.testing.assert_array_equal(
            read_polygon_array_at(buffer, offsets[idx], lengths[idx]), original
        )


@pytest.mark.unit
def test_table_agrees_with_the_flatbuffers_reader(written_collection):
    """The reader is the definition of what a stored polygon means; the table is fast.

    Checked against each other rather than only against the input, because the two can
    also drift while both still round-trip - the reader is what the converter, the
    integrity check and the documented format all describe.
    """
    buffer, collection = written_collection
    offsets, lengths = derive_coord_offset_table(collection)

    for idx in range(len(POLYGONS)):
        expected = read_polygon_array_from_binary(collection, idx)
        actual = read_polygon_array_at(buffer, offsets[idx], lengths[idx])
        assert actual.shape == expected.shape
        assert actual.dtype == expected.dtype
        np.testing.assert_array_equal(actual, expected)


@pytest.mark.unit
def test_fetched_rows_are_contiguous(written_collection):
    """Both acceleration backends reject a strided row, so the reshape must stay a view."""
    buffer, collection = written_collection
    offsets, lengths = derive_coord_offset_table(collection)

    coords = read_polygon_array_at(buffer, offsets[2], lengths[2])
    assert coords[0].flags["C_CONTIGUOUS"]
    assert coords[1].flags["C_CONTIGUOUS"]


@pytest.mark.unit
def test_table_owns_its_data_and_references_nothing(written_collection):
    """The point of caching integers rather than arrays.

    A cached polygon array is a live export of the buffer it came from, so it would keep
    a memory map alive for as long as the accessor exists - in the mode that exists to
    avoid holding the data in memory. Integers referencing nothing is what makes the
    cache free of that trade, and ``base is None`` is what says so.
    """
    _, collection = written_collection
    offsets, lengths = derive_coord_offset_table(collection)

    assert offsets.base is None
    assert lengths.base is None
    assert offsets.dtype == np.uint32
    assert lengths.dtype == np.uint32


@pytest.mark.unit
def test_a_live_table_does_not_pin_the_mapping(tmp_path):
    """The claim the design rests on, asserted the only way it can be: by unmapping.

    A ``mmap`` refuses to close while any export of it is alive, so this passes only if
    the table really holds no view onto the buffer - and the accompanying case shows the
    refusal is real for something that does.
    """
    path = tmp_path / "coordinates.bin"
    write_polygon_collection_flatbuffer(path, POLYGONS)

    with open(path, "rb") as coord_file:
        coord_buf = mmap.mmap(coord_file.fileno(), 0, access=mmap.ACCESS_READ)
        collection = get_polygon_collection(coord_buf, path)
        offsets, lengths = derive_coord_offset_table(collection)
        del collection

        coord_buf.close()  # would raise BufferError if the table held a view
        assert coord_buf.closed
        assert len(offsets) == len(POLYGONS) == len(lengths)

    with open(path, "rb") as coord_file:
        coord_buf = mmap.mmap(coord_file.fileno(), 0, access=mmap.ACCESS_READ)
        coords = read_polygon_array_at(coord_buf, offsets[0], lengths[0])
        with pytest.raises(BufferError):
            coord_buf.close()
        del coords
        coord_buf.close()


@pytest.mark.unit
@pytest.mark.parametrize("in_memory", [False, True])
def test_accessors_return_what_the_reader_returns(tmp_path, in_memory):
    path = tmp_path / "coordinates.bin"
    write_polygon_collection_flatbuffer(path, POLYGONS)

    accessor_type = MemoryCoordAccessor if in_memory else FileCoordAccessor
    accessor = accessor_type(path)
    assert len(accessor) == len(POLYGONS)
    for idx, original in enumerate(POLYGONS):
        np.testing.assert_array_equal(accessor[idx], original)
        # polygon ids reach __getitem__ straight out of the shortcut arrays
        np.testing.assert_array_equal(accessor[np.int64(idx)], original)
    # released through __del__ rather than cleanup(): MemoryCoordAccessor.cleanup is
    # not safe to call twice, as its own docstring records.
    del accessor


@pytest.mark.integration
def test_packaged_data_offset_table_matches_the_reader():
    """The exhaustive check, over what the repository actually ships.

    Runs the same assertions the converter applies to what it just wrote, which is why
    they live in ``scripts.data_integrity`` rather than here - the two must not drift
    into asserting different things about the same files.
    """
    validate_coordinate_offset_table(DEFAULT_DATA_DIR)


@pytest.mark.integration
def test_integrity_check_rejects_a_table_that_addresses_the_wrong_bytes(
    tmp_path, monkeypatch
):
    """The check has to be able to fail, or it says nothing about the packaged data.

    A wrong offset is not self-announcing - it still yields plausible ``int32``
    coordinates - so a broken derivation is simulated rather than waited for.
    """
    data_dir = tmp_path / "data"
    for polygon_dir in (get_boundaries_dir(data_dir), get_holes_dir(data_dir)):
        polygon_dir.mkdir(parents=True)
        write_polygon_collection_flatbuffer(get_coordinate_path(polygon_dir), POLYGONS)

    def shifted(collection):
        offsets, lengths = derive_coord_offset_table(collection)
        # one int32 early: still inside the buffer, still readable, wrong
        return offsets - 4, lengths

    monkeypatch.setattr(
        "scripts.data_integrity.derive_coord_offset_table", shifted, raising=True
    )
    with pytest.raises(DataIntegrityError, match="offset table does not address"):
        validate_coordinate_offset_table(data_dir)


@pytest.mark.integration
def test_lookups_agree_across_memory_modes():
    """What the whole table is for: the same answers, addressed a cheaper way."""
    points = np.load("tests/fixtures/benchmarks/ambiguous_shortcut_points.npy")
    mapped = TimezoneFinder(in_memory=False)
    loaded = TimezoneFinder(in_memory=True)
    try:
        for lng, lat in points[:500]:
            lng, lat = float(lng), float(lat)
            assert mapped.timezone_at(lng=lng, lat=lat) == loaded.timezone_at(
                lng=lng, lat=lat
            )
    finally:
        mapped.cleanup()
        loaded.cleanup()
