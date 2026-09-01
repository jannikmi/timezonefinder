#!/usr/bin/env python3

"""Sweep ``POLYGON_BLOCK_SIZE`` over the packaged data and say which value is cheapest.

``POLYGON_BLOCK_SIZE`` trades two things that run opposite ways: smaller blocks bound a
ring's latitudes more tightly and so skip more of it, larger blocks mean fewer range
comparisons to decide that. Neither side is guessable, and both are *counts* - they do
not depend on the machine, the acceleration backend or what a candidate polygon costs to
fetch, which is why this reports work rather than time. ``docs/benchmarking_methodology``
explains why a count is the instrument to reach for first.

The workload is the point-in-polygon tests the committed query fixtures actually
produce, recorded off a real lookup rather than constructed: which polygons a point is
tested against is decided by the shortcut index, and a synthetic pairing of random
points with random polygons is filtered out by the bounding latitudes alone.

Each candidate size is measured against rings rotated *for that size*, since the
converter chooses the ring start per block size and comparing a re-blocked ring against
one rotated for 128 would charge the alternative for a choice it never made.

Usage::

    PYTHONPATH=. uv run python -m scripts.tune_block_size
    PYTHONPATH=. uv run python -m scripts.tune_block_size --sizes 32,64,128,256
"""

import argparse
from collections import defaultdict

import numpy as np

from scripts.block_index import (
    best_rotation_offset,
    block_latitude_ranges,
    nr_blocks_for,
)
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder
from timezonefinder.configs import (
    BLOCK_BASE_DTYPE,
    BLOCK_RANGE_DTYPE,
    BLOCK_WIDTH_DTYPE,
    POLYGON_BLOCK_SIZE,
)
from timezonefinder.polygon_array import PolygonArray

DEFAULT_SIZES = (32, 64, 128, 256, 512)
DEFAULT_NR_POINTS = 5_000

# Bytes one block costs beside the payload, all of which scale with the block count:
# the latitude index's [min, max] pair, the frame's x origin, and the two bit widths.
# There is no y origin - the index's lower bound is it (timezonefinder/block_payload.py).
BYTES_PER_BLOCK = (
    2 * BLOCK_RANGE_DTYPE.itemsize
    + BLOCK_BASE_DTYPE.itemsize
    + 2 * BLOCK_WIDTH_DTYPE.itemsize
)


def record_pip_calls(
    finder: TimezoneFinder, nr_points: int
) -> dict[tuple[int, int], list[int]]:
    """The query latitudes each ring is actually tested against.

    Keyed by ``(id(collection), ring id)`` rather than by ring id alone: ``HoleArray``
    subclasses ``PolygonArray``, so patching the base method intercepts hole tests too,
    and hole ids index a different space than boundary ids.
    """
    asked: dict[tuple[int, int], list[int]] = defaultdict(list)
    original = PolygonArray.pip

    def recording(self, poly_id, x, y):
        asked[(id(self), int(poly_id))].append(int(y))
        return original(self, poly_id, x, y)

    PolygonArray.pip = recording  # type: ignore[method-assign]
    try:
        for fixture in (ON_LAND_POINTS_FIXTURE, AMBIGUOUS_SHORTCUT_POINTS_FIXTURE):
            for lng, lat in load_benchmark_points(fixture)[:nr_points]:
                finder.timezone_at(lng=lng, lat=lat)
    finally:
        PolygonArray.pip = original  # type: ignore[method-assign]
    return dict(asked)


def scan_cost(
    ranges: np.ndarray, nr_vertices: int, latitudes: np.ndarray, block_size: int
) -> tuple[int, int]:
    """``(edges scanned, block range tests)`` for one ring over the latitudes asked of it."""
    surviving = (ranges[:, 0][None, :] <= latitudes[:, None]) & (
        ranges[:, 1][None, :] >= latitudes[:, None]
    )
    nr_blocks = len(ranges)
    # every block holds block_size edges but the last, which holds the remainder
    per_block = np.full(nr_blocks, block_size, dtype=np.int64)
    per_block[-1] = nr_vertices - (nr_blocks - 1) * block_size
    edges = int((surviving * per_block[None, :]).sum())
    return edges, nr_blocks * len(latitudes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--sizes",
        default=",".join(str(size) for size in DEFAULT_SIZES),
        help=f"comma-separated block sizes to compare (default: {DEFAULT_SIZES})",
    )
    parser.add_argument(
        "--points",
        type=int,
        default=DEFAULT_NR_POINTS,
        help=f"query points per fixture (default: {DEFAULT_NR_POINTS})",
    )
    args = parser.parse_args()
    sizes = [int(size) for size in args.sizes.split(",")]

    finder = TimezoneFinder(in_memory=True)
    collections = {
        id(finder.boundaries): finder.boundaries,
        id(finder.holes): finder.holes,
    }
    asked = record_pip_calls(finder, args.points)
    nr_calls = sum(len(v) for v in asked.values())
    print(
        f"{nr_calls:,} point-in-polygon tests over {len(asked):,} distinct rings, "
        f"from {args.points:,} points of each committed query fixture\n"
    )

    # Every ring the converter would *store*, for the index size - not only the ones
    # queried. Read `nr_vertices`, which is keyed by *storage* position exactly as the
    # coordinate accessor is, rather than going through `coords_of`: the index has one
    # entry per stored ring, and `HoleArray.coords_of` takes a hole id and resolves it
    # through `poly_ref`, so indexing it by a storage position would measure some
    # referenced boundary polygon instead of the inline ring meant (756 hole ids against
    # 27 inline rings in the packaged data). Since polygon layout 3 the accessor hands
    # out a ring's packed payload words, whose length is a byte count rather than a
    # vertex count - `nr_vertices` is where that number lives now.
    all_vertex_counts = [
        int(collection.nr_vertices[ring_id])
        for collection in (finder.boundaries, finder.holes)
        for ring_id in range(len(collection.coordinates))
    ]
    rows: list[tuple[int, int, int, int, int]] = []
    for block_size in sizes:
        edges = blocks_tested = 0
        for (collection_id, ring_id), latitudes in asked.items():
            ring = collections[collection_id].coords_of(ring_id)
            y = np.asarray(ring[1], dtype=np.int64)
            # rotated for *this* block size, as the converter would store it
            y = np.roll(y, -best_rotation_offset(y, block_size))
            ranges = block_latitude_ranges(y, block_size)
            ring_edges, ring_blocks = scan_cost(
                ranges, len(y), np.array(latitudes), block_size
            )
            edges += ring_edges
            blocks_tested += ring_blocks
        index_bytes = (
            sum(nr_blocks_for(count, block_size) for count in all_vertex_counts)
            * BYTES_PER_BLOCK
        )
        rows.append(
            (block_size, edges, blocks_tested, edges + blocks_tested, index_bytes)
        )

    baseline = next(
        (row for row in rows if row[0] == POLYGON_BLOCK_SIZE),
        None,
    )
    label = f"vs B={POLYGON_BLOCK_SIZE}"
    print(
        f"{'B':>5} {'edges scanned':>16} {'block tests':>14} {'work units':>13} "
        f"{label:>10} {'index':>12}"
    )
    for block_size, edges, blocks_tested, work, index_bytes in rows:
        ratio = f"{work / baseline[3]:.3f}x" if baseline else "-"
        print(
            f"{block_size:>5} {edges:>16,} {blocks_tested:>14,} {work:>13,} "
            f"{ratio:>10} {index_bytes / 1e6:>9.2f} MB"
        )

    print(
        "\nOne block range test is weighted as one edge test, which is conservative: a "
        "range test is two comparisons against an edge test's several plus, sometimes, "
        "two 64-bit multiplies. Read the work column as an upper bound on what a "
        "smaller block size costs, and the index column as what it costs on disk and in "
        f"every process. POLYGON_BLOCK_SIZE is currently {POLYGON_BLOCK_SIZE}; changing "
        "it changes what every polygon directory means, so it moves "
        "POLYGON_LAYOUT_VERSION and DATA_FORMAT_VERSION with it."
    )


if __name__ == "__main__":
    main()
