"""performance critical utility functions

JIT compiled for efficiency in case `numba` is installed

TODO Numba Ahead-Of-Time Compilation:
cc = CC('precompiled_helpers', )
# Uncomment the following line to print out the compilation steps
cc.verbose = True

if __name__ == "__main__":
    cc.compile()
"""

import numpy as np

from timezonefinder.configs import (
    COORD2INT_FACTOR,
    INT2COORD_FACTOR,
    MAX_LAT_VAL,
    MAX_LNG_VAL,
    MIN_LAT_VAL,
    MIN_LNG_VAL,
    SOURCE_COORD_STEP,
    CoordLists,
    CoordPairs,
)

try:
    from numba import njit, boolean, i4, i8, u1, u4, f8
    from numba.types import Array

    using_numba = True
except ImportError:
    using_numba = False
    # replace Numba functionality with "transparent" implementations
    from timezonefinder._numba_replacements import (
        njit,
        boolean,
        Array,
        i4,
        i8,
        u1,
        u4,
        f8,
    )


# Coordinates are stored one axis at a time ([x0...xN-1, y0...yN-1]), so a (2, N)
# polygon view is C-contiguous and so is each of its rows. The signature is eager:
# an F-ordered array is rejected with a TypeError at call time rather than silently
# copied, which is what keeps the dense single-axis scan below honest.
CoordType = Array(i4, 2, "C", True, aligned=True)

# One ring's slice of the latitude block index: ``[min, max]`` per block, in ring
# order. Eager for the same reason, and read-only because the index is shared by every
# lookup against the collection that owns it and is never written after construction.
BlockRangeType = Array(i4, 2, "C", True, aligned=True)

# The packed payload of one ring, and the three per-block columns that decode it: the
# frame origins ``[base_x, base_y]``, the bit widths ``[width_x, width_y]`` and where
# each block's residuals start inside the payload. All read-only for the same reason
# ``BlockRangeType`` is - they are built once per collection and shared by every lookup
# - and all eager, so a wrong dtype or a strided slice is a TypeError at the call rather
# than a silent copy on the query path.
PayloadType = Array(u4, 1, "C", True, aligned=True)
BlockBaseType = Array(i4, 1, "C", True, aligned=True)
BlockWidthType = Array(u1, 2, "C", True, aligned=True)
BlockPayloadOffsetType = Array(u4, 1, "C", True, aligned=True)


# @cc.export('inside_polygon', 'b1(i4, i4, i4[:, :])')
@njit(boolean(i4, i4, CoordType), cache=True)
def pt_in_poly_python(x: int, y: int, coords: np.ndarray) -> bool:
    """
    Implementing the ray casting point in polygon test algorithm
    cf. https://en.wikipedia.org/wiki/Point_in_polygon#Ray_casting_algorithm
    :param x:
    :param y:
    :param coords: a polygon represented by a list containing two lists (x and y coordinates):
        [ [x1,x2,x3...], [y1,y2,y3...]]
        those lists are actually numpy arrays which are being read directly from a binary file
    :return: true if the point (x,y) lies within the polygon

    Some overflow considerations for the critical part of comparing the line segment slopes:

        (y2 - y) * (x2 - x1) <= delta_y_max * delta_x_max
        (y2 - y1) * (x2 - x) <= delta_y_max * delta_x_max
        delta_y_max * delta_x_max = 180 * 360 < 65 x10^3

    Instead of calculating with float I decided using just ints (by multiplying with 10^7). That gives us:

        delta_y_max * delta_x_max = 180x10^7 * 360x10^7
        delta_y_max * delta_x_max <= 65x10^17

    So these numbers need up to log_2(65 x10^17) ~ 63 bits to be represented! Even though values this big should never
     occur in practice (timezone polygons do not span the whole lng lat coordinate space),
     32bit accuracy hence is not safe to use here!
     pure Python automatically uses the appropriate int data type preventing overflow
     (cf. https://www.python.org/dev/peps/pep-0237/),
     but here the data types are numpy internal static data types. The data is stored as int32
     -> use int64 when comparing slopes!

    slower naive implementation:
    j = nr_coords - 1
    for i in range(nr_coords):
        if ((y_coords[i] > y) != (y_coords[j] > y)) and (
                x
                < (int64(x_coords[j]) - int64(x_coords[i]))
                * (int64(y) - int64(y_coords[i]))
                / (int64(y_coords[j]) - int64(y_coords[i]))
                + int64(x_coords[i])
        ):
            inside = not inside
        j = i
        i += 1
    """
    x_coords = coords[0]
    y_coords = coords[1]
    nr_coords = len(x_coords)
    inside = False

    # the edge from the last to the first point is checked first
    y1 = y_coords[-1]
    y_gt_y1 = y > y1
    for i in range(nr_coords):
        y2 = y_coords[i]
        y_gt_y2 = y > y2
        if y_gt_y1 ^ y_gt_y2:  # XOR
            # [p1-p2] crosses horizontal line in p
            x1 = x_coords[i - 1]
            x2 = x_coords[i]
            # only count crossings "right" of the point ( >= x)
            x_le_x1 = x <= x1
            x_le_x2 = x <= x2
            if x_le_x1 or x_le_x2:
                if x_le_x1 and x_le_x2:
                    # p1 and p2 are both to the right -> valid crossing
                    inside = not inside
                else:
                    # compare the slope of the line [p1-p2] and [p-p2]
                    # depending on the position of p2 this determines whether
                    # the polygon edge is right or left of the point
                    # to avoid expensive division the divisors (of the slope dy/dx) are brought to the other side
                    # ( dy/dx > a  ==  dy > a * dx )
                    # only one of the points is to the right
                    # NOTE: int64 precision required to prevent overflow
                    y_64 = np.int64(y)
                    y1_64 = np.int64(y1)
                    y2_64 = np.int64(y2)
                    x_64 = np.int64(x)
                    x1_64 = np.int64(x1)
                    x2_64 = np.int64(x2)
                    slope1 = (y2_64 - y_64) * (x2_64 - x1_64)
                    slope2 = (y2_64 - y1_64) * (x2_64 - x_64)
                    # NOTE: accept slope equality to also detect if p lies directly on an edge
                    if y_gt_y1:
                        if slope1 <= slope2:
                            inside = not inside
                    elif slope1 >= slope2:  # NOT y_gt_y1
                        inside = not inside

        # next point
        y1 = y2
        y_gt_y1 = y_gt_y2

    return inside


@njit(i8(PayloadType, i8, i8, i8), cache=True, inline="always")
def _residual_at(payload: np.ndarray, region: int, width: int, k: int) -> int:
    """One residual out of a block's axis region, as an unsigned value.

    ``region`` is the word offset the axis' bit stream starts at; the field is ``width``
    bits wide, starts at bit ``k * width`` of that stream and is stored least
    significant bit first. A field is at most 32 bits wide and begins at most 31 bits
    into a word, so two consecutive words always hold it -
    :data:`~timezonefinder.block_payload.PAYLOAD_PADDING_WORDS` is what makes reading
    the second one safe on a ring's last field.
    """
    if width == 0:
        return 0  # an axis the block is constant on occupies no words at all
    bit = k * width
    word = region + (bit >> 5)
    chunk = np.uint64(payload[word]) | (np.uint64(payload[word + 1]) << np.uint64(32))
    mask = (np.uint64(1) << np.uint64(width)) - np.uint64(1)
    return np.int64((chunk >> np.uint64(bit & 31)) & mask)


@njit(
    boolean(
        i4,
        i4,
        i4,
        i4,
        i8,
        i8,
        PayloadType,
        BlockRangeType,
        BlockBaseType,
        BlockWidthType,
        BlockPayloadOffsetType,
    ),
    cache=True,
)
def pt_in_poly_packed(
    x: int,
    y: int,
    nr_coords: int,
    block_size: int,
    block_start: int,
    nr_blocks: int,
    payload: np.ndarray,
    block_ranges: np.ndarray,
    block_bases: np.ndarray,
    block_widths: np.ndarray,
    block_payload_offsets: np.ndarray,
) -> bool:
    """:func:`pt_in_poly_python` with the blocks the ray cannot cross skipped, over the
    packed payload of polygon layout 3.

    Same filter, same predicate, same answer. What differs is where the coordinates come
    from: the surviving blocks are tested in their own coordinate frame, against a query
    translated into it, rather than in absolute coordinates read out of an ``int32``
    array. That translation is exact because every quantity the predicate forms is a
    difference of two coordinates - ``x2 - xq`` below *is* ``x2_absolute - x`` - so the
    frame origin is never added back per vertex and the arithmetic stays inside the
    ``int64`` bounds :func:`pt_in_poly_python` documents.

    A block stores its bridging vertex, so both endpoints of every edge it owns are
    inside it and no edge is read through two frames. That is also why this loop has no
    wrap-around case the naive kernel needs: the wrap is encoded, as
    the last block's bridging vertex being vertex 0.

    The x residuals are unpacked only on the edges that survive the latitude test, which
    is what keeps the decode off the common path: ``timezonefinder/block_payload.py``
    describes the layout, and ``docs/data_format.rst`` what it costs and buys.

    **Every array is the whole collection's**, addressed by ``block_start`` rather than
    sliced per ring, and ``payload`` is the whole coordinate buffer the per-block offsets
    address absolutely. Slicing four arrays per point-in-polygon test would cost more
    than the test does - a slice with numpy bounds measures ~200 ns - and the C backend
    would additionally have to rebuild a cffi buffer handle per call at ~0.30 us each.

    :param nr_coords: the ring's vertex count, which a packed payload's length no longer
        gives - only the last block's ragged size depends on it
    :param block_size: vertices per block, as in :func:`pt_in_poly_blocked`
    :param block_start: where this ring's blocks begin in the collection's arrays
    :param nr_blocks: how many blocks the ring owns
    :param payload: the collection's packed residuals, as 32-bit words
    :param block_ranges: the collection's ``[min, max]`` latitude per block
    :param block_bases: the collection's x frame origin per block; the y origin is
        ``block_ranges[:, 0]``, which is not stored twice
    :param block_widths: the collection's bit widths per block, x then y
    :param block_payload_offsets: where each block's residuals start in ``payload``
    """
    inside = False

    for block in range(block_start, block_start + nr_blocks):
        if y < block_ranges[block, 0] or y > block_ranges[block, 1]:
            continue
        nr_edges = np.int64(nr_coords) - (block - block_start) * block_size
        if nr_edges > block_size:
            nr_edges = block_size
        # int64 rather than the widths and offsets as they come out of their narrow
        # stored columns. numba casts them through this function's declared signature,
        # but the pure-Python fallback has no signature to cast through: there
        # ``block_widths[block, 0]`` stays ``uint8``, and NEP 50 keeps ``k * width`` in
        # ``uint8`` with it - so every residual past bit 255 wrapped, silently, and only
        # on the backend that has no accelerator beside it to disagree with. 412 of
        # 1,000 lookups did disagree before this, which is what
        # ``tests/test_acceleration_paths.py`` exists to catch.
        width_x = np.int64(block_widths[block, 0])
        width_y = np.int64(block_widths[block, 1])
        x_region = np.int64(block_payload_offsets[block])
        # the y region follows the word-aligned x one; nr_edges + 1 values per axis
        y_region = x_region + (((nr_edges + 1) * width_x + 31) >> 5)
        # int64 throughout: the query may sit far outside the frame even though the
        # residuals cannot, and it is the differences that are bounded, not the operands
        xq = np.int64(x) - np.int64(block_bases[block])
        # the y frame origin is the latitude index's own lower bound, already read above
        # to decide whether this block survives at all - so it costs nothing here and is
        # not stored a second time (see timezonefinder/block_payload.py)
        yq = np.int64(y) - np.int64(block_ranges[block, 0])

        # A residual counts source grid steps, so it is scaled back into coordinate
        # units here; everything below is then the same arithmetic on the same numbers
        # the unpacked kernel sees. See timezonefinder/block_payload.py.
        y1 = SOURCE_COORD_STEP * _residual_at(payload, y_region, width_y, 0)
        y_gt_y1 = yq > y1
        for i in range(nr_edges):
            y2 = SOURCE_COORD_STEP * _residual_at(payload, y_region, width_y, i + 1)
            y_gt_y2 = yq > y2
            if y_gt_y1 ^ y_gt_y2:  # XOR
                x1 = SOURCE_COORD_STEP * _residual_at(payload, x_region, width_x, i)
                x2 = SOURCE_COORD_STEP * _residual_at(payload, x_region, width_x, i + 1)
                x_le_x1 = xq <= x1
                x_le_x2 = xq <= x2
                if x_le_x1 or x_le_x2:
                    if x_le_x1 and x_le_x2:
                        inside = not inside
                    else:
                        # NOTE: int64 precision required to prevent overflow
                        slope1 = (y2 - yq) * (x2 - x1)
                        slope2 = (y2 - y1) * (x2 - xq)
                        if y_gt_y1:
                            if slope1 <= slope2:
                                inside = not inside
                        elif slope1 >= slope2:
                            inside = not inside

            # next edge of this block; the next block re-seeds these
            y1 = y2
            y_gt_y1 = y_gt_y2

    return inside


def packed_buffers_numba(
    payload: np.ndarray,
    block_ranges: np.ndarray,
    block_bases: np.ndarray,
    block_widths: np.ndarray,
    block_payload_offsets: np.ndarray,
) -> tuple:
    """The numba backend's counterpart to ``utils_clang.packed_buffers_clang``.

    Nothing to wrap: :func:`pt_in_poly_packed` takes the arrays themselves. It exists so
    that both backends are reached the same way - a collection wraps its arrays once and
    the call site spreads the result - rather than through a branch on every lookup.
    """
    return (payload, block_ranges, block_bases, block_widths, block_payload_offsets)


# @cc.export('int2coord', f8(i4))
@njit(f8(i4), cache=True)
def int2coord(i4: int) -> float:
    return float(i4 * INT2COORD_FACTOR)


# @cc.export('coord2int', i4(f8))
@njit(i4(f8), cache=True)
def coord2int(double: float) -> int:
    return int(double * COORD2INT_FACTOR)


@njit(cache=True)
def convert2coords(polygon_data: np.ndarray) -> CoordLists:
    # return a tuple of coordinate lists
    return [
        [int2coord(x) for x in polygon_data[0]],
        [int2coord(y) for y in polygon_data[1]],
    ]


@njit(cache=True)
def convert2coord_pairs(polygon_data: np.ndarray) -> CoordPairs:
    # return a list of coordinate tuples (x,y)
    x_coords = polygon_data[0]
    y_coords = polygon_data[1]
    nr_coords = len(x_coords)
    coodinate_list = [
        (int2coord(x_coords[i]), int2coord(y_coords[i])) for i in range(nr_coords)
    ]
    return coodinate_list


@njit(boolean(f8), cache=True)
def is_valid_lat(lat: float) -> bool:
    return MIN_LAT_VAL <= lat <= MAX_LAT_VAL


@njit(boolean(f8), cache=True)
def is_valid_lng(lng: float) -> bool:
    return MIN_LNG_VAL <= lng <= MAX_LNG_VAL
