"""functions for compiling the h3 hexagon shortcuts"""

import itertools
from pathlib import Path
from typing import List, Set, Tuple

import h3.api.numpy_int as h3
import numpy as np

from scripts.timezone_data import TimezoneData
from scripts.helper_classes import Boundaries
from scripts.configs import (
    DEFAULT_INPUT_PATH,
    MAX_LAT,
    MAX_LNG,
    HexIdSet,
    SHORTCUT_H3_RES,
    ShortcutMapping,
)
from scripts.utils import (
    time_execution,
)
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.shortcut_utils import (
    get_shortcut_file_path,
    write_shortcuts_flatbuffers,
)
from timezonefinder.utils_numba import coord2int, int2coord, using_numba


def get_corrected_hex_boundaries(
    x_coords, y_coords, surr_n_pole, surr_s_pole
) -> Tuple["Boundaries", bool]:
    """boundaries of a hex cell used for pre-filtering the polygons
    which have to be checked with expensive point-in-polygon algorithm

    ATTENTION: a h3 polygon may cross the boundaries of the lat/lng coordinate plane (only in lng=x direction)
    -> cannot use usual geometry assumptions (polygon algorithm, min max boundary check etc.)
    -> rectify boundaries

    ATTENTION: only using coordinates converted to integers!
    NOTE: convert to regular int type to prevent overflow

    Observation: except for cells close to the poles,
        h3 hexagons can usually only span a fraction of the globe (<< 360 degree lng)
    high longitude difference observed without surrounding a pole
    -> indicates crossing the +-180 deg lng boundary
    ATTENTION: min and max of the coordinates would only  pick the points closest to the +-180 deg lng boundary,
        but not the points furthest apart!
    getting this "pre-filtering" based on boundaries right across the +-180 deg lng boundary is tricky
        -> do not exclude any longitudes for simplicity and correctness
    this is only relevant for a fraction of hex cells plus filtering will still happen based on the latitude!
    """
    xmax0, xmin0, ymax0, ymin0 = (
        int(max(x_coords)),
        int(min(x_coords)),
        int(max(y_coords)),
        int(min(y_coords)),
    )
    max_latitude = coord2int(MAX_LAT)
    max_longitude = coord2int(MAX_LNG)

    delta_y = abs(ymax0 - ymin0)
    assert delta_y < max_latitude, f"longitude difference {int2coord(delta_y)} too high"
    delta_x = abs(xmax0 - xmin0)
    x_overflow = delta_x > max_longitude

    if surr_n_pole:
        # clip to max lat
        ymax0 = max_latitude
    elif surr_s_pole:
        # clip to min lat
        ymin0 = -max_latitude

    if surr_n_pole or surr_s_pole or x_overflow:
        # search all lngs for cells close to the poles or crossing the +-180 deg lng boundary
        xmin0 = -max_longitude
        xmax0 = max_longitude

    return Boundaries(xmax0, xmin0, ymax0, ymin0), x_overflow


def optimise_shortcut_ordering(data: TimezoneData, poly_ids: List[int]) -> List[int]:
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

    poly_sizes = [data.polygon_lengths[i] for i in poly_ids]
    zone_ids = [data.poly_zone_ids[i] for i in poly_ids]
    zone_ids_unique = list(set(zone_ids))
    zipped = list(zip(poly_ids, zone_ids, poly_sizes))
    zone2size = {
        i: sum(map(lambda e: e[2], filter(lambda e: e[1] == i, zipped)))
        for i in zone_ids_unique
    }
    zone_ids_sorted = sorted(zone_ids_unique, key=lambda x: zone2size[x])
    poly_ids_sorted = []
    for zone_id in zone_ids_sorted:
        # smaller polygons can be ruled out faster -> smaller polygons should come first
        zone_entries = filter(lambda e: e[1] == zone_id, zipped)
        zone_entries_sorted = sorted(zone_entries, key=lambda x: x[2])
        zone_poly_ids_sorted, _, _ = zip(*zone_entries_sorted)
        poly_ids_sorted += list(zone_poly_ids_sorted)
    return poly_ids_sorted


def has_coherent_sequences(lst: List[int]) -> bool:
    """
    :return: True if equal entries in the list are not separated by entries of other values
    """
    if len(lst) <= 1:
        return True
    encountered = set()
    # at least 2 entries
    lst_iter = iter(lst)
    prev = next(lst_iter)
    for e in lst:
        if e in encountered:
            # the entry appeared earlier already
            return False
        if e != prev:
            encountered.add(prev)
            prev = e

    return True


def check_shortcut_sorting(polygon_ids: np.ndarray, all_zone_ids: np.ndarray):
    # the polygons in the shortcuts are sorted by their zone id (and the size of their polygons)
    if len(polygon_ids) == 1:
        # single polygon in the shortcut, no need to check
        return
    zone_ids = all_zone_ids[polygon_ids]
    assert has_coherent_sequences(zone_ids), (
        f"shortcut polygon ids {polygon_ids} do not have coherent sequences of zone ids: {zone_ids}"
    )


def process_single_hex(hex_id: int, data: TimezoneData) -> Tuple[int, List[int]]:
    """
    Process a single hex cell to find its polygon shortcuts.

    Args:
        hex_id: The H3 hexagon ID to process
        data: The timezone data (shared read-only resource)

    Returns:
        Tuple of (hex_id, list of optimized polygon IDs)
    """
    # IMPORTANT: cache hexagons to avoid recomputing them
    cell = data.get_hex(hex_id)
    polys = list(cell.polys_in_cell)
    polys_optimised = optimise_shortcut_ordering(data, polys)
    check_shortcut_sorting(polys_optimised, data.poly_zone_ids)
    return hex_id, polys_optimised


def compile_h3_map(
    data: TimezoneData,
    candidates: Set,
) -> ShortcutMapping:
    """
    operate on one hex resolution
    also store results separately to divide the output data files

    Args:
        data: TimezoneData instance
        candidates: Set of hex IDs to process
        use_parallel: Whether to use parallel processing (default: True)
        max_workers: Maximum number of worker threads (default: optimal based on benchmarks)
    """

    if not using_numba:
        print(
            "NOTE: if the shortcut compilation is slow, consider installing Numba for JIT compilation\n"
        )

    mapping: ShortcutMapping = {}
    total_candidates = len(candidates)

    processed = 0
    for hex_id in candidates:
        hex_id, polys_optimised = process_single_hex(hex_id, data)
        mapping[hex_id] = polys_optimised
        processed += 1
        print(
            f"\r{processed:,} processed\t{total_candidates - processed:,} remaining\t",
            end="",
            flush=True,
        )

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
def compile_shortcut_mapping(data: TimezoneData) -> ShortcutMapping:
    """compiles h3 hexagon shortcut mapping

    Args:
        data: TimezoneData instance containing polygon and timezone information

    Returns:
        mapping from hexagon id to list of polygon ids

    cf. https://eng.uber.com/h3/

    NOTE: benchmarking parallel execution revealed no significant speedup (baseline: 13s for 40k hexes)
        -> probably because of the fast per-hex processing time and the overhead of managing threads
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


def compile_shortcuts(
    output_path: Path,
    data: TimezoneData,
) -> ShortcutMapping:
    print("\ncompiling shortcuts...")
    shortcuts: ShortcutMapping = compile_shortcut_mapping(data)
    output_file: Path = get_shortcut_file_path(output_path)
    write_shortcuts_flatbuffers(shortcuts, output_file)
    return shortcuts


if __name__ == "__main__":
    data: TimezoneData = TimezoneData.from_path(DEFAULT_INPUT_PATH)
    compile_shortcuts(output_path=DEFAULT_DATA_DIR, data=data)
