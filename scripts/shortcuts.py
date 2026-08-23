"""functions for compiling the h3 hexagon shortcuts"""

import itertools
import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

import h3.api.numpy_int as h3
import numpy as np

from scripts.timezone_data import TimezoneData
from scripts.configs import (
    DEFAULT_INPUT_PATH,
    SOURCE_DATA_DIR,
    HexIdSet,
    SHORTCUT_H3_RES,
    ShortcutMapping,
)
from scripts.utils import (
    time_execution,
)
from timezonefinder.shortcut_index import (
    build_shortcut_index,
    get_shortcut_file_path,
    write_shortcuts_binary,
)
from timezonefinder.utils_numba import using_numba


try:
    profile  # type: ignore[used-before-def]
except NameError:  # pragma: no cover - used only during profiling

    def profile(func):
        return func


@profile
def optimise_shortcut_ordering(data: TimezoneData, poly_ids: list[int]) -> list[int]:
    """optimises the order of polygon ids for faster timezone checks

    observation: as soon as just polygons of one zone are left, this zone can be returned
    -> try to "rule out" zones fast
    polygons from different zones should not get mixed up (group by zone id)
    point in polygon test is faster with smaller polygons (fewer coordinates)
    -> polygons of zones with fewer coordinates should come first!
    -> sort the list of polygon ids in each shortcut after the size of the corresponding polygons
    """
    if len(poly_ids) <= 1:
        return poly_ids

    polygon_lengths = data.polygon_lengths
    zone_ids = data.poly_zone_ids

    zone_buckets = defaultdict(list)
    zone_sizes: defaultdict[int, int] = defaultdict(int)

    for poly_id in poly_ids:
        zone_id = int(zone_ids[poly_id])
        zone_buckets[zone_id].append(poly_id)
        zone_sizes[zone_id] += int(polygon_lengths[poly_id])

    zone_ids_sorted = sorted(zone_buckets, key=zone_sizes.__getitem__)
    get_length = polygon_lengths.__getitem__
    poly_ids_sorted: list[int] = []

    for zone_id in zone_ids_sorted:
        zone_poly_ids = zone_buckets[zone_id]
        zone_poly_ids.sort(key=get_length)
        poly_ids_sorted.extend(zone_poly_ids)

    return poly_ids_sorted


def has_coherent_sequences(lst: Sequence[int] | np.ndarray) -> bool:
    """
    :return: True if equal entries in the list are not separated by entries of other values
    """
    if len(lst) <= 1:
        return True
    encountered = set()
    # at least 2 entries, so lst[0] exists; comparing it against itself on the
    # first iteration is a deliberate no-op.
    prev = lst[0]
    for e in lst:
        if e in encountered:
            # the entry appeared earlier already
            return False
        if e != prev:
            encountered.add(prev)
            prev = e

    return True


def check_shortcut_sorting(
    polygon_ids: Sequence[int] | np.ndarray, all_zone_ids: np.ndarray
) -> None:
    # the polygons in the shortcuts are sorted by their zone id (and the size of their polygons)
    if len(polygon_ids) == 1:
        # single polygon in the shortcut, no need to check
        return
    zone_ids = all_zone_ids[polygon_ids]
    assert has_coherent_sequences(zone_ids), (
        f"shortcut polygon ids {polygon_ids} do not have coherent sequences of zone ids: {zone_ids}"
    )


@profile
def process_single_hex(hex_id: int, data: TimezoneData) -> list[int]:
    """
    Process a single hex cell to find its polygon shortcuts.

    Args:
        hex_id: The H3 hexagon ID to process
        data: The timezone data (shared read-only resource)

    Returns:
        The optimized polygon IDs for this hex cell
    """
    # IMPORTANT: cache hexagons to avoid recomputing them
    cell = data.get_hex(hex_id)
    polys = list(cell.polys_in_cell)
    polys_optimised = optimise_shortcut_ordering(data, polys)
    check_shortcut_sorting(polys_optimised, data.poly_zone_ids)
    return polys_optimised


@profile
def compile_h3_map(data: TimezoneData, candidates: set[int]) -> ShortcutMapping:
    """
    operate on one hex resolution
    also store results separately to divide the output data files

    Args:
        data: TimezoneData instance
        candidates: Set of hex IDs to process
    """
    if not using_numba:
        print(
            "NOTE: if the shortcut compilation is slow, consider installing Numba for JIT compilation\n"
        )

    mapping: ShortcutMapping = {}
    total_candidates = len(candidates)

    progress_interval = 50

    for processed, hex_id in enumerate(candidates, start=1):
        polys_optimised = process_single_hex(hex_id, data)
        mapping[hex_id] = polys_optimised

        if processed % progress_interval == 0 or processed == total_candidates:
            remaining = total_candidates - processed
            sys.stdout.write(f"\r{processed:,} processed\t{remaining:,} remaining\t")
            sys.stdout.flush()

    print()  # New line after progress reporting
    return mapping


def all_res_candidates(res: int) -> HexIdSet:
    print(f"compiling hex candidates for resolution {res}.")
    if res == 0:
        return set(h3.get_res0_cells())
    parent_res_candidates = all_res_candidates(res - 1)
    child_iter = (h3.cell_to_children(h) for h in parent_res_candidates)
    return set(itertools.chain.from_iterable(child_iter))


@time_execution
def compile_shortcut_mapping(
    data: TimezoneData,
) -> ShortcutMapping:
    """compiles the h3 hexagon shortcut mapping

    Args:
        data: TimezoneData instance containing polygon and timezone information

    Returns:
        mapping from hexagon id to list of polygon ids

    cf. https://eng.uber.com/h3/

    NOTE: the compilation is sequential. Benchmarking parallel execution revealed no
        significant speedup (baseline: 13s for 40k hexes) -> probably because of the fast
        per-hex processing time and the overhead of managing threads
    """
    print("\n\ncomputing timezone polygon index ('shortcuts')...")

    candidates = all_res_candidates(SHORTCUT_H3_RES)
    print(
        f"reached desired resolution {SHORTCUT_H3_RES}.\n"
        "storing mapping to timezone polygons for every hexagon candidate at this resolution (-> 'full coverage')"
    )
    shortcuts = compile_h3_map(data, candidates=candidates)
    # Shortcut statistics will be printed in the reporting module
    return shortcuts


def compute_unique_shortcut_mapping(
    shortcuts: ShortcutMapping, zone_ids: np.ndarray
) -> dict[int, int]:
    """Derive a mapping from hex id to a unique zone id when present."""

    unique_map: dict[int, int] = {}
    for hex_id, polygon_ids in shortcuts.items():
        if len(polygon_ids) == 0:
            continue
        polygon_zone_ids = zone_ids[np.asarray(polygon_ids, dtype=np.int64)]
        first_zone = int(polygon_zone_ids[0])
        if np.all(polygon_zone_ids == first_zone):
            unique_map[hex_id] = first_zone

    return unique_map


def build_hybrid_index_from_separate_indices(
    shortcuts: ShortcutMapping, unique_shortcuts: dict[int, int]
) -> dict[int, int | list[int]]:
    """Build hybrid index from separate shortcuts and unique_shortcuts indices.

    This algorithm combines the two legacy data structures into a single hybrid
    structure that replaces both, optimizing storage and lookup performance.

    ALGORITHM EXPLANATION:
    The legacy system uses two separate data structures:
    1. `shortcuts`: Maps hex_id -> [polygon_ids] for ALL hex cells
    2. `unique_shortcuts`: Maps hex_id -> zone_id for hex cells where all polygons belong to same zone

    The hybrid system combines these into one structure:
    - If a hex is in unique_shortcuts, store just the zone_id (saves space & lookup time)
    - Otherwise, store the polygon_ids list (allows proper ambiguity resolution)

    This optimization reduces storage (single zone_id vs list of polygon_ids) and
    improves lookup performance (direct zone lookup vs polygon intersection tests)
    for the common case where all polygons in a hex belong to the same timezone.

    Args:
        shortcuts: Dictionary mapping hex IDs to lists of polygon IDs
        unique_shortcuts: Dictionary mapping hex IDs to single zone IDs

    Returns:
        Dictionary mapping hex IDs to either:
        - int: zone ID (for unique cases where all polygons share same zone)
        - list[int]: polygon IDs (for ambiguous cases requiring polygon tests)
    """
    hybrid_mapping: dict[int, int | list[int]] = {}

    # First, add all entries from shortcuts (polygon lists)
    # This ensures we have entries for all hex cells with any polygons
    for hex_id, polygon_ids in shortcuts.items():
        hybrid_mapping[hex_id] = polygon_ids

    # Then, override with unique shortcuts where applicable
    # This replaces polygon lists with single zone IDs when all polygons
    # in the hex belong to the same timezone
    for hex_id, zone_id in unique_shortcuts.items():
        hybrid_mapping[hex_id] = zone_id

    return hybrid_mapping


def compile_shortcut_index(
    shortcuts: ShortcutMapping,
    unique_shortcuts: dict[int, int],
    poly_zone_ids: np.ndarray,
    output_path: Path,
) -> dict[int, int | list[int]]:
    """Compile the shortcut index combining shortcuts and unique_shortcuts, and write it.

    Args:
        shortcuts: Dictionary mapping hex IDs to lists of polygon IDs
        unique_shortcuts: Dictionary mapping hex IDs to single zone IDs
        poly_zone_ids: zone id per boundary polygon; the index precomputes from it where
            a candidate loop may stop
        output_path: Path where to save the shortcut index binary file

    Returns:
        The compiled hybrid shortcuts mapping
    """
    print("compiling the shortcut index...")

    # Build the hybrid index using our algorithm
    hybrid_mapping = build_hybrid_index_from_separate_indices(
        shortcuts, unique_shortcuts
    )

    output_file = get_shortcut_file_path(output_path)
    write_shortcuts_binary(
        build_shortcut_index(hybrid_mapping, poly_zone_ids), output_file
    )

    # Report statistics
    zone_entries = sum(1 for v in hybrid_mapping.values() if isinstance(v, int))
    polygon_entries = sum(1 for v in hybrid_mapping.values() if isinstance(v, list))

    print(f"shortcut index compiled: {len(hybrid_mapping)} total entries")
    print(
        f"  - zone entries: {zone_entries} ({zone_entries / len(hybrid_mapping) * 100:.1f}%)"
    )
    print(
        f"  - polygon entries: {polygon_entries} ({polygon_entries / len(hybrid_mapping) * 100:.1f}%)"
    )
    print(f"  - saved to: {output_file}")

    return hybrid_mapping


def compile_shortcuts(
    output_path: Path,
    data: TimezoneData,
) -> ShortcutMapping:
    print("\ncompiling shortcuts...")
    shortcuts: ShortcutMapping = compile_shortcut_mapping(data)

    # Compute unique shortcuts mapping (needed for hybrid shortcuts)
    unique_mapping = compute_unique_shortcut_mapping(shortcuts, data.poly_zone_ids)

    # Compile and write hybrid shortcuts binary file (replaces legacy formats)
    compile_shortcut_index(
        shortcuts=shortcuts,
        unique_shortcuts=unique_mapping,
        poly_zone_ids=data.poly_zone_ids,
        output_path=output_path,
    )

    return shortcuts


if __name__ == "__main__":
    data: TimezoneData = TimezoneData.from_path(DEFAULT_INPUT_PATH)
    # This writes the shortcut index binary (hex cell -> zone id OR candidate polygons)
    compile_shortcuts(output_path=SOURCE_DATA_DIR, data=data)
