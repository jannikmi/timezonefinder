#!/usr/bin/env python3

"""Make a pytest-benchmark JSON report a chosen estimator instead of the mean.

Why this exists
---------------

``benchmark-action/github-action-benchmark``'s ``tool: pytest`` extractor
takes **one** number per benchmark as the tracked value::

    const value = stats.ops;   // = 1 / stats.mean
    const unit  = 'iter/sec';

i.e. it tracks the *mean*. On shared GitHub-hosted runners the mean is the
most noise-sensitive of pytest-benchmark's estimators: a single descheduled
round drags it up, while the fastest round is essentially unaffected. Since
every round of these benchmarks performs the exact same fixed batch of work
(``benchmarks/conftest.py``'s ``BATCH_SIZE``), ``min`` is the estimator that
best isolates the code's cost from the machine's mood.

Rather than hand-rolling storage/comparison (which is exactly what the action
exists to avoid), this rewrites ``stats.ops`` - and ``stats.mean``, which the
action renders alongside it, so the two stay consistent - from the chosen
estimator, leaving the file a perfectly ordinary pytest-benchmark JSON that
the action still parses natively. ``stats.stddev`` is deliberately left
untouched: the action shows it as the ``range: ±`` annotation, where the
*observed* within-run spread is exactly the useful thing to see.

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
        f"{len(normalized['benchmarks'])} benchmark(s)"
    )


if __name__ == "__main__":
    main()
