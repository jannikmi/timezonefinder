"""Deterministic geometric optimization of the full timezone lookup predicate.

No query points are sampled. All probabilities and work estimates are surface
integrals over clipped geometry. The approximations are these, explicitly:

1. Surface measure is spherical, dmu=cos(phi) dphi dlambda (radius cancels).
   Grid cells are equal-angle, not equal-area, and planar degree areas are not
   probabilities. For WGS84 geodetic area the density is instead proportional to
   cos(phi)/(1-e^2 sin^2(phi))^2. Its ratio to spherical density has max/min
   <=1.013525 globally; this bounds the measure-only loss of a spherical
   population optimum, not our heuristic's or cost model's error.
2. Stored timezone edges are straight in the quantized longitude/latitude
   plane. Their spherical areas are integrated analytically by Green's theorem:
   A(ring)=abs(sum_edges -dlambda * mean_edge(sin(phi))). For a linear edge,
   mean(sin(phi))=sin(mid_phi)*sinc(dphi/(2*pi)). Holes subtract; components add.
   A cell is an axis-aligned rectangle of that same plane, so its region is
   exact and its area closes the same integral - where the H3 hexagons this
   replaced had great-circle edges that had to be subdivided until the
   represented area converged on H3's own, a check that was never a
   boundary-distance certificate. No cell now wraps the plane's cut or encloses
   a pole, so neither needs representing. Overlay roundoff and ignoring the tiny
   query-quantization strips (one coordinate unit, ~1.1 cm) remain geometric
   errors. Small positive regions are not dropped by a probability threshold.
3. The work proxy is a positive sum of rectangular indicator functions:
       c_i(x) = BBOX + sum_t w_it * 1[x in rectangle_it].
   Outer bbox survivors pay the hole-union probe and outer PIP. Only survivors
   of BOTH outer and hole-union boxes pay registry lookup and hole bbox visits.
   Each individual hole PIP is charged only inside its bbox. PIP work includes
   dispatch, every block-range probe, and latitude-active decoded blocks.
   We deliberately charge all holes and the outer PIP even after a matching
   hole would stop execution: a conservative stage-count approximation, whose
   error is concentrated on points actually inside holes. It can affect order.
   The coefficients below are rounded engineering estimates, not fresh timings;
   short-circuit comparison counts, caches, branches, backend/storage differences
   and early PIP termination are unmodeled. Conversion never times code.
4. Let H_i be the full polygon hit region including holes, and
       R(S) = C \\ union_{j in S} H_j.
   The exact incremental proxy cost is d(S,i)=integral_{R(S)} c_i dmu.
   All terms are computed by geometric intersection and analytic area, NOT by
   factoring mean cost from probability of reaching the check. Division by
   mu(C) is common to every order in this cell, so it is omitted.
   Overlapping hit regions use a union, never a sum of polygon probabilities.
5. Search is a heuristic, with no candidate-count cutoff. Enumerate each entire
   final zone L (untested), greedily choose remaining polygons by
       mu(H_i intersect R(S)) / d(S,i),
   then improve by adjacent exchanges. Also refine the legacy-derived order for
   each L. Exchanging adjacent a,b changes cost by
       d(S,b)+d(S union {b},a)-d(S,a)-d(S union {a},b).
   The later suffix is unchanged because its surviving region depends only on
   the tested SET. A relative 1e-12 improvement threshold avoids numerical tie
   churn. The legacy order is always an incumbent: modeled expected work never
   increases. Greedy construction examines O(n^2) choices per final zone; local
   search stops at an adjacent local optimum, with no claim of a polynomial
   worst-case iteration bound. There is no exponential subset enumeration.
   For constant c_i and disjoint H_i, greedy reduces to decreasing p_i/c_i;
   the exchange difference (after minus before) is c_b*p_a-c_a*p_b. Enumerating L
   then gives the GLOBAL optimum for that special case. Point-dependent costs and
   overlaps need not admit a transitive ratio order; no global claim is made.
6. Correctness is separate from that approximate objective. The cell's own
   rectangle, grown one unit on each side and clipped to the coordinate domain,
   certifies coverage and absence of cross-zone positive-area overlap before
   allowing final-zone changes or interleaving. It is exact rather than a
   conservative circumscribed cap, which is what the hexagons needed, so it
   admits more cells than that gate did - including the polar and antimeridian
   cells the cap conversion had to refuse outright. The clip is what makes that
   last clause true rather than merely intended: see `cell_envelope`.
   Otherwise preserve legacy zone priority and final zone, optimizing only
   within tested zone blocks. Block survivors depend on the zone's hit union,
   so this preserves zone answers even where the proxy geometry is inaccurate.
   Invalid source geometry is repaired ONLY for the objective by GEOS make_valid;
   it always fails the safety gate. Runtime geometry is never repaired or removed.
   The gate admits zones that touch, so a point on the border they share keeps
   its answer only because the point-in-polygon kernel gives it exactly one
   owner; tests/test_point_in_polygon_boundary_convention.py pins that rule.
   All candidates, including zero-area candidates, remain in the binary.
"""

from dataclasses import dataclass
from itertools import combinations, groupby
from pathlib import Path

import numpy as np
from shapely import Polygon, box, make_valid, union_all
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry

from scripts.timezone_data import TimezoneData
from timezonefinder import utils
from timezonefinder.configs import (
    INT2COORD_FACTOR,
    MAX_LAT_VAL_INT,
    MAX_LNG_VAL_INT,
    POLYGON_BLOCK_SIZE,
)
from timezonefinder.polygon_array import HoleArray, PolygonArray
from timezonefinder.shortcut_index import cell_bounds

BBOX = 160
HOLE_UNION_PROBE = 80
HOLE_LOOKUP = 120
HOLE_BBOX = 120
PIP_DISPATCH = 700
BLOCK_PROBE = 1
ACTIVE_VERTEX = 1
IMPROVEMENT_RTOL = 1e-12


@dataclass(frozen=True)
class CostCoefficients:
    """Versionable coefficients for the runtime events modeled by the optimizer.

    The converter still uses the reviewed defaults below.  Calibration tooling may
    construct another instance to evaluate an alternative order, but never mutates
    these defaults or makes conversion depend on the machine running it.
    """

    bbox: float = BBOX
    hole_union_probe: float = HOLE_UNION_PROBE
    hole_lookup: float = HOLE_LOOKUP
    hole_bbox: float = HOLE_BBOX
    pip_dispatch: float = PIP_DISPATCH
    block_probe: float = BLOCK_PROBE
    active_vertex: float = ACTIVE_VERTEX


DEFAULT_COST_COEFFICIENTS = CostCoefficients()


def spherical_area(geometry: BaseGeometry) -> float:
    """Steradians for piecewise-linear rings in runtime integer coordinates."""
    if geometry.is_empty:
        return 0.0
    if geometry.geom_type == "Polygon":

        def ring_area(ring) -> float:
            coords = np.asarray(ring.coords) * (INT2COORD_FACTOR * np.pi / 180)
            lat = coords[:, 1]
            mean_sin = np.sin((lat[:-1] + lat[1:]) / 2) * np.sinc(
                np.diff(lat) / (2 * np.pi)
            )
            # A closed planar ring has sum(dlambda)=0. Subtracting a reference
            # density reduces cancellation for small regions at high latitude.
            return abs(
                float(np.sum(np.diff(coords[:, 0]) * (mean_sin - np.sin(lat[0]))))
            )

        return max(
            0.0,
            ring_area(geometry.exterior)
            - sum(ring_area(r) for r in geometry.interiors),
        )
    if geometry.geom_type in ("MultiPolygon", "GeometryCollection"):
        return sum(spherical_area(g) for g in geometry.geoms)
    return 0.0  # shared edges and points have zero area


def cell_region(cell: int) -> BaseGeometry:
    """The cell, as the exact rectangle of the integer plane it is.

    A cell owns the integer points ``cell_bounds`` gives, so as a region of query
    positions it is ``(x0 - 1, x1] x (y0 - 1, y1]`` - half-open on the sides it
    does not own, which an area integral does not distinguish anyway. Exactness
    is what the aligned grid buys here: the H3 version of this function
    subdivided great-circle arcs until the represented area converged on H3's,
    then had to stitch a polar cap onto rings winding round a pole and unwrap
    rings crossing the plane's cut. A rectangle needs none of it.
    """
    x0, y0, x1, y1 = cell_bounds(cell)
    return box(x0 - 1, y0 - 1, x1, y1)


def cell_envelope(cell: int) -> BaseGeometry:
    """What the safety gate has to be satisfied over: the cell plus one unit, clipped.

    Every integer point the cell owns lies inside this, so a coverage or disjointness
    fact established here holds for every query the cell answers. The unit of slack
    absorbs the query quantization the region above ignores.

    **Clipped to the coordinate domain, which is not cosmetic.** The top row's cells end
    at exactly +90 degrees and the last column's at +180, so an unclipped +1 would ask
    the gate to find coverage beyond where any polygon can be - and ``covers`` would be
    False for every one of them, whatever their geometry. That is how the H3 gate's
    pole and antimeridian refusals would have survived the port into a rectangle that
    has no reason for them: silently, as an arithmetic accident rather than a decision,
    over the 384 top-row and 192 last-column root cells and all of their children.
    ``tests/test_shortcut_ordering.py::test_the_gate_can_pass_at_the_edges_of_the_domain``
    is what says they are reachable.
    """
    x0, y0, x1, y1 = cell_bounds(cell)
    return box(
        max(x0 - 1, -MAX_LNG_VAL_INT),
        max(y0 - 1, -MAX_LAT_VAL_INT),
        min(x1 + 1, MAX_LNG_VAL_INT),
        min(y1 + 1, MAX_LAT_VAL_INT),
    )


class CheckCost:
    """A directly integrable point-dependent work model, with no point samples."""

    def __init__(self, base: float = BBOX):
        self.base = base
        self.terms: dict[tuple[int, int, int, int], float] = {}

    def add(self, bounds: tuple[int, int, int, int], weight: float) -> None:
        if bounds[0] < bounds[2] and bounds[1] < bounds[3]:
            self.terms[bounds] = self.terms.get(bounds, 0.0) + weight

    def integral(self, region: BaseGeometry) -> float:
        area = spherical_area(region)
        if area == 0:
            return 0.0
        xmin, ymin, xmax, ymax = region.bounds
        value = self.base * area
        for (x0, y0, x1, y1), weight in self.terms.items():
            if x1 <= xmin or xmax <= x0 or y1 <= ymin or ymax <= y0:
                continue
            if x0 <= xmin and xmax <= x1 and y0 <= ymin and ymax <= y1:
                covered = area
            else:
                covered = spherical_area(region.intersection(box(x0, y0, x1, y1)))
            value += weight * covered
        return value


def improves(value: float, incumbent: float) -> bool:
    return value < incumbent * (1 - IMPROVEMENT_RTOL)


class CellOptimizer:
    """Greedy candidates + local exchanges, scored by exact proxy integrals."""

    def __init__(
        self,
        cell: BaseGeometry,
        hits: list[BaseGeometry],
        costs: list[CheckCost],
        zones: list[int],
    ):
        self.cell, self.hits, self.costs, self.zones = cell, hits, costs, zones
        self.regions = {0: cell}
        self.work: dict[tuple[int, int], float] = {}

    def remaining(self, tested: int) -> BaseGeometry:
        if tested not in self.regions:
            bit = tested & -tested
            self.regions[tested] = self.remaining(tested ^ bit).difference(
                self.hits[bit.bit_length() - 1]
            )
        return self.regions[tested]

    def cost(self, tested: int, i: int) -> float:
        key = tested, i
        if key not in self.work:
            self.work[key] = self.costs[i].integral(self.remaining(tested))
        return self.work[key]

    def score(self, prefix: list[int]) -> float:
        tested = 0
        value = 0.0
        for i in prefix:
            value += self.cost(tested, i)
            tested |= 1 << i
        return value

    def greedy(self, indices: list[int], tested: int = 0) -> list[int]:
        left = indices.copy()
        result: list[int] = []
        while left:
            if len(left) == 1 or spherical_area(self.remaining(tested)) == 0:
                return result + left
            region = self.remaining(tested)

            def ratio(
                i: int, tested: int = tested, region: BaseGeometry = region
            ) -> float:
                work = self.cost(tested, i)
                return (
                    spherical_area(region.intersection(self.hits[i])) / work
                    if work
                    else 0.0
                )

            selected = max(left, key=ratio)
            result.append(selected)
            tested |= 1 << selected
            left.remove(selected)
        return result

    def refine(self, prefix: list[int], fixed_zones: bool) -> list[int]:
        order = prefix.copy()
        while True:
            changed = False
            tested = 0
            for k in range(len(order) - 1):
                a, b = order[k : k + 2]
                if not fixed_zones or self.zones[a] == self.zones[b]:
                    before = self.cost(tested, a) + self.cost(tested | (1 << a), b)
                    after = self.cost(tested, b) + self.cost(tested | (1 << b), a)
                    if improves(after, before):
                        order[k : k + 2] = b, a
                        changed = True
                tested |= 1 << order[k]
            if not changed:
                return order

    def order(self, unrestricted: bool) -> list[int]:
        n = len(self.zones)
        final = self.zones[-1]
        start = self.zones.index(final)
        best = list(range(n))
        value = self.score(best[:start])
        if unrestricted:
            for last in dict.fromkeys(self.zones):
                prefix = [i for i in range(n) if self.zones[i] != last]
                tail = [i for i in range(n) if self.zones[i] == last]
                for candidate in (prefix, self.greedy(prefix)):
                    candidate = self.refine(candidate, False)
                    cost = self.score(candidate)
                    if improves(cost, value):
                        value, best = cost, candidate + tail
        else:
            groups = [list(g) for _, g in groupby(range(n), self.zones.__getitem__)]
            if len(groups) != len(set(self.zones)):
                raise ValueError("zone precedence requires contiguous input blocks")
            greedy = []
            tested = 0
            for group in groups[:-1]:
                greedy.extend(self.greedy(group, tested))
                for i in group:
                    tested |= 1 << i
            for candidate in (list(range(start)), greedy):
                candidate = self.refine(candidate, True)
                cost = self.score(candidate)
                if improves(cost, value):
                    value, best = cost, candidate + groups[-1]
        return best


class ShortcutOrderer:
    """Conversion-local geometry and packed block metadata; no runtime additions."""

    def __init__(
        self,
        data: TimezoneData,
        output_path: Path,
        coefficients: CostCoefficients = DEFAULT_COST_COEFFICIENTS,
    ):
        self.data = data
        self.coefficients = coefficients
        # `self.boundaries` reads the *written* binaries and `self.data.boundaries`
        # the in-memory rings the same parse built. Deliberately both, and one hop
        # apart: the cost model below is about the packed layout, while the geometry
        # above is about the rings - so keep the two apart when adding a caller.
        self.boundaries = PolygonArray(utils.get_boundaries_dir(output_path))
        self.holes = HoleArray(utils.get_holes_dir(output_path), self.boundaries)
        self.geometries: dict[int, BaseGeometry] = {}
        self.invalid_geometries: set[int] = set()
        self.models: dict[int, CheckCost] = {}

    def close(self) -> None:
        self.holes.cleanup()
        self.boundaries.cleanup()

    def geometry(self, pid: int) -> BaseGeometry:
        if pid not in self.geometries:
            geometry = Polygon(
                self.data.boundaries.coords_of(pid).T,
                [hole.T for hole in self.data.holes.holes_of_poly(pid)],
            )
            if not geometry.is_valid:
                self.invalid_geometries.add(pid)
                geometry = make_valid(geometry)
            self.geometries[pid] = geometry
        return self.geometries[pid]

    def safe_to_reorder(self, cell: int, ids: list[int]) -> bool:
        """Whether the zones in this cell may be reordered freely.

        Free reordering is sound exactly where the candidates cover the cell with
        no cross-zone area overlap: every point then has one owner whatever order
        it is found in. Where that cannot be shown the legacy zone precedence is
        preserved and only within-zone blocks are optimized.
        """
        envelope = cell_envelope(cell)
        try:
            geometries = [self.geometry(pid) for pid in ids]
            if any(pid in self.invalid_geometries for pid in ids):
                return False
            clipped = [g.intersection(envelope) for g in geometries]
            for a, b in combinations(range(len(ids)), 2):
                if (
                    self.data.poly_zone_ids[ids[a]] != self.data.poly_zone_ids[ids[b]]
                    and clipped[a].intersection(clipped[b]).area > 0
                ):
                    return False
            return bool(union_all(clipped).covers(envelope))
        except GEOSException:
            return False

    @staticmethod
    def bounds(array: PolygonArray, pid: int) -> tuple[int, int, int, int]:
        return (
            int(array.xmin[pid]),
            int(array.ymin[pid]),
            int(array.xmax[pid]),
            int(array.ymax[pid]),
        )

    @staticmethod
    def intersection(
        a: tuple[int, int, int, int], b: tuple[int, int, int, int]
    ) -> tuple[int, int, int, int]:
        return max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])

    def add_pip(
        self,
        model: CheckCost,
        array: PolygonArray,
        pid: int,
        gate: tuple[int, int, int, int],
    ) -> None:
        if isinstance(array, HoleArray):
            array, pid = array._resolve(pid)
        start, end = array.block_offsets[pid : pid + 2]
        coefficients = self.coefficients
        model.add(
            gate,
            coefficients.pip_dispatch + coefficients.block_probe * (end - start),
        )
        for low, high in array.block_ranges[start:end]:
            model.add(
                self.intersection(gate, (gate[0], int(low), gate[2], int(high))),
                coefficients.active_vertex * POLYGON_BLOCK_SIZE,
            )

    def model(self, pid: int) -> CheckCost:
        if pid not in self.models:
            coefficients = self.coefficients
            model = CheckCost(coefficients.bbox)
            outer = self.bounds(self.boundaries, pid)
            model.add(outer, coefficients.hole_union_probe)
            self.add_pip(model, self.boundaries, pid, outer)
            amount, first = self.data.hole_registry.get(pid, (0, 0))
            if amount:
                boxes = [
                    self.bounds(self.holes, hid) for hid in range(first, first + amount)
                ]
                union = (
                    min(b[0] for b in boxes),
                    min(b[1] for b in boxes),
                    max(b[2] for b in boxes),
                    max(b[3] for b in boxes),
                )
                gate = self.intersection(outer, union)
                model.add(
                    gate,
                    coefficients.hole_lookup + amount * coefficients.hole_bbox,
                )
                for hid, bounds in zip(
                    range(first, first + amount), boxes, strict=True
                ):
                    self.add_pip(
                        model, self.holes, hid, self.intersection(gate, bounds)
                    )
            self.models[pid] = model
        return self.models[pid]

    def order(self, cell: int, ids: list[int]) -> list[int]:
        zones = [int(self.data.poly_zone_ids[pid]) for pid in ids]
        if len(set(zones)) <= 1:
            return ids
        unrestricted = self.safe_to_reorder(cell, ids)
        region = cell_region(cell)
        hits = [self.geometry(pid).intersection(region) for pid in ids]
        optimizer = CellOptimizer(region, hits, [self.model(pid) for pid in ids], zones)
        return [ids[i] for i in optimizer.order(unrestricted)]
