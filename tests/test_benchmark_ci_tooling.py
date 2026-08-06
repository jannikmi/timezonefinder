"""Unit tests for the benchmark CI helper scripts.

Covers the pieces the `benchmark`/`benchmark-comment` workflows depend on
(see `.github/workflows/benchmark.yml`):

* `scripts.normalize_benchmark_json` - rewrites the single value
  `benchmark-action/github-action-benchmark` tracks from the noise-sensitive
  mean to a chosen estimator, and stamps the CPU into the one field that
  reaches the trend chart
* `scripts.compare_benchmark_runs` - compares a pull request's head against
  its merge base, both measured on the same runner
* `scripts.describe_benchmark_machine` - says which machine a report came from
* `scripts.benchmark_noise` - derives the trend chart's alert threshold from a
  measured spread instead of a guess
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
from scripts.benchmark_utils import load_benchmark_json, machine_label
from scripts.compare_benchmark_runs import (
    REGRESSION_THRESHOLD_PCT,
    BenchmarkComparison,
    comparability_warnings,
    compare_runs,
    regressions,
    tracked_estimator,
)
from scripts.compare_benchmark_runs import render_markdown as render_comparison
from scripts.describe_benchmark_machine import acceleration_label
from scripts.describe_benchmark_machine import render_markdown as render_description
from scripts.normalize_benchmark_json import (
    ESTIMATOR_KEY,
    annotate_machine_identity,
    normalize_benchmark_data,
)

CPU_7763 = "AMD EPYC 7763 64-Core Processor"
CPU_9V74 = "AMD EPYC 9V74 80-Core Processor"


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


def _measured_on(
    run: dict, brand: str = CPU_7763, clock: str = "3.2449 GHz", **provenance
) -> dict:
    """Attach the `machine_info` a real pytest-benchmark run would carry."""
    workload = {
        "batch_size": 2500,
        "fixture_version": 2,
        "data_version": "2026c",
        "using_clang_pip": True,
        "using_numba": False,
    }
    workload.update(provenance)
    run["machine_info"] = {
        "cpu": {"brand_raw": brand, "hz_actual_friendly": clock},
        "timezonefinder": workload,
    }
    return run


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
def test_normalize_stamps_the_cpu_into_the_rounds_field():
    # `rounds` is the only pytest-benchmark field the action's extractor
    # copies through verbatim, so it is how the CPU reaches the trend chart's
    # tooltip - without it a stored data point can never be attributed to a
    # machine once its artifact has expired
    data = _measured_on(_run(test_a=_stats(1.0, 2.0, 4.0)))

    annotated = annotate_machine_identity(data)

    rounds = annotated["benchmarks"][0]["stats"]["rounds"]
    assert rounds == f"50 on {CPU_7763} @ 3.2449 GHz"


@pytest.mark.unit
def test_normalize_leaves_rounds_alone_without_a_recorded_cpu():
    data = _run(test_a=_stats(1.0, 2.0, 4.0))

    assert annotate_machine_identity(data)["benchmarks"][0]["stats"]["rounds"] == 50


@pytest.mark.unit
def test_annotating_does_not_mutate_the_input():
    data = _measured_on(_run(test_a=_stats(1.0, 2.0, 4.0)))

    annotate_machine_identity(data)

    assert data["benchmarks"][0]["stats"]["rounds"] == 50


@pytest.mark.unit
def test_compare_reports_the_ratio_worst_first():
    base = _run(slower=_stats(1.0, 1.0, 1.0), faster=_stats(1.0, 1.0, 1.0))
    head = _run(slower=_stats(1.5, 1.5, 1.5), faster=_stats(0.5, 0.5, 0.5))

    comparisons = compare_runs([base], [head], "min")

    assert [c.name for c in comparisons] == [
        "benchmarks/test_x.py::slower",
        "benchmarks/test_x.py::faster",
    ]
    slower, faster = comparisons
    assert slower.ratio_pct == pytest.approx(150.0)
    assert slower.change_pct == pytest.approx(50.0)
    assert faster.factor == pytest.approx(2.0)


@pytest.mark.unit
def test_compare_reduces_repeated_passes_by_min():
    # the workflow measures the merge base twice, sandwiching the head, so a
    # runner that drifts mid-job shows up in the base's own spread
    passes = [_run(a=_stats(2.0, 2.0, 2.0)), _run(a=_stats(1.0, 1.0, 1.0))]
    head = _run(a=_stats(1.0, 1.0, 1.0))

    (comparison,) = compare_runs(passes, [head], "min")

    assert comparison.base == pytest.approx(1.0)
    assert comparison.ratio_pct == pytest.approx(100.0)


@pytest.mark.unit
def test_compare_rejects_a_renamed_benchmark():
    base = _run(a=_stats(1.0, 1.0, 1.0))
    head = _run(b=_stats(1.0, 1.0, 1.0))

    with pytest.raises(ValueError, match="same benchmarks"):
        compare_runs([base], [head], "min")


@pytest.mark.unit
def test_compare_rejects_a_non_positive_duration():
    base = _run(a=_stats(0.0, 1.0, 1.0))
    head = _run(a=_stats(1.0, 1.0, 1.0))

    with pytest.raises(ValueError, match="non-positive"):
        compare_runs([base], [head], "min")


@pytest.mark.unit
def test_tracked_estimator_rejects_reports_that_disagree():
    base = {**_run(a=_stats(1.0, 1.0, 1.0)), ESTIMATOR_KEY: "min"}
    head = {**_run(a=_stats(1.0, 1.0, 1.0)), ESTIMATOR_KEY: "mean"}

    with pytest.raises(ValueError, match="different estimators"):
        tracked_estimator([base, head], "min")


@pytest.mark.unit
def test_tracked_estimator_prefers_what_the_report_records():
    recorded = {**_run(a=_stats(1.0, 1.0, 1.0)), ESTIMATOR_KEY: "median"}

    assert tracked_estimator([recorded], "min") == "median"
    assert tracked_estimator([_run(a=_stats(1.0, 1.0, 1.0))], "min") == "min"


@pytest.mark.unit
def test_warns_when_the_two_sides_ran_on_different_cpus():
    # the entire premise of the comparison is one machine; if that failed, the
    # numbers measure the runner pool instead of the change
    base = _measured_on(_run(a=_stats(1.0, 1.0, 1.0)), brand=CPU_9V74)
    head = _measured_on(_run(a=_stats(1.0, 1.0, 1.0)), brand=CPU_7763)

    (warning,) = comparability_warnings([base], [head])

    assert "not measured on the same machine" in warning
    assert CPU_9V74 in warning and CPU_7763 in warning


@pytest.mark.unit
def test_does_not_warn_on_clock_jitter_within_one_cpu():
    # `hz_actual` is sampled per pytest-benchmark startup and moves by a MHz
    # or so between two runs on the same machine. Comparing on it would make
    # the "different machine" warning fire on literally every pull request.
    base = _measured_on(_run(a=_stats(1.0, 1.0, 1.0)), clock="3.2439 GHz")
    head = _measured_on(_run(a=_stats(1.0, 1.0, 1.0)), clock="3.2449 GHz")

    assert comparability_warnings([base], [head]) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "differing", [{"batch_size": 1000}, {"fixture_version": 3}, {"using_numba": True}]
)
def test_warns_when_the_two_sides_measured_different_workloads(differing):
    base = _measured_on(_run(a=_stats(1.0, 1.0, 1.0)))
    head = _measured_on(_run(a=_stats(1.0, 1.0, 1.0)), **differing)

    (warning,) = comparability_warnings([base], [head])

    assert next(iter(differing)) in warning


@pytest.mark.unit
def test_regressions_are_those_reaching_the_threshold():
    comparisons = [
        BenchmarkComparison("over", base=1.0, head=1.2),
        BenchmarkComparison("under", base=1.0, head=1.05),
    ]

    assert [c.name for c in regressions(comparisons, 110.0)] == ["over"]


@pytest.mark.unit
def test_comparison_markdown_names_the_machine_and_flags_the_verdicts():
    comparisons = [
        BenchmarkComparison("benchmarks/test_x.py::slower", base=1.0, head=1.5),
        BenchmarkComparison("benchmarks/test_x.py::faster", base=1.0, head=0.5),
    ]

    report = render_comparison(
        comparisons,
        estimator="min",
        machine=f"{CPU_7763} @ 3.2449 GHz",
        threshold_pct=REGRESSION_THRESHOLD_PCT,
    )

    assert CPU_7763 in report
    assert "+50.0%" in report and "🔴 slower" in report
    assert "-50.0%" in report and "🟢 faster" in report


@pytest.mark.unit
def test_comparison_markdown_surfaces_the_warnings():
    report = render_comparison(
        [BenchmarkComparison("a", base=1.0, head=1.0)],
        estimator="min",
        machine=None,
        warnings=["they ran on different machines"],
    )

    assert "[!WARNING]" in report
    assert "they ran on different machines" in report


@pytest.mark.unit
def test_comparison_markdown_neutralises_the_benchmark_name():
    # names come from the pull request's own code and are rendered into a
    # comment on the base repository
    report = render_comparison(
        [BenchmarkComparison("evil`|` name\nsecond line", base=1.0, head=1.0)],
        estimator="min",
        machine=None,
    )

    (row,) = (line for line in report.splitlines() if line.startswith("| `"))
    assert row.count("|") == 6  # 5 columns, not forged by the name
    assert "`evil'/' name second line`" in row


@pytest.mark.unit
def test_description_names_the_cpu_and_the_acceleration_path():
    data = _measured_on(_run(a=_stats(0.004, 0.005, 0.006)))

    report = render_description(data, "pull request head")

    assert "pull request head" in report
    assert machine_label(data) in report
    assert "clang C extension" in report
    assert "4.000 ms" in report


@pytest.mark.unit
@pytest.mark.parametrize(
    "provenance, expected",
    [
        ({}, "clang C extension"),
        ({"using_numba": True}, "numba"),
        ({"using_clang_pip": False}, "pure Python"),
    ],
)
def test_acceleration_label_reports_the_measured_path(provenance, expected):
    data = _measured_on(_run(a=_stats(1.0, 1.0, 1.0)), **provenance)

    assert acceleration_label(data) == expected


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
