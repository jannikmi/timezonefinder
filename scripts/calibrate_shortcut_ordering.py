"""Calibrate and validate the shortcut-ordering work model against real predicates.

The converter remains deterministic and timing-free.  This command runs separately,
against the packaged data and committed benchmark fixtures, and writes a reviewable
JSON artifact.  Its counters are adapters around the real predicate methods: the
production early exits execute unchanged, while the adapters count the events mapped
to :class:`scripts.shortcut_ordering.CostCoefficients`.

The fitted coefficients are proposals, never production input.  Changing the reviewed
defaults still requires an ordinary source edit, regenerated shortcut data and the
normal correctness/whole-query gates.
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import inspect
import json
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Final, Iterable, Iterator, Sequence, cast

import h3.api.numpy_int as h3
import numpy as np
from shapely import Polygon

from benchmarks import candidate_comparison
from benchmarks.candidate_comparison import compare_candidates
from scripts.benchmark_utils import cpu_info, get_system_status
from scripts.assert_acceleration_path import (
    PACKED_ACCELERATION_IMPLEMENTATIONS,
    PACKED_BUFFER_FACTORIES,
    active_acceleration_path,
)
from scripts.shortcut_ordering import (
    CELL_AREA_RTOL,
    IMPROVEMENT_RTOL,
    CellOptimizer,
    CheckCost,
    DEFAULT_COST_COEFFICIENTS,
    CostCoefficients,
    ShortcutOrderer,
    _cell_region,
    cell_cap,
    cell_region,
    improves,
    spherical_area,
)
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    benchmark_fixture_provenance,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder, utils, utils_clang, utils_numba
from timezonefinder.configs import (
    COORD2INT_FACTOR,
    INT2COORD_FACTOR,
    POLYGON_BLOCK_SIZE,
    SHORTCUT_H3_RES,
    SOURCE_COORD_STEP,
)
from timezonefinder.polygon_array import HoleArray, PolygonArray
from timezonefinder.shortcut_index import (
    ABSENT,
    SLOT_DIGITS_SHIFT,
    SLOT_MASK,
    ShortcutIndex,
    get_last_change_idx,
)

SCHEMA_VERSION: Final[int] = 1
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
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_FINGERPRINT_PATHS = (
    "timezonefinder/inside_poly_extension/inside_polygon_int.c",
    "timezonefinder/inside_poly_extension/inside_polygon_int.h",
)
_LOCAL_FINGERPRINT_NAMES = (
    "StageCounts",
    "Observation",
    "_bound_backend",
    "_sum_counts",
    "_PolygonProbe",
    "_HoleProbe",
    "trace_predicate",
    "_minimum_predicate_ns",
    "_validation_cell",
    "collect_observations",
    "collect_hole_hit_observations",
    "_fit_nonnegative",
    "_fit_report",
    "_RuntimeHoles",
    "_runtime_orderer",
    "_ReorderedIndex",
    "_ordering_report",
    "measure",
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


def model_input_fingerprint() -> dict[str, Any]:
    """Hash the model, probes, kernels and fixture/data identity they measured."""

    def callable_name(function: Any) -> str:
        return f"{function.__module__}.{function.__qualname__}"

    symbols = {
        "scripts.shortcut_ordering.CostCoefficients": CostCoefficients,
        "scripts.shortcut_ordering.CheckCost": CheckCost,
        "scripts.shortcut_ordering.CellOptimizer": CellOptimizer,
        "scripts.shortcut_ordering.spherical_area": spherical_area,
        "scripts.shortcut_ordering._cell_region": _cell_region,
        "scripts.shortcut_ordering.cell_region": cell_region,
        "scripts.shortcut_ordering.cell_cap": cell_cap,
        "scripts.shortcut_ordering.improves": improves,
        "scripts.shortcut_ordering.ShortcutOrderer.geometry": ShortcutOrderer.geometry,
        "scripts.shortcut_ordering.ShortcutOrderer.safe_to_reorder": ShortcutOrderer.safe_to_reorder,
        "scripts.shortcut_ordering.ShortcutOrderer.bounds": ShortcutOrderer.bounds,
        "scripts.shortcut_ordering.ShortcutOrderer.intersection": ShortcutOrderer.intersection,
        "scripts.shortcut_ordering.ShortcutOrderer.add_pip": ShortcutOrderer.add_pip,
        "scripts.shortcut_ordering.ShortcutOrderer.model": ShortcutOrderer.model,
        "scripts.shortcut_ordering.ShortcutOrderer.order": ShortcutOrderer.order,
        "timezonefinder.timezonefinder.TimezoneFinder.inside_of_polygon": TimezoneFinder.inside_of_polygon,
        "timezonefinder.timezonefinder.TimezoneFinder.timezone_at": TimezoneFinder.timezone_at,
        "timezonefinder.timezonefinder.TimezoneFinder._zone_id_among": TimezoneFinder._zone_id_among,
        "timezonefinder.timezonefinder.TimezoneFinder._zone_id_in_ambiguous_cell": TimezoneFinder._zone_id_in_ambiguous_cell,
        "timezonefinder.polygon_array.PolygonArray.outside_bbox": PolygonArray.outside_bbox,
        "timezonefinder.polygon_array.PolygonArray._pip_at": PolygonArray._pip_at,
        "timezonefinder.polygon_array.PolygonArray.pip_with_bbox_check": PolygonArray.pip_with_bbox_check,
        "timezonefinder.polygon_array.PolygonArray.in_any_polygon": PolygonArray.in_any_polygon,
        "timezonefinder.polygon_array.HoleArray.ids_of": HoleArray.ids_of,
        "timezonefinder.polygon_array.HoleArray.any_contains": HoleArray.any_contains,
        "timezonefinder.polygon_array.HoleArray._resolve": HoleArray._resolve,
        "timezonefinder.polygon_array.HoleArray.pip": HoleArray.pip,
        "timezonefinder.polygon_array.HoleArray._build_union_bounds": HoleArray._build_union_bounds,
        "timezonefinder.shortcut_index.ShortcutIndex.entry_of": ShortcutIndex.entry_of,
        "timezonefinder.shortcut_index.ShortcutIndex.candidates_of": ShortcutIndex.candidates_of,
        "timezonefinder.shortcut_index.ShortcutIndex.stop_index_of": ShortcutIndex.stop_index_of,
        "timezonefinder.shortcut_index.get_last_change_idx": get_last_change_idx,
        "timezonefinder.utils.coord2int": utils.coord2int,
        "timezonefinder.utils.validate_coordinates": utils.validate_coordinates,
        "timezonefinder.utils_numba.pt_in_poly_packed": utils_numba.pt_in_poly_packed,
        "timezonefinder.utils_numba._residual_at": utils_numba._residual_at,
        "timezonefinder.utils_numba.packed_buffers_numba": utils_numba.packed_buffers_numba,
        "timezonefinder.utils_clang.pt_in_poly_clang_packed": utils_clang.pt_in_poly_clang_packed,
        "timezonefinder.utils_clang.packed_buffers_clang": utils_clang.packed_buffers_clang,
        "scripts.assert_acceleration_path.active_acceleration_path": active_acceleration_path,
        "benchmarks.candidate_comparison.CandidateComparison": candidate_comparison.CandidateComparison,
        "benchmarks.candidate_comparison.compare_candidates": candidate_comparison.compare_candidates,
    }
    symbols.update(
        {
            f"scripts.calibrate_shortcut_ordering.{name}": globals()[name]
            for name in _LOCAL_FINGERPRINT_NAMES
        }
    )
    digest = hashlib.sha256()
    for name, symbol in symbols.items():
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(inspect.getsource(symbol).encode())
        digest.update(b"\0")
    for relative_path in _FINGERPRINT_PATHS:
        digest.update(relative_path.encode())
        digest.update(b"\0")
        digest.update((_PROJECT_ROOT / relative_path).read_bytes())
        digest.update(b"\0")
    fixtures = benchmark_fixture_provenance()
    constants = {
        "COORD2INT_FACTOR": COORD2INT_FACTOR,
        "INT2COORD_FACTOR": INT2COORD_FACTOR,
        "POLYGON_BLOCK_SIZE": POLYGON_BLOCK_SIZE,
        "SHORTCUT_H3_RES": SHORTCUT_H3_RES,
        "SOURCE_COORD_STEP": SOURCE_COORD_STEP,
        "CELL_AREA_RTOL": CELL_AREA_RTOL,
        "IMPROVEMENT_RTOL": IMPROVEMENT_RTOL,
        "ABSENT": ABSENT,
        "SLOT_DIGITS_SHIFT": SLOT_DIGITS_SHIFT,
        "SLOT_MASK": SLOT_MASK,
        "FEATURES": list(FEATURES),
        "STRATA": STRATA,
        "candidate_comparison": {
            "batch_size": candidate_comparison.DEFAULT_BATCH_SIZE,
            "rounds": candidate_comparison.DEFAULT_ROUNDS,
            "threshold": candidate_comparison.DEFAULT_THRESHOLD,
            "win_margin": candidate_comparison.DEFAULT_WIN_MARGIN,
        },
        "production_coefficients": asdict(DEFAULT_COST_COEFFICIENTS),
        "packed_acceleration_backends": {
            name: callable_name(function)
            for name, function in PACKED_ACCELERATION_IMPLEMENTATIONS.items()
        },
        "packed_buffer_backends": {
            name: callable_name(function)
            for name, function in PACKED_BUFFER_FACTORIES.items()
        },
    }
    digest.update(json.dumps(fixtures, sort_keys=True).encode())
    digest.update(json.dumps(constants, sort_keys=True).encode())
    return {
        "sha256": digest.hexdigest(),
        "members": [*symbols, *_FINGERPRINT_PATHS],
        "fixtures": fixtures,
        "constants": constants,
    }


def check_model(path: Path = MODEL_PATH) -> dict[str, Any]:
    """Refuse a reference model whose inputs or reviewed constants moved."""
    model = json.loads(path.read_text(encoding="utf-8"))
    if model.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"{path} has schema {model.get('schema_version')!r}, expected {SCHEMA_VERSION}"
        )
    current_fingerprint = model_input_fingerprint()
    recorded_fingerprint = model.get("model_inputs", {})
    if recorded_fingerprint != current_fingerprint:
        raise ValueError(
            "shortcut ordering calibration is stale: a modeled runtime stage, block "
            "size, or feature mapping changed. Re-run this command in every supported "
            "environment and review the resulting artifact before updating the model."
        )
    current_coefficients = asdict(DEFAULT_COST_COEFFICIENTS)
    if model.get("production_coefficients") != current_coefficients:
        raise ValueError(
            "shortcut ordering calibration is stale: the reviewed production "
            "coefficients differ from the reference model"
        )
    if set(model.get("feature_mapping", ())) != set(FEATURES):
        raise ValueError(
            "shortcut ordering calibration is stale: the reference feature mapping "
            "does not name exactly the fitted coefficient features"
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


def _ordering_report(
    finder: TimezoneFinder,
    validation_points: Sequence[tuple[float, float]],
    fitted: CostCoefficients,
    rounds: int,
    max_cells: int,
) -> dict[str, Any]:
    base_index = finder.shortcuts
    cells: dict[int, list[int]] = {}
    frequency: Counter[int] = Counter()
    for lng, lat in validation_points:
        cell = int(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES))
        entry = base_index.entry_of(cell)
        if entry < ABSENT:
            frequency[cell] += 1
            if cell not in cells:
                cells[cell] = base_index.candidates_of(entry).astype(int).tolist()
    richest = max(cells, key=lambda cell: (len(cells[cell]), -cell))
    selected_cells = [richest]
    selected_cells.extend(
        cell
        for cell, _ in sorted(frequency.items(), key=lambda item: (-item[1], item[0]))
        if cell != richest
    )
    selected = {cell: cells[cell] for cell in selected_cells[:max_cells]}
    fitted_orderer = _runtime_orderer(finder, fitted)
    area_orderer = _runtime_orderer(
        finder,
        CostCoefficients(
            bbox=1.0,
            hole_union_probe=0.0,
            hole_lookup=0.0,
            hole_bbox=0.0,
            pip_dispatch=0.0,
            block_probe=0.0,
            active_vertex=0.0,
        ),
    )
    fitted_orders = {
        cell: fitted_orderer.order(cell, ids) for cell, ids in selected.items()
    }
    area_orders = {
        cell: area_orderer.order(cell, ids) for cell, ids in selected.items()
    }
    selected_cell_points = [
        point
        for point in validation_points
        if int(h3.latlng_to_cell(point[1], point[0], SHORTCUT_H3_RES)) in selected
    ]
    if not selected_cell_points:
        return {"cells": 0, "points": 0, "comparisons": {}}
    # The aggregate includes every held-out query. Cells outside the bounded ordering
    # sample delegate to the same base index on both arms, so they are the dilution a
    # real mixed workload imposes rather than silently becoming training examples.
    comparison_points = list(validation_points)

    def compare(name: str, orders: dict[int, list[int]]) -> dict[str, Any]:
        current = _ReorderedIndex(base_index, selected, finder.zone_ids)
        alternative = _ReorderedIndex(base_index, orders, finder.zone_ids)

        def baseline(point: tuple[float, float]) -> object:
            finder.shortcuts = cast(Any, current)
            return finder.timezone_at(lng=point[0], lat=point[1])

        def challenger(point: tuple[float, float]) -> object:
            finder.shortcuts = cast(Any, alternative)
            return finder.timezone_at(lng=point[0], lat=point[1])

        for point in comparison_points:
            if baseline(point) != challenger(point):
                raise AssertionError(f"{name} changed the lookup answer at {point}")
        comparison = compare_candidates(
            ("production", baseline),
            (name, challenger),
            comparison_points,
            rounds=rounds,
            batch_size=min(1_000, len(comparison_points)),
        )
        finder.shortcuts = base_index
        return {
            **asdict(comparison),
            "best_round_change": comparison.best_round_change,
            "win_share": comparison.win_share,
            "verdict": comparison.verdict,
            "changed_cells": sum(orders[cell] != selected[cell] for cell in selected),
        }

    try:
        comparisons = {
            "calibrated": compare("calibrated", fitted_orders),
            "area_only": compare("area_only", area_orders),
        }
    finally:
        finder.shortcuts = base_index
    return {
        "cells": len(selected),
        "candidate_count_max": max(map(len, selected.values())),
        "points": len(comparison_points),
        "selected_cell_points": len(selected_cell_points),
        "comparisons": comparisons,
    }


def measure(
    *,
    points_per_stratum: int,
    repetitions: int,
    comparison_rounds: int,
    max_order_cells: int,
    seed: int,
    in_memory: bool,
    backend: str,
) -> dict[str, Any]:
    model = check_model()
    all_observations: list[Observation] = []
    stage_counts: dict[str, dict[str, int]] = {}
    whole_query_ns: dict[str, float] = {}
    validation_points: list[tuple[float, float]] = []
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
            validation_points.extend(
                point
                for point in points
                if _validation_cell(
                    int(h3.latlng_to_cell(point[1], point[0], SHORTCUT_H3_RES))
                )
            )
        calibration = [o for o in all_observations if not _validation_cell(o.cell)]
        validation = [o for o in all_observations if _validation_cell(o.cell)]
        if not calibration or not validation:
            raise RuntimeError(
                "deterministic cell split produced an empty fit partition"
            )
        fit = _fit_report(calibration, validation, seed)
        targeted_hole_hits = collect_hole_hit_observations(finder, repetitions)
        fitted = CostCoefficients(**fit["coefficients_ns"])
        ordering = _ordering_report(
            finder,
            validation_points,
            fitted,
            comparison_rounds,
            max_order_cells,
        )
    system = get_system_status()
    system["using_numba"] = measured_backend == "numba"
    system["using_clang_pip"] = measured_backend == "clang"
    return {
        "schema_version": SCHEMA_VERSION,
        "reference_policy": model["reference_policy"],
        "provenance": {
            "model_inputs": model_input_fingerprint(),
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
            "max_order_cells": max_order_cells,
            "cell_partition": "sha256(cell little-endian)[0] < 64 is held out",
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
        "held_out_ordering": ordering,
        "limitations": model["structural_limitations"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-model", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--points-per-stratum", type=int, default=1_000)
    parser.add_argument("--candidate-repetitions", type=int, default=7)
    parser.add_argument("--comparison-rounds", type=int, default=15)
    parser.add_argument("--max-order-cells", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20260910)
    parser.add_argument("--in-memory", action="store_true")
    parser.add_argument(
        "--backend",
        choices=("auto", *PACKED_ACCELERATION_IMPLEMENTATIONS),
        default="auto",
    )
    args = parser.parse_args()
    if args.check_model:
        check_model()
        print(f"{MODEL_PATH}: current")
        return
    if args.output is None:
        parser.error("--output is required unless --check-model is used")
    if (
        min(
            args.points_per_stratum,
            args.candidate_repetitions,
            args.comparison_rounds,
            args.max_order_cells,
        )
        < 1
    ):
        parser.error("all measurement sizes must be positive")
    report = measure(
        points_per_stratum=args.points_per_stratum,
        repetitions=args.candidate_repetitions,
        comparison_rounds=args.comparison_rounds,
        max_order_cells=args.max_order_cells,
        seed=args.seed,
        in_memory=args.in_memory,
        backend=args.backend,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["fit"]["coefficients_ns"], indent=2))
    for name, comparison in report["held_out_ordering"]["comparisons"].items():
        print(f"{name}: {comparison['verdict']}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
