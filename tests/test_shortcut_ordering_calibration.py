"""Calibration artifact, counters and the coefficient contract."""

import json
import random
from dataclasses import asdict

import numpy as np
import pytest
from shapely import Polygon

from scripts.calibrate_shortcut_ordering import (
    FEATURES,
    MODEL_PATH,
    StageCounts,
    _ReorderedIndex,
    _fit_nonnegative,
    _query_counts,
    check_model,
    record,
    sample_cell_points,
    trace_predicate,
)
from scripts.shortcut_ordering import DEFAULT_COST_COEFFICIENTS
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder, utils
from timezonefinder.shortcut_index import (
    cell_bounds,
    child_cell_of,
    root_cell_of,
    shifted,
)

pytestmark = pytest.mark.unit


def test_the_model_records_the_reviewed_coefficients_and_a_run_against_them():
    model = check_model()
    assert model["production_coefficients"] == asdict(DEFAULT_COST_COEFFICIENTS)
    assert set(model["feature_mapping"]) == set(FEATURES)
    assert model["structural_limitations"]
    recorded = model["latest_recorded_validation"]
    assert set(recorded["ordering"]) == {"calibrated", "area_only"}
    assert recorded["decision"] != "pending review"


def _write(tmp_path, model):
    path = tmp_path / "model.json"
    path.write_text(json.dumps(model))
    return path


@pytest.mark.parametrize("field", ["schema_version", "production_coefficients"])
def test_a_model_not_describing_the_reviewed_coefficients_is_refused(tmp_path, field):
    model = json.loads(MODEL_PATH.read_text())
    if field == "schema_version":
        model[field] += 1
    else:
        model[field]["bbox"] += 1
    with pytest.raises(ValueError, match="schema|production coefficients"):
        check_model(_write(tmp_path, model))


def test_changed_coefficients_require_a_new_recorded_run_but_not_to_measure_one(
    tmp_path,
):
    model = json.loads(MODEL_PATH.read_text())
    model["latest_recorded_validation"]["production_coefficients"]["bbox"] += 1
    path = _write(tmp_path, model)
    with pytest.raises(ValueError, match="re-run"):
        check_model(path)
    assert check_model(path, require_record=False)


def test_recording_a_run_keeps_the_reviewed_decision(tmp_path):
    model = json.loads(MODEL_PATH.read_text())
    model_path = _write(tmp_path, model)
    ordering = {
        "eligible_cells": 3,
        "changed_cells": 1,
        "changed_area_share_of_sphere": 0.1,
        "fixture_query_share_in_changed_cells": {"random": 0.0},
        "points": 20,
        "modeled_change_ns_per_query": {"production": 1.0, "fitted": -1.0},
        "whole_query": {
            "median_best_round_change": -0.02,
            "best_round_change_range": [-0.03, -0.01],
            "verdicts": {"unresolved": 1},
        },
    }
    report = {
        "provenance": {
            "date": "2026-10-09",
            "fixtures": {"data_version": "2099z", "fixture_version": 9},
            "acceleration_path": "clang",
            "storage_mode": "mapped",
            "cpu": {"brand_raw": "test cpu"},
            "production_coefficients": asdict(DEFAULT_COST_COEFFICIENTS),
        },
        "fit": {
            "coefficients_ns": dict.fromkeys(FEATURES, 1.0),
            "calibration_observations": 2,
            "validation_observations": 1,
            "held_out_error_ns": {"median_absolute": 1.0, "p95_absolute": 2.0},
        },
        "ordering": {"calibrated": ordering, "area_only": {**ordering, "points": 0}},
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report))
    record(report_path, model_path)
    recorded = json.loads(model_path.read_text())["latest_recorded_validation"]
    assert recorded["data_version"] == "2099z"
    assert recorded["ordering"]["calibrated"]["verdicts"] == {"unresolved": 1}
    assert recorded["decision"] == model["latest_recorded_validation"]["decision"]
    assert check_model(model_path)


@pytest.mark.parametrize(
    "lat, lng", [(0.0, 10.0), (0.0, 180.0), (89.99, 0.0), (-89.99, 0.0)]
)
@pytest.mark.parametrize("level", ["root", "finest"])
def test_cell_samples_stay_inside_the_cell(lat, lng, level, tf):
    """Every sampled point has to read the cell it was sampled from, or the A/B that
    prices a re-ordering is measuring a mix of cells. The rejection loop the hexagons
    needed is gone - the cell *is* its own box - so this is what says the replacement
    samples the same set."""
    x, y = shifted(lng, lat)
    cell = root_cell_of(x, y) if level == "root" else child_cell_of(x, y)
    points = sample_cell_points(cell, 50, random.Random(0))
    assert len(points) == 50
    x0, y0, x1, y1 = cell_bounds(cell)
    for lng_sample, lat_sample in points:
        sx, sy = utils.query2int(lng_sample, lat_sample)
        assert x0 <= sx <= x1 and y0 <= sy <= y1


def test_nonnegative_fit_recovers_independent_features_without_scipy():
    x = np.asarray(
        [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 2, 3],
            [3, 2, 1],
        ],
        dtype=float,
    )
    expected = np.asarray([2.0, 5.0, 11.0])
    assert _fit_nonnegative(x, x @ expected) == pytest.approx(expected)
    assert np.all(_fit_nonnegative(x, -(x @ expected)) == 0)


def test_stage_vector_order_is_the_coefficient_contract():
    counts = StageCounts(
        bbox=1,
        hole_union_probe=2,
        hole_lookup=3,
        hole_bbox=4,
        pip_dispatch=5,
        block_probe=6,
        active_vertex=7,
        hole_hit=99,
    )
    assert counts.vector() == [1, 2, 3, 4, 5, 6, 7]


def test_probe_runs_the_real_early_exit_and_preserves_answers(tf):
    points = load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)[:100]
    saw_outer_rejection = False
    saw_pip = False
    for lng, lat in points:
        cell = tf.shortcuts.cell_at(lng, lat)
        entry = tf.shortcuts.entry_of(cell)
        candidates = tf.shortcuts.candidates_of(entry)
        stop = tf.shortcuts.stop_index_of(entry)
        x, y = utils.coord2int(lng), utils.coord2int(lat)
        for polygon_id_value in candidates[:stop]:
            polygon_id = int(polygon_id_value)
            expected = tf.inside_of_polygon(polygon_id, x, y)
            actual, counts = trace_predicate(tf, polygon_id, x, y)
            assert actual == expected
            assert counts.bbox == 1
            if counts.hole_union_probe == 0:
                saw_outer_rejection = True
                assert counts.pip_dispatch == 0
            if counts.pip_dispatch:
                saw_pip = True
                assert counts.block_probe >= 1
            if saw_outer_rejection and saw_pip:
                return
    pytest.fail("fixture did not exercise both an outer rejection and a packed PIP")


# The counters are only evidence while the real predicate path still runs through
# them. Each test below fails on a code change that would leave answers intact but
# the counts incomplete - which no answer-comparing test can see.


def _traced_queries(tf):
    """Every candidate test of 300 ambiguous lookups, plus points inside real holes."""
    queries = []
    for lng, lat in load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)[:300]:
        entry = tf.shortcuts.entry_at(lng, lat)
        candidates = tf.shortcuts.candidates_of(entry)
        stop = tf.shortcuts.stop_index_of(entry)
        x, y = utils.coord2int(lng), utils.coord2int(lat)
        for polygon_id in candidates[:stop]:
            queries.append((int(polygon_id), x, y))
            if tf.inside_of_polygon(int(polygon_id), x, y):
                break
    holed = [(pid, first) for pid, (n, first) in tf.holes.hole_registry.items() if n]
    for polygon_id, first_hole_id in holed[:24]:
        point = Polygon(tf.holes.coords_of(first_hole_id).T).representative_point()
        queries.append((int(polygon_id), round(point.x), round(point.y)))
    return queries


def test_every_kernel_call_is_a_counted_dispatch_and_no_method_bypasses_a_counter(
    tf, monkeypatch
):
    calls = [0]

    def counting(kernel):
        def wrapped(*args):
            calls[0] += 1
            return kernel(*args)

        return wrapped

    for array in (tf.boundaries, tf.holes):
        monkeypatch.setattr(array, "pip_kernel", counting(array.pip_kernel))
    unmodeled: set[str] = set()
    for polygon_id, x, y in _traced_queries(tf):
        calls[0] = 0
        _, counts = trace_predicate(tf, polygon_id, x, y, unmodeled)
        assert counts.pip_dispatch == calls[0], (polygon_id, x, y)
    assert not unmodeled, f"the predicate path calls uncounted methods: {unmodeled}"


def test_every_counter_still_fires_on_the_predicate_path(tf):
    total = StageCounts()
    for polygon_id, x, y in _traced_queries(tf):
        total.add(trace_predicate(tf, polygon_id, x, y)[1])
    silent = [name for name, value in asdict(total).items() if not value]
    assert not silent, f"counters the real predicate path no longer reaches: {silent}"


def test_a_lookup_walks_exactly_the_candidates_the_calibration_traces(tf, monkeypatch):
    points = load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)[:300]
    expected = [_query_counts(tf, tf.shortcuts, lng, lat).bbox for lng, lat in points]
    calls = [0]
    real = TimezoneFinder.inside_of_polygon

    def counted(self, boundary_id, x, y):
        calls[0] += 1
        return real(self, boundary_id, x, y)

    monkeypatch.setattr(TimezoneFinder, "inside_of_polygon", counted)
    walked = []
    for lng, lat in points:
        calls[0] = 0
        tf.timezone_at(lng=lng, lat=lat)
        walked.append(calls[0])
    assert walked == expected
    assert max(walked) > 1


@pytest.mark.unit
def test_the_reordered_overlay_serves_the_lookup_it_is_installed_under(tf):
    """``_ordering_report`` installs the overlay as ``finder.shortcuts`` and calls
    ``timezone_at``, so the overlay must answer every question the lookup asks - a
    method the lookups gain and the overlay lacks fails calibration runs only, which
    no other test reaches. A held-out cell has to resolve to the overlay's own entry
    from a point inside it, and every other point to the base index's.
    """
    points = load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)[:200]
    base = tf.shortcuts
    lng, lat = points[0]
    held_out = base.cell_at(lng, lat)
    order = base.candidates_of(base.entry_of(held_out)).astype(int).tolist()
    overlay = _ReorderedIndex(base, {held_out: order}, tf.zone_ids)

    assert overlay.entry_at(lng, lat) == overlay.cell_entries[held_out]
    expected = [tf.timezone_at(lng=x, lat=y) for x, y in points]
    try:
        tf.shortcuts = overlay
        assert [tf.timezone_at(lng=x, lat=y) for x, y in points] == expected
    finally:
        tf.shortcuts = base
