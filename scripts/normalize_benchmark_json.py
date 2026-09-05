#!/usr/bin/env python3

"""Make a pytest-benchmark JSON report track a chosen estimator, not the mean.

Why this exists
---------------

pytest-benchmark's own headline number is the mean, and so is what every tool
that reads its JSON reaches for by default. On shared GitHub-hosted runners the
mean is the most noise-sensitive of its estimators: a single descheduled round
drags it up, while the fastest round is essentially unaffected. Since every
round of these benchmarks performs the exact same fixed batch of work
(``benchmarks/conftest.py``'s ``BATCH_SIZE``), ``min`` is the estimator that
best isolates the code's cost from the machine's mood.

This rewrites ``stats.ops`` - and ``stats.mean``, from which it is derived, so
the two stay consistent - from the chosen estimator, and records which one
under :data:`ESTIMATOR_KEY`. The result is still a perfectly ordinary
pytest-benchmark JSON, so ``--benchmark-compare`` and anything else pointed at
the stored report reads the tracked number rather than the mean, and this
project's own consumers (``scripts.compare_benchmark_runs``,
``scripts.describe_benchmark_machine``, both chart exports) resolve the
estimator from that key instead of hardcoding one.

``stats.stddev`` is deliberately left untouched: the *observed* within-run
spread is exactly the useful thing to see beside a min, and it is what both
chart exports render as their ``range`` annotation.

Nothing here shapes the trend chart itself. Neither suite is handed to
``benchmark-action/github-action-benchmark``'s ``pytest`` extractor any more -
that one reads ``stats.ops`` as ``iter/sec``, i.e. batches per second under a
raw node id, which is neither an interpretable unit nor a readable name. Both
charts are exported explicitly instead, by
:mod:`scripts.export_timing_chart_json` and
:mod:`scripts.export_memory_chart_json`.

Usage::

    uv run python -m scripts.normalize_benchmark_json \\
        --benchmark-json tmp/benchmark-core-raw.json \\
        --output tmp/benchmark-core-tracked.json \\
        --estimator min

The original file is never modified in place - the raw report keeps the full
min/max/mean/median/stddev statistics for anyone debugging a run.
"""

import argparse
import copy
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

# recorded at the top level of the rewritten file so a stored report says for
# itself which estimator its `ops`/`mean` were derived from. Unknown top-level
# keys are ignored by both pytest-benchmark and github-action-benchmark.
ESTIMATOR_KEY = "timezonefinder_tracked_estimator"


def normalize_benchmark_data(
    data: dict[str, Any], estimator: BenchmarkEstimator
) -> dict[str, Any]:
    """Return a copy of ``data`` with ``ops``/``mean`` derived from ``estimator``.

    :raises ValueError: if a benchmark lacks the estimator field or reports a
        non-positive duration for it (which would make ``ops`` undefined).
    """
    normalized = copy.deepcopy(data)
    benchmarks = normalized.get("benchmarks")
    if not benchmarks:
        raise ValueError(
            "benchmark JSON contains no 'benchmarks' entries - nothing to "
            "normalize. Was the pytest run empty (e.g. a marker expression "
            "that deselected everything)?"
        )
    for bench in benchmarks:
        stats = bench["stats"]
        if estimator not in stats:
            raise ValueError(
                f"benchmark {bench.get('fullname', bench.get('name'))!r} has no "
                f"'{estimator}' statistic; available: {sorted(stats)}"
            )
        value = stats[estimator]
        if value <= 0:
            raise ValueError(
                f"benchmark {bench.get('fullname', bench.get('name'))!r} reports a "
                f"non-positive '{estimator}' of {value!r}s, so operations/second "
                "cannot be derived from it"
            )
        stats["mean"] = value
        stats["ops"] = 1.0 / value
    normalized[ESTIMATOR_KEY] = estimator
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Rewrite a pytest-benchmark JSON report so the single value tracked "
            "by benchmark-action/github-action-benchmark is a chosen estimator "
            "instead of the (noise-sensitive) mean."
        )
    )
    parser.add_argument(
        "--benchmark-json",
        type=Path,
        required=True,
        help="Path to the raw JSON produced by `pytest benchmarks/ --benchmark-json=...`",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to write the rewritten report to (must differ from the input)",
    )
    parser.add_argument(
        "--estimator",
        choices=BENCHMARK_ESTIMATORS,
        default=DEFAULT_BENCHMARK_ESTIMATOR,
        help=f"statistic to track (default: {DEFAULT_BENCHMARK_ESTIMATOR})",
    )
    args = parser.parse_args()

    if args.output.resolve() == args.benchmark_json.resolve():
        parser.error(
            "--output must differ from --benchmark-json: the raw report is kept "
            "so the full min/max/mean/median/stddev statistics survive"
        )

    data = load_benchmark_json(args.benchmark_json)
    normalized = normalize_benchmark_data(data, args.estimator)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(normalized))
    print(
        f"Wrote {args.output} tracking '{args.estimator}' for "
        f"{len(normalized['benchmarks'])} benchmark(s), "
        f"measured on {machine_label(normalized) or 'an unrecorded CPU'}"
    )


if __name__ == "__main__":
    main()
