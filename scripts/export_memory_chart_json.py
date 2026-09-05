#!/usr/bin/env python3

"""Convert a memory report into what the trend chart action can store.

Why this exists
---------------

``benchmark-action/github-action-benchmark`` picks the tracked value with a
per-tool extractor, and its ``tool: pytest`` extractor is hard-wired to
durations::

    const value = stats.ops;   // = 1 / stats.mean
    const unit  = 'iter/sec';

Bigger is better there, and the unit is fixed - both wrong for a footprint. The
action's ``customSmallerIsBetter`` tool takes a plain list of
``{name, unit, value}`` objects instead and treats a *rise* as the regression,
which is what a memory chart needs. This is the memory counterpart of
:mod:`scripts.export_timing_chart_json`, which does the same for the timing
suite: the measurement stays untouched, only the shape and the unit the action
reads change.

Only the ``*_heap`` metrics are charted. The ``*_rss`` ones are reported in
``docs/benchmark_results_memory.rst`` and in the pull request comment, but they
count memory-mapped pages, which the kernel maps and reclaims according to
machine-wide pressure that has nothing to do with this code - tracking them
would alert on the runner's mood. ``tracemalloc`` sees allocations only, and
the same code allocates the same bytes on every machine.

Usage::

    uv run python -m scripts.export_memory_chart_json \\
        --memory-json tmp/memory-tracked.json --output tmp/memory-chart.json
"""

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.benchmark_utils import (
    BENCHMARK_ESTIMATORS,
    DEFAULT_BENCHMARK_ESTIMATOR,
    BenchmarkEstimator,
    load_benchmark_json,
    machine_label,
)
from scripts.measure_memory import HEAP_METRICS
from scripts.normalize_benchmark_json import ESTIMATOR_KEY

CHART_UNIT = "MiB"
BYTES_PER_UNIT = 1024**2


def is_charted(name: str) -> bool:
    return name.endswith(HEAP_METRICS)


def to_chart_entries(
    data: dict[str, Any], estimator: BenchmarkEstimator
) -> list[dict[str, Any]]:
    """Render the charted metrics as ``customSmallerIsBetter`` entries.

    :raises ValueError: if no metric qualifies, which would silently push an
        empty data point onto the chart and leave a gap in the history.
    """
    machine = machine_label(data) or "an unrecorded CPU"
    entries = []
    for bench in data.get("benchmarks", []):
        name = bench["fullname"]
        if not is_charted(name):
            continue
        stats = bench["stats"]
        entries.append(
            {
                "name": name,
                "unit": CHART_UNIT,
                "value": stats[estimator] / BYTES_PER_UNIT,
                "range": f"± {stats['stddev'] / BYTES_PER_UNIT:.3f}",
                # the chart outlives the artifact that records `machine_info`,
                # so every point has to name its own machine, exactly as
                # scripts/export_timing_chart_json.py does for the timing one.
                "extra": f"{estimator} of {stats['rounds']} run(s) on {machine}",
            }
        )
    if not entries:
        raise ValueError(
            "no charted metric found in the report - expected metric names "
            f"ending in one of {HEAP_METRICS}, got "
            f"{[b['fullname'] for b in data.get('benchmarks', [])]}"
        )
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a scripts.measure_memory report into the "
            "customSmallerIsBetter JSON that github-action-benchmark stores."
        )
    )
    parser.add_argument(
        "--memory-json",
        type=Path,
        required=True,
        help="a report written by `scripts.measure_memory` (normalized or raw)",
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

    data = load_benchmark_json(args.memory_json)
    estimator = data.get(ESTIMATOR_KEY, args.estimator)
    entries = to_chart_entries(data, estimator)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(entries))
    print(f"Wrote {args.output} with {len(entries)} charted metric(s) in {CHART_UNIT}")


if __name__ == "__main__":
    main()
