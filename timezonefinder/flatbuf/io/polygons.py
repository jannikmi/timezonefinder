import flatbuffers
import mmap
import numpy as np
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO, Final

from timezonefinder.block_payload import PAYLOAD_WORD_DTYPE
from timezonefinder.configs import DEFAULT_DATA_DIR, IntegerLike
from timezonefinder.layout import incompatible_layout_error
from timezonefinder.flatbuf.generated.polygons.Polygon import (
    PolygonStart,
    PolygonEnd,
    PolygonAddPayload,
)
from timezonefinder.flatbuf.generated.polygons.PolygonCollection import (
    PolygonCollection,
    PolygonCollectionStart,
    PolygonCollectionEnd,
    PolygonCollectionAddPolygons,
    PolygonCollectionAddLayoutVersion,
    PolygonCollectionStartPolygonsVector,
)

# Byte offset of a field inside a FlatBuffers vtable, as the generated accessors spell
# it: `Polygon.PayloadAsNumpy` opens with `self._tab.Offset(4)` and
# `PolygonCollection.Polygons` with the same 4. Named here because
# `derive_payload_offset_table` walks those vtables itself instead of going through the
# generated classes, and a bare 4 in that arithmetic says nothing.
PAYLOAD_VTABLE_SLOT: Final[int] = 4
POLYGONS_VTABLE_SLOT: Final[int] = 4

# Widths of the FlatBuffers primitives the vtable walk steps over.
_UOFFSET_BYTES: Final[int] = 4  # table/vector references, and a vector's length prefix
_VOFFSET_BYTES: Final[int] = 2  # a vtable entry

# The three word types the walk reads, and how wide each is.
_SOFFSET: Final[str] = "<i4"  # signed: a table's offset back to its vtable
_UOFFSET: Final[str] = "<u4"
_VOFFSET: Final[str] = "<u2"
_WORD_BYTES: Final[dict[str, int]] = {
    _SOFFSET: _UOFFSET_BYTES,
    _UOFFSET: _UOFFSET_BYTES,
    _VOFFSET: _VOFFSET_BYTES,
}

# How many bytes one payload word occupies, which is what the offset arithmetic below
# converts between. The element type itself is
# :data:`~timezonefinder.block_payload.PAYLOAD_WORD_DTYPE`, and the two sides have to
# agree on it: `Builder.CreateNumpyVector` takes the element width from the array's
# dtype, so a wider array would write elements `read_payload_at` reads back as several.
PAYLOAD_WORD_BYTES: Final[int] = PAYLOAD_WORD_DTYPE.itemsize

# FlatBuffers file identifier (bytes 4-8), answering "is this a timezonefinder
# polygon file at all?". Files written before this marker existed carry none.
POLYGON_FILE_IDENTIFIER: Final[bytes] = b"TZFP"

# What a polygon collection file means. Absent in pre-guard files, which read back as
# the FlatBuffers default 0, so those files self-identify without special casing.
#
#   0 = coordinates interleaved [x0, y0, x1, y1, ...], every hole ring stored inline
#   1 = coordinates in per-axis blocks [x0...xN-1, y0...yN-1], and a *hole* collection
#       holds only the rings that are not a verbatim copy of a boundary polygon, with
#       holes/poly_ref.npy mapping hole ids onto them
#   2 = the same coordinates, plus the latitude block index beside them
#       (block_ranges.npy / block_offsets.npy, see timezonefinder/configs.py's
#       POLYGON_BLOCK_SIZE), and every ring rotated to the start index that index
#       is cheapest at
#   3 = the coordinates themselves are gone: each ring is a stream of 32-bit words
#       holding bit-packed residuals against one coordinate frame per block
#       (timezonefinder/block_payload.py), with the frames in block_bases.npy /
#       block_widths.npy and the vertex counts in nr_vertices.npy, which a packed
#       payload's length no longer gives
#
# Deliberately NOT tied to the package version: bump it only when what the file means
# changes, never for an ordinary release. Data compiled by any version that writes a
# given layout stays readable by any version that reads it, so a `bin_file_location`
# directory does not have to be regenerated on upgrade.
#
# Layout 1 covers both the per-axis encoding and the hole reference encoding because
# they ship together: neither has appeared in a release, so no version in the wild
# reads or writes layout 1, and giving the second change a version of its own would
# rewrite every packaged coordinate file to distinguish states that never coexisted.
#
# Layout 2 adds the latitude block index and the ring rotation that suits it. Neither
# is stored *in* this file - the index sits in two .npy files next to it, and a
# rotation is invisible by construction - so this marker is what a reader has to reject
# a layout 1 directory by: there the index files are absent, and a coordinate file from
# a layout 2 directory read at a different POLYGON_BLOCK_SIZE would be blocked
# differently while parsing perfectly. The check therefore has to happen before
# anything reads the index, which is where it does: PolygonArray builds its coordinate
# accessor first.
#
# Layout 3 changes the vector's element type as well as its meaning, so a layout 2 file
# read as layout 3 would parse - `[int]` and `[uint]` are the same bytes - and answer
# with nonsense. The marker is the only thing that separates them, which is why it is
# checked before the payload is touched rather than trusted.
POLYGON_LAYOUT_VERSION: Final[int] = 3


def get_coordinate_path(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the boundaries flatbuffer file.

    ``.bin`` rather than ``.fbs``: the latter is the FlatBuffers *schema* extension,
    and a schema is what ``timezonefinder/flatbuf/schemas/`` holds. This is a
    serialised buffer, which says what it is through its file identifier
    (``POLYGON_FILE_IDENTIFIER``) rather than through its name.
    """
    return data_dir / "coordinates.bin"


def write_polygon_collection_flatbuffer(
    file_path: Path, payloads: list[np.ndarray]
) -> None:
    """Write one packed payload per ring to a flatbuffer file.

    The container half of polygon layout 3, and only that: what a payload *means* is
    ``timezonefinder/block_payload.py``'s, and what a data directory needs beside it is
    ``scripts.file_converter.write_polygon_collection``'s. Splitting them is what keeps
    this testable against a hand-built collection that is not a timezone at all.

    :param file_path: where to write the collection
    :param payloads: one ring's payload words each, as :func:`.block_payload.encode_ring`
        returns them
    """
    print(f"writing {len(payloads)} polygons to binary file {file_path}")
    builder = flatbuffers.Builder(0)
    polygon_offsets = []

    for payload in payloads:
        # One copy per ring rather than a `Prepend` per word: the builder lays a numpy
        # vector down exactly as the element-wise loop did, for output that is
        # byte-identical and ~300x faster over a collection this size.
        words = np.ascontiguousarray(payload, dtype=PAYLOAD_WORD_DTYPE)
        payload_offset = builder.CreateNumpyVector(words)

        PolygonStart(builder)
        PolygonAddPayload(builder, payload_offset)
        polygon_offsets.append(PolygonEnd(builder))

    # Create polygon vector
    PolygonCollectionStartPolygonsVector(builder, len(polygon_offsets))
    for offset in reversed(polygon_offsets):
        builder.PrependUOffsetTRelative(offset)
    polygons_offset = builder.EndVector()

    # Create root table
    PolygonCollectionStart(builder)
    PolygonCollectionAddPolygons(builder, polygons_offset)
    PolygonCollectionAddLayoutVersion(builder, POLYGON_LAYOUT_VERSION)
    collection_offset = PolygonCollectionEnd(builder)

    # Finish buffer, stamping the identifier so readers can tell this file apart
    # from one written before the coordinate layout changed
    builder.Finish(collection_offset, file_identifier=POLYGON_FILE_IDENTIFIER)

    # Write to file
    with open(file_path, "wb") as f:
        buf = builder.Output()
        f.write(buf)
        # The whole file is read back as one `uint32` array, so its length has to be a
        # multiple of a word. FlatBuffers aligns what it writes but does not pad the
        # tail, and a file one byte short of a word would make `np.frombuffer` refuse
        # the buffer rather than any single polygon.
        padding = -len(buf) % PAYLOAD_WORD_BYTES
        if padding:
            f.write(b"\x00" * padding)


def _incompatible_layout_error(
    found_version: int, file_path: Path | None
) -> ValueError:
    """Build the error raised for coordinate data this version cannot read."""
    return incompatible_layout_error(
        "polygon coordinate file", found_version, POLYGON_LAYOUT_VERSION, file_path
    )


def get_polygon_collection(
    buf: bytes | mmap.mmap, file_path: Path | None = None
) -> PolygonCollection:
    """Load a PolygonCollection from a buffer, rejecting incompatible coordinate data.

    The layout changed without any change to the container: same file name,
    same schema, same vector lengths, values still plausible int32. Parsing such a file
    succeeds and returns wrong timezones silently, so the layout markers are checked
    here rather than trusted. This runs once per accessor construction, never per
    lookup, and does not touch the coordinate vectors - the zero-copy path is unaffected.

    Args:
        buf: A binary stream or memory-mapped file containing the flatbuffer data.
        file_path: Where ``buf`` came from, named in the error message. Optional so
            in-memory buffers can be checked too.

    Returns: PolygonCollection

    Raises:
        ValueError: if the buffer was written by an incompatible timezonefinder version.
    """
    if not PolygonCollection.PolygonCollectionBufferHasIdentifier(buf, 0):
        # Written before the identifier existed, i.e. the interleaved layout.
        # Reported as version 0 rather than as a corrupt file, since that is what
        # it actually is for everyone who will ever hit this.
        raise _incompatible_layout_error(0, file_path)
    collection = PolygonCollection.GetRootAs(buf, 0)
    version = collection.LayoutVersion()
    if version != POLYGON_LAYOUT_VERSION:
        raise _incompatible_layout_error(version, file_path)
    return collection


def read_payload_from_binary(
    poly_collection: PolygonCollection, idx: IntegerLike
) -> np.ndarray:
    """Read a ring's payload words from a FlatBuffers collection.

    The reference implementation of where a stored ring lives, and the slow one: it
    re-walks the vtables through the generated accessors on every call. The lookup path
    goes through :func:`derive_payload_offset_table` and :func:`read_payload_at`
    instead; this is what those are checked against, by
    ``scripts.data_integrity.validate_payload_offset_table``.
    """
    # value checks not required as this is a private function
    # processed polygon indices are expected to be in range
    poly = poly_collection.Polygons(idx)
    return poly.PayloadAsNumpy()


def _buffer_word_reader(buf: bytes | mmap.mmap) -> Callable:
    """Read scattered header words out of ``buf`` itself.

    Whole-buffer views plus advanced indexing, which is a gather: only the words
    addressed are read. Correct for any buffer, and the right choice when the bytes are
    already in memory - which for ``MemoryCoordAccessor`` and for the integrity check
    they are.
    """
    views = {
        dtype: np.frombuffer(buf, dtype=dtype, count=len(buf) // width)
        for dtype, width in _WORD_BYTES.items()
    }

    def read(positions: np.ndarray, dtype: str) -> np.ndarray:
        return views[dtype][positions // _WORD_BYTES[dtype]]

    return read


def _file_word_reader(coordinate_file: BinaryIO) -> Callable:
    """Read scattered header words through the file rather than through a mapping.

    Why this exists, and why it is worth ~4 ms of construction. The header words are
    ~5 KiB in total but sit next to the polygons they describe, so they are spread over
    every part of the file - 788 distinct pages of the packaged boundaries, across
    60 MiB. Reading them through the mapping faults every one of those pages in, and
    the kernel's readahead multiplies that: the resident set of a freshly constructed
    memory-mapped finder more than doubled, on the one mode whose reason for existing
    is that it stays small. Reading them through the file puts them in the page cache -
    shared, reclaimable, and nobody's resident set - and copies ~5 KiB into the heap.

    Requires ``coordinate_file`` to be **unbuffered** (``buffering=0``). Through a
    buffered object each seek discards a 128 KiB read-ahead buffer that the next seek
    refills, which measures 6x slower over the same reads.
    """

    def read(positions: np.ndarray, dtype: str) -> np.ndarray:
        width = _WORD_BYTES[dtype]
        chunks = []
        for position in positions.tolist():
            coordinate_file.seek(position)
            chunks.append(coordinate_file.read(width))
        return np.frombuffer(b"".join(chunks), dtype=dtype)

    return read


def derive_payload_offset_table(
    poly_collection: PolygonCollection,
    coordinate_file: BinaryIO | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Locate every ring's payload once, as plain integers.

    Returns ``(offsets, lengths)``: for polygon *i*, the offset of its first payload
    word into the buffer *read as words* and how many words follow. That is everything
    :func:`read_payload_at` needs, so fetching a candidate polygon costs one slice
    rather than a FlatBuffers vtable walk rebuilt in Python per lookup - which on the
    memory-mapped path was the dominant cost of a query.

    Word offsets rather than byte ones because that is what every consumer wants: the
    point-in-polygon kernels address the payload as ``uint32``, and a FlatBuffers vector
    of them is aligned to its element, so the conversion is exact by construction.

    **Integers, not arrays, and that is the whole design.** Caching the polygon arrays
    would be shorter and just as fast, but each cached array is a live export of the
    memory map, so the cache would pin the mapping for the accessor's lifetime - in the
    mode that exists precisely so the data need not be held in memory. Two ``uint32``
    vectors pin nothing, and cost ~10 KiB for the packaged dataset.

    **Derived with whole-array arithmetic, not a loop over ``Polygons(i)``.** The loop
    costs ~6 ms for the packaged boundaries against ~0.1 ms here, or ~4 ms through a
    file - which is what ``coordinate_file`` buys and why. That cost decides *how* the
    table is derived, never *whether* to defer it: callers build this eagerly because
    polygon coordinates are certainly needed, not because it is cheap (see
    ``FileCoordAccessor.__init__``). Keeping it cheap is what stops that decision from
    being paid for, on a construction the one-instance-per-thread pattern multiplies by
    the thread count.

    The walk mirrors what the generated accessors do, one step at a time over all
    polygons at once: read the polygons vector's relative offsets, turn them into table
    positions, follow each table's negative offset to its vtable, take the coords entry,
    and land on the coordinate vector's length prefix. It reads 4- and 2-byte words
    through whole-buffer views, which relies on FlatBuffers' guarantee that tables and
    vectors are aligned to ``uoffset`` and vtables to ``voffset``. Nothing here rejects a
    file that violates that - a misaligned position would read a neighbouring word and
    yield wrong coordinates silently, so what establishes it is
    ``scripts.data_integrity.validate_coordinate_offset_table``, comparing this table
    against :func:`read_payload_from_binary` for every polygon where the data is
    produced and again over what the repository ships.

    :param poly_collection: A collection returned by :func:`get_polygon_collection`
    :param coordinate_file: An **unbuffered** file open on the same data. When given,
        the header words are read through it instead of out of the collection's buffer,
        so building the table does not make a memory map resident - see
        :func:`_file_word_reader`. Pass nothing when the buffer is already in memory.
    :return: ``(offsets, lengths)`` in payload words, both ``uint32`` and both owning
        their data
    """
    root = poly_collection._tab
    read = (
        _buffer_word_reader(root.Bytes)
        if coordinate_file is None
        else _file_word_reader(coordinate_file)
    )

    slot = root.Offset(POLYGONS_VTABLE_SLOT)
    vector_start = np.int64(root.Vector(slot))
    count = root.VectorLen(slot)

    # Each element of a vector of tables is a reference relative to its own position.
    element_pos = vector_start + np.arange(count, dtype=np.int64) * _UOFFSET_BYTES
    table_pos = element_pos + read(element_pos, _UOFFSET)

    # A table opens with a *signed* offset backwards to its vtable, which lists where
    # each field sits relative to the table. FlatBuffers shares one vtable between
    # identically shaped tables, so these positions repeat - harmlessly.
    vtable_pos = table_pos - read(table_pos, _SOFFSET)
    field_offset = read(vtable_pos + PAYLOAD_VTABLE_SLOT, _VOFFSET).astype(np.int64)

    # The field holds a reference to the coordinate vector, whose length prefix sits
    # immediately before its data.
    reference_pos = table_pos + field_offset
    length_pos = reference_pos + read(reference_pos, _UOFFSET)

    lengths = read(length_pos, _UOFFSET).astype(np.uint32)
    byte_offsets = length_pos + _UOFFSET_BYTES
    if np.any(byte_offsets % PAYLOAD_WORD_BYTES):
        # Would mean the buffer is not what FlatBuffers wrote: a vector of `uint` is
        # aligned to four bytes, and its data starts right after a four-byte length
        # prefix. Checked rather than assumed, because a word view taken at an odd
        # offset reads neighbouring bytes and answers with plausible nonsense.
        raise ValueError(
            "payload vector not aligned to a word; the coordinate file was not written "
            "by this format"
        )
    return (byte_offsets // PAYLOAD_WORD_BYTES).astype(np.uint32), lengths


def read_payload_at(
    words: np.ndarray, offset: IntegerLike, length: IntegerLike
) -> np.ndarray:
    """Read a ring's payload straight out of ``words`` at a known position.

    The fetch half of :func:`derive_payload_offset_table`. Returns a zero-copy view, so
    it costs no allocation and nothing is decoded - the point-in-polygon kernels read
    the collection's whole payload and address a ring by offset, and this is for the
    callers that want one ring on its own.

    :param words: the coordinate buffer read as :data:`.block_payload.PAYLOAD_WORD_DTYPE`
    :param offset: word offset of the ring's payload
    :param length: how many words it occupies
    """
    return words[int(offset) : int(offset) + int(length)]
