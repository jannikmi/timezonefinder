"""Calibration artifact, counters and stale-input detection."""

import json
from dataclasses import asdict

import h3.api.numpy_int as h3
import numpy as np
import pytest

import scripts.calibrate_shortcut_ordering as calibration
from scripts.calibrate_shortcut_ordering import (
    FEATURES,
    MODEL_PATH,
    StageCounts,
    _fit_nonnegative,
    check_model,
    model_input_fingerprint,
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


def test_the_reference_model_matches_executable_inputs_and_coefficients():
    model = check_model()
    assert model["model_inputs"] == model_input_fingerprint()
    assert model["model_inputs"]["fixtures"] == {
        "data_version": "2026d",
        "fixture_version": 3,
    }
    assert (
        "timezonefinder/inside_poly_extension/inside_polygon_int.c"
        in model["model_inputs"]["members"]
    )
    assert (
        "benchmarks.candidate_comparison.CandidateComparison"
        in model["model_inputs"]["members"]
    )
    assert (
        "timezonefinder.shortcut_index.ShortcutIndex.candidates_of"
        in model["model_inputs"]["members"]
    )
    assert "timezonefinder.utils.coord2int" in model["model_inputs"]["members"]
    assert "timezonefinder/timezonefinder.py" not in model["model_inputs"]["members"]
    assert model["production_coefficients"] == asdict(DEFAULT_COST_COEFFICIENTS)
    assert set(model["feature_mapping"]) == set(FEATURES)
    assert model["structural_limitations"]


@pytest.mark.parametrize(
    "field", ["schema_version", "model_inputs", "production_coefficients"]
)
def test_a_stale_reference_model_is_refused(tmp_path, field):
    model = json.loads(MODEL_PATH.read_text())
    if field == "schema_version":
        model[field] += 1
    elif field == "model_inputs":
        model[field]["sha256"] = "0" * 64
    else:
        model[field]["bbox"] += 1
    path = tmp_path / "model.json"
    path.write_text(json.dumps(model))
    with pytest.raises(ValueError, match="schema|stale"):
        check_model(path)


def test_a_new_fixture_or_data_version_makes_the_model_stale(monkeypatch):
    monkeypatch.setattr(
        calibration,
        "benchmark_fixture_provenance",
        lambda: {"fixture_version": 4, "data_version": "2027a"},
    )
    with pytest.raises(ValueError, match="stale"):
        check_model()


def test_a_new_comparison_threshold_makes_the_model_stale(monkeypatch):
    monkeypatch.setattr(calibration.candidate_comparison, "DEFAULT_THRESHOLD", 0.04)
    with pytest.raises(ValueError, match="stale"):
        check_model()


def test_an_ordering_helper_or_shortcut_constant_makes_the_model_stale(monkeypatch):
    original_improves = calibration.improves

    def changed_improves(value, incumbent):
        return original_improves(value, incumbent)

    monkeypatch.setattr(calibration, "improves", changed_improves)
    with pytest.raises(ValueError, match="stale"):
        check_model()

    monkeypatch.setattr(calibration, "improves", original_improves)
    monkeypatch.setattr(calibration, "SLOT_MASK", calibration.SLOT_MASK ^ 1)
    with pytest.raises(ValueError, match="stale"):
        check_model()


def test_a_misrouted_backend_mapping_makes_the_model_stale(monkeypatch):
    monkeypatch.setitem(
        calibration.PACKED_ACCELERATION_IMPLEMENTATIONS,
        "clang",
        calibration.PACKED_ACCELERATION_IMPLEMENTATIONS["numba"],
    )
    with pytest.raises(ValueError, match="stale"):
        check_model()


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
