#!/usr/bin/env python3

"""Say which machine produced a benchmark report, in markdown.

Why this exists
---------------

``runs-on: ubuntu-latest`` pins the runner *image*, not the hardware. The pool
has served this project AMD EPYC 9V74, AMD EPYC 7763 and Intel Xeon Platinum
8573C parts between 2.30 and 3.69 GHz, and the clock varies run to run even
within one model. On unchanged code that is worth up to ~1.58x on the tracked
core set - more than most changes anyone would review.

pytest-benchmark records all of this under ``machine_info``, but it only ever
reaches the artifact:
``benchmark-action/github-action-benchmark``'s pytest extractor keeps name,
value, unit, range and a fixed ``extra`` string, so ``dev/bench/data.js`` never
sees it. Artifacts expire; the trend chart does not. Printing this block to
``$GITHUB_STEP_SUMMARY`` makes every run self-describing in the Actions UI
without downloading anything, and
``scripts.normalize_benchmark_json`` carries the same one-line label into the
chart's own tooltip so an old data point can still be read.

Usage::

    uv run python -m scripts.describe_benchmark_machine tmp/benchmark-core-tracked.json \\
        --title "head (this pull request)" --markdown-out "$GITHUB_STEP_SUMMARY"
"""

import argparse
import sys
from pathlib import Path
from typing import Any

from scripts.benchmark_utils import (
    BENCHMARK_ESTIMATORS,
    DEFAULT_BENCHMARK_ESTIMATOR,
    DEFAULT_METRIC_KEY,
    METRIC_SPECS,
    BenchmarkEstimator,
    MetricSpec,
    load_benchmark_json,
    machine_label,
)
from scripts.normalize_benchmark_json import ESTIMATOR_KEY


def acceleration_label(data: dict[str, Any]) -> str:
    """Name the point-in-polygon path the measurement actually exercised.

    Numba and clang are different implementations whose numbers are not
    comparable (see :mod:`scripts.assert_acceleration_path`), so a report that
    describes itself has to say which one it used.
    """
    recorded = data.get("machine_info", {}).get("timezonefinder") or {}
    if recorded.get("using_numba"):
        return "numba"
    if recorded.get("using_clang_pip"):
        return "clang C extension"
    if not recorded:
        return "unrecorded"
    return "pure Python"


def workload_label(provenance: dict[str, Any]) -> str:
    """Describe the amount of work the measurements cover.

    A timing report records the ``batch_size`` one round performs; a memory
    report records how many lookups preceded the steady-state reading
    (``memory_workload_size``, see :mod:`scripts.measure_memory`). Reporting
    whichever the file actually carries keeps one renderer honest for both
    instead of printing ``batch size ?`` for half of them.
    """
    if "memory_workload_size" in provenance:
        size = f"workload {provenance['memory_workload_size']}"
    else:
        size = f"batch size {provenance.get('batch_size', '?')}"
    return (
        f"{size}, fixtures {provenance.get('fixture_version', '?')}, "
        f"timezone data {provenance.get('data_version', '?')}"
    )


def render_markdown(
    data: dict[str, Any],
    title: str,
    metric: MetricSpec = METRIC_SPECS[DEFAULT_METRIC_KEY],
) -> str:
    """Render the machine, the acceleration path and the tracked values."""
    estimator: BenchmarkEstimator = data.get(ESTIMATOR_KEY, DEFAULT_BENCHMARK_ESTIMATOR)
    provenance = data.get("machine_info", {}).get("timezonefinder") or {}
    lines = [
        f"## {metric.heading} run: {title}",
        "",
        f"- **CPU**: {machine_label(data) or 'not recorded'}",
        f"- **Acceleration path**: {acceleration_label(data)}",
        f"- **Tracked estimator**: `{estimator}`",
        f"- **Workload**: {workload_label(provenance)}",
        "",
        "> `ubuntu-latest` pins the runner image, not the CPU. Two runs on "
        "different CPUs from this pool differ by more than most code changes "
        "do, so never read a difference between two runs without checking this "
        "line on both.",
        "",
        f"| {metric.row_noun} | {estimator} |",
        "| --- | ---: |",
    ]
    for bench in data.get("benchmarks", []):
        value = bench["stats"][estimator]
        lines.append(f"| `{bench['fullname']}` | {metric.format_value(value)} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Print the machine and workload a pytest-benchmark report describes, "
            "as a markdown block for a GitHub job summary."
        )
    )
    parser.add_argument(
        "benchmark_json",
        type=Path,
        help="a pytest-benchmark JSON report",
    )
    parser.add_argument(
        "--title",
        default="measurement",
        help="heading for the block, naming what was measured",
    )
    parser.add_argument(
        "--estimator",
        choices=BENCHMARK_ESTIMATORS,
        default=DEFAULT_BENCHMARK_ESTIMATOR,
        help=(
            "statistic to list, used only if the report does not record which "
            f"one it was normalized to (default: {DEFAULT_BENCHMARK_ESTIMATOR})"
        ),
    )
    parser.add_argument(
        "--metric",
        choices=sorted(METRIC_SPECS),
        default=DEFAULT_METRIC_KEY,
        help=(
            "what the listed numbers measure, which selects their units and the "
            f"heading (default: {DEFAULT_METRIC_KEY})"
        ),
    )
    parser.add_argument(
        "--markdown-out",
        type=Path,
        help="also append the block to this file (e.g. $GITHUB_STEP_SUMMARY)",
    )
    args = parser.parse_args()

    data = load_benchmark_json(args.benchmark_json)
    data.setdefault(ESTIMATOR_KEY, args.estimator)
    try:
        report = render_markdown(data, args.title, METRIC_SPECS[args.metric])
    except KeyError as exc:
        print(
            f"ERROR: {args.benchmark_json} has no {exc} statistic to report",
            file=sys.stderr,
        )
        sys.exit(1)
    print(report)
    if args.markdown_out is not None:
        with open(args.markdown_out, "a") as f:
            f.write(report)


if __name__ == "__main__":
    main()
