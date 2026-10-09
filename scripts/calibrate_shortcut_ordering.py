"""Calibrate and validate the shortcut-ordering work model against real predicates.

The converter remains deterministic and timing-free.  This command runs separately,
against the packaged data and committed benchmark fixtures, and writes a reviewable
JSON artifact.  Its counters are adapters around the real predicate methods: the
production early exits execute unchanged, while the adapters count the events mapped
to :class:`scripts.shortcut_ordering.CostCoefficients`.

The fitted coefficients are proposals, never production input.  Changing the reviewed
defaults still requires an ordinary source edit, regenerated shortcut data and the
normal correctness/whole-query gates.  Re-run it when the predicate path, the packed
kernels or the boundary data change; ``--record`` copies a reviewed run's summary into
the model file.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date
import hashlib
import json
import math
import platform
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Final, Iterable, Iterator, Sequence, cast

import h3.api.numpy_int as h3
import numpy as np
from shapely import Polygon

from benchmarks.candidate_comparison import compare_candidates
from scripts.benchmark_utils import cpu_info, get_system_status
from scripts.assert_acceleration_path import (
    PACKED_ACCELERATION_IMPLEMENTATIONS,
    PACKED_BUFFER_FACTORIES,
    active_acceleration_path,
)
from scripts.shortcut_ordering import (
    DEFAULT_COST_COEFFICIENTS,
    CostCoefficients,
    ShortcutOrderer,
)
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    benchmark_fixture_provenance,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import (
    INT2COORD_FACTOR,
    POLYGON_BLOCK_SIZE,
    SHORTCUT_H3_RES,
)
from timezonefinder.polygon_array import HoleArray, PolygonArray
from timezonefinder.shortcut_index import ABSENT, get_last_change_idx

SCHEMA_VERSION: Final[int] = 2
MODEL_PATH = Path("benchmarks/shortcut_ordering_model.json")
FEATURES: Final[tuple[str, ...]] = (
    "bbox",
    "hole_union_probe",
    "hole_lookup",
    "hole_bbox",
    "pip_dispatch",
    "block_probe",
    "active_vertex",
)
STRATA: Final[dict[str, str]] = {
    "random": RANDOM_POINTS_FIXTURE,
    "on_land": ON_LAND_POINTS_FIXTURE,
    "ambiguous_shortcut": AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    "unique_shortcut": UNIQUE_SHORTCUT_POINTS_FIXTURE,
}
#: the area-only alternative: every candidate costs one check, so only coverage counts
AREA_ONLY_COEFFICIENTS: Final = CostCoefficients(
    bbox=1.0,
    hole_union_probe=0.0,
    hole_lookup=0.0,
    hole_bbox=0.0,
    pip_dispatch=0.0,
    block_probe=0.0,
    active_vertex=0.0,
)


@dataclass
class StageCounts:
    """Runtime events with a one-to-one mapping to the model coefficients."""

    bbox: int = 0
    hole_union_probe: int = 0
    hole_lookup: int = 0
    hole_bbox: int = 0
    pip_dispatch: int = 0
    block_probe: int = 0
    active_vertex: int = 0
    hole_hit: int = 0

    def vector(self) -> list[float]:
        return [float(getattr(self, name)) for name in FEATURES]

    def add(self, other: StageCounts) -> None:
        for name in self.__dataclass_fields__:
            setattr(self, name, getattr(self, name) + getattr(other, name))


@dataclass(frozen=True)
class Observation:
    cell: int
    polygon_id: int
    elapsed_ns: int
    matched: bool
    counts: StageCounts


@contextmanager
def _bound_backend(backend: str) -> Iterator[None]:
    """Bind a packed backend while collections capture its kernel and buffers."""
    if backend == "auto":
        yield
        return
    previous = (utils.inside_polygon_packed, utils.packed_buffers)
    utils.inside_polygon_packed = PACKED_ACCELERATION_IMPLEMENTATIONS[backend]
    utils.packed_buffers = PACKED_BUFFER_FACTORIES[backend]
    try:
        yield
    finally:
        utils.inside_polygon_packed, utils.packed_buffers = previous


def _sum_counts(observations: Sequence[Observation]) -> dict[str, int]:
    total = StageCounts()
    for observation in observations:
        total.add(observation.counts)
    return asdict(total)


def check_model(
    path: Path = MODEL_PATH, *, require_record: bool = True
) -> dict[str, Any]:
    """Refuse a model file that does not describe the reviewed coefficients.

    Deliberately not a source fingerprint: ordering never changes an answer, so a
    stale calibration costs at most a little speed, while a hash over predicate
    source fails on every unrelated edit. What must agree is what a reviewer reads:
    the coefficients in source, the ones the file maps, and the ones its recorded
    run compared against.
    """
    model = json.loads(path.read_text(encoding="utf-8"))
    if model.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"{path} has schema {model.get('schema_version')!r}, expected {SCHEMA_VERSION}"
        )
    current_coefficients = asdict(DEFAULT_COST_COEFFICIENTS)
    if model.get("production_coefficients") != current_coefficients:
        raise ValueError(
            f"{path} does not record the production coefficients in "
            "scripts/shortcut_ordering.py"
        )
    if set(model.get("feature_mapping", ())) != set(FEATURES):
        raise ValueError(
            f"{path}: the feature mapping does not name exactly the fitted features"
        )
    recorded = model.get("latest_recorded_validation", {})
    if (
        require_record
        and recorded.get("production_coefficients") != current_coefficients
    ):
        raise ValueError(
            "the recorded calibration run compared different production coefficients; "
            "re-run `make shortcut-calibration` and `make shortcut-calibration-record`"
        )
    return model


class _PolygonProbe:
    def __init__(self, array: PolygonArray, counts: StageCounts, *, hole: bool):
        self._array = array
        self._counts = counts
        self._hole = hole

    def __getattr__(self, name: str) -> Any:
        return getattr(self._array, name)

    def outside_bbox(self, polygon_id: int, x: int, y: int) -> bool:
        if self._hole:
            self._counts.hole_bbox += 1
        else:
            self._counts.bbox += 1
        return self._array.outside_bbox(polygon_id, x, y)

    def pip_with_bbox_check(self, polygon_id: int, x: int, y: int) -> bool:
        return PolygonArray.pip_with_bbox_check(cast(Any, self), polygon_id, x, y)

    def pip(self, polygon_id: int, x: int, y: int) -> bool:
        collection: PolygonArray = self._array
        storage_id = polygon_id
        if self._hole:
            collection, storage_id = cast(HoleArray, self._array)._resolve(polygon_id)
        start = collection.block_offsets[storage_id]
        stop = collection.block_offsets[storage_id + 1]
        ranges = collection.block_ranges[start:stop]
        self._counts.pip_dispatch += 1
        self._counts.block_probe += stop - start
        self._counts.active_vertex += (
            int(np.count_nonzero((ranges[:, 0] <= y) & (y <= ranges[:, 1])))
            * POLYGON_BLOCK_SIZE
        )
        return self._array.pip(polygon_id, x, y)


class _HoleProbe(_PolygonProbe):
    def __init__(self, array: HoleArray, counts: StageCounts):
        super().__init__(array, counts, hole=True)

    def ids_of(self, boundary_id: int) -> range:
        self._counts.hole_lookup += 1
        return cast(HoleArray, self._array).ids_of(boundary_id)

    def in_any_polygon(self, polygon_ids: Iterable[int], x: int, y: int) -> bool:
        return PolygonArray.in_any_polygon(cast(Any, self), polygon_ids, x, y)

    def any_contains(self, boundary_id: int, x: int, y: int) -> bool:
        self._counts.hole_union_probe += 1
        matched = HoleArray.any_contains(cast(Any, self), boundary_id, x, y)
        if matched:
            self._counts.hole_hit += 1
        return matched


def trace_predicate(
    finder: TimezoneFinder, polygon_id: int, x: int, y: int
) -> tuple[bool, StageCounts]:
    """Run the real top-level predicate with counting adapters underneath it."""
    counts = StageCounts()
    probe = SimpleNamespace(
        boundaries=_PolygonProbe(finder.boundaries, counts, hole=False),
        holes=_HoleProbe(finder.holes, counts),
    )
    matched = TimezoneFinder.inside_of_polygon(cast(Any, probe), polygon_id, x, y)
    return matched, counts


def _minimum_predicate_ns(
    finder: TimezoneFinder,
    polygon_id: int,
    x: int,
    y: int,
    repetitions: int,
) -> int:
    best = 2**63 - 1
    for _ in range(repetitions):
        started = time.perf_counter_ns()
        finder.inside_of_polygon(polygon_id, x, y)
        best = min(best, time.perf_counter_ns() - started)
    return best


def _validation_cell(cell: int) -> bool:
    digest = hashlib.sha256(cell.to_bytes(8, "little", signed=False)).digest()
    return digest[0] < 64


def collect_observations(
    finder: TimezoneFinder,
    points: Sequence[tuple[float, float]],
    repetitions: int,
) -> tuple[list[Observation], StageCounts]:
    observations: list[Observation] = []
    total = StageCounts()
    for lng, lat in points:
        cell = int(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES))
        entry = finder.shortcuts.entry_of(cell)
        if entry >= ABSENT:
            continue
        candidates = finder.shortcuts.candidates_of(entry)
        stop = finder.shortcuts.stop_index_of(entry)
        x, y = utils.coord2int(lng), utils.coord2int(lat)
        for polygon_id_value in candidates[:stop]:
            polygon_id = int(polygon_id_value)
            matched, counts = trace_predicate(finder, polygon_id, x, y)
            total.add(counts)
            observations.append(
                Observation(
                    cell=cell,
                    polygon_id=polygon_id,
                    elapsed_ns=_minimum_predicate_ns(
                        finder, polygon_id, x, y, repetitions
                    ),
                    matched=matched,
                    counts=counts,
                )
            )
            if matched:
                break
    return observations, total


def collect_hole_hit_observations(
    finder: TimezoneFinder, repetitions: int, limit: int = 24
) -> list[Observation]:
    """Deliberately cover the rare successful-hole early exit.

    The ordinary fixtures represent real workload proportions and may contain no hole
    hit in a bounded run.  These targeted observations are reported separately and do
    not enter the fit, so oversampling a rare path cannot bias its coefficients.
    """
    observations = []
    registry = finder.holes.hole_registry
    if registry is None:
        raise RuntimeError("finder has no hole registry")
    for polygon_id, (amount, first_hole_id) in registry.items():
        if not amount:
            continue
        point = Polygon(finder.holes.coords_of(first_hole_id).T).representative_point()
        x, y = round(point.x), round(point.y)
        matched, counts = trace_predicate(finder, polygon_id, x, y)
        if matched or counts.hole_hit != 1:
            continue
        lng, lat = x * INT2COORD_FACTOR, y * INT2COORD_FACTOR
        observations.append(
            Observation(
                cell=int(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)),
                polygon_id=int(polygon_id),
                elapsed_ns=_minimum_predicate_ns(
                    finder, int(polygon_id), x, y, repetitions
                ),
                matched=False,
                counts=counts,
            )
        )
        if len(observations) >= limit:
            break
    if not observations:
        raise RuntimeError("packaged geometry produced no successful-hole observation")
    return observations


def _fit_nonnegative(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Small dependency-free NNLS coordinate descent for seven nonnegative terms."""
    coefficients = np.zeros(x.shape[1], dtype=np.float64)
    for _ in range(10_000):
        previous = coefficients.copy()
        for column in range(x.shape[1]):
            values = x[:, column]
            denominator = float(values @ values)
            if denominator == 0:
                continue
            residual = y - x @ coefficients + values * coefficients[column]
            coefficients[column] = max(0.0, float(values @ residual) / denominator)
        if np.max(np.abs(coefficients - previous)) < 1e-8:
            break
    return coefficients


def _fit_report(
    calibration: Sequence[Observation], validation: Sequence[Observation], seed: int
) -> dict[str, Any]:
    x_cal = np.asarray([o.counts.vector() for o in calibration], dtype=np.float64)
    y_cal = np.asarray([o.elapsed_ns for o in calibration], dtype=np.float64)
    x_val = np.asarray([o.counts.vector() for o in validation], dtype=np.float64)
    y_val = np.asarray([o.elapsed_ns for o in validation], dtype=np.float64)
    coefficients = _fit_nonnegative(x_cal, y_cal)
    predicted = x_val @ coefficients
    residual = y_val - predicted
    rng = np.random.default_rng(seed)
    bootstraps = []
    for _ in range(100):
        sample = rng.integers(0, len(calibration), size=len(calibration))
        bootstraps.append(_fit_nonnegative(x_cal[sample], y_cal[sample]))
    bootstrap = np.asarray(bootstraps)
    with np.errstate(invalid="ignore", divide="ignore"):
        correlation = np.nan_to_num(np.corrcoef(x_cal, rowvar=False), nan=0.0)
    return {
        "calibration_observations": len(calibration),
        "validation_observations": len(validation),
        "coefficients_ns": dict(zip(FEATURES, coefficients.tolist(), strict=True)),
        "coefficient_interval_90pct_ns": {
            name: [float(low), float(high)]
            for name, low, high in zip(
                FEATURES,
                np.percentile(bootstrap, 5, axis=0),
                np.percentile(bootstrap, 95, axis=0),
                strict=True,
            )
        },
        "feature_correlation": {
            row: {
                column: float(correlation[row_index, column_index])
                for column_index, column in enumerate(FEATURES)
            }
            for row_index, row in enumerate(FEATURES)
        },
        "held_out_error_ns": {
            "median_absolute": float(np.median(np.abs(residual))),
            "p95_absolute": float(np.percentile(np.abs(residual), 95)),
            "median_signed": float(np.median(residual)),
        },
    }


class _RuntimeHoles:
    def __init__(self, holes: HoleArray):
        self.holes = holes

    def holes_of_poly(self, polygon_id: int) -> list[np.ndarray]:
        return [self.holes.coords_of(i) for i in self.holes.ids_of(polygon_id)]


def _runtime_orderer(
    finder: TimezoneFinder, coefficients: CostCoefficients
) -> ShortcutOrderer:
    orderer = object.__new__(ShortcutOrderer)
    orderer.data = cast(
        Any,
        SimpleNamespace(
            boundaries=finder.boundaries,
            holes=_RuntimeHoles(finder.holes),
            hole_registry=finder.holes.hole_registry,
            poly_zone_ids=finder.zone_ids,
        ),
    )
    orderer.coefficients = coefficients
    orderer.boundaries = finder.boundaries
    orderer.holes = finder.holes
    orderer.geometries = {}
    orderer.invalid_geometries = set()
    orderer.models = {}
    return orderer


class _ReorderedIndex:
    """Delegate every cell except a bounded held-out set with alternative orders."""

    def __init__(self, base: Any, orders: dict[int, list[int]], zone_ids: np.ndarray):
        self.base = base
        self.cell_entries = {
            cell: -1_000_000 - i for i, cell in enumerate(sorted(orders))
        }
        self.orders = {
            self.cell_entries[cell]: np.asarray(order, dtype=np.uint16)
            for cell, order in orders.items()
        }
        self.stops = {
            entry: get_last_change_idx(zone_ids[order])
            for entry, order in self.orders.items()
        }

    def entry_of(self, cell: int) -> int:
        return self.cell_entries.get(cell, self.base.entry_of(cell))

    def candidates_of(self, entry: int) -> np.ndarray:
        if entry in self.orders:
            return self.orders[entry]
        return self.base.candidates_of(entry)

    def stop_index_of(self, entry: int) -> int:
        if entry in self.stops:
            return self.stops[entry]
        return self.base.stop_index_of(entry)


def ambiguous_cells(finder: TimezoneFinder) -> dict[int, list[int]]:
    """Every shortcut cell whose stored order the optimizer could change."""
    cells = {}
    for root in h3.get_res0_cells():
        for child in h3.cell_to_children(root, SHORTCUT_H3_RES):
            cell = int(child)
            entry = finder.shortcuts.entry_of(cell)
            if entry < ABSENT:
                candidates = finder.shortcuts.candidates_of(entry).astype(int).tolist()
                if len(candidates) > 1:
                    cells[cell] = candidates
    return cells


def sample_cell_points(
    cell: int, amount: int, rng: random.Random
) -> list[tuple[float, float]]:
    """Points uniform on the sphere inside one H3 cell, by rejection from its box."""
    boundary = np.asarray(h3.cell_to_boundary(cell))
    lats, lngs = boundary[:, 0], boundary[:, 1]
    lat_low, lat_high = lats.min(), lats.max()
    if int(h3.latlng_to_cell(90.0, 0.0, SHORTCUT_H3_RES)) == cell:
        lat_high, lngs = 90.0, np.asarray([-180.0, 180.0])
    elif int(h3.latlng_to_cell(-90.0, 0.0, SHORTCUT_H3_RES)) == cell:
        lat_low, lngs = -90.0, np.asarray([-180.0, 180.0])
    elif lngs.max() - lngs.min() > 180:
        # the cell straddles the antimeridian: sample the box east of it, unwrapped
        lngs = np.where(lngs < 0, lngs + 360, lngs)
    low = math.sin(math.radians(lat_low))
    high = math.sin(math.radians(lat_high))
    points: list[tuple[float, float]] = []
    while len(points) < amount:
        lat = math.degrees(math.asin(rng.uniform(low, high)))
        lng = rng.uniform(lngs.min(), lngs.max())
        lng = lng - 360 if lng > 180 else lng
        if int(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)) == cell:
            points.append((lng, lat))
    return points


def _query_counts(
    finder: TimezoneFinder, index: Any, lng: float, lat: float
) -> StageCounts:
    """Stage counts of the real candidate walk one query makes under ``index``."""
    entry = index.entry_of(int(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)))
    candidates = index.candidates_of(entry)
    stop = index.stop_index_of(entry)
    x, y = utils.coord2int(lng), utils.coord2int(lat)
    total = StageCounts()
    for polygon_id in candidates[:stop]:
        matched, counts = trace_predicate(finder, int(polygon_id), x, y)
        total.add(counts)
        if matched:
            break
    return total


def _modeled_ns(counts: StageCounts, coefficients: CostCoefficients) -> float:
    return sum(getattr(counts, name) * getattr(coefficients, name) for name in FEATURES)


def _ordering_report(
    finder: TimezoneFinder,
    cells: dict[int, list[int]],
    alternative: CostCoefficients,
    fitted: CostCoefficients,
    *,
    points_per_cell: int,
    rounds: int,
    seeds: int,
    rng: random.Random,
) -> dict[str, Any]:
    """Re-order every eligible cell and measure the cells the alternative changes.

    Every cell is evaluated, not a sample: the cells an order change touches are a
    few percent of all ambiguous cells and rarely the most-visited ones, so a bounded
    sample can show no change at all. The whole-query A/B runs on uniform points in
    the changed cells only, where the effect lives; the per-stratum share of fixture
    queries landing in those cells says how far it dilutes in a real workload.
    """
    base_index = finder.shortcuts
    orderer = _runtime_orderer(finder, alternative)
    changed = {}
    for cell, candidates in cells.items():
        order = orderer.order(cell, candidates)
        if order != candidates:
            changed[cell] = order
    earth = sum(
        h3.cell_area(int(child), "rads^2")
        for root in h3.get_res0_cells()
        for child in h3.cell_to_children(root, SHORTCUT_H3_RES)
    )
    workload_share = {}
    for stratum, fixture in STRATA.items():
        points = load_benchmark_points(fixture)
        hits = sum(
            int(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)) in changed
            for lng, lat in points
        )
        workload_share[stratum] = hits / len(points)
    report: dict[str, Any] = {
        "eligible_cells": len(cells),
        "changed_cells": len(changed),
        "changed_area_share_of_sphere": sum(
            h3.cell_area(cell, "rads^2") for cell in changed
        )
        / earth,
        "fixture_query_share_in_changed_cells": workload_share,
    }
    if not changed:
        return report
    points = [
        point
        for cell in sorted(changed)
        for point in sample_cell_points(cell, points_per_cell, rng)
    ]
    current = _ReorderedIndex(
        base_index, {cell: cells[cell] for cell in changed}, finder.zone_ids
    )
    reordered = _ReorderedIndex(base_index, changed, finder.zone_ids)
    current_counts, reordered_counts = StageCounts(), StageCounts()
    modeled: dict[str, list[float]] = {"production": [], "fitted": []}
    try:
        for lng, lat in points:
            finder.shortcuts = cast(Any, current)
            expected = finder.timezone_at(lng=lng, lat=lat)
            before = _query_counts(finder, current, lng, lat)
            finder.shortcuts = cast(Any, reordered)
            if finder.timezone_at(lng=lng, lat=lat) != expected:
                raise AssertionError(f"reordering changed the answer at {lng}, {lat}")
            after = _query_counts(finder, reordered, lng, lat)
            current_counts.add(before)
            reordered_counts.add(after)
            for name, coefficients in (
                ("production", DEFAULT_COST_COEFFICIENTS),
                ("fitted", fitted),
            ):
                modeled[name].append(
                    _modeled_ns(after, coefficients) - _modeled_ns(before, coefficients)
                )

        def lookup(index: Any):
            def run(point: tuple[float, float]) -> object:
                finder.shortcuts = index
                return finder.timezone_at(lng=point[0], lat=point[1])

            return run

        comparisons = []
        for seed in range(seeds):
            comparison = compare_candidates(
                ("production", lookup(current)),
                ("alternative", lookup(reordered)),
                points,
                rounds=rounds,
                batch_size=min(2_500, len(points)),
                seed=seed,
            )
            comparisons.append(
                {
                    **asdict(comparison),
                    "best_round_change": comparison.best_round_change,
                    "win_share": comparison.win_share,
                    "verdict": comparison.verdict,
                }
            )
    finally:
        finder.shortcuts = base_index
    changes = [c["best_round_change"] for c in comparisons]
    verdicts = [c["verdict"] for c in comparisons]
    report.update(
        {
            "points": len(points),
            "points_per_cell": points_per_cell,
            "answers_identical": True,
            "stage_counts": {
                "production_order": asdict(current_counts),
                "alternative_order": asdict(reordered_counts),
            },
            # deterministic: the counted work difference, priced by each model
            "modeled_change_ns_per_query": {
                name: float(np.mean(values)) for name, values in modeled.items()
            },
            "whole_query": {
                "seeds": seeds,
                "median_best_round_change": float(np.median(changes)),
                "best_round_change_range": [min(changes), max(changes)],
                "verdicts": {v: verdicts.count(v) for v in sorted(set(verdicts))},
                "comparisons": comparisons,
            },
        }
    )
    return report


def measure(
    *,
    points_per_stratum: int,
    repetitions: int,
    comparison_rounds: int,
    comparison_seeds: int,
    points_per_changed_cell: int,
    seed: int,
    in_memory: bool,
    backend: str,
) -> dict[str, Any]:
    # a run is how a stale record gets replaced, so it must not require a fresh one
    model = check_model(require_record=False)
    all_observations: list[Observation] = []
    stage_counts: dict[str, dict[str, int]] = {}
    whole_query_ns: dict[str, float] = {}
    with _bound_backend(backend):
        measured_backend = active_acceleration_path()
        finder = TimezoneFinder(in_memory=in_memory)
    with finder:
        # Pay any JIT compilation and first page faults before a candidate is timed.
        warm_lng, warm_lat = load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)[0]
        finder.timezone_at(lng=warm_lng, lat=warm_lat)
        for stratum, fixture in STRATA.items():
            points = load_benchmark_points(fixture)[:points_per_stratum]
            started = time.perf_counter_ns()
            for lng, lat in points:
                finder.timezone_at(lng=lng, lat=lat)
            whole_query_ns[stratum] = (time.perf_counter_ns() - started) / len(points)
            observations, counts = collect_observations(finder, points, repetitions)
            stage_counts[stratum] = asdict(counts)
            all_observations.extend(observations)
        calibration = [o for o in all_observations if not _validation_cell(o.cell)]
        validation = [o for o in all_observations if _validation_cell(o.cell)]
        if not calibration or not validation:
            raise RuntimeError(
                "deterministic cell split produced an empty fit partition"
            )
        fit = _fit_report(calibration, validation, seed)
        targeted_hole_hits = collect_hole_hit_observations(finder, repetitions)
        fitted = CostCoefficients(**fit["coefficients_ns"])
        # The fit saw predicate timings from these cells; keep them out of the
        # ordering evaluation so it only scores cells the coefficients never saw.
        fit_cells = {o.cell for o in calibration}
        cells = {
            cell: candidates
            for cell, candidates in ambiguous_cells(finder).items()
            if cell not in fit_cells
        }
        rng = random.Random(seed)
        ordering = {
            name: _ordering_report(
                finder,
                cells,
                coefficients,
                fitted,
                points_per_cell=points_per_changed_cell,
                rounds=comparison_rounds,
                seeds=comparison_seeds,
                rng=rng,
            )
            for name, coefficients in (
                ("calibrated", fitted),
                ("area_only", AREA_ONLY_COEFFICIENTS),
            )
        }
    system = get_system_status()
    system["using_numba"] = measured_backend == "numba"
    system["using_clang_pip"] = measured_backend == "clang"
    return {
        "schema_version": SCHEMA_VERSION,
        "reference_policy": model["reference_policy"],
        "provenance": {
            "date": date.today().isoformat(),
            "production_coefficients": asdict(DEFAULT_COST_COEFFICIENTS),
            "fixtures": benchmark_fixture_provenance(),
            "system": system,
            "cpu": cpu_info(),
            "python": platform.python_version(),
            "acceleration_path": measured_backend,
            "storage_mode": "in_memory" if in_memory else "mapped",
            "points_per_stratum": points_per_stratum,
            "candidate_repetitions": repetitions,
            "comparison_rounds": comparison_rounds,
            "comparison_seeds": comparison_seeds,
            "points_per_changed_cell": points_per_changed_cell,
            "cell_partition": "sha256(cell little-endian)[0] < 64 is held out",
            "ordering_cells": "every ambiguous cell without a fit observation",
            "seed": seed,
        },
        "stage_counts": stage_counts,
        "whole_query_ns_per_call": whole_query_ns,
        "fit": fit,
        "targeted_hole_hits": {
            "observations": len(targeted_hole_hits),
            "stage_counts": _sum_counts(targeted_hole_hits),
            "elapsed_ns": [o.elapsed_ns for o in targeted_hole_hits],
        },
        "ordering": ordering,
        "limitations": model["structural_limitations"],
    }


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    """The reviewable digest of one run that the model file keeps."""
    provenance = report["provenance"]
    fit = report["fit"]
    summary: dict[str, Any] = {
        "date": provenance["date"],
        **provenance["fixtures"],
        "acceleration_path": provenance["acceleration_path"],
        "storage_mode": provenance["storage_mode"],
        "cpu": provenance["cpu"].get("brand_raw", provenance["cpu"]),
        "production_coefficients": provenance["production_coefficients"],
        "fitted_coefficients_ns": fit["coefficients_ns"],
        "calibration_observations": fit["calibration_observations"],
        "held_out_observations": fit["validation_observations"],
        "held_out_median_absolute_error_ns": fit["held_out_error_ns"][
            "median_absolute"
        ],
        "held_out_p95_absolute_error_ns": fit["held_out_error_ns"]["p95_absolute"],
        "ordering": {},
        "reproduce": "make shortcut-calibration, or dispatch benchmark.yml with "
        "calibrate_shortcuts=true; then make shortcut-calibration-record",
    }
    for name, ordering in report["ordering"].items():
        digest = {
            key: ordering[key]
            for key in (
                "eligible_cells",
                "changed_cells",
                "changed_area_share_of_sphere",
                "fixture_query_share_in_changed_cells",
            )
        }
        if "whole_query" in ordering:
            whole_query = ordering["whole_query"]
            digest |= {
                "points": ordering["points"],
                "modeled_change_ns_per_query": ordering["modeled_change_ns_per_query"],
                "median_best_round_change": whole_query["median_best_round_change"],
                "best_round_change_range": whole_query["best_round_change_range"],
                "verdicts": whole_query["verdicts"],
            }
        summary["ordering"][name] = digest
    return summary


def record(report_path: Path, model_path: Path = MODEL_PATH) -> dict[str, Any]:
    """Write a run's summary into the model file, keeping its reviewed decision."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    model = json.loads(model_path.read_text(encoding="utf-8"))
    previous = model.get("latest_recorded_validation", {})
    summary = summarize(report)
    # The decision is a reviewer's sentence, not a measurement: carry it until edited.
    summary["decision"] = previous.get("decision", "pending review")
    model["latest_recorded_validation"] = summary
    model_path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--record",
        type=Path,
        metavar="REPORT",
        help="copy the summary of a finished run into the model file and exit",
    )
    parser.add_argument("--points-per-stratum", type=int, default=1_000)
    parser.add_argument("--candidate-repetitions", type=int, default=7)
    parser.add_argument("--comparison-rounds", type=int, default=61)
    parser.add_argument("--comparison-seeds", type=int, default=8)
    parser.add_argument("--points-per-changed-cell", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260910)
    parser.add_argument("--in-memory", action="store_true")
    parser.add_argument(
        "--backend",
        choices=("auto", *PACKED_ACCELERATION_IMPLEMENTATIONS),
        default="auto",
    )
    args = parser.parse_args()
    if args.record is not None:
        summary = record(args.record)
        print(json.dumps(summary["ordering"], indent=2))
        print(f"Recorded {args.record} in {MODEL_PATH}; review its decision line")
        return
    if args.output is None:
        parser.error("--output is required unless --record is used")
    if (
        min(
            args.points_per_stratum,
            args.candidate_repetitions,
            args.comparison_seeds,
            args.points_per_changed_cell,
        )
        < 1
        or args.comparison_rounds < 2
    ):
        parser.error("all measurement sizes must be positive, and rounds at least 2")
    report = measure(
        points_per_stratum=args.points_per_stratum,
        repetitions=args.candidate_repetitions,
        comparison_rounds=args.comparison_rounds,
        comparison_seeds=args.comparison_seeds,
        points_per_changed_cell=args.points_per_changed_cell,
        seed=args.seed,
        in_memory=args.in_memory,
        backend=args.backend,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summarize(report)["ordering"], indent=2))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
