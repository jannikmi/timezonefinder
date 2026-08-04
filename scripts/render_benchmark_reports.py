#!/usr/bin/env python3

"""Render docs/benchmark_results_*.rst from a pytest-benchmark JSON file.

Usage:
    uv run python scripts/render_benchmark_reports.py --benchmark-json <path>

Rendering is a pure function of the JSON: measurement (`make benchmarks`,
pytest-benchmark) and rendering (this script) are fully decoupled, so the
docs can be regenerated from a stored JSON without re-running anything.

Reuses ``BenchmarkReporter`` / ``add_system_status_section``
(scripts/benchmark_utils.py) rather than a second RST-rendering
implementation. The reported numba/clang/version flags and batch size
describe the environment/run that *produced* the JSON - captured at
benchmark-run time by ``benchmarks/conftest.py``'s
``pytest_benchmark_update_machine_info`` hook, not whichever checkout
happens to render this script. Importing ``BATCH_SIZE`` from
``benchmarks.conftest`` directly would be wrong here: a stored JSON must
render correctly even from a checkout where that constant has since
changed.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable

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


def _decimals_for_magnitude(value: float) -> int:
    """Decimal places giving ~3 significant figures for ``value``.

    Fewer digits as the value grows (0 decimals at >=100, 1 at >=10, else 2),
    so a table doesn't show false precision on a large number (``"192.30x"``)
    or too few significant digits on a small one. This is the "human
    friendly rounding" shared by every formatter below.
    """
    abs_value = abs(value)
    if abs_value >= 100:
        return 0
    if abs_value >= 10:
        return 1
    return 2


def format_duration(seconds: float) -> str:
    """Format a duration using the most readable unit for its magnitude.

    Milliseconds/microseconds/nanoseconds below one second, so batch and
    per-query times read naturally instead of forcing scientific notation on
    every cell, rounded to ~3 significant figures (see
    :func:`_decimals_for_magnitude`) instead of a fixed number of decimals -
    "414ms" and "8.47ms" are both more readable than "414.000ms"/"8.475ms".
    Falls back to scientific notation only outside the ns-s range, which
    shouldn't occur for these benchmarks.
    """
    abs_seconds = abs(seconds)
    if abs_seconds == 0:
        return "0ms"
    if abs_seconds >= 1:
        value, unit = seconds, "s"
    elif abs_seconds >= 1e-3:
        value, unit = seconds * 1e3, "ms"
    elif abs_seconds >= 1e-6:
        value, unit = seconds * 1e6, "µs"
    elif abs_seconds >= 1e-9:
        value, unit = seconds * 1e9, "ns"
    else:
        return f"{seconds:.3e}s"
    return f"{value:.{_decimals_for_magnitude(value)}f}{unit}"


def format_rate(rate: float) -> str:
    """Format an operations-per-second rate with a k/M suffix and ~3
    significant figures, so a throughput column scans as quickly as the
    duration columns instead of a long run of digits (``"3.57M/s"`` rather
    than ``"3,573,050/s"``).
    """
    abs_rate = abs(rate)
    if abs_rate >= 1e6:
        value, suffix = rate / 1e6, "M"
    elif abs_rate >= 1e3:
        value, suffix = rate / 1e3, "k"
    else:
        value, suffix = rate, ""
    return f"{value:.{_decimals_for_magnitude(value)}f}{suffix}/s"


def format_ratio(ratio: float) -> str:
    """Format a speedup ratio to ~3 significant figures (``"192x"`` rather
    than ``"192.30x"``, but ``"1.39x"`` unchanged for a small ratio)."""
    return f"{ratio:.{_decimals_for_magnitude(ratio)}f}x"


# below this relative difference, "X% faster" reads as a false signal -
# treat it as measurement noise instead of declaring an arbitrary winner
NEGLIGIBLE_DIFFERENCE_PCT = 2.0


def speedup_ratio(slower_seconds: float, faster_seconds: float) -> float:
    """How many times faster ``faster_seconds`` is than ``slower_seconds``."""
    return slower_seconds / faster_seconds


def percent_faster(slower_seconds: float, faster_seconds: float) -> float:
    """How many percent faster ``faster_seconds`` is than ``slower_seconds``.

    Defined as ``(speedup_ratio - 1) * 100`` - i.e. anchored to the same
    "x times" scale as :func:`speedup_ratio` (2x is exactly 100% faster) -
    rather than the percent *time reduction* ``(slower-faster)/slower*100``.
    The time-reduction formula asymptotically approaches but can never reach
    100% no matter how large the speedup, which badly undersells a big one:
    it would report a 192x speedup as "99% faster", directly contradicting
    the "192x" printed right next to it.
    """
    return (speedup_ratio(slower_seconds, faster_seconds) - 1) * 100


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


def get_batch_size(system_info: dict[str, Any]) -> int:
    """Read back the ``BATCH_SIZE`` that produced these measurements.

    Reading this from the JSON (rather than importing ``benchmarks.conftest.
    BATCH_SIZE`` directly) is what makes it safe to render a JSON stored from
    an older run against a checkout where that constant has since changed -
    the reported batch size and the derived Time/Query/Throughput columns
    must reflect the measured run, not the current code.
    """
    batch_size = system_info.get("batch_size")
    if batch_size is None:
        raise ValueError(
            "benchmark JSON's machine_info['timezonefinder'] is missing 'batch_size' "
            "- it was produced before this field was added. Regenerate it with "
            "`pytest benchmarks/` (`make benchmarks`)."
        )
    return batch_size


def benchmarks_from_file(data: dict[str, Any], file_stem: str) -> list[dict[str, Any]]:
    prefix = f"benchmarks/{file_stem}.py::"
    matches = [b for b in data["benchmarks"] if b["fullname"].startswith(prefix)]
    if not matches:
        raise ValueError(
            f"benchmark JSON contains no results for {prefix}* - was it generated "
            "from the full `make benchmarks` run?"
        )
    return sorted(matches, key=lambda b: b["name"])


ExtraColumn = tuple[str, Callable[[dict[str, Any]], str]]


def stats_row(
    label: str, bench: dict[str, Any], extra_columns: tuple[ExtraColumn, ...] = ()
) -> list[str]:
    stats = bench["stats"]
    row = [
        label,
        format_duration(stats["mean"]),
        format_duration(stats["median"]),
        format_duration(stats["stddev"]),
        format_duration(stats["min"]),
        format_duration(stats["max"]),
        str(stats["rounds"]),
    ]
    row.extend(column_fn(bench) for _, column_fn in extra_columns)
    return row


def add_benchmark_table(
    reporter: BenchmarkReporter,
    benches: list[dict[str, Any]],
    section_level: int,
    extra_columns: tuple[ExtraColumn, ...] = (),
) -> None:
    """Add one table per function label found in ``benches``.

    Every row in a single pytest-benchmark table otherwise repeats the same
    ``FUNCTION_LABELS`` prefix (e.g. ``"TimezoneFinder.timezone_at() - ..."``
    in every row); grouping by function and hoisting that shared prefix into
    a section heading removes the redundancy instead of showing it in every
    row's "Configuration" cell. ``extra_columns`` appends derived metrics
    (e.g. per-query time, throughput) beyond the raw pytest-benchmark stats.
    """
    headers = [*CONFIG_HEADERS, *(name for name, _ in extra_columns)]
    groups: dict[str, list[dict[str, Any]]] = {}
    for bench in benches:
        func_label, _ = split_benchmark_label(bench["name"])
        groups.setdefault(func_label, []).append(bench)

    for func_label, group in groups.items():
        reporter.add_section(func_label, level=section_level)
        rows = []
        for bench in sorted(group, key=lambda b: b["name"]):
            _, params_label = split_benchmark_label(bench["name"])
            rows.append(stats_row(params_label or "-", bench, extra_columns))
        reporter.add_table(headers, rows)


def _full_label(bench: dict[str, Any]) -> str:
    return humanize_benchmark_name(bench["name"])


def _function_label(bench: dict[str, Any]) -> str:
    func_label, _ = split_benchmark_label(bench["name"])
    return func_label


def _memory_mode_label(bench: dict[str, Any]) -> str:
    return "in-memory" if bench["name"].endswith("in_memory]") else "file-based"


def add_comparison_bullet(
    reporter: BenchmarkReporter,
    context: str,
    bench_a: dict[str, Any],
    bench_b: dict[str, Any],
    label_fn: Callable[[dict[str, Any]], str] = _full_label,
) -> None:
    """Add one bullet comparing two benchmarks' mean time.

    Which one is faster is determined from the JSON at render time, never
    assumed - flipping which implementation wins on a given machine still
    produces a correct sentence. A difference under ``NEGLIGIBLE_DIFFERENCE_PCT``
    is reported as "about the same" rather than declaring an arbitrary
    winner - below that threshold the gap is noise, not signal (it's smaller
    than the stddev typically seen between rounds of the same benchmark).
    """
    mean_a, mean_b = bench_a["stats"]["mean"], bench_b["stats"]["mean"]
    if mean_a <= mean_b:
        faster, slower, faster_t, slower_t = bench_a, bench_b, mean_a, mean_b
    else:
        faster, slower, faster_t, slower_t = bench_b, bench_a, mean_b, mean_a
    pct = percent_faster(slower_t, faster_t)
    ratio = speedup_ratio(slower_t, faster_t)
    if pct < NEGLIGIBLE_DIFFERENCE_PCT:
        reporter.add_text(
            f"* {context}: **{label_fn(faster)}** and **{label_fn(slower)}** perform "
            f"about the same ({format_duration(faster_t)} vs {format_duration(slower_t)}, "
            f"{pct:.1f}% difference)"
        )
        return
    reporter.add_text(
        f"* {context}: **{label_fn(faster)}** is {pct:.0f}% faster ({format_ratio(ratio)}) than "
        f"**{label_fn(slower)}** ({format_duration(faster_t)} vs {format_duration(slower_t)})"
    )


def add_fastest_slowest_bullet(
    reporter: BenchmarkReporter, benches: list[dict[str, Any]], context: str = "Overall"
) -> None:
    fastest = min(benches, key=lambda b: b["stats"]["mean"])
    slowest = max(benches, key=lambda b: b["stats"]["mean"])
    fastest_t, slowest_t = fastest["stats"]["mean"], slowest["stats"]["mean"]
    pct = percent_faster(slowest_t, fastest_t)
    ratio = speedup_ratio(slowest_t, fastest_t)
    reporter.add_text(
        f"* {context}: fastest is **{humanize_benchmark_name(fastest['name'])}** "
        f"({format_duration(fastest_t)}), slowest is "
        f"**{humanize_benchmark_name(slowest['name'])}** ({format_duration(slowest_t)}) "
        f"- {pct:.0f}% faster ({format_ratio(ratio)})"
    )


def render_timezone_finding(data: dict[str, Any], output_path: Path) -> None:
    reporter = BenchmarkReporter(
        title="Timezone Finding Performance Benchmark", output_path=output_path
    )
    system_info = get_system_info(data)
    batch_size = get_batch_size(system_info)
    add_system_status_section(
        reporter,
        system_info,
        {
            "benchmark_source": "pytest-benchmark",
            "batch_size": batch_size,
        },
    )
    reporter.add_text(
        f"Each benchmark times one pass over {batch_size:,} fixed, committed query "
        "points (see benchmarks/conftest.py). Mean/Median/StdDev/Min/Max below are "
        f"for the full {batch_size:,}-query batch; Time/Query and Throughput divide "
        "and scale that out to a per-query figure."
    )

    benches = benchmarks_from_file(data, "test_timezone_finding")
    by_name = {b["name"]: b for b in benches}
    extra_columns: tuple[ExtraColumn, ...] = (
        ("Time/Query", lambda b: format_duration(b["stats"]["mean"] / batch_size)),
        ("Throughput", lambda b: format_rate(batch_size / b["stats"]["mean"])),
    )

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
        add_benchmark_table(
            reporter, group, section_level=3, extra_columns=extra_columns
        )

    if other:
        reporter.add_section("TimezoneFinderL (heuristic-only)", level=2)
        reporter.add_note(
            "TimezoneFinderL does not support in-memory mode; shortcuts are always "
            "loaded from disk."
        )
        add_benchmark_table(
            reporter, other, section_level=3, extra_columns=extra_columns
        )

    reporter.add_section("Performance Summary", level=2)
    reporter.add_text("**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):")
    for point_type in ("random", "on_land", "unique_shortcut", "ambiguous_shortcut"):
        in_mem = by_name.get(f"test_timezone_at[{point_type}-in_memory]")
        file_b = by_name.get(f"test_timezone_at[{point_type}-file_based]")
        if in_mem and file_b:
            context = PARAM_LABELS.get(point_type, point_type).capitalize()
            add_comparison_bullet(
                reporter, context, in_mem, file_b, label_fn=_memory_mode_label
            )

    land_in_mem = by_name.get("test_timezone_at_land[in_memory]")
    land_file_b = by_name.get("test_timezone_at_land[file_based]")
    if land_in_mem and land_file_b:
        add_comparison_bullet(
            reporter,
            "TimezoneFinder.timezone_at_land()",
            land_in_mem,
            land_file_b,
            label_fn=_memory_mode_label,
        )

    unique = by_name.get("test_timezone_at[unique_shortcut-in_memory]")
    ambiguous = by_name.get("test_timezone_at[ambiguous_shortcut-in_memory]")
    if unique and ambiguous:
        ratio = speedup_ratio(ambiguous["stats"]["mean"], unique["stats"]["mean"])
        reporter.add_text(
            f"* Ambiguous-shortcut points are {ratio:.1f}x slower than unique-shortcut "
            "points (in-memory): a unique shortcut resolves directly from the H3 index, "
            "while an ambiguous one falls through to the full point-in-polygon check."
        )

    add_fastest_slowest_bullet(reporter, benches)

    reporter.write_report()


def render_polygon(data: dict[str, Any], output_path: Path) -> None:
    reporter = BenchmarkReporter(
        title="Point-in-Polygon Algorithm Performance Benchmark",
        output_path=output_path,
    )
    system_info = get_system_info(data)
    batch_size = get_batch_size(system_info)
    add_system_status_section(
        reporter,
        system_info,
        {
            "benchmark_source": "pytest-benchmark",
            "batch_size": batch_size,
            "polygon_strata": "small / medium / large (by vertex count percentile)",
        },
    )
    reporter.add_text(
        f"Each benchmark times one pass over {batch_size:,} fixed, committed (point, "
        "polygon) pairs drawn from a single polygon-size stratum, so the cost of the "
        "largest polygons isn't hidden behind an unweighted average. Mean/Median/"
        f"StdDev/Min/Max are for the full {batch_size:,}-pair batch; Throughput is "
        "queries/second for that batch."
    )

    benches = benchmarks_from_file(data, "test_inside_polygon")
    by_name = {b["name"]: b for b in benches}
    extra_columns: tuple[ExtraColumn, ...] = (
        ("Throughput", lambda b: format_rate(batch_size / b["stats"]["mean"])),
    )

    reporter.add_section("Results", level=2)
    add_benchmark_table(reporter, benches, section_level=3, extra_columns=extra_columns)

    reporter.add_section("Performance Summary", level=2)
    for stratum in ("small", "medium", "large"):
        clang = by_name.get(f"test_pt_in_poly_clang[{stratum}]")
        python = by_name.get(f"test_pt_in_poly_python[{stratum}]")
        if clang and python:
            add_comparison_bullet(
                reporter,
                PARAM_LABELS[stratum].capitalize(),
                clang,
                python,
                label_fn=_function_label,
            )
    add_fastest_slowest_bullet(reporter, benches)

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
    by_name = {b["name"]: b for b in benches}
    reporter.add_section("Results", level=2)
    add_benchmark_table(reporter, benches, section_level=3)

    reporter.add_section("Performance Summary", level=2)
    for cls in ("TimezoneFinder", "TimezoneFinderL"):
        in_mem = by_name.get(f"test_initialization[{cls}-in_memory]")
        file_b = by_name.get(f"test_initialization[{cls}-file_based]")
        if in_mem and file_b:
            add_comparison_bullet(
                reporter, cls, in_mem, file_b, label_fn=_memory_mode_label
            )
    add_fastest_slowest_bullet(reporter, benches)

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
