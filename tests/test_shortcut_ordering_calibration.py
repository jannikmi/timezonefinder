"""Calibration artifact, counters and stale-input detection."""

import json
import random
from dataclasses import asdict

import h3.api.numpy_int as h3
import numpy as np
import pytest

from scripts.calibrate_shortcut_ordering import (
    FEATURES,
    MODEL_PATH,
    StageCounts,
    _fit_nonnegative,
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
from timezonefinder import utils
from timezonefinder.configs import SHORTCUT_H3_RES

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
def test_cell_samples_stay_inside_the_cell(lat, lng):
    cell = int(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES))
    points = sample_cell_points(cell, 50, random.Random(0))
    assert len(points) == 50
    assert {int(h3.latlng_to_cell(y, x, SHORTCUT_H3_RES)) for x, y in points} == {cell}


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
        cell = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
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
