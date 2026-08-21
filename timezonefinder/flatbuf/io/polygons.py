import flatbuffers
import mmap
import numpy as np
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO, Final

from timezonefinder.configs import DEFAULT_DATA_DIR, IntegerLike
from timezonefinder.flatbuf.io.layout import incompatible_layout_error
from timezonefinder.flatbuf.generated.polygons.Polygon import (
    PolygonStart,
    PolygonEnd,
    PolygonAddCoords,
    PolygonStartCoordsVector,
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
# it: `Polygon.CoordsAsNumpy` opens with `self._tab.Offset(4)` and
# `PolygonCollection.Polygons` with the same 4. Named here because
# `derive_coord_offset_table` walks those vtables itself instead of going through the
# generated classes, and a bare 4 in that arithmetic says nothing.
COORDS_VTABLE_SLOT: Final[int] = 4
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
POLYGON_LAYOUT_VERSION: Final[int] = 1


def flatten_polygon_coords(polygon: np.ndarray) -> np.ndarray:
    """Convert polygon coordinates from shape (2, N) to a flat [x0...xN-1, y0...yN-1] array.

    All x coordinates are stored first, followed by all y coordinates, so that each
    axis forms one contiguous block on disk.

    Args:
        polygon: Array of polygon coordinates with shape (2, N)
                where the first row contains x coordinates and the second row contains y coordinates

    Returns:
        Flattened 1D array of coordinates in the format [x0...xN-1, y0...yN-1]
    """
    # C order ravels row by row, i.e. all of row 0 (x) then all of row 1 (y).
    # Kept layout-agnostic on purpose: an F-ordered input still ravels to the same
    # result (via a copy), so the writer cannot silently emit the interleaved layout.
    return polygon.ravel(order="C")


def reshape_to_polygon_coords(coords: np.ndarray) -> np.ndarray:
    """Reshape flattened coordinates to the format (2, N).

    Returns a **view** onto ``coords`` whose rows are each C-contiguous: row 0 is the
    leading x block, row 1 the trailing y block. That is what keeps ``coords_of()``
    zero-copy, and both acceleration backends depend on it - the C extension rejects a
    strided row outright, and the Numba kernel's eager signature requires C order.

    Args:
        coords: Flattened 1D array of coordinates in the format [x0...xN-1, y0...yN-1]

    Returns:
        Array of polygon coordinates with shape (2, N)
        where the first row contains x coordinates and the second row contains y coordinates
    """
    return coords.reshape(2, -1)


def get_coordinate_path(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the boundaries flatbuffer file.

    ``.bin`` rather than ``.fbs``: the latter is the FlatBuffers *schema* extension,
    and a schema is what ``timezonefinder/flatbuf/schemas/`` holds. This is a
    serialised buffer, which says what it is through its file identifier
    (``POLYGON_FILE_IDENTIFIER``) rather than through its name.
    """
    return data_dir / "coordinates.bin"


def write_polygon_collection_flatbuffer(
    file_path: Path, polygons: list[np.ndarray]
) -> None:
    """Write a collection of polygons to a flatbuffer file using a single coordinate vector.

    Args:
        file_path: Path to save the flatbuffer file
        polygons: List of polygon coordinates as numpy arrays with shape (2, N)
                  where the first row contains x coordinates and the second row contains y coordinates

    Returns:
        None
    """
    print(f"writing {len(polygons)} polygons to binary file {file_path}")
    builder = flatbuffers.Builder(0)
    polygon_offsets = []

    # Create each polygon and store its offset
    for polygon in polygons:
        # Flatten coordinates to [x0...xN-1, y0...yN-1] format
        coords = flatten_polygon_coords(polygon)

        # Create coords vector
        PolygonStartCoordsVector(builder, len(coords))
        for coord in reversed(coords):
            builder.PrependInt32(int(coord))  # Use signed 32-bit integer
        coords_offset = builder.EndVector()

        # Create polygon
        PolygonStart(builder)
        PolygonAddCoords(builder, coords_offset)  # Use Coords for combined vector
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


def read_polygon_array_from_binary(
    poly_collection: PolygonCollection, idx: IntegerLike
) -> np.ndarray:
    """Read a polygon's coordinates from a FlatBuffers collection.

    The reference implementation of what a stored polygon means, and the slow one: it
    re-walks the vtables through the generated accessors on every call. The lookup path
    goes through :func:`derive_coord_offset_table` and :func:`read_polygon_array_at`
    instead; this is what those are checked against, by
    ``scripts.data_integrity.validate_coordinate_offset_table``.
    """
    # value checks not required as this is a private function
    # processed polygon indices are expected to be in range
    # nr_polygons = collection.PolygonsLength()
    # if idx >= nr_polygons:
    #     raise IndexError(
    #         f"Index {idx} out of bounds for collection with {nr_polygons} polygons."
    #     )
    poly = poly_collection.Polygons(idx)
    coords = poly.CoordsAsNumpy()  # flat 1D array: all x values, then all y values
    # Reshape to a (2, N) view with contiguous rows
    return reshape_to_polygon_coords(coords)


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


def derive_coord_offset_table(
    poly_collection: PolygonCollection,
    coordinate_file: BinaryIO | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Locate every polygon's coordinate vector once, as plain integers.

    Returns ``(offsets, lengths)``: for polygon *i*, the byte offset of its first
    coordinate into the underlying buffer and how many ``int32`` values follow. That is
    everything :func:`read_polygon_array_at` needs, so fetching a candidate polygon
    costs one ``np.frombuffer`` rather than a FlatBuffers vtable walk rebuilt in Python
    per lookup - which on the memory-mapped path was the dominant cost of a query.

    **Integers, not arrays, and that is the whole design.** Caching the polygon arrays
    would be shorter and just as fast, but each cached array is a live export of the
    memory map, so the cache would pin the mapping for the accessor's lifetime - in the
    mode that exists precisely so the data need not be held in memory. Two ``uint32``
    vectors pin nothing, and cost ~10 KiB for the packaged dataset.

    **Derived with whole-array arithmetic, not a loop over ``Polygons(i)``.** Not a
    micro-optimisation: the loop costs ~6 ms for the packaged boundaries, and a
    per-construction cost of that size is what would make *when* to build the table a
    decision - one paid again by every thread, since concurrent workloads are told to
    use one instance each. Against a ~390 ms construction there is nothing to weigh and
    the table is simply built eagerly: ~0.1 ms reading the words out of a buffer, ~4 ms
    reading them through a file, which is what ``coordinate_file`` buys and why.

    The walk mirrors what the generated accessors do, one step at a time over all
    polygons at once: read the polygons vector's relative offsets, turn them into table
    positions, follow each table's negative offset to its vtable, take the coords entry,
    and land on the coordinate vector's length prefix. It reads 4- and 2-byte words
    through whole-buffer views, which relies on FlatBuffers' guarantee that tables and
    vectors are aligned to ``uoffset`` and vtables to ``voffset``. Nothing here rejects a
    file that violates that - a misaligned position would read a neighbouring word and
    yield wrong coordinates silently, so what establishes it is
    ``scripts.data_integrity.validate_coordinate_offset_table``, comparing this table
    against :func:`read_polygon_array_from_binary` for every polygon where the data is
    produced and again over what the repository ships.

    :param poly_collection: A collection returned by :func:`get_polygon_collection`
    :param coordinate_file: An **unbuffered** file open on the same data. When given,
        the header words are read through it instead of out of the collection's buffer,
        so building the table does not make a memory map resident - see
        :func:`_file_word_reader`. Pass nothing when the buffer is already in memory.
    :return: ``(offsets, lengths)``, both ``uint32`` and both owning their data
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
    field_offset = read(vtable_pos + COORDS_VTABLE_SLOT, _VOFFSET).astype(np.int64)

    # The field holds a reference to the coordinate vector, whose length prefix sits
    # immediately before its data.
    reference_pos = table_pos + field_offset
    length_pos = reference_pos + read(reference_pos, _UOFFSET)

    lengths = read(length_pos, _UOFFSET).astype(np.uint32)
    offsets = (length_pos + _UOFFSET_BYTES).astype(np.uint32)
    return offsets, lengths


def read_polygon_array_at(
    buf: bytes | mmap.mmap, offset: IntegerLike, length: IntegerLike
) -> np.ndarray:
    """Read a polygon's coordinates straight out of ``buf`` at a known position.

    The fetch half of :func:`derive_coord_offset_table`. Returns the same ``(2, N)``
    zero-copy view with contiguous rows that :func:`read_polygon_array_from_binary`
    does, without consulting the FlatBuffers structure at all.

    :param buf: The buffer the offsets were derived against
    :param offset: Byte offset of the polygon's first coordinate
    :param length: Number of ``int32`` coordinate values
    """
    coords = np.frombuffer(buf, dtype="<i4", count=int(length), offset=int(offset))
    return reshape_to_polygon_coords(coords)
