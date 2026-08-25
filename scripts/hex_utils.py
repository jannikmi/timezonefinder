"""
Hex-related utility functions that don't depend on classes.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import h3.api.numpy_int as h3
import numpy as np

from scripts.configs import HexIdSet, PolyIdSet, ZoneIdSet
from scripts.helper_classes import Boundaries
from scripts.utils import to_numpy_polygon_repr
from scripts.utils_numba import (
    any_edge_crossing,
    any_pt_in_poly,
    fully_contained_in_hole,
)
from timezonefinder.configs import MAX_LAT_VAL, MAX_LNG_VAL
from timezonefinder.utils_numba import coord2int, int2coord

if TYPE_CHECKING:
    from scripts.timezone_data import TimezoneData


try:
    profile  # type: ignore[used-before-def]
except NameError:  # pragma: no cover - used only during profiling

    def profile(func):  # type: ignore[misc]
        return func


def lies_in_h3_cell(h: int, lng: float, lat: float) -> bool:
    res = h3.get_resolution(h)
    return h3.latlng_to_cell(lat, lng, res) == h


def surrounds_north_pole(hex_id: int) -> bool:
    """Check if a hex cell surrounds the north pole."""
    return lies_in_h3_cell(hex_id, lng=0.0, lat=MAX_LAT_VAL)


def surrounds_south_pole(hex_id: int) -> bool:
    """Check if a hex cell surrounds the south pole."""
    return lies_in_h3_cell(hex_id, lng=0.0, lat=-MAX_LAT_VAL)


def get_corrected_hex_boundaries(
    x_coords, y_coords, surr_n_pole, surr_s_pole
) -> tuple[Boundaries, bool]:
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
    max_latitude = coord2int(MAX_LAT_VAL)
    max_longitude = coord2int(MAX_LNG_VAL)

    delta_y = abs(ymax0 - ymin0)
    assert delta_y < max_latitude, f"latitude difference {int2coord(delta_y)} too high"
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


# Half a turn about the polar axis, in the scaled integer longitudes everything here
# works in. Applied to every vertex of a ring it moves the coordinate plane's cut from
# the antimeridian to the prime meridian, which is what a ring straddling +-180 deg needs
# before any Euclidean test says what it means: stored as they are, its longitudes jump
# from one edge of the plane to the other and the ring self-intersects.
# int32-safe in both directions - a negative longitude gains at most 180 deg and a
# positive one loses at least as much, so nothing leaves [-180 deg, 180 deg].
HALF_TURN_LNG = coord2int(MAX_LNG_VAL)


def rotate_half_turn(ring: np.ndarray) -> np.ndarray:
    """``ring`` rotated half a turn about the polar axis, so the cut falls on lng 0.

    A rigid rotation of the sphere, so every planar relation between two rings rotated
    together is preserved - except across the cut, which is the whole point: what used to
    be torn apart by it becomes contiguous, and what sat on the prime meridian is torn
    instead. `is_torn_by_cut` is what says which of the two a given ring is.
    """
    rotated = ring.copy()
    negative = ring[0] < 0
    rotated[0, negative] += HALF_TURN_LNG
    rotated[0, ~negative] -= HALF_TURN_LNG
    return rotated


def is_torn_by_cut(ring: np.ndarray) -> bool:
    """True if the ring's longitudes span more than half the globe in this frame.

    Which means one of two things, and neither can be judged by a Euclidean test: the
    ring wraps the coordinate plane's cut and its stored longitudes jump from one edge
    to the other, or it encloses a pole and genuinely reaches every meridian. Nothing
    else here is that wide - the widest timezone polygon that is neither spans ~61 deg.
    `get_corrected_hex_boundaries` applies the same test to a cell, where the answer is
    called `x_overflow`.
    """
    return int(ring[0].max()) - int(ring[0].min()) > HALF_TURN_LNG


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
    _rotated_coords: np.ndarray | None = None
    _poly_candidates: PolyIdSet | None = None
    _polys_in_cell: PolyIdSet | None = None
    _zones_in_cell: ZoneIdSet | None = None

    @classmethod
    def from_id(cls, hex_id: int, data: "TimezoneData") -> "Hex":
        res = h3.get_resolution(hex_id)
        coord_pairs = h3.cell_to_boundary(hex_id)
        # ATTENTION: (lat, lng)! pairs
        coords = to_numpy_polygon_repr(coord_pairs, flipped=True)
        x_coords, y_coords = coords[0], coords[1]
        surr_n_pole = surrounds_north_pole(hex_id)
        surr_s_pole = surrounds_south_pole(hex_id)
        bounds, x_overflow = get_corrected_hex_boundaries(
            x_coords, y_coords, surr_n_pole, surr_s_pole
        )
        return cls(
            hex_id, res, coords, bounds, x_overflow, surr_n_pole, surr_s_pole, data
        )

    @property
    def is_special(self) -> bool:
        """Stored coordinates no Euclidean test can be applied to as they stand."""
        return self.x_overflow or self.surr_n_pole or self.surr_s_pole

    @property
    def crosses_antimeridian(self) -> bool:
        """Torn by the coordinate plane's cut, with no pole inside the ring.

        The distinction `is_special` does not draw, and the one that decides whether
        anything can be done about it: a ring enclosing a pole reaches every meridian,
        so no cut leaves it whole, while one that merely wraps +-180 deg becomes an
        ordinary hexagon under `rotate_half_turn`.
        """
        return self.x_overflow and not (self.surr_n_pole or self.surr_s_pole)

    @property
    def rotated_coords(self) -> np.ndarray:
        """The cell's ring in the frame `rotate_half_turn` defines."""
        if self._rotated_coords is None:
            self._rotated_coords = rotate_half_turn(self.coords)
        return self._rotated_coords

    def _init_candidates(self) -> PolyIdSet:
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
            return self._poly_candidates
        if self.res == 0:
            # at the highest level all polygons should be tested
            self._poly_candidates = set(range(self.data.nr_of_polygons))
            return self._poly_candidates

        # polygon ids, inherited from the true parents - not hex ids
        candidates: PolyIdSet = set()
        for parent_id in self.true_parents:
            parent_hex = self.data.get_hex(parent_id)
            parent_polys = parent_hex.poly_candidates
            candidates.update(parent_polys)

        self._poly_candidates = candidates
        return candidates

    def is_poly_candidate(self, poly_id: int) -> bool:
        cell_bounds = self.bounds
        poly_bounds = self.data.poly_boundaries[poly_id]
        overlapping = cell_bounds.overlaps(poly_bounds)
        return overlapping

    @property
    def poly_candidates(self) -> PolyIdSet:
        # `_init_candidates` leaves a set behind on every path, so it returns
        # one rather than the property re-reading the attribute and guarding
        # against a `None` that cannot occur. That guard returned an empty set,
        # which means "no candidate polygons" - a converter bug would have
        # surfaced as silently missing shortcuts rather than as a failure.
        if self._poly_candidates is None:
            inherited = self._init_candidates()
            self._poly_candidates = {
                poly_id for poly_id in inherited if self.is_poly_candidate(poly_id)
            }
        return self._poly_candidates

    @profile
    def lies_in_cell(self, poly_nr: int) -> bool:
        poly_coords = self.data.polygons[poly_nr]
        holes = self.data.holes_in_poly(poly_nr)
        rotated = False
        if self.crosses_antimeridian:
            # The cell's stored ring jumps the cut, so every Euclidean test below would
            # be applied to a self-intersecting shape spanning most of the globe instead
            # of to the cell. Rotating the whole scene - cell, polygon and holes alike -
            # moves the cut to lng 0 and leaves the cell an ordinary hexagon.
            #
            # Only for a polygon the new cut leaves whole, which is the same span test
            # the cell itself was judged by. One that fails it is either wrapping lng 0
            # or wrapped around a pole, and is left to the tests it already had rather
            # than judged in a frame that tears it: a polygon at the prime meridian
            # cannot reach a cell at the antimeridian anyway, and one enclosing a pole
            # is no better off in either frame.
            rotated_poly = rotate_half_turn(poly_coords)
            rotated = not is_torn_by_cut(rotated_poly)
            if rotated:
                poly_coords = rotated_poly
                holes = (rotate_half_turn(hole) for hole in holes)
        hex_coords = self.rotated_coords if rotated else self.coords

        overlap = any_pt_in_poly(hex_coords, poly_coords)
        if not overlap:
            # also test the inverse: if any point of the polygon lies inside the hex cell
            # ATTENTION: some hex cells cannot be used as polygons in regular point in polygon algorithm!
            # h3 answers this one on the sphere, so it needs no frame of its own
            overlap = any_pt_in_cell(self.data, self, poly_nr)
        if not overlap and (rotated or not self.is_special):
            # Two rings can overlap with no vertex of either inside the other, when an edge
            # passes clean through. Vertex inclusion alone therefore misses real coverage,
            # and the cell is recorded as uncovered - a wrong timezone for every point in
            # it, announced by nothing. This used to be left out as a simplification valid
            # while "the polygons and cells have a similar size", which stops holding as
            # the H3 resolution rises and cells shrink while the polygons do not.
            #
            # Skipped for the special cells that could not be rotated onto a frame
            # where a segment test means what it says - those enclosing a pole, and
            # those judging a polygon that is itself torn. They keep the vertex tests
            # alone, as every special cell used to.
            overlap = any_edge_crossing(hex_coords, poly_coords)

        # account for holes in polygon
        # only check if found overlapping
        if overlap:
            for hole in holes:
                # the whole cell inside the hole, not merely its corners - a hole
                # boundary running through the cell leaves part of it covered
                if fully_contained_in_hole(hex_coords, hole):
                    return False
        return overlap

    @property
    def polys_in_cell(self) -> set[int]:
        if self._polys_in_cell is None:
            # lazy evaluation, caching
            self._polys_in_cell = set(filter(self.lies_in_cell, self.poly_candidates))
        return self._polys_in_cell

    @property
    def zones_in_cell(self) -> set[int]:
        if self._zones_in_cell is None:
            # lazy evaluation, caching
            self._zones_in_cell = {
                self.data.poly_zone_ids[p] for p in self.polys_in_cell
            }
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


@profile
def any_pt_in_cell(data: "TimezoneData", hex_obj: Hex, poly_nr: int) -> bool:
    """Check if any polygon points lie inside the hex cell via cached vertex mappings."""
    target_hex_id = hex_obj.id
    resolution = hex_obj.res
    vertex_hexes = data.polygon_vertex_hexes(poly_nr, resolution)
    return target_hex_id in vertex_hexes
