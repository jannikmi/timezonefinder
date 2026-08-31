"""Shared latitude-block calculations used by the builder and data validator.

The full block-index builder remains under :mod:`scripts`. These two calculations
also have to ship because the installed ``validate-data`` command independently
re-derives the index stored in a compiled data directory.
"""

import numpy as np

from timezonefinder.configs import BLOCK_RANGE_DTYPE, POLYGON_BLOCK_SIZE


def nr_blocks_for(nr_vertices: int, block_size: int = POLYGON_BLOCK_SIZE) -> int:
    """How many blocks a ring of ``nr_vertices`` vertices is split into."""
    return -(-nr_vertices // block_size)


def block_latitude_ranges(
    y_coords: np.ndarray, block_size: int = POLYGON_BLOCK_SIZE
) -> np.ndarray:
    """Return the ``[min, max]`` latitude spanned by every vertex block."""
    y = np.asarray(y_coords, dtype=np.int64)
    nr_vertices = y.shape[0]
    nr_blocks = nr_blocks_for(nr_vertices, block_size)

    # Pad the ragged final block with a value it already contains, so that a whole-array
    # min/max over a rectangular view answers for every block including the short one.
    padded = np.full(nr_blocks * block_size, y[-1], dtype=np.int64)
    padded[:nr_vertices] = y
    blocks = padded.reshape(nr_blocks, block_size)

    # Each block owns the edge reaching the first vertex of the next one; the last
    # wraps to vertex zero.
    bridging = np.roll(blocks[:, 0], -1)
    bridging[-1] = y[0]

    ranges = np.empty((nr_blocks, 2), dtype=BLOCK_RANGE_DTYPE)
    ranges[:, 0] = np.minimum(blocks.min(axis=1), bridging)
    ranges[:, 1] = np.maximum(blocks.max(axis=1), bridging)
    return ranges
