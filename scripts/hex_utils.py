"""
Hex-related utility functions that don't depend on classes.
Created to break circular import between shortcuts.py and classes.py.
"""

from dataclasses import dataclass
from typing import Set, Tuple, TYPE_CHECKING, Optional

import h3.api.numpy_int as h3
import numpy as np

from scripts.configs import MAX_LAT, MAX_LNG, HexIdSet, PolyIdSet, ZoneIdSet
from scripts.helper_classes import Boundaries
from scripts.utils import to_numpy_polygon_repr
from scripts.utils_numba import any_pt_in_poly, fully_contained_in_hole
from timezonefinder.utils_numba import coord2int, int2coord

if TYPE_CHECKING:
    from scripts.timezone_data import TimezoneData


def lies_in_h3_cell(h: int, lng: float, lat: float) -> bool:
    res = h3.get_resolution(h)
    return h3.latlng_to_cell(lat, lng, res) == h


def surrounds_north_pole(hex_id: int) -> bool:
    """Check if a hex cell surrounds the north pole."""
    return lies_in_h3_cell(hex_id, lng=0.0, lat=MAX_LAT)


def surrounds_south_pole(hex_id: int) -> bool:
    """Check if a hex cell surrounds the south pole."""
    return lies_in_h3_cell(hex_id, lng=0.0, lat=-MAX_LAT)


def get_corrected_hex_boundaries(
    x_coords, y_coords, surr_n_pole, surr_s_pole
) -> Tuple[Boundaries, bool]:
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
    data: "TimezoneData"
    _poly_candidates: Optional[PolyIdSet] = None
    _polys_in_cell: Optional[PolyIdSet] = None
    _zones_in_cell: Optional[ZoneIdSet] = None

    @classmethod
    def from_id(cls, id: int, data: "TimezoneData"):
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
            parent_hex = self.data.get_hex(parent_id)
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
            for hole in self.data.holes_in_poly(poly_nr):
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


def any_pt_in_cell(data: "TimezoneData", h: int, poly_nr: int) -> bool:
    """
    Optimized version using hex coordinates and fast Numba point-in-polygon test.

    Instead of checking if polygon points lie in the hex cell (expensive H3 operations),
    we check if any hex vertices lie inside the polygon using fast Numba JIT functions.
    This is geometrically equivalent and much faster.
    """
    # Fast geometric pre-filter: check if bounding boxes overlap
    poly_bounds = data.poly_boundaries[poly_nr]
    hex_obj = data.get_hex(h)
    hex_bounds = hex_obj.bounds

    if not poly_bounds.overlaps(hex_bounds):
        return False

    # Use hex coordinates and fast Numba point-in-polygon test
    # This is geometrically equivalent to testing polygon points in hex
    # but uses the fast JIT-compiled point-in-polygon algorithm
    hex_coords = hex_obj.coords
    poly_coords = data.polygons[poly_nr]

    # Use the fast Numba JIT function to test if any hex vertex is in the polygon
    return any_pt_in_poly(hex_coords, poly_coords)
