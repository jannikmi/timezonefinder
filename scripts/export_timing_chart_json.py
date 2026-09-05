#!/usr/bin/env python3

"""Convert a timing report into what the trend chart action can store.

Why this exists
---------------

``benchmark-action/github-action-benchmark`` picks the tracked value with a
per-tool extractor, and its ``tool: pytest`` extractor tracks one round of
whatever the benchmark happened to call::

    const value = stats.ops;   // = 1 / stats.mean
    const unit  = 'iter/sec';

Both halves of that are unreadable here. Every benchmark in the tracked core
subset times *one pass over a fixed batch* of points (``BATCH_SIZE`` in
``benchmarks/conftest.py``), so an "iteration" is 2,500 lookups and the charted
number - 183 iter/sec - is a figure nobody can compare against the µs/query
numbers the published reports and the README quote. The name the extractor
stores is the raw node id (``test_timezone_at[random-in_memory]``), which
reads as an implementation detail rather than as the workload it measures.

The action's ``customBiggerIsBetter`` tool takes a plain list of
``{name, unit, value}`` objects instead, which lets this module state both
properly: the value is divided by the batch size the measuring run recorded,
giving **lookups/sec**, and the name is the human-readable label
``scripts/render_benchmark_reports.py`` already renders in the docs. This is
the timing counterpart of :mod:`scripts.export_memory_chart_json`; the
measurement is untouched, only the shape and the unit the action reads change.

Note that lookups/sec is the batch throughput, i.e. exactly the reciprocal of
the "Time/Query" column of ``docs/benchmark_results_timezonefinding.rst`` - it
is not a per-call latency, and the same batch-hides-the-tail caveat applies
(see ``docs/benchmarking_methodology.rst``).

Usage::

    uv run python -m scripts.export_timing_chart_json \\
        --benchmark-json tmp/benchmark-core-tracked.json \\
        --output tmp/benchmark-chart.json
"""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.benchmark_utils import (
    BENCHMARK_ESTIMATORS,
    DEFAULT_BENCHMARK_ESTIMATOR,
    BenchmarkEstimator,
    load_benchmark_json,
    machine_label,
)
from scripts.normalize_benchmark_json import ESTIMATOR_KEY
from scripts.render_benchmark_reports import humanize_benchmark_name

#: what one charted point counts. Every tracked benchmark performs the same
#: fixed batch of single-point lookups per round, whether it issues them one
#: call at a time or hands the whole batch to the vectorised API, so one unit
#: means the same thing on every series of the chart.
CHART_UNIT = "lookups/sec"


def batch_size(data: dict[str, Any]) -> int:
    """The number of lookups one round of ``data``'s benchmarks performed.

    Read from the report rather than imported from ``benchmarks/conftest.py``:
    the batch size belongs to the run that produced the numbers, and a stored
    report rendered by a later checkout must not be divided by a batch size
    that has changed since (the same reason the conftest records it at all).

    :raises ValueError: if the report does not record one. Without it there is
        no way to turn a duration into lookups/sec, and guessing would put a
        wrong-by-a-constant-factor point on a chart that keeps it forever.
    """
    recorded = (data.get("machine_info") or {}).get("timezonefinder") or {}
    size = recorded.get("batch_size")
    if not isinstance(size, int) or size <= 0:
        raise ValueError(
            "the report does not record a positive "
            "machine_info.timezonefinder.batch_size "
            f"(got {size!r}), so its durations cannot be expressed as "
            f"{CHART_UNIT}. Was it produced by a run of benchmarks/ "
            "(see its conftest's pytest_benchmark_update_machine_info)?"
        )
    return size


def to_chart_entries(
    data: dict[str, Any], estimator: BenchmarkEstimator
) -> list[dict[str, Any]]:
    """Render every benchmark in ``data`` as a ``customBiggerIsBetter`` entry.

    :raises ValueError: if the report is empty, or if two benchmarks humanize
        to the same label - the label is the chart's join key, so a collision
        would silently interleave two metrics into one history.
    """
    lookups = batch_size(data)
    machine = machine_label(data) or "an unrecorded CPU"
    entries: list[dict[str, Any]] = []
    for bench in data.get("benchmarks", []):
        stats = bench["stats"]
        seconds = stats[estimator]
        if seconds <= 0:
            raise ValueError(
                f"benchmark {bench.get('fullname', bench.get('name'))!r} reports a "
                f"non-positive '{estimator}' of {seconds!r}s, so a throughput "
                "cannot be derived from it"
            )
        throughput = lookups / seconds
        entries.append(
            {
                "name": humanize_benchmark_name(bench["name"]),
                "unit": CHART_UNIT,
                "value": throughput,
                # the observed spread, carried over as a throughput band. A
                # duration's standard deviation is not linear in throughput,
                # so this is the first-order propagation
                # `sigma_f = f * sigma_t / t` - accurate while the spread is
                # small, which for a `range: +-` annotation is the whole point.
                "range": f"± {throughput * stats['stddev'] / seconds:.0f}",
                # the chart outlives the artifact that records `machine_info`,
                # so every point has to name its own machine - the same reason
                # scripts/normalize_benchmark_json.py stamps it into `rounds`
                # for the pytest extractor, which has nowhere else to put it.
                "extra": f"{estimator} of {stats['rounds']} round(s) on {machine}",
            }
        )
    if not entries:
        raise ValueError(
            "benchmark JSON contains no 'benchmarks' entries - nothing to chart. "
            "Was the pytest run empty (e.g. a marker expression that deselected "
            "everything)?"
        )
    duplicates = [
        name for name, count in Counter(e["name"] for e in entries).items() if count > 1
    ]
    if duplicates:
        raise ValueError(
            "two benchmarks render the same chart label, which would merge their "
            f"histories into one series: {sorted(duplicates)}. Give the colliding "
            "cases distinguishable labels in scripts/render_benchmark_reports.py's "
            "FUNCTION_LABELS/PARAM_LABELS."
        )
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a pytest-benchmark report of the tracked core subset into "
            "the customBiggerIsBetter JSON that github-action-benchmark stores, "
            f"in {CHART_UNIT} and under human-readable names."
        )
    )
    parser.add_argument(
        "--benchmark-json",
        type=Path,
        required=True,
        help="a pytest-benchmark report of the core subset (normalized or raw)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to write the chart JSON to",
    )
    parser.add_argument(
        "--estimator",
        choices=BENCHMARK_ESTIMATORS,
        default=DEFAULT_BENCHMARK_ESTIMATOR,
        help=(
            "statistic to chart, used only if the report does not record which "
            f"one it was normalized to (default: {DEFAULT_BENCHMARK_ESTIMATOR})"
        ),
    )
    args = parser.parse_args()

    data = load_benchmark_json(args.benchmark_json)
    estimator = data.get(ESTIMATOR_KEY, args.estimator)
    entries = to_chart_entries(data, estimator)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries))
    print(
        f"Wrote {args.output} with {len(entries)} charted benchmark(s) in "
        f"{CHART_UNIT}, from batches of {batch_size(data):,} lookups"
    )


if __name__ == "__main__":
    main()
