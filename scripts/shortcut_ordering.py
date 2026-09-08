"""Optimize shortcut prefixes against deterministic, point-dependent work.

The model, proof and limitations are part of this module's contract:

* X is uniform in spherical surface area conditional on its H3 cell. In geodetic
  coordinates dA = R² cos(latitude) dlatitude dlongitude. Uniform degrees is NOT
  uniform area; H3 cells are NOT equal-area either (resolution-4 hexagon areas
  differ by almost a factor of two). Cell probabilities multiply independent
  objectives by positive constants, so they cannot change a per-cell minimizer.
  We sample a containing spherical cap and reject using H3 itself. Each cell gets
  its own fixed seed: traversal order cannot affect the generated binary.
* WGS84 is approximated by a sphere, not by a flat longitude/latitude plane.
  Ellipsoidal dA = a²(1-e²) cos(phi)/(1-e² sin²(phi))² dphi dlambda.
  Relative to spherical samples, normalized importance weights are proportional
  to (1-e² sin²(phi))**-2. Their whole-globe max/min ratio is 1.013525;
  the measure-only loss of a spherical population optimum is bounded by this
  ratio. This does NOT bound finite-sample or cost-model error.
* h_i(x) is the FULL boundary predicate, including bbox and holes. c_i(x) is
  deterministic estimated work for that predicate at x, independent of prefix
  order. With S the already tested set, R(S,x)=product(1-h_j(x), j in S).
  J(pi)=E[sum_k c_pi[k](X) R(prefix_k,X)]. Never replace this by
  E[c_i] P(reach i): bbox/holes make cost and survival correlated.
* One COMPLETE original zone G must remain untested at the end. All other
  polygons may interleave freely. For sample weights w=1/N, define
  d(S,i)=sum_x w c_i(x) R(S,x). Then F(S)=0 if I\\S=G for some complete zone;
  F(S)=infinity if no complete zone remains untouched; otherwise
  F(S)=min_i(d(S,i)+F(S union {i})). Conditioning on the first remaining test
  proves this recurrence by induction on |I\\S|. There is no active-zone state.
  A suffix containing one zone is insufficient if that zone was partly tested.
  Constants 1/N are omitted in code without changing the minimizer.
* For constant c_i and disjoint hits, exchanging adjacent a,b changes the cost
  by p_b*c_a-p_a*c_b: sort ALL nonterminal polygons by decreasing p_i/c_i,
  enumerate the terminal zone, and choose the least J. Probabilities are still
  unconditional within the cell, not renormalized after excluding that zone.
  Our point-dependent model needs the recurrence instead of a ratio sort.
* The optimum is exact for the sampled work objective, NOT measured latency or
  the population integral. 128 samples are a fixed conversion-time accuracy
  budget, with no claim that small slivers are resolved. States cost O(N n 2^n);
  above 14 candidates the legacy order is retained, not called optimal.
* Warm additive work omits caches, branch prediction, storage/backend variation,
  and lookup overhead independent of order. Coefficients below are deliberately
  rounded engineering estimates informed by earlier full-predicate measurements,
  not a fitted timing model. Conversion never times code. CI measures latency.
  Crucially, 95 rejected holes still cost 95 bbox/dispatch checks; modelling only
  outer PIP would miss the dominant cost of some candidates.
* Sampling is NOT a correctness certificate. Geometry is used separately to
  preserve the old order where different zones overlap with positive area.
  Invalid geometry is retained unchanged, never repaired for this decision.
  A conservative cap bbox also checks coverage by the candidate union; if it
  cannot prove coverage, the old order is retained (including custom land-only
  data). This rejects some safe changes, including cells crossing the date line.
  GEOS operates on the same quantized planar rings as the runtime; it is used
  for set relations, never as a spherical probability/area estimator. Numerical
  overlay error and boundary tie conventions remain limitations: no ordering
  establishes a unique timezone on a shared border. No polygon is removed.
"""

from functools import lru_cache
from itertools import combinations
from math import inf
from pathlib import Path

import h3.api.numpy_int as h3
import numpy as np
from shapely import Polygon, box, union_all
from shapely.errors import GEOSException

from scripts.timezone_data import TimezoneData
from timezonefinder import utils
from timezonefinder.configs import POLYGON_BLOCK_SIZE, SHORTCUT_H3_RES
from timezonefinder.polygon_array import HoleArray, PolygonArray

SAMPLES_PER_CELL = 128
MAX_EXACT_CANDIDATES = 14
# Relative work units, roughly nanoseconds on the reference warm C/mapped path.
# Bbox includes candidate dispatch; hole lookup is paid after a surviving bbox;
# each visited hole pays HOLE_BBOX even if it rejects. PIP pays dispatch + all
# block range probes + decoded vertices in latitude-active blocks (ragged end
# rounded up). Full predicate observations previously ranged from ~160 units
# for bbox misses to ~12,200 for a boundary with 95 holes. These constants are
# explicit approximation parameters, not fresh benchmark results.
BBOX = 160
HOLE_LOOKUP = 120
HOLE_BBOX = 120
PIP_DISPATCH = 700
BLOCK_PROBE = 1
ACTIVE_VERTEX = 1


def optimal_order(zones: list[int], hits: np.ndarray, costs: np.ndarray) -> list[int]:
    """Return positions, retaining the input order on objective ties.

    Caller bounds the exponential state count. Costs must be nonnegative and
    have shape (candidate, sample), as must Boolean hits.
    """
    n = len(zones)
    full = (1 << n) - 1
    groups = tuple(
        sum(1 << i for i, z in enumerate(zones) if z == zone)
        for zone in dict.fromkeys(zones)
    )

    @lru_cache(None)
    def dp(tested: int) -> tuple[float, tuple[int, ...]]:
        remaining = full ^ tested
        if remaining in groups:
            return 0, tuple(i for i in range(n) if remaining & (1 << i))
        if not any(remaining & group == group for group in groups):
            return inf, ()
        alive = np.ones(hits.shape[1], dtype=bool)
        for i in range(n):
            if tested & (1 << i):
                alive &= ~hits[i]
        best: tuple[float, tuple[int, ...]] = (inf, ())
        for i in range(n):
            if remaining & (1 << i):
                tail_cost, tail = dp(tested | (1 << i))
                value = float(costs[i, alive].sum()) + tail_cost
                if value < best[0]:
                    best = value, (i,) + tail
        return best

    value, order = dp(0)
    alive = np.ones(hits.shape[1], dtype=bool)
    original = 0.0
    for i, zone in enumerate(zones):
        if zone == zones[-1]:
            break
        original += float(costs[i, alive].sum())
        alive &= ~hits[i]
    return list(range(n)) if original <= value else list(order)


def cell_cap(cell: int) -> tuple[float, float, float]:
    """Center and conservative radius in radians (including H3 distortion)."""
    lat, lng = np.radians(h3.cell_to_latlng(cell))
    boundary = np.radians(h3.cell_to_boundary(cell))
    distances = np.arccos(
        np.clip(
            np.sin(lat) * np.sin(boundary[:, 0])
            + np.cos(lat) * np.cos(boundary[:, 0]) * np.cos(boundary[:, 1] - lng),
            -1,
            1,
        )
    )
    # Resolution-4 edges stay within the cap containing their vertices. The
    # margin covers numerical noise; this construction is not for coarse cells
    # spanning a hemisphere.
    return float(lat), float(lng), float(distances.max()) * 1.01


def cell_points(cell: int) -> np.ndarray:
    """Fixed-seed uniform spherical samples, accepted by actual H3 membership."""
    rng = np.random.Generator(np.random.PCG64(cell))
    lat, lng, radius = cell_cap(cell)
    accepted: list[tuple[float, float]] = []
    while len(accepted) < SAMPLES_PER_CELL:
        count = 2 * SAMPLES_PER_CELL
        cos_r = rng.uniform(np.cos(radius), 1, count)
        sin_r = np.sqrt(1 - cos_r * cos_r)
        angle = rng.uniform(0, 2 * np.pi, count)
        phi = np.arcsin(
            np.clip(np.sin(lat) * cos_r + np.cos(lat) * sin_r * np.cos(angle), -1, 1)
        )
        lam = lng + np.arctan2(
            np.sin(angle) * sin_r * np.cos(lat), cos_r - np.sin(lat) * np.sin(phi)
        )
        lats = np.degrees(phi)
        lngs = (np.degrees(lam) + 180) % 360 - 180
        accepted.extend(
            (x, y)
            for x, y in zip(lngs.tolist(), lats.tolist(), strict=True)
            if h3.latlng_to_cell(y, x, SHORTCUT_H3_RES) == cell
        )
    return np.asarray(accepted[:SAMPLES_PER_CELL])


class ShortcutOrderer:
    """Conversion-local geometry/cache ownership; nothing added to runtime state."""

    def __init__(self, data: TimezoneData, output_path: Path):
        self.data = data
        self.boundaries = PolygonArray(utils.get_boundaries_dir(output_path))
        self.holes = HoleArray(utils.get_holes_dir(output_path), self.boundaries)
        self.geometries: dict[int, Polygon] = {}
        self.invalid_geometries: set[int] = set()

    def close(self) -> None:
        self.holes.cleanup()
        self.boundaries.cleanup()

    def geometry(self, pid: int) -> Polygon:
        if pid not in self.geometries:
            self.geometries[pid] = Polygon(
                self.data.polygons[pid].T,
                [hole.T for hole in self.data.holes_in_poly(pid)],
            )
            if not self.geometries[pid].is_valid:
                self.invalid_geometries.add(pid)
        return self.geometries[pid]

    def safe_to_reorder(self, cell: int, ids: list[int]) -> bool:
        """Conservative geometric gate, independent of training samples."""
        lat, lng, radius = cell_cap(cell)
        if abs(lat) + radius >= np.pi / 2:
            return False
        delta = float(np.arcsin(np.sin(radius) / np.cos(lat)))
        if abs(lng) + delta >= np.pi:
            return False
        # Quantization is truncation toward zero, so enlarge each side by one
        # coordinate unit. Covers all integer query coordinates assigned to cell.
        xmin, ymin = np.degrees([lng - delta, lat - radius])
        xmax, ymax = np.degrees([lng + delta, lat + radius])
        envelope = box(
            utils.coord2int(xmin) - 1,
            utils.coord2int(ymin) - 1,
            utils.coord2int(xmax) + 1,
            utils.coord2int(ymax) + 1,
        )
        try:
            geometries = [self.geometry(pid) for pid in ids]
            if any(pid in self.invalid_geometries for pid in ids):
                return False
            clipped = [g.intersection(envelope) for g in geometries]
            for a, b in combinations(range(len(ids)), 2):
                if self.data.poly_zone_ids[ids[a]] != self.data.poly_zone_ids[ids[b]]:
                    if clipped[a].intersection(clipped[b]).area > 0:
                        return False
            return bool(union_all(clipped).covers(envelope))
        except GEOSException:
            return False

    @staticmethod
    def pip_cost(array: PolygonArray, pid: int, y: int) -> int:
        if isinstance(array, HoleArray):
            array, pid = array._resolve(pid)
        start, end = array.block_offsets[pid : pid + 2]
        ranges = array.block_ranges[start:end]
        active = int(np.count_nonzero((ranges[:, 0] <= y) & (y <= ranges[:, 1])))
        return (
            PIP_DISPATCH
            + BLOCK_PROBE * (end - start)
            + ACTIVE_VERTEX * POLYGON_BLOCK_SIZE * active
        )

    def observe(
        self, ids: list[int], points: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Replay the full predicate, recording deterministic work, never timings."""
        hits = np.zeros((len(ids), len(points)), dtype=bool)
        costs = np.zeros(hits.shape, dtype=np.int64)
        for j, (lng, lat) in enumerate(points):
            x, y = utils.coord2int(lng), utils.coord2int(lat)
            for i, pid in enumerate(ids):
                cost = BBOX
                if self.boundaries.outside_bbox(pid, x, y):
                    costs[i, j] = cost
                    continue
                cost += HOLE_LOOKUP
                amount, first = self.data.hole_registry.get(pid, (0, 0))
                in_hole = False
                for hid in range(first, first + amount):
                    cost += HOLE_BBOX
                    if not self.holes.outside_bbox(hid, x, y):
                        cost += self.pip_cost(self.holes, hid, y)
                        if self.holes.pip(hid, x, y):
                            in_hole = True
                            break
                if not in_hole:
                    cost += self.pip_cost(self.boundaries, pid, y)
                    hits[i, j] = self.boundaries.pip(pid, x, y)
                costs[i, j] = cost
        return hits, costs

    def order(self, cell: int, ids: list[int]) -> list[int]:
        zones = [int(self.data.poly_zone_ids[pid]) for pid in ids]
        if len(set(zones)) <= 1 or len(ids) > MAX_EXACT_CANDIDATES:
            return ids
        if not self.safe_to_reorder(cell, ids):
            return ids
        hits, costs = self.observe(ids, cell_points(cell))
        return [ids[i] for i in optimal_order(zones, hits, costs)]
