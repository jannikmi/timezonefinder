"""Compiling the grid-tree shortcut index: which polygons each cell has to test.

The tree is built level by level, which is what decides its shape: every root cell is
given its candidate polygons, a cell only one zone can own is answered by that zone id,
and a cell several zones can own is refined into its block of children and the question
asked again of each. A child several zones can still own keeps a candidate list, ordered
so the point-in-polygon loop does the least work.

``scripts/grid_cells.py`` holds the candidate rule itself and why it is exact;
``timezonefinder/shortcut_index.py`` holds the layout the result is written in.
"""

import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import shapely

from scripts.configs import (
    DEFAULT_INPUT_PATH,
    SOURCE_DATA_DIR,
    ShortcutMapping,
)
from scripts.grid_cells import grouped, owned_pairs, planar_polygons
from scripts.shortcut_ordering import ShortcutOrderer, spherical_area
from scripts.timezone_data import TimezoneData
from scripts.utils import time_execution
from timezonefinder.shortcut_index import (
    BLOCK_CELLS,
    CHILD_COLUMNS,
    ROOT_CELLS,
    ROOT_COLUMNS,
    build_shortcut_index,
    cell_bounds_of,
    child_cells_of,
    get_shortcut_file_path,
    write_shortcuts_binary,
)


try:
    profile  # type: ignore[used-before-def]  # noqa: B018 - probing for the name
except NameError:  # pragma: no cover - used only during profiling

    def profile(func):
        return func


@profile
def zone_areas(data: TimezoneData) -> np.ndarray:
    """Spherical area of every zone, in steradians, indexed by zone id.

    The overlap precedence key. Summed over the zone's polygons with their holes cut
    out, from the stored rings as they are: :func:`spherical_area` integrates the ring
    coordinates, so a ring that is not a valid planar polygon gets the area of its ring
    integral - for a self-intersecting ring, the difference of its lobes - and never the
    bounding box the candidate rule falls back to.
    """
    areas = np.zeros(data.nr_of_zones, dtype=np.float64)
    for boundary_id, zone_id in enumerate(data.poly_zone_ids):
        outer = data.boundaries.coords_of(boundary_id).T.astype(np.float64)
        holes = [
            hole.T.astype(np.float64) for hole in data.holes.holes_of_poly(boundary_id)
        ]
        areas[int(zone_id)] += spherical_area(shapely.Polygon(outer, holes))
    return areas


def optimise_shortcut_ordering(
    data: TimezoneData, poly_ids: list[int], zone_area: np.ndarray
) -> list[int]:
    """Zone precedence, retained where geometry restricts reordering.

    The work optimizer runs after candidate compilation, against the packed
    geometry the runtime will use. This order is kept wherever that optimizer
    cannot establish safe coverage and disjointness, so where two zones overlap it
    *is* the answer: the zone with the smaller spherical area comes first. Of two
    overlapping zones that is the one the shared area is the larger share of - the
    enclave - and because it compares one scalar per zone, every cell ranks a pair
    the same way, whatever the index's cells are.

    ``poly_ids`` arrive in set iteration order, so every key is a total order:
    equal zone areas fall back to the timezone identifier, which does not depend
    on how the data is laid out or indexed. Within a zone, polygons go fewest
    vertices first, then by polygon id, which never changes a zone answer.
    """
    if len(poly_ids) <= 1:
        return poly_ids

    nr_vertices = data.boundaries.nr_vertices
    zone_ids = data.poly_zone_ids

    zone_buckets = defaultdict(list)
    for poly_id in poly_ids:
        zone_buckets[int(zone_ids[poly_id])].append(poly_id)

    tz_names = data.all_tz_names
    zone_ids_sorted = sorted(
        zone_buckets,
        key=lambda zone_id: (float(zone_area[zone_id]), tz_names[zone_id]),
    )
    poly_ids_sorted: list[int] = []

    for zone_id in zone_ids_sorted:
        zone_poly_ids = zone_buckets[zone_id]
        zone_poly_ids.sort(key=lambda poly_id: (int(nr_vertices[poly_id]), poly_id))
        poly_ids_sorted.extend(zone_poly_ids)

    return poly_ids_sorted


def check_shortcut_sorting(
    polygon_ids: Sequence[int] | np.ndarray, all_zone_ids: np.ndarray
) -> None:
    """Only the final zone must be a complete, contiguous suffix."""
    if len(polygon_ids) == 0:
        return
    zones = all_zone_ids[polygon_ids]
    final_positions = np.flatnonzero(zones == zones[-1])
    assert np.array_equal(final_positions, np.arange(final_positions[0], len(zones))), (
        f"final zone is partially tested: {polygon_ids}"
    )


@profile
def candidates_per_cell(
    polygons: np.ndarray, cell_ids: np.ndarray, poly_zone_ids: np.ndarray
) -> list[tuple[int, np.ndarray, int]]:
    """One level's worth of candidates: ``(cell id, polygon ids, single zone or -1)``.

    Cells with no candidate at all are simply absent from the result, which is what the
    index stores them as.
    """
    cell_idx, poly_idx = owned_pairs(polygons, *cell_bounds_of(cell_ids))
    return [
        (int(cell_ids[cell]), polys, single)
        for cell, polys, single in grouped(cell_idx, poly_idx, poly_zone_ids)
    ]


@time_execution
def compile_shortcut_mapping(data: TimezoneData) -> ShortcutMapping:
    """Compile the grid tree's leaves: cell id -> zone id or candidate polygon ids.

    Two passes, because the second one's cells are the first one's answer: a root cell
    several zones can own is the only thing that refines, and nothing else in the tree
    depends on the data.

    The candidate lists carry the zone precedence order here;
    :func:`compile_shortcuts` then re-orders them against the packed geometry.
    """
    print("\n\ncomputing the timezone polygon index ('shortcuts')...")
    polygons = planar_polygons(data)
    poly_zone_ids = data.poly_zone_ids
    zone_area = zone_areas(data)

    mapping: ShortcutMapping = {}
    refine: list[int] = []
    root_cells = np.arange(ROOT_CELLS, dtype=np.int64)
    print(f"level 0: {ROOT_CELLS:,} root cells of {360 / ROOT_COLUMNS:g} degrees")
    for cell_id, _polys, single in candidates_per_cell(
        polygons, root_cells, poly_zone_ids
    ):
        if single >= 0:
            mapping[cell_id] = single
        else:
            refine.append(cell_id)

    children = (
        np.concatenate([child_cells_of(cell) for cell in refine])
        if refine
        else np.empty(0, dtype=np.int64)
    )
    print(
        f"level 1: {len(refine):,} root cells several zones can own refine into "
        f"{len(children):,} cells of {360 / CHILD_COLUMNS:g} degrees"
    )
    ambiguous = 0
    for cell_id, polys, single in candidates_per_cell(
        polygons, children, poly_zone_ids
    ):
        if single >= 0:
            mapping[cell_id] = single
            continue
        ordered = optimise_shortcut_ordering(
            data, sorted(int(p) for p in polys), zone_area
        )
        check_shortcut_sorting(ordered, poly_zone_ids)
        mapping[cell_id] = np.asarray(ordered, dtype=np.int64)
        ambiguous += 1
    print(
        f"{len(mapping):,} cells stored; {ambiguous:,} of them carry a candidate list"
    )
    return mapping


def compile_shortcut_index(
    mapping: ShortcutMapping,
    poly_zone_ids: np.ndarray,
    output_path: Path,
) -> None:
    """Lay the compiled mapping out as the binary a lookup reads, and report its shape.

    :param mapping: the tree's leaves, as :func:`compile_shortcut_mapping` compiles them
    :param poly_zone_ids: zone id per boundary polygon; the index precomputes from it
        where a candidate loop may stop
    :param output_path: the compiled data directory to write into
    """
    print("compiling the shortcut index...")
    index = build_shortcut_index(mapping, poly_zone_ids)
    output_file = get_shortcut_file_path(output_path)
    write_shortcuts_binary(index, output_file)

    zone_cells = sum(1 for v in mapping.values() if isinstance(v, (int, np.integer)))
    list_cells = len(mapping) - zone_cells
    print(f"shortcut index compiled: {len(mapping):,} stored cells")
    print(
        f"  - answered by a zone id: {zone_cells:,} "
        f"({zone_cells / len(mapping) * 100:.1f}%)"
    )
    print(
        f"  - carrying a candidate list: {list_cells:,} "
        f"({list_cells / len(mapping) * 100:.1f}%), "
        f"{index.nr_of_entries:,} of them distinct"
    )
    print(f"  - refined root cells: {index.nr_of_blocks:,}, {BLOCK_CELLS} cells each")
    print(f"  - saved to: {output_file} ({output_file.stat().st_size:,} bytes)")


def compile_shortcuts(
    output_path: Path,
    data: TimezoneData,
) -> ShortcutMapping:
    print("\ncompiling shortcuts...")
    mapping = compile_shortcut_mapping(data)

    with_lists = [
        cell
        for cell, value in mapping.items()
        if not isinstance(value, (int, np.integer))
    ]
    orderer = ShortcutOrderer(data, output_path)
    changed = 0
    try:
        for processed, cell in enumerate(with_lists, start=1):
            ids = [int(p) for p in mapping[cell]]
            ordered = orderer.order(cell, ids)
            check_shortcut_sorting(ordered, data.poly_zone_ids)
            changed += ordered != ids
            mapping[cell] = np.asarray(ordered, dtype=np.int64)
            if processed % 500 == 0:
                print(
                    f"Ordering: {processed:,}/{len(with_lists):,} cells",
                    flush=True,
                )
                sys.stdout.flush()
    finally:
        orderer.close()
    print(f"Optimized {changed:,} shortcut candidate orders")

    compile_shortcut_index(
        mapping=mapping,
        poly_zone_ids=data.poly_zone_ids,
        output_path=output_path,
    )
    return mapping


if __name__ == "__main__":
    data: TimezoneData = TimezoneData.from_path(DEFAULT_INPUT_PATH)
    # This writes the shortcut index binary (cell -> zone id OR candidate polygons)
    compile_shortcuts(output_path=SOURCE_DATA_DIR, data=data)
