"""Unit tests for the benchmark CI helper scripts.

Covers the three pieces the `benchmark`/`benchmark-comment` workflows depend
on (see `.github/workflows/benchmark.yml`):

* `scripts.normalize_benchmark_json` - rewrites the single value
  `benchmark-action/github-action-benchmark` tracks from the noise-sensitive
  mean to a chosen estimator
* `scripts.benchmark_noise` - derives the alert threshold from a measured
  spread instead of a guess
* `scripts.assert_acceleration_path` - guards the trend history against a
  silent numba/clang switch
"""

import json

import pytest

from scripts.assert_acceleration_path import (
    active_acceleration_path,
    check_acceleration_path,
)
from scripts.benchmark_noise import (
    MIN_SUGGESTED_THRESHOLD_PCT,
    THRESHOLD_ROUNDING_PCT,
    collect_estimator_values,
    render_markdown,
    suggest_alert_threshold,
    summarize_noise,
)
from scripts.benchmark_utils import load_benchmark_json
from scripts.normalize_benchmark_json import ESTIMATOR_KEY, normalize_benchmark_data


def _run(**name_to_stats: dict[str, float]) -> dict:
    """Build a minimal pytest-benchmark-shaped report."""
    return {
        "machine_info": {},
        "benchmarks": [
            {
                "fullname": f"benchmarks/test_x.py::{name}",
                "name": name,
                "stats": stats,
            }
            for name, stats in name_to_stats.items()
        ],
    }


def _stats(minimum: float, median: float, mean: float) -> dict[str, float]:
    return {
        "min": minimum,
        "median": median,
        "mean": mean,
        "max": mean * 2,
        "stddev": mean / 10,
        "ops": 1.0 / mean,
        "rounds": 50,
    }


@pytest.mark.unit
def test_normalize_tracks_the_requested_estimator():
    data = _run(test_a=_stats(minimum=1.0, median=2.0, mean=4.0))

    normalized = normalize_benchmark_data(data, "min")

    stats = normalized["benchmarks"][0]["stats"]
    # `ops` is the only number the action reads; `mean` is what it renders
    # next to it, so the two must agree
    assert stats["ops"] == pytest.approx(1.0)
    assert stats["mean"] == pytest.approx(1.0)
    # the untouched statistics survive for anyone debugging the run
    assert stats["median"] == pytest.approx(2.0)
    assert stats["stddev"] == pytest.approx(0.4)
    assert normalized[ESTIMATOR_KEY] == "min"


@pytest.mark.unit
def test_normalize_does_not_mutate_the_input():
    data = _run(test_a=_stats(minimum=1.0, median=2.0, mean=4.0))

    normalize_benchmark_data(data, "min")

    assert data["benchmarks"][0]["stats"]["mean"] == pytest.approx(4.0)


@pytest.mark.unit
@pytest.mark.parametrize("estimator", ["min", "median", "mean"])
def test_normalize_supports_every_estimator(estimator):
    expected = {"min": 1.0, "median": 2.0, "mean": 4.0}[estimator]
    data = _run(test_a=_stats(minimum=1.0, median=2.0, mean=4.0))

    normalized = normalize_benchmark_data(data, estimator)

    assert normalized["benchmarks"][0]["stats"]["ops"] == pytest.approx(1 / expected)


@pytest.mark.unit
def test_normalize_rejects_an_empty_report():
    with pytest.raises(ValueError, match="no 'benchmarks' entries"):
        normalize_benchmark_data({"benchmarks": []}, "min")


@pytest.mark.unit
def test_normalize_rejects_a_non_positive_duration():
    data = _run(test_a=_stats(minimum=0.0, median=2.0, mean=4.0))

    with pytest.raises(ValueError, match="non-positive"):
        normalize_benchmark_data(data, "min")


@pytest.mark.unit
def test_normalized_report_round_trips_through_json(tmp_path):
    data = _run(test_a=_stats(minimum=1.0, median=2.0, mean=4.0))
    path = tmp_path / "report.json"

    path.write_text(json.dumps(normalize_benchmark_data(data, "min")))

    assert load_benchmark_json(path)["benchmarks"][0]["stats"]["ops"] == 1.0


@pytest.mark.unit
def test_collect_groups_values_by_node_id():
    runs = [
        _run(a=_stats(1.0, 1.0, 1.0), b=_stats(3.0, 3.0, 3.0)),
        _run(a=_stats(2.0, 2.0, 2.0), b=_stats(4.0, 4.0, 4.0)),
    ]

    values = collect_estimator_values(runs, "min")

    assert values == {
        "benchmarks/test_x.py::a": [1.0, 2.0],
        "benchmarks/test_x.py::b": [3.0, 4.0],
    }


@pytest.mark.unit
def test_collect_rejects_runs_with_differing_benchmarks():
    runs = [
        _run(a=_stats(1.0, 1.0, 1.0), b=_stats(1.0, 1.0, 1.0)),
        _run(a=_stats(1.0, 1.0, 1.0)),
    ]

    with pytest.raises(ValueError, match="do not contain the same set"):
        collect_estimator_values(runs, "min")


@pytest.mark.unit
def test_summarize_reports_the_spread_worst_first():
    runs = [
        _run(quiet=_stats(1.0, 1.0, 1.0), noisy=_stats(1.0, 1.0, 1.0)),
        _run(quiet=_stats(1.1, 1.1, 1.1), noisy=_stats(2.0, 2.0, 2.0)),
    ]

    stats = summarize_noise(runs, "min")

    assert [s.name for s in stats] == [
        "benchmarks/test_x.py::noisy",
        "benchmarks/test_x.py::quiet",
    ]
    noisy, quiet = stats
    assert noisy.spread_pct == pytest.approx(200.0)
    assert quiet.spread_pct == pytest.approx(110.0)
    assert noisy.runs == 2


@pytest.mark.unit
def test_suggested_threshold_clears_the_observed_spread():
    # a 40% observed spread must not yield a threshold that would have fired
    # on the very runs it was derived from
    runs = [
        _run(a=_stats(1.0, 1.0, 1.0)),
        _run(a=_stats(1.4, 1.4, 1.4)),
    ]

    threshold = suggest_alert_threshold(summarize_noise(runs, "min"))

    assert threshold > 140
    assert threshold % THRESHOLD_ROUNDING_PCT == 0


@pytest.mark.unit
def test_suggested_threshold_has_a_floor():
    runs = [_run(a=_stats(1.0, 1.0, 1.0)), _run(a=_stats(1.0, 1.0, 1.0))]

    assert (
        suggest_alert_threshold(summarize_noise(runs, "min"))
        == MIN_SUGGESTED_THRESHOLD_PCT
    )


@pytest.mark.unit
def test_markdown_report_names_the_benchmarks_and_the_threshold():
    runs = [_run(a=_stats(1.0, 1.0, 1.0)), _run(a=_stats(1.2, 1.2, 1.2))]
    stats = summarize_noise(runs, "min")

    report = render_markdown(stats, "min", suggest_alert_threshold(stats))

    assert "benchmarks/test_x.py::a" in report
    assert "120.0%" in report
    assert "2 runs of identical code" in report


@pytest.mark.unit
def test_acceleration_path_check_accepts_the_active_path():
    # whichever path this environment happens to have bound must pass
    check_acceleration_path(active_acceleration_path())


@pytest.mark.unit
def test_acceleration_path_check_rejects_the_inactive_path():
    active = active_acceleration_path()
    inactive = "numba" if active == "clang" else "clang"

    with pytest.raises(RuntimeError, match="acceleration path"):
        check_acceleration_path(inactive)
