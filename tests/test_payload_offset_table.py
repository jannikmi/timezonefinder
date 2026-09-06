"""The offset table the coordinate accessors address ring payloads through.

The lookup path does not walk the FlatBuffers structure per candidate polygon. It
resolves every ring's ``(word offset, length)`` once and afterwards addresses payload
words straight in the buffer, so what used to be a guarantee of the reader is now an
assumption of arithmetic. These tests pin down the three things that assumption rests
on: that the table addresses the same words the reader does, that it holds nothing but
integers - the property that lets a memory map be released while the table lives - and
that a ``TimezoneFinder`` built on it answers identically.
"""

import mmap
from pathlib import Path

import numpy as np
import pytest

from timezonefinder._data_integrity import (
    DataIntegrityError,
    validate_payload_offset_table,
    validate_payload_offset_width,
)
from timezonefinder import TimezoneFinder
from timezonefinder.configs import BLOCK_PAYLOAD_OFFSET_DTYPE, DEFAULT_DATA_DIR
from timezonefinder.coord_accessors import FileCoordAccessor, MemoryCoordAccessor
from timezonefinder.block_payload import PAYLOAD_WORD_DTYPE
from timezonefinder.flatbuf.io.polygons import (
    derive_payload_offset_table,
    get_coordinate_path,
    get_polygon_collection,
    read_payload_at,
    read_payload_from_binary,
    write_polygon_collection_flatbuffer,
)
from timezonefinder.utils import get_boundaries_dir, get_holes_dir

# Deliberately uneven: a one-word payload, an odd length and a long one, so a
# derivation that quietly assumed a uniform stride would not survive. Raw words rather
# than encoded rings, because what is under test is the addressing and not the encoding.
PAYLOADS = [
    np.array([0, 1, 2], dtype=PAYLOAD_WORD_DTYPE),
    np.array([1000], dtype=PAYLOAD_WORD_DTYPE),
    np.arange(50, dtype=PAYLOAD_WORD_DTYPE),
    np.array([10, 20, 30, 40], dtype=PAYLOAD_WORD_DTYPE),
]


@pytest.fixture
def written_collection(tmp_path):
    path = tmp_path / "coordinates.bin"
    write_polygon_collection_flatbuffer(path, PAYLOADS)
    with open(path, "rb") as file:
        buffer = file.read()
    words = np.frombuffer(buffer, dtype=PAYLOAD_WORD_DTYPE)
    return buffer, words, get_polygon_collection(buffer, path)


@pytest.mark.unit
def test_table_addresses_what_was_written(written_collection):
    _, words, collection = written_collection
    offsets, lengths = derive_payload_offset_table(collection)

    assert len(offsets) == len(PAYLOADS)
    for idx, original in enumerate(PAYLOADS):
        np.testing.assert_array_equal(
            read_payload_at(words, offsets[idx], lengths[idx]), original
        )


@pytest.mark.unit
def test_table_agrees_with_the_flatbuffers_reader(written_collection):
    """The reader is the definition of where a stored ring is; the table is fast.

    Checked against each other rather than only against the input, because the two can
    also drift while both still round-trip - the reader is what the converter, the
    integrity check and the documented format all describe.
    """
    _, words, collection = written_collection
    offsets, lengths = derive_payload_offset_table(collection)

    for idx in range(len(PAYLOADS)):
        expected = read_payload_from_binary(collection, idx)
        actual = read_payload_at(words, offsets[idx], lengths[idx])
        assert actual.shape == expected.shape
        assert actual.dtype == expected.dtype
        np.testing.assert_array_equal(actual, expected)


@pytest.mark.unit
def test_file_read_table_matches_the_buffer_read_one(tmp_path):
    """The two readers must not drift: same walk, different way of fetching the words."""
    path = tmp_path / "coordinates.bin"
    write_polygon_collection_flatbuffer(path, PAYLOADS)

    with open(path, "rb", buffering=0) as coordinate_file:
        with mmap.mmap(coordinate_file.fileno(), 0, access=mmap.ACCESS_READ) as buf:
            collection = get_polygon_collection(buf, path)
            from_buffer = derive_payload_offset_table(collection)
            from_file = derive_payload_offset_table(collection, coordinate_file)
            np.testing.assert_array_equal(from_file[0], from_buffer[0])
            np.testing.assert_array_equal(from_file[1], from_buffer[1])
            del collection


@pytest.mark.unit
def test_a_given_file_is_read_instead_of_the_buffer(tmp_path):
    """Why it matters that the file is used at all, and it does not show in the result.

    The header words sit next to the polygons they describe, so reading them through a
    memory map faults in a page per polygon - the resident set of a finder that has
    answered nothing yet more than doubled that way, on the one mode whose reason for
    existing is that it stays small. Both readers return the same table, so nothing
    about the return value says which ran.
    """
    path = tmp_path / "coordinates.bin"
    write_polygon_collection_flatbuffer(path, PAYLOADS)

    class CountingFile:
        def __init__(self, wrapped):
            self._wrapped = wrapped
            self.reads = 0

        def seek(self, position):
            return self._wrapped.seek(position)

        def read(self, size):
            self.reads += 1
            return self._wrapped.read(size)

    with open(path, "rb", buffering=0) as coordinate_file:
        counting = CountingFile(coordinate_file)
        with mmap.mmap(coordinate_file.fileno(), 0, access=mmap.ACCESS_READ) as buf:
            collection = get_polygon_collection(buf, path)
            derive_payload_offset_table(collection, counting)
            del collection
    # three scattered words per polygon (vtable reference, coords reference, length)
    assert counting.reads >= 3 * len(PAYLOADS)


@pytest.mark.unit
def test_the_mapped_accessor_opens_its_file_unbuffered(tmp_path):
    """Buffered, every seek discards a read-ahead buffer the next seek refills.

    Nothing else reads through this object - the mapping serves the coordinates - so a
    later tidy-up to a plain ``open(path, "rb")`` would look harmless and cost ~6x on
    the table's scattered reads, silently.
    """
    path = tmp_path / "coordinates.bin"
    write_polygon_collection_flatbuffer(path, PAYLOADS)

    accessor = FileCoordAccessor(path)
    try:
        # io.BufferedReader wraps a raw stream and exposes it as `.raw`; FileIO is raw
        assert not hasattr(accessor.coord_file, "raw")
    finally:
        accessor.cleanup()


@pytest.mark.unit
def test_a_fetched_payload_is_a_contiguous_view(written_collection):
    """The C backend rejects a strided buffer, and a copy per fetch is what this avoids."""
    _, words, collection = written_collection
    offsets, lengths = derive_payload_offset_table(collection)

    payload = read_payload_at(words, offsets[2], lengths[2])
    assert payload.flags["C_CONTIGUOUS"]
    assert payload.base is not None, "a fetched payload must not own its data"


@pytest.mark.unit
def test_table_owns_its_data_and_references_nothing(written_collection):
    """The point of caching integers rather than arrays.

    A cached polygon array is a live export of the buffer it came from, so it would keep
    a memory map alive for as long as the accessor exists - in the mode that exists to
    avoid holding the data in memory. Integers referencing nothing is what makes the
    cache free of that trade, and ``base is None`` is what says so.
    """
    _, _, collection = written_collection
    offsets, lengths = derive_payload_offset_table(collection)

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
    write_polygon_collection_flatbuffer(path, PAYLOADS)

    with open(path, "rb") as coord_file:
        coord_buf = mmap.mmap(coord_file.fileno(), 0, access=mmap.ACCESS_READ)
        collection = get_polygon_collection(coord_buf, path)
        offsets, lengths = derive_payload_offset_table(collection)
        del collection

        coord_buf.close()  # would raise BufferError if the table held a view
        assert coord_buf.closed
        assert len(offsets) == len(PAYLOADS) == len(lengths)

    with open(path, "rb") as coord_file:
        coord_buf = mmap.mmap(coord_file.fileno(), 0, access=mmap.ACCESS_READ)
        words = np.frombuffer(coord_buf, dtype=PAYLOAD_WORD_DTYPE)
        payload = read_payload_at(words, offsets[0], lengths[0])
        with pytest.raises(BufferError):
            coord_buf.close()
        del payload
        del words
        coord_buf.close()


@pytest.mark.unit
@pytest.mark.parametrize("in_memory", [False, True])
def test_accessors_return_what_the_reader_returns(tmp_path, in_memory):
    path = tmp_path / "coordinates.bin"
    write_polygon_collection_flatbuffer(path, PAYLOADS)

    accessor_type = MemoryCoordAccessor if in_memory else FileCoordAccessor
    accessor = accessor_type(path)
    assert len(accessor) == len(PAYLOADS)
    for idx, original in enumerate(PAYLOADS):
        np.testing.assert_array_equal(accessor[idx], original)
        # polygon ids reach __getitem__ straight out of the shortcut arrays
        np.testing.assert_array_equal(accessor[np.int64(idx)], original)
    # released through __del__ rather than cleanup(): MemoryCoordAccessor.cleanup is
    # not safe to call twice, as its own docstring records.
    del accessor


@pytest.mark.unit
@pytest.mark.parametrize("in_memory", [False, True])
def test_a_lookup_mutates_no_accessor_state(tmp_path, in_memory):
    """The offset table is built eagerly, and this is the invariant that says so.

    Not a style preference. Polygon coordinates are not optional-path data - every
    query a ``TimezoneFinder`` does not answer from a unique-zone shortcut cell reaches
    the accessor - so a lazily built table would defer a certain cost rather than avoid
    one, and would pay for it twice: an ``is None`` branch per fetch on the hot path,
    and a write to ``self`` from a lookup. The second is the expensive half. A shared
    instance is safe for concurrent reads precisely because every attribute is assigned
    in ``__init__`` or ``cleanup()`` and nothing on the lookup path mutates state; a
    lazy cache would be the first thing to break that, silently and only under load.

    So: fetch every polygon and assert the accessor is byte-for-byte the object it was.
    """
    path = tmp_path / "coordinates.bin"
    write_polygon_collection_flatbuffer(path, PAYLOADS)

    accessor_type = MemoryCoordAccessor if in_memory else FileCoordAccessor
    accessor = accessor_type(path)

    def state():
        # identity, not equality: a rebuilt-but-equal array is still a write
        return {name: id(value) for name, value in vars(accessor).items()}

    before = state()
    for idx in range(len(accessor)):
        accessor[idx]
    assert state() == before, (
        "a lookup replaced accessor state - the offset table must be built in "
        "__init__, never on first use"
    )
    # released through __del__ when the test returns: `del` here would leave the
    # `state()` closure referring to an unbound name.


@pytest.mark.integration
def test_packaged_data_offset_table_matches_the_reader():
    """The exhaustive check, over what the repository actually ships.

    Runs the same assertions the converter applies to what it just wrote, which is why
    they live in ``timezonefinder._data_integrity`` rather than here - the two must not drift
    into asserting different things about the same files.
    """
    validate_payload_offset_table(DEFAULT_DATA_DIR)


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
        write_polygon_collection_flatbuffer(get_coordinate_path(polygon_dir), PAYLOADS)

    def shifted(collection):
        offsets, lengths = derive_payload_offset_table(collection)
        # one word early: still inside the buffer, still readable, wrong
        return offsets - 1, lengths

    monkeypatch.setattr(
        "timezonefinder._data_integrity.derive_payload_offset_table",
        shifted,
        raising=True,
    )
    with pytest.raises(DataIntegrityError, match="offset table does not address"):
        validate_payload_offset_table(data_dir)


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


@pytest.mark.unit
def test_the_payload_offset_width_bounds_the_whole_buffer_not_one_ring(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A collection larger than the offset dtype must be refused, not wrapped.

    ``PolygonArray`` makes the per-block offsets absolute against the coordinate buffer
    with unsigned arithmetic, so a buffer past the dtype's reach would address another
    ring's residuals rather than raise. The guard is stated against the buffer because
    that - not the largest single ring - is the quantity at risk.

    The real dtype addresses 4.29 billion words, so the *width* is narrowed here rather
    than the file grown to 17 GB: what is under test is the comparison and the message,
    both of which read the dtype rather than a literal.
    """
    import timezonefinder._data_integrity as integrity

    monkeypatch.setattr(integrity, "BLOCK_PAYLOAD_OFFSET_DTYPE", np.dtype("<u1"))
    limit = int(np.iinfo(np.uint8).max)

    data_dir = tmp_path / "data"
    boundaries = data_dir / "boundaries"
    holes = data_dir / "holes"
    boundaries.mkdir(parents=True)
    holes.mkdir(parents=True)
    get_coordinate_path(holes).write_bytes(b"")
    path = get_coordinate_path(boundaries)

    # exactly at the limit: allowed
    path.write_bytes(b"\0" * (limit * PAYLOAD_WORD_DTYPE.itemsize))
    validate_payload_offset_width(data_dir)

    # one word past it: refused, naming the wrap it prevents
    path.write_bytes(b"\0" * ((limit + 1) * PAYLOAD_WORD_DTYPE.itemsize))
    with pytest.raises(DataIntegrityError, match="payload words"):
        validate_payload_offset_width(data_dir)


@pytest.mark.unit
def test_the_packaged_payload_offsets_are_inside_the_stored_width() -> None:
    """What the packaged data actually needs, against what the dtype addresses."""
    finder = TimezoneFinder()
    limit = int(np.iinfo(BLOCK_PAYLOAD_OFFSET_DTYPE).max)
    for collection in (finder.boundaries, finder.holes):
        assert collection.block_payload_offsets.dtype == BLOCK_PAYLOAD_OFFSET_DTYPE
        assert int(collection.block_payload_offsets.max()) <= limit
        # the offsets are absolute into the buffer, which is the bound the guard states
        assert int(collection.block_payload_offsets.max()) < len(
            collection.coordinates.words
        )
