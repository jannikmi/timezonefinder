"""Building the latitude block index, and choosing where each ring starts.

The index itself is one ``[min, max]`` latitude pair per block of
``POLYGON_BLOCK_SIZE`` consecutive vertices, covering the edges *leaving* those
vertices. Ray casting flips parity only on an edge spanning the query latitude, so a
block whose range excludes it holds nothing that can change the answer and the kernels
skip it - see ``timezonefinder/utils_numba.py``'s ``pt_in_poly_blocked`` for why that
is exact, and ``docs/data_format.rst`` for what it is worth.

Nothing here runs at lookup time. It builds what the converter writes, and it is what
``scripts/data_integrity.py`` re-derives to check the packaged binaries against.

**A block's range includes its bridging vertex**, the first vertex of the next block,
because the block owns the edge reaching it. On the last block that vertex is vertex 0.
That detail is what makes every edge lie inside exactly one block's range - and it is
also why the two intuitive ring rotations lose (see :func:`best_rotation_offset`).
"""

import numpy as np

from timezonefinder.configs import (
    BLOCK_OFFSET_DTYPE,
    BLOCK_RANGE_DTYPE,
    POLYGON_BLOCK_SIZE,
)


def nr_blocks_for(nr_vertices: int, block_size: int = POLYGON_BLOCK_SIZE) -> int:
    """How many blocks a ring of ``nr_vertices`` vertices is split into."""
    return -(-nr_vertices // block_size)


def block_latitude_ranges(
    y_coords: np.ndarray, block_size: int = POLYGON_BLOCK_SIZE
) -> np.ndarray:
    """The ``[min, max]`` latitude each block of ``y_coords`` spans, as ``(nr_blocks, 2)``.

    ``y_coords`` is one ring's latitude row, in stored order. The returned ranges are
    what the packaged index holds and what the kernels compare a query latitude against.

    :param y_coords: the ring's latitudes, scaled ``int32`` as stored
    :param block_size: vertices per block
    :return: ``(nr_blocks, 2)`` array of ``[min, max]``, in :data:`BLOCK_RANGE_DTYPE`
    """
    y = np.asarray(y_coords, dtype=np.int64)
    nr_vertices = y.shape[0]
    nr_blocks = nr_blocks_for(nr_vertices, block_size)

    # Pad the ragged final block with a value it already contains, so that a whole-array
    # min/max over a rectangular view answers for every block including the short one.
    padded = np.full(nr_blocks * block_size, y[-1], dtype=np.int64)
    padded[:nr_vertices] = y
    blocks = padded.reshape(nr_blocks, block_size)

    # each block also reaches the first vertex of the next one; the last wraps to 0
    bridging = np.roll(blocks[:, 0], -1)
    bridging[-1] = y[0]

    ranges = np.empty((nr_blocks, 2), dtype=BLOCK_RANGE_DTYPE)
    ranges[:, 0] = np.minimum(blocks.min(axis=1), bridging)
    ranges[:, 1] = np.maximum(blocks.max(axis=1), bridging)
    return ranges


def block_scan_cost(y_coords: np.ndarray, block_size: int = POLYGON_BLOCK_SIZE) -> int:
    """What a rotation costs: expected edges scanned, up to a constant factor.

    For a query latitude drawn uniformly from the ring's own range - which is the range
    a bounding-box check has already narrowed it to - the expected number of edges
    scanned is ``sum(size_b * span_b) / total_span``. The denominator does not move under
    rotation, so minimising the numerator minimises the expected scan without the builder
    ever seeing a query.

    **Every block is weighted by how many edges it actually holds**, which is the whole
    difference between this and summing the spans. The final block is ragged: for a ring
    of 129 vertices at 128 per block it holds one edge against the first block's 128, and
    weighting the two equally would trade a large real cost for a tiny one. Rings whose
    vertex count the block size does not divide are the common case, so this is not an
    edge case - it is most of them.
    """
    ranges = block_latitude_ranges(y_coords, block_size)
    spans = ranges[:, 1].astype(np.int64) - ranges[:, 0].astype(np.int64)
    return int((block_edge_counts(len(y_coords), block_size) * spans).sum())


def block_edge_counts(
    nr_vertices: int, block_size: int = POLYGON_BLOCK_SIZE
) -> np.ndarray:
    """How many edges each block owns - ``block_size`` each, and the remainder last."""
    nr_blocks = nr_blocks_for(nr_vertices, block_size)
    counts = np.full(nr_blocks, block_size, dtype=np.int64)
    counts[-1] = nr_vertices - (nr_blocks - 1) * block_size
    return counts


def _every_window_span(y: np.ndarray, width: int) -> np.ndarray:
    """``max - min`` over the cyclic window of ``width`` vertices starting at each index."""
    extended = np.concatenate([y, np.resize(y, width - 1)])
    windows = np.lib.stride_tricks.sliding_window_view(extended, width)
    return windows.max(axis=1) - windows.min(axis=1)


def best_rotation_offset(
    y_coords: np.ndarray,
    block_size: int = POLYGON_BLOCK_SIZE,
    chunk: int = 2048,
) -> int:
    """Which vertex the stored ring should start at, in ``[0, nr_vertices)``.

    Blocks partition a ring from its first vertex, so where it starts is free to choose:
    the converter rotates what it stores and no reader can tell. Nothing downstream
    depends on it - ``canonical_ring_key`` is rotation-invariant, the bounding boxes are
    unaffected, and a hole kept as a reference follows its boundary automatically - so
    the choice costs nothing to store and nothing to read back.

    **All ``n`` rotations are searched, not one block of them.** Rotating by a whole
    block only relabels the blocks when ``block_size`` divides the vertex count;
    otherwise it also moves the ragged final block, which repartitions the ring. A search
    bounded at ``block_size`` therefore misses the minimum for most rings - measured at
    392 of the 602 the committed fixtures reach.

    Done directly this would be O(n^2). It is O(n * nr_blocks) instead: the span of every
    window is computed once for all start positions, and each rotation is then a gather
    and a sum over ``nr_blocks`` of them, chunked so the index array stays small. ~12 s
    for the whole collection against ~2 s for the bounded search, in a converter that
    takes about a minute.

    Measured over the real query pairs the committed fixtures produce, the two changes
    together - weighting each block by its edge count, and searching every rotation -
    scan **0.941x** the edges of the bounded search over unweighted spans. Weighting
    alone accounts for 0.984x of that and costs nothing; the wider search is what needs
    the machinery above. The two rules that suggest themselves both *lose* - starting at
    the minimum-latitude vertex costs 1.026x and the maximum-latitude one 1.010x -
    because a block's range includes its bridging vertex and the last block's bridge
    wraps to vertex 0, so putting a latitude extreme there stretches exactly that block.

    Worth a few percent of the edges a query scans, which is well under the benchmark
    suite's noise floor. It is taken because the converter is already rewriting these
    files, not because it can be demonstrated on a clock.

    Neither half is a candidate for simplification, and the weighting is the half that
    cannot go: dropping it while keeping the wider search measures **1.001x** - worse
    than the bounded-and-unweighted version it started from, because a search widened
    against a wrong objective just finds a better answer to the wrong question. Dropping
    the wider search instead keeps 0.984x of the 0.941x. The refusal is recorded in
    ``contributing/improvements/decisions/geometry-data-format-and-validation-decisions.md``.
    """
    y = np.asarray(y_coords, dtype=np.int64)
    nr_vertices = y.shape[0]
    if nr_vertices <= block_size:
        # one block either way, and its range is the whole ring's - nothing to choose
        return 0

    counts = block_edge_counts(nr_vertices, block_size)
    nr_blocks = len(counts)
    full_span = _every_window_span(y, block_size + 1)
    last_span = (
        full_span
        if counts[-1] == block_size
        else _every_window_span(y, int(counts[-1]) + 1)
    )

    # where each block starts, relative to the rotation, and where the ragged one does
    offsets = np.arange(nr_blocks - 1) * block_size
    last_start = (np.arange(nr_vertices) + (nr_blocks - 1) * block_size) % nr_vertices

    best_cost: int | None = None
    best_offset = 0
    for lo in range(0, nr_vertices, chunk):
        rotations = np.arange(lo, min(lo + chunk, nr_vertices))
        starts = (rotations[:, None] + offsets[None, :]) % nr_vertices
        cost = (
            block_size * full_span[starts].sum(axis=1)
            + counts[-1] * last_span[last_start[rotations]]
        )
        winner = int(cost.argmin())
        if best_cost is None or int(cost[winner]) < best_cost:
            best_cost = int(cost[winner])
            best_offset = int(rotations[winner])
    return best_offset


def rotate_ring(ring: np.ndarray, offset: int) -> np.ndarray:
    """The same ring, stored from vertex ``offset`` instead of vertex 0."""
    if offset == 0:
        return ring
    return np.ascontiguousarray(np.roll(ring, -offset, axis=1))


def rotate_rings(
    rings: list[np.ndarray], block_size: int = POLYGON_BLOCK_SIZE
) -> list[np.ndarray]:
    """Every ring rotated to the start index its block index is cheapest at."""
    return [
        rotate_ring(ring, best_rotation_offset(ring[1], block_size)) for ring in rings
    ]


def build_block_index(
    rings: list[np.ndarray], block_size: int = POLYGON_BLOCK_SIZE
) -> tuple[np.ndarray, np.ndarray]:
    """The block index of a whole collection: one flat range array plus its offsets.

    :param rings: the rings *as they will be stored*, i.e. already rotated
    :param block_size: vertices per block
    :return: ``(ranges, offsets)`` - ``ranges`` is ``(total_blocks, 2)`` in
        :data:`BLOCK_RANGE_DTYPE`, ``offsets`` is ``len(rings) + 1`` entries of
        :data:`BLOCK_OFFSET_DTYPE` such that ring *i* owns
        ``ranges[offsets[i]:offsets[i + 1]]``
    :raises ValueError: if the collection holds more blocks than the offset column can
        address
    """
    per_ring = [block_latitude_ranges(ring[1], block_size) for ring in rings]
    counts = [len(ranges) for ranges in per_ring]
    total_blocks = sum(counts)

    ceiling = int(np.iinfo(BLOCK_OFFSET_DTYPE).max)
    if total_blocks > ceiling:
        raise ValueError(
            f"the collection needs {total_blocks:,} block index entries, but the offset "
            f"column is {BLOCK_OFFSET_DTYPE.name} and addresses at most {ceiling:,}. "
            f"Widen BLOCK_OFFSET_DTYPE (timezonefinder/configs.py) to uint64, and bump "
            f"POLYGON_LAYOUT_VERSION and DATA_FORMAT_VERSION with it - the widened "
            f"column changes what every polygon directory holds."
        )

    offsets = np.zeros(len(rings) + 1, dtype=BLOCK_OFFSET_DTYPE)
    offsets[1:] = np.cumsum(counts, dtype=np.int64)
    ranges = (
        np.concatenate(per_ring)
        if per_ring
        else np.empty((0, 2), dtype=BLOCK_RANGE_DTYPE)
    )
    return np.ascontiguousarray(ranges, dtype=BLOCK_RANGE_DTYPE), offsets
