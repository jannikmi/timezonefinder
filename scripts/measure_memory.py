#!/usr/bin/env python3

"""Measure the memory footprint of every supported finder configuration.

Why this is not a ``benchmarks/`` suite
---------------------------------------

pytest-benchmark measures wall clock and nothing else, and it reaches its
numbers by running each benchmark for many calibration, warmup and timed
rounds. Enabling ``tracemalloc`` across those rounds would distort exactly the
timings that suite exists to produce, and a footprint has no meaningful
"rounds" anyway - constructing the same finder twice in one process measures
the allocator, not the library. So memory gets its own harness, one fresh
subprocess per configuration (see :mod:`scripts._memory_probe`).

Why the output is shaped like a pytest-benchmark report
-------------------------------------------------------

Everything downstream of a measurement in this repo already speaks that shape:
``scripts.normalize_benchmark_json`` picks the tracked estimator and stamps the
CPU, ``scripts.benchmark_noise`` derives an alert threshold from repeated runs,
``scripts.compare_benchmark_runs`` compares a pull request against its merge
base on the same runner, and ``scripts.describe_benchmark_machine`` says which
machine a report came from. None of that logic is about time - it is about
"one number per named metric, measured several times" - so emitting
``{"machine_info": ..., "benchmarks": [{"fullname", "stats"}]}`` here buys all
of it instead of reimplementing it for bytes.

Usage::

    uv run python -m scripts.measure_memory --output tmp/memory.json
"""

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, NamedTuple

from scripts.benchmark_utils import cpu_info, get_system_status
from scripts.configs import DEBUG, PROJECT_ROOT
from tests.auxiliaries import (
    BENCHMARK_FIXTURES_DIR,
    RANDOM_POINTS_FIXTURE,
    benchmark_fixture_provenance,
)

# How many lookups each configuration performs before its steady-state
# footprint is read. This is the whole committed random-point fixture: with
# `in_memory=False` the coordinate data is memory mapped and only becomes
# resident as lookups fault its pages in, so too small a workload would report
# the file-based mode as nearly free. It is recorded into the report and
# treated as a comparability key, so two reports taken at different sizes
# refuse to be compared rather than silently describing different work.
MEMORY_WORKLOAD_SIZE = 10_000

# Every metric is a byte count, and every configuration reports the same four.
# `init` is immediately after construction, `steady` after the workload; the
# gap between them is the memory mapping being faulted in.
HEAP_METRICS = ("init_heap", "steady_heap")
RSS_METRICS = ("init_rss", "steady_rss")
CONFIG_METRICS = (*HEAP_METRICS, *RSS_METRICS)

# The one measurement that is not per configuration: importing the package
# (numpy and h3 above all) before any timezone data is touched.
IMPORT_METRIC_NAME = "memory::import::rss"

METRIC_NAME_PREFIX = "memory::"


class MemoryConfig(NamedTuple):
    """One finder construction whose footprint is measured on its own."""

    id: str
    finder_class: str
    in_memory: bool


# `TimezoneFinderL` appears once, not twice: it holds no `PolygonArray`, so its
# `in_memory` argument never reaches `create_coord_accessor()` in
# `timezonefinder/coord_accessors.py` - the package's only branch on the flag.
# A second entry for it would put a duplicate measurement on the trend chart
# and present it as coverage.
CONFIGS: tuple[MemoryConfig, ...] = (
    MemoryConfig("TimezoneFinder[in_memory]", "TimezoneFinder", True),
    MemoryConfig("TimezoneFinder[file_based]", "TimezoneFinder", False),
    MemoryConfig("TimezoneFinderL", "TimezoneFinderL", False),
)

DEFAULT_REPETITIONS = 3

PROBE_MODULE = "scripts._memory_probe"


def metric_name(config_id: str, metric: str) -> str:
    """The name a metric is recorded and charted under.

    Metric names are the trend chart's join key, exactly like the benchmark
    node ids pinned by ``tests/test_benchmark_names.py``: renaming one starts
    a fresh history rather than continuing the old one, silently.
    """
    return f"{METRIC_NAME_PREFIX}{config_id}::{metric}"


def expected_metric_names() -> set[str]:
    """Every name this harness can emit, including the RSS ones.

    RSS is unavailable on some platforms and those metrics are then omitted
    (see :func:`build_report`), so this is a superset of what any single run
    produces - which is what ``tests/test_memory_metric_names.py`` checks
    against.
    """
    return {IMPORT_METRIC_NAME} | {
        metric_name(config.id, metric)
        for config in CONFIGS
        for metric in CONFIG_METRICS
    }


def points_fixture_path() -> Path:
    """The committed query points, resolved from the fixture constants.

    Resolved here rather than in the probe because the probe must not import
    ``tests.auxiliaries`` - see its module docstring.
    """
    return BENCHMARK_FIXTURES_DIR / f"{RANDOM_POINTS_FIXTURE}.npy"


def run_probe(
    config: MemoryConfig, points_path: Path, workload_size: int
) -> dict[str, int | None]:
    """Measure one configuration in a fresh interpreter."""
    command = [
        sys.executable,
        "-m",
        PROBE_MODULE,
        "--finder-class",
        config.finder_class,
        "--points",
        str(points_path),
        "--workload-size",
        str(workload_size),
    ]
    if config.in_memory:
        command.append("--in-memory")
    # from the project root, so `-m scripts._memory_probe` resolves whatever
    # the caller's working directory happens to be (pytest, make, a CI step)
    result = subprocess.run(command, capture_output=True, text=True, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise RuntimeError(
            f"memory probe for {config.id!r} failed with exit code "
            f"{result.returncode}:\n{result.stderr}"
        )
    return json.loads(result.stdout)


def measure_configs(
    configs: Iterable[MemoryConfig],
    repetitions: int,
    workload_size: int = MEMORY_WORKLOAD_SIZE,
) -> dict[str, list[int | None]]:
    """Collect ``repetitions`` samples of every metric, keyed by metric name."""
    points_path = points_fixture_path()
    samples: dict[str, list[int | None]] = {}
    for config in configs:
        for _ in range(repetitions):
            measured = run_probe(config, points_path, workload_size)
            for metric in CONFIG_METRICS:
                samples.setdefault(metric_name(config.id, metric), []).append(
                    measured[metric]
                )
            samples.setdefault(IMPORT_METRIC_NAME, []).append(measured["import_rss"])
    return samples


def _stats(values: list[int]) -> dict[str, float | int]:
    """Summarise repeated samples the way pytest-benchmark's ``stats`` does."""
    return {
        "min": float(min(values)),
        "max": float(max(values)),
        "mean": float(statistics.fmean(values)),
        "median": float(statistics.median(values)),
        "stddev": float(statistics.stdev(values)) if len(values) > 1 else 0.0,
        "rounds": len(values),
    }


def build_report(
    samples: dict[str, list[int | None]], workload_size: int
) -> dict[str, Any]:
    """Assemble a pytest-benchmark-shaped report from collected samples.

    Metrics whose value is unavailable (RSS on a platform that exposes
    neither ``/proc/self/status`` nor ``getrusage``) or non-positive are
    dropped rather than recorded as ``None`` or ``0``: every consumer of this
    shape divides by the value at some point, and a report that is missing a
    metric is far easier to diagnose than one that quietly contains a zero.
    """
    benchmarks = []
    for name in sorted(samples):
        values = [v for v in samples[name] if v is not None and v > 0]
        if len(values) != len(samples[name]) or not values:
            continue
        benchmarks.append({"fullname": name, "name": name, "stats": _stats(values)})
    if not benchmarks:
        raise RuntimeError(
            "no memory metric could be measured - every sample was unavailable "
            "or non-positive"
        )
    return {
        "machine_info": {
            "cpu": cpu_info(),
            "timezonefinder": {
                **get_system_status(),
                **benchmark_fixture_provenance(),
                "memory_workload_size": workload_size,
            },
        },
        "benchmarks": benchmarks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Measure the memory footprint of each TimezoneFinder configuration "
            "and write a pytest-benchmark-shaped JSON report."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to write the JSON report to",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=DEFAULT_REPETITIONS,
        help=(
            "how many fresh subprocesses to measure per configuration "
            f"(default: {DEFAULT_REPETITIONS})"
        ),
    )
    parser.add_argument(
        "--configs",
        help=(
            "comma-separated subset of "
            f"{','.join(c.id for c in CONFIGS)} (default: all). Measuring one "
            "configuration is the fast path while iterating locally."
        ),
    )
    args = parser.parse_args()

    if DEBUG:
        # the same guard benchmarks/conftest.py applies: DEBUG lowers
        # SHORTCUT_H3_RES, which changes the size of the shortcut index and so
        # the very thing being measured
        parser.error(
            "scripts.configs.DEBUG is True, which overrides SHORTCUT_H3_RES to a "
            "much coarser resolution. Footprints measured under DEBUG describe a "
            "different shortcut index and must never be recorded."
        )
    if args.repetitions < 1:
        parser.error("--repetitions must be at least 1")

    configs = CONFIGS
    if args.configs:
        wanted = [c.strip() for c in args.configs.split(",")]
        by_id = {c.id: c for c in CONFIGS}
        unknown = [name for name in wanted if name not in by_id]
        if unknown:
            parser.error(f"unknown config(s) {unknown}; choose from {sorted(by_id)}")
        configs = tuple(by_id[name] for name in wanted)

    samples = measure_configs(configs, args.repetitions, MEMORY_WORKLOAD_SIZE)
    report = build_report(samples, MEMORY_WORKLOAD_SIZE)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report))
    print(
        f"Wrote {args.output} with {len(report['benchmarks'])} memory metric(s) "
        f"from {args.repetitions} repetition(s) of {len(configs)} configuration(s)"
    )


if __name__ == "__main__":
    main()
