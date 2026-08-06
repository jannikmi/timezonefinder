#!/usr/bin/env python3

"""Measure the run-to-run noise floor of the benchmark suite.

A benchmark alert threshold that is not derived from a measurement is a
guess, and a guessed threshold either fires constantly (and gets ignored) or
never fires at all. This script consumes several pytest-benchmark JSON
reports produced from **identical code** and reports, per benchmark, how far
apart those supposedly-identical runs actually landed.

The headline number is the *spread*, ``max / min * 100%``, because that is
directly comparable to ``benchmark-action/github-action-benchmark``'s
``alert-threshold`` input: a threshold of ``150%`` fires when a benchmark got
50% worse than its baseline, so a threshold at or below the observed noise
spread would fire on unchanged code.

There are two different noise floors, and this script measures whichever one
it is fed:

* **one machine, repeated** (``make benchmark-noise``) is the residual the
  same-runner base/head comparison has to clear - see
  :mod:`scripts.compare_benchmark_runs`.
* **many machines** (the ``benchmark`` workflow via ``workflow_dispatch``,
  where every repetition lands on a fresh runner) is the spread of the
  ``ubuntu-latest`` pool itself, which is what the cross-machine trend chart's
  ``ALERT_THRESHOLD`` has to clear. It is by far the larger of the two: the
  pool serves several CPU models, and the measured spread on unchanged code
  reached 158%.

Usage::

    make benchmark-noise

    uv run python -m scripts.benchmark_noise tmp/benchmark-noise/run-*.json
"""

import argparse
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from scripts.benchmark_utils import (
    BENCHMARK_ESTIMATORS,
    DEFAULT_BENCHMARK_ESTIMATOR,
    DEFAULT_METRIC_KEY,
    METRIC_SPECS,
    BenchmarkEstimator,
    MetricSpec,
    load_benchmark_json,
)

# the threshold must be derived from at least this many repetitions of the
# benchmark on unchanged code. Fewer runs cannot distinguish a noise floor
# from a coincidence.
MIN_RUNS_FOR_THRESHOLD = 5

# how much headroom to leave above the worst observed spread when suggesting
# a threshold. The observed maximum over N runs is a sample, not a bound -
# run N+1 can be worse - so a threshold sitting exactly on it would fire
# roughly as often as the sample maximum is exceeded.
THRESHOLD_SAFETY_FACTOR = 1.2
# suggested thresholds are rounded up to a multiple of this many percentage
# points; a threshold precise to the decimal implies a precision the
# measurement does not have
THRESHOLD_ROUNDING_PCT = 10
# a threshold below this is tighter than pytest-benchmark's own measurement
# resolution warrants regardless of what the sample says
MIN_SUGGESTED_THRESHOLD_PCT = 110


@dataclass(frozen=True)
class NoiseStats:
    """Spread of one benchmark's estimator across several identical runs."""

    name: str
    runs: int
    minimum: float
    maximum: float
    median: float
    mean: float
    stddev: float

    @property
    def spread_pct(self) -> float:
        """``max / min`` as a percentage - comparable to ``alert-threshold``."""
        return self.maximum / self.minimum * 100.0

    @property
    def cv_pct(self) -> float:
        """Coefficient of variation (stddev / mean) as a percentage."""
        return self.stddev / self.mean * 100.0


def collect_estimator_values(
    runs: Iterable[dict[str, Any]], estimator: BenchmarkEstimator
) -> dict[str, list[float]]:
    """Group each benchmark's ``estimator`` value across ``runs`` by node id.

    Uses ``fullname`` (the pytest node id), which is the join key for the
    historical trend chart - see ``tests/test_benchmark_names.py``.

    :raises ValueError: if the runs do not all contain the same benchmarks;
        comparing a partial run against a full one would silently understate
        or overstate the spread.
    """
    values: dict[str, list[float]] = {}
    expected_names: set[str] | None = None
    for run_index, data in enumerate(runs):
        benchmarks = data.get("benchmarks") or []
        names = {b["fullname"] for b in benchmarks}
        if not names:
            raise ValueError(f"run #{run_index + 1} contains no benchmark results")
        if expected_names is None:
            expected_names = names
        elif names != expected_names:
            raise ValueError(
                "the given runs do not contain the same set of benchmarks, so "
                "their spread is not comparable. "
                f"run #{run_index + 1} is missing {sorted(expected_names - names)} "
                f"and adds {sorted(names - expected_names)}"
            )
        for bench in benchmarks:
            values.setdefault(bench["fullname"], []).append(bench["stats"][estimator])
    if expected_names is None:
        raise ValueError("no benchmark runs were given")
    return values


def summarize_noise(
    runs: Iterable[dict[str, Any]], estimator: BenchmarkEstimator
) -> list[NoiseStats]:
    """Summarise the spread of every benchmark, worst spread first."""
    grouped = collect_estimator_values(runs, estimator)
    stats = [
        NoiseStats(
            name=name,
            runs=len(values),
            minimum=min(values),
            maximum=max(values),
            median=statistics.median(values),
            mean=statistics.fmean(values),
            # population stddev: these are all the runs there are, not a
            # sample drawn from a larger set of runs
            stddev=statistics.pstdev(values),
        )
        for name, values in grouped.items()
    ]
    return sorted(stats, key=lambda s: s.spread_pct, reverse=True)


def suggest_alert_threshold(stats: Iterable[NoiseStats]) -> int:
    """Derive an ``alert-threshold`` percentage from the observed spreads.

    Takes the worst observed spread across all tracked benchmarks, adds
    :data:`THRESHOLD_SAFETY_FACTOR` headroom, and rounds up to a multiple of
    :data:`THRESHOLD_ROUNDING_PCT`. The worst benchmark sets the threshold
    because the action applies one threshold to all of them.
    """
    stats = list(stats)
    if not stats:
        raise ValueError("cannot suggest a threshold without any benchmark stats")
    worst_excess_pct = max(s.spread_pct for s in stats) - 100.0
    raw = 100.0 + worst_excess_pct * THRESHOLD_SAFETY_FACTOR
    rounded = math.ceil(raw / THRESHOLD_ROUNDING_PCT) * THRESHOLD_ROUNDING_PCT
    return max(rounded, MIN_SUGGESTED_THRESHOLD_PCT)


def render_markdown(
    stats: list[NoiseStats],
    estimator: BenchmarkEstimator,
    threshold_pct: int,
    metric: MetricSpec = METRIC_SPECS[DEFAULT_METRIC_KEY],
) -> str:
    """Render a report for a PR description or a GitHub job summary."""
    run_counts = {s.runs for s in stats}
    runs_label = (
        str(next(iter(run_counts))) if len(run_counts) == 1 else "varying numbers of"
    )
    lines = [
        f"## {metric.heading} noise floor",
        "",
        f"Spread of the `{estimator}` estimator across **{runs_label} runs of "
        "identical code**. `spread` is `max / min`, directly comparable to "
        "`github-action-benchmark`'s `alert-threshold`.",
        "",
        f"| {metric.row_noun} | runs | min | median | max | spread | CV |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for s in stats:
        lines.append(
            f"| `{s.name}` | {s.runs} | {metric.format_value(s.minimum)} | "
            f"{metric.format_value(s.median)} | {metric.format_value(s.maximum)} | "
            f"{s.spread_pct:.1f}% | {s.cv_pct:.1f}% |"
        )
    lines += [
        "",
        f"**Derived alert threshold: `{threshold_pct}%`** "
        f"(worst observed spread + {round((THRESHOLD_SAFETY_FACTOR - 1) * 100)}% "
        f"headroom, rounded up to a multiple of {THRESHOLD_ROUNDING_PCT}).",
        "",
        "> A threshold at or below the observed spread would fire on unchanged "
        "code. Repeats on one machine measure only that machine's jitter; the "
        "trend chart spans the whole `ubuntu-latest` pool, which serves "
        "several CPU models and spreads far wider. Derive the threshold that "
        "actually ships from a CI measurement (`benchmark` workflow, "
        "`workflow_dispatch`), where each repetition draws a fresh runner.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Report the run-to-run spread of pytest-benchmark results measured "
            "on identical code, and derive an alert threshold from it."
        )
    )
    parser.add_argument(
        "benchmark_json",
        type=Path,
        nargs="+",
        help="two or more pytest-benchmark JSON reports of the same code",
    )
    parser.add_argument(
        "--estimator",
        choices=BENCHMARK_ESTIMATORS,
        default=DEFAULT_BENCHMARK_ESTIMATOR,
        help=f"statistic to analyse (default: {DEFAULT_BENCHMARK_ESTIMATOR})",
    )
    parser.add_argument(
        "--min-runs",
        type=int,
        default=MIN_RUNS_FOR_THRESHOLD,
        help=(
            "fail unless at least this many reports are given "
            f"(default: {MIN_RUNS_FOR_THRESHOLD})"
        ),
    )
    parser.add_argument(
        "--metric",
        choices=sorted(METRIC_SPECS),
        default=DEFAULT_METRIC_KEY,
        help=(
            "what the reports measure, which selects the units of the rendered "
            f"table (default: {DEFAULT_METRIC_KEY})"
        ),
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        help="also write the report to this file (e.g. $GITHUB_STEP_SUMMARY)",
    )
    args = parser.parse_args()

    if len(args.benchmark_json) < args.min_runs:
        parser.error(
            f"got {len(args.benchmark_json)} benchmark report(s) but need at least "
            f"{args.min_runs} to characterise the noise floor. A threshold derived "
            "from fewer runs is a guess wearing a table."
        )

    try:
        stats = summarize_noise(
            (load_benchmark_json(path) for path in args.benchmark_json),
            args.estimator,
        )
        threshold = suggest_alert_threshold(stats)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    report = render_markdown(
        stats, args.estimator, threshold, METRIC_SPECS[args.metric]
    )
    print(report)
    if args.markdown_out is not None:
        with open(args.markdown_out, "a") as f:
            f.write(report)


if __name__ == "__main__":
    main()
