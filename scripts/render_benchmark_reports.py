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
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable

from scripts.benchmark_utils import (
    BenchmarkReporter,
    add_system_status_section,
    decimals_for_magnitude,
    format_bytes,
    load_benchmark_json,
)
from scripts.configs import (
    INITIALIZATION_REPORT_FILE,
    MEMORY_REPORT_FILE,
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


def format_duration(seconds: float) -> str:
    """Format a duration using the most readable unit for its magnitude.

    Milliseconds/microseconds/nanoseconds below one second, so batch and
    per-query times read naturally instead of forcing scientific notation on
    every cell, rounded to ~3 significant figures (see
    :func:`decimals_for_magnitude`) instead of a fixed number of decimals -
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
    return f"{value:.{decimals_for_magnitude(value)}f}{unit}"


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
    return f"{value:.{decimals_for_magnitude(value)}f}{suffix}/s"


def format_ratio(ratio: float) -> str:
    """Format a speedup ratio to ~3 significant figures (``"192x"`` rather
    than ``"192.30x"``, but ``"1.39x"`` unchanged for a small ratio)."""
    return f"{ratio:.{decimals_for_magnitude(ratio)}f}x"


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


PROVENANCE_FIELDS = ("fixture_version", "data_version")


def get_fixture_provenance(system_info: dict[str, Any]) -> dict[str, Any]:
    """Read back which fixture set and boundary data produced these measurements.

    Missing fields are an error rather than a silently omitted section: a
    report that simply leaves out its provenance is exactly the stale-report
    failure this stamp exists to prevent (see
    ``tests.auxiliaries.benchmark_fixture_provenance``).
    """
    missing = [f for f in PROVENANCE_FIELDS if system_info.get(f) is None]
    if missing:
        raise ValueError(
            f"benchmark JSON's machine_info['timezonefinder'] is missing {missing} "
            "- it was produced before these fields were added. Regenerate it with "
            "`pytest benchmarks/` (`make benchmarks`)."
        )
    return {f: system_info[f] for f in PROVENANCE_FIELDS}


def acceleration_path_label(system_info: dict[str, Any]) -> str:
    """Name the point-in-polygon implementation that actually produced the numbers.

    ``timezonefinder/utils.py`` binds the implementation at import time and
    prefers Numba over the C extension when both are importable, so the two
    recorded flags are not two independent choices - only one path ran. The
    "System Status" section prints both flags; this collapses them to the one
    fact a reader needs above the fold.
    """
    if system_info.get("using_numba"):
        return "Numba JIT"
    if system_info.get("using_clang_pip"):
        return "C extension (clang)"
    return "pure Python"


def is_ci_tracked_configuration(system_info: dict[str, Any]) -> bool:
    """Whether these numbers come from the configuration CI tracks.

    CI measures the C extension without Numba, because that is what a plain
    ``pip install timezonefinder`` gives you (see .github/workflows/benchmark.yml
    and docs/benchmarking_methodology.rst). Derived from the JSON rather than
    assumed, so a report rendered from a CI run says so and one rendered from a
    laptop carries the warning instead.
    """
    return bool(system_info.get("using_clang_pip")) and not system_info.get(
        "using_numba"
    )


def add_headline_section(
    reporter: BenchmarkReporter,
    system_info: dict[str, Any],
    headlines: Sequence[str],
) -> None:
    """Put the report's answer, and the configuration behind it, above the fold.

    Without this a reader has to parse four tables before learning how fast the
    library is, and never learns which acceleration path produced the figures -
    the reports are usually rendered from a developer machine whose
    configuration is neither the default install nor the CI-tracked one, so an
    unqualified table invites a comparison against the trend chart that is not
    a comparison at all.

    Every figure passed in ``headlines`` must be derived from the same parsed
    JSON as the tables below it; nothing here may be hardcoded, or the block
    goes stale exactly when the numbers change.
    """
    for headline in headlines:
        reporter.add_text(headline)

    platform = f"{system_info['platform_system']} {system_info['platform_machine']}"
    banner = (
        f"*Measured on {platform}, Python {system_info['python_version']}, "
        f"using the {acceleration_path_label(system_info)} point-in-polygon path.*"
    )
    if is_ci_tracked_configuration(system_info):
        banner += (
            " This is the configuration continuous integration tracks - what a plain "
            "``pip install timezonefinder`` gives you."
        )
    else:
        banner += (
            " Continuous integration tracks a different one - the C extension without "
            "Numba, what a plain ``pip install timezonefinder`` gives you - so these "
            "figures are not comparable to the trend chart."
        )
    banner += " See :doc:`benchmarking_methodology`."
    reporter.add_text(banner)


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
    # via PARAM_LABELS, the module's declared display vocabulary: spelling the
    # two labels out here let the comparison bullets keep the old wording while
    # the tables above them rendered the new one.
    param = "in_memory" if bench["name"].endswith("in_memory]") else "file_based"
    return PARAM_LABELS[param]


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
    benches = benchmarks_from_file(data, "test_timezone_finding")
    by_name = {b["name"]: b for b in benches}

    # the headline is the random-point workload, not the fastest one: uniformly
    # random queries are the only globally representative mix (see
    # docs/benchmarking_methodology.rst), so quoting unique-shortcut points here
    # would answer "how fast is it" with the best case
    headline_bench = by_name.get("test_timezone_at[random-in_memory]")
    headlines = []
    if headline_bench is not None:
        headline_mean = headline_bench["stats"]["mean"]
        headlines.append(
            f"**~{format_duration(headline_mean / batch_size)} per lookup, "
            f"~{format_rate(batch_size / headline_mean)}** - "
            "``TimezoneFinder.timezone_at()`` over uniformly random query points in "
            "memory, the workload closest to a real query mix."
        )
    add_headline_section(reporter, system_info, headlines)

    add_system_status_section(
        reporter,
        system_info,
        {
            "benchmark_source": "pytest-benchmark",
            "batch_size": batch_size,
        },
        provenance=get_fixture_provenance(system_info),
    )
    reporter.add_text(
        f"Each benchmark times one pass over {batch_size:,} fixed, committed query "
        "points (see benchmarks/conftest.py). Mean/Median/StdDev/Min/Max below are "
        f"for the full {batch_size:,}-query batch; Time/Query and Throughput divide "
        "and scale that out to a per-query figure."
    )

    extra_columns: tuple[ExtraColumn, ...] = (
        ("Time/Query", lambda b: format_duration(b["stats"]["mean"] / batch_size)),
        ("Throughput", lambda b: format_rate(batch_size / b["stats"]["mean"])),
    )

    in_memory = [b for b in benches if b["name"].endswith("in_memory]")]
    file_based = [b for b in benches if b["name"].endswith("file_based]")]
    other = [
        b for b in benches if not b["name"].endswith(("in_memory]", "file_based]"))
    ]

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
    benches = benchmarks_from_file(data, "test_inside_polygon")
    by_name = {b["name"]: b for b in benches}

    # per-check cost of the faster backend in each stratum. The spread between
    # the smallest and largest stratum *is* the finding this suite exists to
    # report, so it is the headline rather than any single number.
    per_check = {}
    for stratum in ("small", "large"):
        measured = [
            by_name[name]["stats"]["mean"]
            for name in (
                f"test_pt_in_poly_clang[{stratum}]",
                f"test_pt_in_poly_python[{stratum}]",
            )
            if name in by_name
        ]
        if measured:
            per_check[stratum] = min(measured) / batch_size
    headlines = []
    if "small" in per_check and "large" in per_check:
        headlines.append(
            f"**~{format_duration(per_check['small'])} per check on a small polygon, "
            f"~{format_duration(per_check['large'])} on the largest** "
            f"({format_ratio(per_check['large'] / per_check['small'])}) - which is why "
            "this suite is stratified by vertex count instead of averaged."
        )
    add_headline_section(reporter, system_info, headlines)

    add_system_status_section(
        reporter,
        system_info,
        {
            "benchmark_source": "pytest-benchmark",
            "batch_size": batch_size,
            "polygon_strata": "small / medium / large (by vertex count percentile)",
        },
        provenance=get_fixture_provenance(system_info),
    )
    reporter.add_text(
        f"Each benchmark times one pass over {batch_size:,} fixed, committed (point, "
        "polygon) pairs drawn from a single polygon-size stratum, so the cost of the "
        "largest polygons isn't hidden behind an unweighted average. Mean/Median/"
        f"StdDev/Min/Max are for the full {batch_size:,}-pair batch; Throughput is "
        "queries/second for that batch."
    )

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
    system_info = get_system_info(data)
    benches = benchmarks_from_file(data, "test_initialization")
    by_name = {b["name"]: b for b in benches}

    # the default construction (no in_memory argument) is the one a reader is
    # actually choosing between; TimezoneFinderL is quoted beside it because
    # "how much do I save by giving up the polygons" is the decision this page
    # informs
    default_init = by_name.get("test_initialization[TimezoneFinder-file_based]")
    lite_init = by_name.get("test_initialization[TimezoneFinderL-file_based]")
    headlines = []
    if default_init is not None:
        # RST inline markup does not nest: a ``literal`` inside **bold** renders
        # its backticks verbatim, so the two never overlap in these headlines
        headline = (
            f"**~{format_duration(default_init['stats']['mean'])}** to construct a "
            "``TimezoneFinder`` in the default file-based mode"
        )
        if lite_init is not None:
            headline += (
                f", **~{format_duration(lite_init['stats']['mean'])}** for "
                "``TimezoneFinderL``"
            )
        headline += (
            ". This is paid once per process - build one instance and reuse it "
            "rather than constructing per lookup."
        )
        headlines.append(headline)
    add_headline_section(reporter, system_info, headlines)

    add_system_status_section(
        reporter,
        system_info,
        {"benchmark_source": "pytest-benchmark"},
        provenance=get_fixture_provenance(system_info),
    )
    reporter.add_text(
        "Each round constructs one fresh instance (cold construction); "
        "`benchmark.pedantic(..., warmup_rounds=0)` disables pytest-benchmark's "
        "usual calibration warmup so it cannot touch the on-disk data ahead of "
        "the measured rounds (see benchmarks/test_initialization.py)."
    )

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


# Display labels and column order for the metrics `scripts/measure_memory.py`
# emits. Kept here rather than imported from that module for the same reason
# `batch_size` is read out of the JSON: a stored report must still render from
# a checkout whose metric set has moved on.
MEMORY_METRIC_LABELS = {
    "init_heap": "Heap after init",
    "steady_heap": "Heap after workload",
    "init_rss": "RSS after init",
    "steady_rss": "RSS after workload",
}

MEMORY_NAME_PATTERN = re.compile(r"^memory::(?P<config>.+)::(?P<metric>[^:]+)$")

# the one metric that is not per configuration - see scripts/measure_memory.py
MEMORY_IMPORT_NAME = "memory::import::rss"

MEMORY_UNAVAILABLE = "n/a"


def memory_values_by_config(data: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Group a memory report's metrics into ``{config: {metric: bytes}}``.

    The tracked ``min`` is used rather than the mean: every repetition measures
    the same construction, so the spread between them is the measurement
    settling, not a distribution worth averaging.
    """
    grouped: dict[str, dict[str, float]] = {}
    for bench in data.get("benchmarks", []):
        match = MEMORY_NAME_PATTERN.match(bench["fullname"])
        if match is None or bench["fullname"] == MEMORY_IMPORT_NAME:
            continue
        config = grouped.setdefault(match["config"], {})
        config[match["metric"]] = bench["stats"]["min"]
    if not grouped:
        raise ValueError(
            "memory JSON contains no per-configuration metrics - was it produced "
            "by `scripts.measure_memory` (`make memory`)?"
        )
    return grouped


def _memory_cell(values: dict[str, float], metric: str) -> str:
    """Render one measurement, or mark it unavailable.

    RSS is omitted entirely on platforms exposing neither ``/proc/self/status``
    nor ``getrusage``, so a cell can legitimately have no number behind it.
    """
    value = values.get(metric)
    return MEMORY_UNAVAILABLE if value is None else format_bytes(value)


def render_memory(data: dict[str, Any], output_path: Path) -> None:
    reporter = BenchmarkReporter(
        title="TimezoneFinder Memory Footprint", output_path=output_path
    )
    system_info = get_system_info(data)
    workload_size = system_info.get("memory_workload_size")
    by_config = memory_values_by_config(data)

    # the two modes a deployment actually chooses between, on the heap metric -
    # the only one that is charted, because RSS residency is decided by
    # machine-wide pressure (see docs/benchmarking_methodology.rst)
    file_based = by_config.get("TimezoneFinder[file_based]", {})
    in_memory = by_config.get("TimezoneFinder[in_memory]", {})
    headlines = []
    if "steady_heap" in file_based and "steady_heap" in in_memory:
        headlines.append(
            f"**~{format_bytes(file_based['steady_heap'])}** allocated in the default "
            f"mode, **~{format_bytes(in_memory['steady_heap'])}** with "
            "``in_memory=True`` - the default maps the coordinate data instead of "
            "reading it, which is what keeps it viable in a constrained container."
        )
    add_headline_section(reporter, system_info, headlines)

    add_system_status_section(
        reporter,
        system_info,
        {
            "measurement_source": "scripts/measure_memory.py",
            "workload_size": workload_size or "unknown",
        },
        provenance=get_fixture_provenance(system_info),
    )
    reporter.add_text(
        "Every figure below is a **delta**, measured in a fresh subprocess per "
        "configuration against a baseline taken once the package is imported. "
        "The import itself dominates any of them and is reported separately: it "
        "is the cost of NumPy and H3, paid once per process whichever finder "
        "you build."
    )
    # Two whole paragraphs rather than one with a conditional clause: the long one
    # interpolates the workload size, which is absent from an older measurement JSON,
    # and a ternary between two multi-line strings puts the branch where a reader
    # editing either one will not look for it.
    if workload_size:
        metric_explanation = (
            "``Heap`` is what ``tracemalloc`` accounts for - Python and NumPy "
            "allocations. ``RSS`` is the process resident set, which additionally "
            "counts memory-mapped pages. The two differ by design and the gap is "
            "the point: with ``in_memory=False`` the coordinate data is mapped "
            f"rather than read, so it becomes resident only as the {workload_size:,} "
            "lookups of the workload fault its pages in - which is why the "
            "``after init`` and ``after workload`` columns are both shown."
        )
    else:
        metric_explanation = (
            "``Heap`` is what ``tracemalloc`` accounts for; ``RSS`` is the "
            "process resident set, which additionally counts memory-mapped pages."
        )
    reporter.add_text(metric_explanation)

    metrics = list(MEMORY_METRIC_LABELS)
    headers = ["Configuration", *(MEMORY_METRIC_LABELS[m] for m in metrics)]
    rows = [
        [config, *(_memory_cell(by_config[config], m) for m in metrics)]
        for config in sorted(by_config)
    ]

    reporter.add_section("Results", level=2)
    reporter.add_table(headers, rows)

    reporter.add_section("Summary", level=2)
    import_bench = next(
        (b for b in data["benchmarks"] if b["fullname"] == MEMORY_IMPORT_NAME), None
    )
    if import_bench is not None:
        reporter.add_text(
            f"* Importing the package costs "
            f"**{format_bytes(import_bench['stats']['min'])}** of resident memory "
            "before any timezone data is touched."
        )

    if "steady_heap" in in_memory and "steady_heap" in file_based:
        ratio = in_memory["steady_heap"] / file_based["steady_heap"]
        reporter.add_text(
            f"* ``in_memory=True`` holds **{format_bytes(in_memory['steady_heap'])}** "
            f"on the heap against **{format_bytes(file_based['steady_heap'])}** for "
            f"the default file-based mode ({format_ratio(ratio)} more). That is the "
            "price of the speedup documented in :doc:`benchmark_results_timezonefinding`."
        )
    if "init_rss" in file_based and "steady_rss" in file_based:
        reporter.add_text(
            f"* The file-based mode's resident set grows from "
            f"**{format_bytes(file_based['init_rss'])}** at construction to "
            f"**{format_bytes(file_based['steady_rss'])}** once the workload has "
            "run, as the kernel faults in the mapped coordinate pages actually "
            "queried. Unlike the in-memory mode's allocation, these pages are "
            "reclaimable under memory pressure."
        )
    finder_l = by_config.get("TimezoneFinderL", {})
    if "steady_heap" in finder_l:
        reporter.add_text(
            f"* ``TimezoneFinderL`` holds **{format_bytes(finder_l['steady_heap'])}**: "
            "it consults only the shortcut index and loads no polygon data at all, "
            "which is why it takes no ``in_memory`` variant here."
        )

    reporter.add_note(
        "These numbers describe the data structures this package builds, not a "
        "container sizing recommendation: add the interpreter and the import cost "
        "above, and note that RSS attribution of memory-mapped pages is "
        "platform-specific."
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
    parser.add_argument(
        "--memory-json",
        type=Path,
        help=(
            "Path to a JSON file produced by `scripts.measure_memory` "
            "(`make memory`). Omit to leave the memory report untouched."
        ),
    )
    args = parser.parse_args()

    data = load_benchmark_json(args.benchmark_json)
    render_timezone_finding(data, PERFORMANCE_REPORT_FILE)
    render_polygon(data, POLYGON_REPORT_FILE)
    render_initialization(data, INITIALIZATION_REPORT_FILE)
    written = [PERFORMANCE_REPORT_FILE, POLYGON_REPORT_FILE, INITIALIZATION_REPORT_FILE]
    if args.memory_json is not None:
        render_memory(load_benchmark_json(args.memory_json), MEMORY_REPORT_FILE)
        written.append(MEMORY_REPORT_FILE)
    print(f"Wrote {', '.join(str(path) for path in written)}")


if __name__ == "__main__":
    main()
