from typing import Optional

from scripts.configs import DEBUG, MAX_LAT, MAX_LNG, HexIdSet, PolyIdSet, ZoneIdSet
from scripts.file_converter import (
    Boundaries,
    ShortcutMapping,
    TimezoneData,
)
from scripts.utils import check_shortcut_sorting, time_execution, to_numpy_polygon_repr
from scripts.utils_numba import any_pt_in_poly, fully_contained_in_hole
from timezonefinder.configs import SHORTCUT_H3_RES
from timezonefinder.utils_numba import coord2int, int2coord


import h3.api.numpy_int as h3
import numpy as np


import functools
import itertools
from dataclasses import dataclass
from typing import List, Set, Tuple


# lower the shortcut resolution for debugging
SHORTCUT_H3_RES = 0 if DEBUG else SHORTCUT_H3_RES


def _holes_in_poly(data: TimezoneData, poly_nr):
    for i, nr in enumerate(data.polynrs_of_holes):
        if nr == poly_nr:
            yield data.holes[i]


def lies_in_h3_cell(h: int, lng: float, lat: float) -> bool:
    res = h3.get_resolution(h)
    return h3.latlng_to_cell(lat, lng, res) == h


def surrounds_north_pole(hex_id: int) -> bool:
    """Check if a hex cell surrounds the north pole."""
    return lies_in_h3_cell(hex_id, lng=0.0, lat=MAX_LAT)


def surrounds_south_pole(hex_id: int) -> bool:
    """Check if a hex cell surrounds the south pole."""
    return lies_in_h3_cell(hex_id, lng=0.0, lat=-MAX_LAT)


def any_pt_in_cell(data: TimezoneData, h: int, poly_nr: int) -> bool:
    def pt_in_cell(pt: np.ndarray) -> bool:
        # ATTENTION: must first convert integers back to coord floats!
        lng = int2coord(pt[0])
        lat = int2coord(pt[1])
        return lies_in_h3_cell(h, lng, lat)

    poly = data.polygons[poly_nr]
    return any(map(pt_in_cell, poly.T))


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


@dataclass
class Hex:
    id: int
    res: int
    coords: np.ndarray
    bounds: Boundaries
    x_overflow: bool
    surr_n_pole: bool
    surr_s_pole: bool
    data: TimezoneData
    _poly_candidates: Optional[PolyIdSet] = None
    _polys_in_cell: Optional[PolyIdSet] = None
    _zones_in_cell: Optional[ZoneIdSet] = None

    @classmethod
    def from_id(cls, id: int, data: TimezoneData):
        res = h3.get_resolution(id)
        coord_pairs = h3.cell_to_boundary(id)
        # ATTENTION: (lat, lng)! pairs
        coords = to_numpy_polygon_repr(coord_pairs, flipped=True)
        x_coords, y_coords = coords[0], coords[1]
        surr_n_pole = surrounds_north_pole(id)
        surr_s_pole = surrounds_south_pole(id)
        bounds, x_overflow = get_corrected_hex_boundaries(
            x_coords, y_coords, surr_n_pole, surr_s_pole
        )
        return cls(id, res, coords, bounds, x_overflow, surr_n_pole, surr_s_pole, data)

    @property
    def is_special(self) -> bool:
        return self.x_overflow or self.surr_n_pole or self.surr_s_pole

    def _init_candidates(self):
        """
        here one might be tempted to only consider the actual detected zones of the parent cell
        to narrow down choice and speed up the computation up.
        however, the child hexagon cells protrude from the parent (cf. https://h3geo.org/docs/highlights/indexing)
            and hence the candidate zones are different
        solution: take the "true" parents not just the single parent
        note: do not just take the true included polygons,
            but only the candidates to avoid expensive point-in-polygon computations

        Note: also the root level hexagon cells are too large to easily check for polygon in hex inclusion
        (might overlap without included vertices but just intersecting edges!).
        Taking just the smaller set of candidates is still valid (no point in polygon check)
        """
        if self._poly_candidates is not None:
            # avoid overwriting initialised values
            return
        if self.res == 0:
            # at the highest level all polygons should be tested
            self._poly_candidates = set(range(self.data.nr_of_polygons))
            return

        candidates: HexIdSet = set()
        for parent_id in self.true_parents:
            parent_hex = get_hex(parent_id, self.data)
            parent_polys = parent_hex.poly_candidates
            candidates.update(parent_polys)

        self._poly_candidates = candidates

    def is_poly_candidate(self, poly_id: int) -> bool:
        cell_bounds = self.bounds
        poly_bounds = self.data.poly_boundaries[poly_id]
        overlapping = cell_bounds.overlaps(poly_bounds)
        return overlapping

    @property
    def poly_candidates(self) -> Set[int]:
        self._init_candidates()
        real_candidates = set(filter(self.is_poly_candidate, self._poly_candidates))
        self._poly_candidates = real_candidates
        return self._poly_candidates

    def lies_in_cell(self, poly_nr: int) -> bool:
        hex_coords = self.coords
        poly_coords = self.data.polygons[poly_nr]
        overlap = any_pt_in_poly(hex_coords, poly_coords)
        if not overlap:
            # also test the inverse: if any point of the polygon lies inside the hex cell
            # ATTENTION: some hex cells cannot be used as polygons in regular point in polygon algorithm!
            overlap = any_pt_in_cell(self.data, self.id, poly_nr)

        # ATTENTION: in general polygons can overlap without having included vertices
        # usually the polygon edges would need to be checked for intersections
        # assumption: the polygons and cells have a similar size
        # and are small enough to just check vertex inclusion
        # valid simplification

        # account for holes in polygon
        # only check if found overlapping
        if overlap:
            for hole in _holes_in_poly(self.data, poly_nr):
                # check all hex point within hole
                if fully_contained_in_hole(hex_coords, hole):
                    return False
        return overlap

    @property
    def polys_in_cell(self) -> Set[int]:
        if self._polys_in_cell is None:
            # lazy evaluation, caching
            self._polys_in_cell = set(filter(self.lies_in_cell, self.poly_candidates))
        return self._polys_in_cell

    @property
    def zones_in_cell(self) -> Set[int]:
        if self._zones_in_cell is None:
            # lazy evaluation, caching
            self._zones_in_cell = set(
                map(lambda p: self.data.poly_zone_ids[p], self.polys_in_cell)
            )
        return self._zones_in_cell

    @property
    def true_parents(self) -> HexIdSet:
        """
        hexagons do not cleanly subdivide into seven finer hexagons.
        the child hexagon cells protrude from the parent (cf. https://h3geo.org/docs/highlights/indexing)
            and hence a cell does not have a single, but actually up to 2 "true" parents

        returns: the hex ids of all parent cells which any of the cell points belong
        """
        if self.res == 0:
            raise ValueError("not defined for resolution 0")
        lower_res = self.res - 1
        # NOTE: (lat,lng) pairs!
        coord_pairs = h3.cell_to_boundary(self.id)
        return {h3.latlng_to_cell(pt[0], pt[1], lower_res) for pt in coord_pairs}


@functools.lru_cache(maxsize=int(1e6))
def get_hex(hex_id: int, data: TimezoneData) -> Hex:
    return Hex.from_id(hex_id, data)


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


def compile_h3_map(data: TimezoneData, candidates: Set) -> ShortcutMapping:
    """
    operate on one hex resolution
    also store results separately to divide the output data files
    """
    mapping: ShortcutMapping = {}
    total_candidates = len(candidates)

    def report_progress():
        nr_candidates = len(candidates)
        processed = total_candidates - nr_candidates
        print(
            f"\r{processed:,} processed\t{nr_candidates:,} remaining\t",
            end="",
            flush=True,
        )

    while candidates:
        hex_id = candidates.pop()
        cell = get_hex(hex_id, data)
        polys = list(cell.polys_in_cell)
        polys_optimised = optimise_shortcut_ordering(data, polys)
        check_shortcut_sorting(polys_optimised, data.poly_zone_ids)
        mapping[hex_id] = polys_optimised
        report_progress()

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

    returns: mapping from hexagon id to list of polygon ids

    cf. https://eng.uber.com/h3/
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
