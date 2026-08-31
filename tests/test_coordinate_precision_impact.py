"""Semantics and reproducibility of the coordinate-precision measurement."""

import json

import numpy as np
import pytest

from scripts.border_sampling import Candidate, CandidatePair
from scripts.configs import read_data_version
from scripts.measure_coordinate_precision import (
    MEASUREMENT_PATH,
    REPORT_PATH,
    AnswerChanges,
    ChangeExample,
    DistanceResult,
    Measurement,
    PairedChanges,
    count_answer_changes,
    count_paired_changes,
    quantize_ring,
    render_report,
    sample_uniform_globe,
)


@pytest.mark.unit
def test_quantization_recovers_the_source_digit_before_rounding_it() -> None:
    # 13.35805 is exactly halfway on the five-place grid. coord2int can store the
    # positive source value one integer low; nearest rounding must still move it up.
    ring = np.array([[133_580_499, -133_580_499, 10], [0, 0, 0]], dtype=np.int32)

    quantized = quantize_ring(ring, decimal_places=5)

    assert quantized[0].tolist() == [133_580_500, -133_580_500, 0]
    assert quantized.dtype == np.dtype("<i4")
    assert quantized.flags.c_contiguous


@pytest.mark.unit
def test_quantization_refuses_precision_the_source_does_not_carry() -> None:
    ring = np.zeros((2, 3), dtype=np.int32)
    with pytest.raises(ValueError, match="between 0 and 6"):
        quantize_ring(ring, decimal_places=7)


@pytest.mark.unit
def test_answer_changes_keep_counts_and_checkable_examples() -> None:
    points = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]
    source = {0.0: "A", 1.0: "B", 2.0: "C"}
    quantized = {0.0: "A", 1.0: "C", 2.0: "C"}

    changes = count_answer_changes(
        points,
        lambda lng, lat: source[lng],
        lambda lng, lat: quantized[lng],
    )

    assert changes.total == 3
    assert changes.changed == 1
    assert changes.changed_rate == pytest.approx(100 / 3)
    assert changes.examples == (ChangeExample(1.0, 0.0, "B", "C"),)


@pytest.mark.unit
def test_paired_changes_distinguish_one_changed_side_from_both() -> None:
    def candidate(lng: float) -> Candidate:
        return Candidate(lng, 0.0, 1.0, (0,))

    pairs = [
        CandidatePair(candidate(1.0), candidate(2.0), (0,)),
        CandidatePair(candidate(3.0), candidate(4.0), (0,)),
        CandidatePair(candidate(5.0), candidate(6.0), (0,)),
    ]
    source = {lng: "A" for lng in range(1, 7)}
    quantized = {1: "B", 2: "A", 3: "B", 4: "B", 5: "A", 6: "A"}

    changes = count_paired_changes(
        pairs,
        lambda lng, lat: source[int(lng)],
        lambda lng, lat: quantized[int(lng)],
    )

    assert changes.total == 3
    assert changes.affected_one_side == 1
    assert changes.affected_both_sides == 1
    assert changes.affected == 2
    assert changes.affected_rate == pytest.approx(200 / 3)


@pytest.mark.unit
def test_uniform_globe_sampling_is_seeded_and_area_uniform() -> None:
    first = np.array(list(sample_uniform_globe(np.random.default_rng(7), 20_000)))
    second = np.array(list(sample_uniform_globe(np.random.default_rng(7), 20_000)))

    assert np.array_equal(first, second)
    assert np.mean(np.abs(first[:, 1]) > 60.0) == pytest.approx(0.134, abs=0.015)


def _synthetic_measurement() -> Measurement:
    return Measurement(
        data_version="2026c",
        source_decimal_places=6,
        tested_decimal_places=5,
        quantization="nearest, ties away from zero",
        seed=7,
        by_distance=(
            DistanceResult(
                distance_m=0.5,
                drawn=120,
                all_borders=PairedChanges(100, 12, 3),
                land_borders=PairedChanges(80, 11, 3),
            ),
        ),
        uniform_globe=AnswerChanges(200_000, 1),
        by_point_class={"random_points": AnswerChanges(5_000, 0)},
    )


@pytest.mark.unit
def test_measurement_json_round_trips_and_the_report_uses_its_counts() -> None:
    measurement = _synthetic_measurement()

    rebuilt = Measurement.from_json(json.loads(json.dumps(measurement.as_json())))
    report = render_report(rebuilt)

    assert rebuilt == measurement
    assert "15 (15.0%)" in report
    assert "14 (17.5%)" in report
    assert "1 (0.001%)" in report
    assert "0 (95% bound <0.060%)" in report
    assert report.endswith("\n")


@pytest.mark.unit
def test_committed_run_and_generated_report_stay_together() -> None:
    measurement = Measurement.from_json(json.loads(MEASUREMENT_PATH.read_text("utf-8")))

    assert measurement.data_version == read_data_version()
    assert measurement.source_decimal_places == 6
    assert measurement.tested_decimal_places == 5
    assert any(result.all_borders.affected for result in measurement.by_distance)
    assert REPORT_PATH.read_text("utf-8") == render_report(measurement)
