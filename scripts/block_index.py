"""Building the latitude block index, and choosing where each ring starts.

The index itself is one ``[min, max]`` latitude pair per block of
``POLYGON_BLOCK_SIZE`` consecutive vertices, covering the edges *leaving* those
vertices. Ray casting flips parity only on an edge spanning the query latitude, so a
block whose range excludes it holds nothing that can change the answer and the kernels
skip it - see ``timezonefinder/utils_numba.py``'s ``pt_in_poly_blocked`` for why that
is exact, and ``docs/data_format.rst`` for what it is worth.

Nothing here runs at lookup time. It builds what the converter writes, and it is what
``scripts/data_integrity.py`` re-derives to check the committed binaries against.

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


def block_span_sum(y_coords: np.ndarray, block_size: int = POLYGON_BLOCK_SIZE) -> int:
    """Total latitude covered by a ring's blocks - the objective the rotation minimises.

    For a latitude drawn uniformly from the ring's own range, the expected number of
    edges scanned is ``block_size * sum(block spans) / total span``. The denominator does
    not move under rotation, so minimising this sum minimises the expected scan without
    the builder ever seeing a query.
    """
    ranges = block_latitude_ranges(y_coords, block_size)
    return int((ranges[:, 1].astype(np.int64) - ranges[:, 0].astype(np.int64)).sum())


def best_rotation_offset(
    y_coords: np.ndarray, block_size: int = POLYGON_BLOCK_SIZE
) -> int:
    """Which vertex the stored ring should start at, in ``[0, block_size)``.

    Blocks partition a ring from its first vertex, so where it starts is free to choose:
    the converter rotates what it stores and no reader can tell. Nothing downstream
    depends on it - ``canonical_ring_key`` is rotation-invariant, the bounding boxes are
    unaffected, and a hole kept as a reference follows its boundary automatically - so
    the choice costs nothing to store and nothing to read back.

    Only offsets below ``block_size`` differ: rotating by a whole block relabels the
    blocks without repartitioning anything but where the ragged final block falls.

    Measured over the real query pairs the committed fixtures produce, this objective
    scans **0.961x** the edges the unrotated order does. The two rules that suggest
    themselves both *lose* - starting at the minimum-latitude vertex costs 1.026x and
    the maximum-latitude one 1.010x - because a block's range includes its bridging
    vertex and the last block's bridge wraps to vertex 0, so putting a latitude extreme
    there stretches exactly that block. Fitting the rotation to the fixtures themselves
    would give 0.939x, and the gap is not reachable: it is fitted.

    Worth ~3.9 % of the edges a query scans, which is well under the benchmark suite's
    noise floor. It is taken because the converter is already rewriting these files, not
    because it can be demonstrated on a clock.
    """
    nr_vertices = np.asarray(y_coords).shape[0]
    if nr_vertices <= block_size:
        # one block either way, and its range is the whole ring's - nothing to choose
        return 0
    y = np.asarray(y_coords, dtype=np.int64)
    return min(
        range(block_size),
        key=lambda offset: block_span_sum(np.roll(y, -offset), block_size),
    )


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
