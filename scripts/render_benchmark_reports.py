#!/usr/bin/env python3

"""Render docs/benchmark_results_*.rst from a pytest-benchmark JSON file.

Usage:
    uv run python scripts/render_benchmark_reports.py --benchmark-json <path>

Rendering is a pure function of the JSON: measurement (`make benchmarks`,
pytest-benchmark) and rendering (this script) are fully decoupled, so the
docs can be regenerated from a stored JSON without re-running anything.

Reuses ``BenchmarkReporter`` / ``add_system_status_section``
(scripts/benchmark_utils.py) rather than a second RST-rendering
implementation. The reported numba/clang/version flags describe the
environment that *produced* the JSON - captured at benchmark-run time by
``benchmarks/conftest.py``'s ``pytest_benchmark_update_machine_info`` hook -
not whichever environment happens to run this script.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

from benchmarks.conftest import BATCH_SIZE
from scripts.benchmark_utils import BenchmarkReporter, add_system_status_section
from scripts.configs import (
    INITIALIZATION_REPORT_FILE,
    PERFORMANCE_REPORT_FILE,
    POLYGON_REPORT_FILE,
)

CONFIG_HEADERS = [
    "Configuration",
    "Mean",
    "Median",
    "StdDev",
    "Min",
    "Max",
    "Rounds",
]

# Human-readable replacements for raw pytest-benchmark node-id pieces, used
# only for display in the rendered docs. Substitutions apply to the test
# function name and to each parametrize-id fragment separately (not the full
# name), so a new parametrize case reads sensibly without needing its own
# lookup entry. The raw id itself - the actual join key for historical
# tracking, see tests/test_benchmark_names.py - is not needed in the docs and
# is intentionally dropped here.
FUNCTION_LABELS = {
    "test_timezone_at": "TimezoneFinder.timezone_at()",
    "test_timezone_at_land": "TimezoneFinder.timezone_at_land()",
    "test_timezone_at_timezonefinderl": "TimezoneFinderL.timezone_at() (ambiguous-shortcut points)",
    "test_pt_in_poly_clang": "point-in-polygon (C/clang)",
    "test_pt_in_poly_python": "point-in-polygon (Python, Numba if available)",
    "test_initialization": "Initialization",
}

PARAM_LABELS = {
    "random": "random points",
    "on_land": "on-land points",
    "unique_shortcut": "unique-shortcut points",
    "ambiguous_shortcut": "ambiguous-shortcut points",
    "in_memory": "in-memory",
    "file_based": "file-based",
    "small": "small polygons",
    "medium": "medium polygons",
    "large": "large polygons",
}

_NODE_ID_PATTERN = re.compile(r"^(?P<func>[^\[]+)(\[(?P<params>.+)\])?$")


def split_benchmark_label(name: str) -> tuple[str, str]:
    """Split a raw pytest-benchmark ``name`` into ``(function_label, params_label)``.

    E.g. ``"test_timezone_at[ambiguous_shortcut-in_memory]"`` becomes
    ``("TimezoneFinder.timezone_at()", "ambiguous-shortcut points, in-memory")``.
    ``params_label`` is ``""`` for a non-parametrized benchmark. Falls back to
    the raw piece (underscores turned to spaces) for anything not in
    ``FUNCTION_LABELS``/``PARAM_LABELS``, so an unmapped new benchmark still
    renders reasonably instead of erroring.
    """
    match = _NODE_ID_PATTERN.match(name)
    if match is None:
        return name, ""
    func_label = FUNCTION_LABELS.get(match["func"], match["func"])
    params = match["params"]
    if not params:
        return func_label, ""
    param_labels = [PARAM_LABELS.get(p, p.replace("_", " ")) for p in params.split("-")]
    return func_label, ", ".join(param_labels)


def humanize_benchmark_name(name: str) -> str:
    """Turn a raw pytest-benchmark ``name`` into a single human-readable label.

    E.g. ``"test_timezone_at[ambiguous_shortcut-in_memory]"`` becomes
    ``"TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory"``.
    For a table with several rows sharing the same function, prefer
    :func:`split_benchmark_label` plus :func:`add_benchmark_table` instead -
    repeating the function label in every row is the redundancy this module
    otherwise avoids.
    """
    func_label, params_label = split_benchmark_label(name)
    if not params_label:
        return func_label
    return f"{func_label} - {params_label}"


def load_benchmark_json(json_path: Path) -> dict[str, Any]:
    with open(json_path) as f:
        return json.load(f)


def get_system_info(data: dict[str, Any]) -> dict[str, Any]:
    system_info = data.get("machine_info", {}).get("timezonefinder")
    if system_info is None:
        raise ValueError(
            "benchmark JSON is missing machine_info['timezonefinder']. It must be "
            "produced by `pytest benchmarks/` (see benchmarks/conftest.py's "
            "pytest_benchmark_update_machine_info hook), not an arbitrary "
            "pytest-benchmark run."
        )
    return system_info


def benchmarks_from_file(data: dict[str, Any], file_stem: str) -> list[dict[str, Any]]:
    prefix = f"benchmarks/{file_stem}.py::"
    matches = [b for b in data["benchmarks"] if b["fullname"].startswith(prefix)]
    if not matches:
        raise ValueError(
            f"benchmark JSON contains no results for {prefix}* - was it generated "
            "from the full `make benchmarks` run?"
        )
    return sorted(matches, key=lambda b: b["name"])


def stats_row(label: str, bench: dict[str, Any], divisor: float = 1.0) -> list[str]:
    stats = bench["stats"]
    return [
        label,
        f"{stats['mean'] / divisor:.2e}s",
        f"{stats['median'] / divisor:.2e}s",
        f"{stats['stddev'] / divisor:.2e}s",
        f"{stats['min'] / divisor:.2e}s",
        f"{stats['max'] / divisor:.2e}s",
        str(stats["rounds"]),
    ]


def add_benchmark_table(
    reporter: BenchmarkReporter,
    benches: list[dict[str, Any]],
    section_level: int,
    divisor: float = 1.0,
) -> None:
    """Add one table per function label found in ``benches``.

    Every row in a single pytest-benchmark table otherwise repeats the same
    ``FUNCTION_LABELS`` prefix (e.g. ``"TimezoneFinder.timezone_at() - ..."``
    in every row); grouping by function and hoisting that shared prefix into
    a section heading removes the redundancy instead of showing it in every
    row's "Configuration" cell.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for bench in benches:
        func_label, _ = split_benchmark_label(bench["name"])
        groups.setdefault(func_label, []).append(bench)

    for func_label, group in groups.items():
        reporter.add_section(func_label, level=section_level)
        rows = []
        for bench in sorted(group, key=lambda b: b["name"]):
            _, params_label = split_benchmark_label(bench["name"])
            rows.append(stats_row(params_label or "-", bench, divisor))
        reporter.add_table(CONFIG_HEADERS, rows)


def render_timezone_finding(data: dict[str, Any], output_path: Path) -> None:
    reporter = BenchmarkReporter(
        title="Timezone Finding Performance Benchmark", output_path=output_path
    )
    add_system_status_section(
        reporter,
        get_system_info(data),
        {
            "benchmark_source": "pytest-benchmark",
            "batch_size": BATCH_SIZE,
        },
    )
    reporter.add_text(
        f"Each benchmark times one pass over {BATCH_SIZE:,} fixed, committed "
        "query points (see benchmarks/conftest.py); rows below report "
        "seconds-per-batch. Divide by the batch size for seconds-per-query."
    )

    benches = benchmarks_from_file(data, "test_timezone_finding")
    in_memory = [b for b in benches if b["name"].endswith("in_memory]")]
    file_based = [b for b in benches if b["name"].endswith("file_based]")]
    other = [b for b in benches if b not in in_memory and b not in file_based]

    for section_title, group in (
        ("In-Memory Mode", in_memory),
        ("File-Based Mode", file_based),
    ):
        if not group:
            continue
        reporter.add_section(section_title, level=2)
        add_benchmark_table(reporter, group, section_level=3)

    if other:
        reporter.add_section("TimezoneFinderL (heuristic-only)", level=2)
        reporter.add_note(
            "TimezoneFinderL does not support in-memory mode; shortcuts are always "
            "loaded from disk."
        )
        add_benchmark_table(reporter, other, section_level=3)

    reporter.write_report()


def render_polygon(data: dict[str, Any], output_path: Path) -> None:
    reporter = BenchmarkReporter(
        title="Point-in-Polygon Algorithm Performance Benchmark",
        output_path=output_path,
    )
    add_system_status_section(
        reporter,
        get_system_info(data),
        {
            "benchmark_source": "pytest-benchmark",
            "batch_size": BATCH_SIZE,
            "polygon_strata": "small / medium / large (by vertex count percentile)",
        },
    )
    reporter.add_text(
        f"Each benchmark times one pass over {BATCH_SIZE:,} fixed, committed "
        "(point, polygon) pairs drawn from a single polygon-size stratum, so the "
        "cost of the largest polygons isn't hidden behind an unweighted average."
    )

    benches = benchmarks_from_file(data, "test_inside_polygon")
    reporter.add_section("Results", level=2)
    add_benchmark_table(reporter, benches, section_level=3)

    reporter.write_report()


def render_initialization(data: dict[str, Any], output_path: Path) -> None:
    reporter = BenchmarkReporter(
        title="TimezoneFinder Initialization Performance Benchmark",
        output_path=output_path,
    )
    add_system_status_section(
        reporter,
        get_system_info(data),
        {"benchmark_source": "pytest-benchmark"},
    )
    reporter.add_text(
        "Each round constructs one fresh instance (cold construction); "
        "`benchmark.pedantic(..., warmup_rounds=0)` disables pytest-benchmark's "
        "usual calibration warmup so it cannot touch the on-disk data ahead of "
        "the measured rounds (see benchmarks/test_initialization.py)."
    )

    benches = benchmarks_from_file(data, "test_initialization")
    reporter.add_section("Results", level=2)
    add_benchmark_table(reporter, benches, section_level=3)

    fastest = min(benches, key=lambda b: b["stats"]["mean"])
    slowest = max(benches, key=lambda b: b["stats"]["mean"])
    reporter.add_section("Performance Analysis", level=2)
    reporter.add_text(
        f"* **Fastest configuration**: {humanize_benchmark_name(fastest['name'])}"
    )
    reporter.add_text(
        f"* **Slowest configuration**: {humanize_benchmark_name(slowest['name'])}"
    )

    reporter.write_report()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render docs/benchmark_results_*.rst from a pytest-benchmark JSON file."
    )
    parser.add_argument(
        "--benchmark-json",
        type=Path,
        required=True,
        help="Path to a JSON file produced by `pytest benchmarks/ --benchmark-json=...`",
    )
    args = parser.parse_args()

    data = load_benchmark_json(args.benchmark_json)
    render_timezone_finding(data, PERFORMANCE_REPORT_FILE)
    render_polygon(data, POLYGON_REPORT_FILE)
    render_initialization(data, INITIALIZATION_REPORT_FILE)
    print(
        f"Wrote {PERFORMANCE_REPORT_FILE}, {POLYGON_REPORT_FILE}, "
        f"{INITIALIZATION_REPORT_FILE}"
    )


if __name__ == "__main__":
    main()
