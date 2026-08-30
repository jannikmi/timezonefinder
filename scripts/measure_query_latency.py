#!/usr/bin/env python3

"""Measure the per-query latency *distribution* of ``timezone_at``.

Why this is not a ``benchmarks/`` suite
---------------------------------------

``benchmarks/test_timezone_finding.py`` times one pass over a fixed batch of points as
a single round, and the tracked estimator is the minimum over rounds. That is the right
shape for comparing two commits on a noisy runner, and it cannot express a tail: a batch
mean averages the distribution away before any estimator sees it, so a change that
leaves the median alone and moves p99 by a factor of four is reported as a small shift
in one number - or as nothing at all.

This package's worst latency is one ray cast across a very large ring, which is exactly
the quantity a batch mean hides. So the distribution is measured on its own, per query,
over the same committed fixtures, and published beside the batch tables rather than
instead of them (``docs/benchmarking_methodology.rst`` says why both are kept).

What it measures, and what that costs
-------------------------------------

One ``timezone_at`` call per sample, timed with ``time.perf_counter``, over the first
``--points`` entries of each committed fixture. A single call is a few microseconds and
the clock's resolution is nanoseconds, so per-call timing is honest here in a way it
would not be for a stage of a query - but it does capture whatever the scheduler did
during that call, which is why the pass is repeated and each query keeps its *best*
observed time. That is the same argument the batch suite's ``min`` estimator rests on,
applied per query instead of per round: the fastest observation is the one least
polluted by work that was not ours.

Default mapped mode, deliberately: it is what a plain install runs and what CI tracks.
The acceleration path is recorded into the report rather than assumed - see
``scripts/assert_acceleration_path.py``, which ``make latency`` runs first.

Usage::

    uv run python -m scripts.measure_query_latency --output tmp/latency.json
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from scripts.benchmark_utils import get_system_status
from scripts.configs import DEBUG
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    benchmark_fixture_provenance,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder

# The committed query fixtures, in the order the report lists them. ``random`` is the
# headline because it is the only globally representative mix; the other three say where
# a change in it came from.
STRATA: tuple[tuple[str, str], ...] = (
    ("random", RANDOM_POINTS_FIXTURE),
    ("on_land", ON_LAND_POINTS_FIXTURE),
    ("unique_shortcut", UNIQUE_SHORTCUT_POINTS_FIXTURE),
    ("ambiguous_shortcut", AMBIGUOUS_SHORTCUT_POINTS_FIXTURE),
)

# How many queries make up one distribution. p99.9 needs at least a few thousand samples
# to mean anything at all - at 2,500 it is the two slowest queries in the set - so this
# is the smallest fixture's full size rather than the batch suite's BATCH_SIZE.
DEFAULT_NR_POINTS = 5_000

# Passes over the whole fixture. Each query keeps its minimum across passes, so this
# trades wall clock for a distribution with less of the machine in it; three is enough
# to remove the isolated outliers a single pass shows and cheap at ~5,000 queries.
DEFAULT_REPETITIONS = 3

# Queries run before the clock starts, so that page faults, branch predictors and - on a
# dev checkout - Numba's JIT are not measured as latency. Not a fixed slice of the
# fixture: the same points are timed afterwards.
WARMUP_QUERIES = 500

# What the report states about each stratum. The high quantiles are the reason this
# harness exists; the median is here because a filter that improves the tail while
# moving the median is a bad trade, and only stating both can show that it did not.
QUANTILES: tuple[float, ...] = (50.0, 90.0, 99.0, 99.9)

METRIC_NAME_PREFIX = "latency::"


def metric_name(stratum: str, statistic: str) -> str:
    """The name a latency metric is recorded under.

    Structured like ``scripts.measure_memory``'s so that one reader can walk either
    report, and prefixed so the two cannot collide if they are ever merged.
    """
    return f"{METRIC_NAME_PREFIX}{stratum}::{statistic}"


def quantile_label(quantile: float) -> str:
    """``50.0 -> 'p50'``, ``99.9 -> 'p99.9'``."""
    text = f"{quantile:g}"
    return f"p{text}"


def measure_stratum(
    finder: TimezoneFinder,
    points: list[tuple[float, float]],
    repetitions: int,
) -> np.ndarray:
    """Per-query seconds over ``points``, each query's best of ``repetitions`` passes."""
    for lng, lat in points[:WARMUP_QUERIES]:
        finder.timezone_at(lng=lng, lat=lat)

    best = np.full(len(points), np.inf)
    for _ in range(repetitions):
        for i, (lng, lat) in enumerate(points):
            start = time.perf_counter()
            finder.timezone_at(lng=lng, lat=lat)
            elapsed = time.perf_counter() - start
            if elapsed < best[i]:
                best[i] = elapsed
    return best


def summarise(timings: np.ndarray) -> dict[str, float]:
    """The published statistics of one stratum's distribution, in seconds."""
    summary = {quantile_label(q): float(np.percentile(timings, q)) for q in QUANTILES}
    summary["mean"] = float(timings.mean())
    summary["max"] = float(timings.max())
    return summary


def build_report(
    measured: dict[str, dict[str, float]],
    nr_points: int,
    repetitions: int,
) -> dict[str, Any]:
    """Assemble a pytest-benchmark-shaped report, as ``scripts.measure_memory`` does.

    The shape buys ``scripts.describe_benchmark_machine`` and the report renderer
    without either learning a second format. Each metric is a single value rather than a
    sample, so its ``stats`` block repeats it - a quantile of a distribution is not
    something to take a mean of.
    """
    benchmarks = []
    for stratum, summary in measured.items():
        for statistic, value in summary.items():
            name = metric_name(stratum, statistic)
            benchmarks.append(
                {
                    "fullname": name,
                    "name": name,
                    "stats": {
                        "min": value,
                        "max": value,
                        "mean": value,
                        "median": value,
                        "stddev": 0.0,
                        "rounds": 1,
                    },
                }
            )
    return {
        "machine_info": {
            "cpu": _cpu_info(),
            "timezonefinder": {
                **get_system_status(),
                **benchmark_fixture_provenance(),
                "latency_points": nr_points,
                "latency_repetitions": repetitions,
            },
        },
        "benchmarks": benchmarks,
    }


def _cpu_info() -> dict[str, Any]:
    """The ``machine_info["cpu"]`` block pytest-benchmark records, when available."""
    try:
        import cpuinfo  # noqa: PLC0415 - optional, and only needed here
    except ImportError:
        return {}
    return cpuinfo.get_cpu_info()


def measure(nr_points: int, repetitions: int) -> dict[str, dict[str, float]]:
    """Every stratum's distribution, in the default memory-mapped mode."""
    finder = TimezoneFinder()
    measured: dict[str, dict[str, float]] = {}
    for stratum, fixture in STRATA:
        points = load_benchmark_points(fixture)[:nr_points]
        if len(points) < nr_points:
            raise ValueError(
                f"benchmark fixture {fixture!r} holds {len(points)} points, but this "
                f"harness was asked for {nr_points}. Lower --points, or regenerate the "
                "fixtures with a larger count via `make benchmark-fixtures`."
            )
        print(f"measuring {len(points):,} {stratum} queries...")
        measured[stratum] = summarise(measure_stratum(finder, points, repetitions))
    return measured


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Measure the per-query latency distribution of TimezoneFinder.timezone_at "
            "and write a pytest-benchmark-shaped JSON report."
        )
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Path to write the JSON report to"
    )
    parser.add_argument(
        "--points",
        type=int,
        default=DEFAULT_NR_POINTS,
        help=f"queries per stratum (default: {DEFAULT_NR_POINTS})",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=DEFAULT_REPETITIONS,
        help=(
            "passes over each fixture, keeping every query's fastest observation "
            f"(default: {DEFAULT_REPETITIONS})"
        ),
    )
    args = parser.parse_args()

    if DEBUG:
        # the same guard benchmarks/conftest.py applies: DEBUG lowers SHORTCUT_H3_RES,
        # which changes how many queries reach the geometry at all - i.e. exactly the
        # distribution this measures
        raise RuntimeError(
            "scripts.configs.DEBUG is True, which overrides SHORTCUT_H3_RES to a much "
            "coarser resolution. Latency measured under DEBUG describes a different "
            "index and must never be published."
        )

    measured = measure(args.points, args.repetitions)
    report = build_report(measured, args.points, args.repetitions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    for stratum, summary in measured.items():
        cells = "  ".join(
            f"{label} {summary[label] * 1e6:7.2f}"
            for label in (*(quantile_label(q) for q in QUANTILES), "mean", "max")
        )
        print(f"{stratum:>19}  {cells}  (us)")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
