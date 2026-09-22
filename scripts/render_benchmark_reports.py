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
from contextlib import contextmanager
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, Callable, NamedTuple

from benchmarks.candidate_comparison import CandidateComparison
from scripts.benchmark_utils import (
    DEFAULT_BENCHMARK_ESTIMATOR,
    TZFPY_DISTRIBUTION,
    BenchmarkReporter,
    add_system_status_section,
    decimals_for_magnitude,
    format_bytes,
    load_benchmark_json,
    comparability_info,
    cpu_model,
    machine_label,
)
from scripts.configs import (
    ACCELERATION_REPORT_FILE,
    BATCH_BREAK_EVEN_CHART_FILE,
    BATCH_BREAK_EVEN_REPORT_FILE,
    COMPARISON_REPORT_FILE,
    INITIALIZATION_REPORT_FILE,
    MEMORY_REPORT_FILE,
    PERFORMANCE_REPORT_FILE,
    POLYGON_REPORT_FILE,
)

# The break-even and saturation rules live with the measurement, not here, so this page
# and that script's stdout cannot drift apart - the same reason `CandidateComparison` is
# imported above rather than its verdict rule reimplemented.
from scripts.measure_batch_break_even import (
    CONTROL_MIN_BATCH_SIZE,
    CONTROL_SPREAD_THRESHOLD,
    DEFAULT_SATURATION_TOLERANCE,
    break_even,
    comparison_of,
    control_spread,
    per_point_seconds,
    point_class_label,
    saturation,
    speedup,
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
    "test_timezone_ids_at": "TimezoneFinder.timezone_ids_at()",
    "test_timezone_names_at": "TimezoneFinder.timezone_names_at()",
    "test_timezone_at_land": "TimezoneFinder.timezone_at_land()",
    "test_timezone_at_timezonefinderl": "TimezoneFinderL.timezone_at() (ambiguous-shortcut points)",
    "test_pt_in_poly_clang": "bare kernel (C/clang)",
    # The two rows below are relabelled per run - see `apply_interpreted_kernel_labels`.
    # These defaults describe neither path and exist only so a lookup never misses.
    "test_pt_in_poly_python": "bare kernel (interpreted)",
    "test_pt_in_poly_clang_packed": "packed kernel (C/clang)",
    "test_pt_in_poly_python_packed": "packed kernel (interpreted)",
    "test_initialization": "Initialization",
    "test_lookup_timezonefinder": "TimezoneFinder.timezone_at() (in-memory)",
    "test_lookup_timezonefinderl": "TimezoneFinderL.timezone_at()",
    "test_lookup_tzfpy": "tzfpy.get_tz()",
    "test_first_answer": "Time to first answer",
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
    "baseline": "bare interpreter (baseline)",
    "tzfpy": "tzfpy",
    "timezonefinder": "timezonefinder",
    "timezonefinderl": "TimezoneFinderL",
}

_NODE_ID_PATTERN = re.compile(r"^(?P<func>[^\[]+)(\[(?P<params>.+)\])?$")

# What a table cell says when the JSON carries no number for it. A cell can
# legitimately have nothing behind it - RSS is unavailable on some platforms,
# and a comparison column is empty when its benchmark was skipped - and one
# spelling shared by every table is what keeps "not measured" from reading as
# two different things on two pages.
MEASUREMENT_UNAVAILABLE = "n/a"


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

    ``timezonefinder/utils.py`` binds the implementation at import time, the C
    extension wherever it loaded, so the two recorded flags are not two independent
    choices - only one path ran, and ``using_clang_pip`` is the one that reports the
    *binding* rather than what the environment happens to hold. It is therefore read
    first: a process with Numba installed and the extension built runs the extension,
    and labelling its numbers "Numba JIT" would name an implementation that did not
    produce them. The "System Status" section prints both flags; this collapses them
    to the one fact a reader needs above the fold.
    """
    if system_info.get("using_clang_pip"):
        return "C extension (clang)"
    if system_info.get("using_numba"):
        return "Numba JIT"
    return "pure Python"


@contextmanager
def interpreted_kernel_labels(system_info: dict[str, Any]) -> Iterator[None]:
    """Name the ``utils_numba`` kernel rows after the path that actually produced them.

    ``benchmarks/test_inside_polygon.py``'s ``*_python`` benchmarks time
    ``timezonefinder/utils_numba.py``, which is the Numba-JIT'd kernel where Numba is
    installed and the plain Python one where it is not - the same node id carrying
    numbers from two implementations that are far apart. The node id has to stay
    put, since it is the trend chart's join key, so the *label* is what says which ran:
    a page rendered from the tracked configuration reads "pure Python", which is what a
    plain ``pip install`` runs and what those numbers have always described.

    Scoped rather than assigned, because ``FUNCTION_LABELS`` is shared by every
    renderer and a label left behind would describe the wrong run - in a test session
    it would describe the wrong *test*. See
    :doc:`benchmark_results_acceleration_paths` for the two measured against each other.
    """
    path = "Numba" if system_info.get("using_numba") else "pure Python"
    replacements = {
        "test_pt_in_poly_python": f"bare kernel ({path})",
        "test_pt_in_poly_python_packed": f"packed kernel ({path})",
    }
    previous = {name: FUNCTION_LABELS[name] for name in replacements}
    FUNCTION_LABELS.update(replacements)
    try:
        yield
    finally:
        FUNCTION_LABELS.update(previous)


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
    machine: str | None = None,
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
    measured_on = (
        f"{platform}, {machine}" if machine else f"{platform}, CPU not recorded"
    )
    banner = (
        f"*Measured on {measured_on}, Python {system_info['python_version']}, "
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


def add_ci_tracking_note(
    reporter: BenchmarkReporter,
    system_info: dict[str, Any],
    benches: Sequence[dict[str, Any]],
) -> None:
    """State how this full report differs from the CI trend measurement."""
    tracked = system_info.get("ci_tracked_benchmarks")
    estimator = system_info.get("ci_benchmark_estimator")
    if tracked is None or estimator is None:
        raise ValueError(
            "benchmark JSON is missing the recorded CI subset or estimator; "
            "re-measure it with `make reports` before rendering"
        )

    tracked_names = set(tracked)
    tracked_here = [
        humanize_benchmark_name(bench["name"])
        for bench in benches
        if bench.get("fullname") in tracked_names
    ]
    if tracked_here:
        rows = ", ".join(f"``{name}``" for name in tracked_here)
        reporter.add_text(
            f"Continuous integration records the ``{estimator}`` estimator for "
            f"these rows: {rows}. This published table leads with ``Mean`` and "
            "includes the full suite, so its values answer a different question "
            "from the trend chart."
        )
        return

    reporter.add_text(
        "Continuous integration tracks none of the rows on this page. This "
        "published table leads with ``Mean`` and belongs to the full on-demand "
        f"suite, while the trend chart records the ``{estimator}`` estimator for "
        "the smaller ``benchmark_core`` subset."
    )


# --- the acceleration paths, which take three runs to describe and two to measure ----

#: How far two runs' clang baselines may sit apart before the page says so. The same
#: 3 % the candidate harness calls the bottom of one machine's own jitter: below it a
#: difference is not demonstrable, above it the two processes were not doing the same
#: thing and the reader needs to know before reading the columns beside each other.
ANCHOR_AGREEMENT_THRESHOLD = 0.03

#: What the one-configuration pages say about the other two implementations. They
#: measure whichever path their environment bound and must keep doing so - three
#: environments on a page whose header asserts one is what
#: :doc:`benchmark_results_acceleration_paths` exists to avoid - so they point at it
#: rather than carrying its columns.
ACCELERATION_PATHS_POINTER = (
    "This page describes one point-in-polygon implementation. The other two are "
    "measured against it in :doc:`benchmark_results_acceleration_paths` - which is "
    "where the ranking between them is stated, since it is a measurement that moves "
    "and a claim repeated in prose would not."
)

ACCELERATION_PATH_LABELS = {
    "clang": "C extension (clang)",
    "numba": "Numba JIT",
    "python": "pure Python",
}

KERNEL_STRATUM_LABELS = {
    "small": "small polygons",
    "medium": "medium polygons",
    "large": "large polygons",
}


def _comparison_of(stored: dict[str, Any]) -> CandidateComparison:
    """Rebuild the harness's dataclass from what the measurement stored.

    The verdict rule - two estimators, believed only where they agree - lives in
    ``benchmarks/candidate_comparison.py`` and is reconstructed here rather than
    reimplemented, so a page can never disagree with the harness about what a
    measurement was allowed to claim.
    """
    return CandidateComparison(**stored)


def _acceleration_row(label: str, stored: dict[str, Any]) -> list[str]:
    comparison = _comparison_of(stored)
    # The challenger relative to clang, as a multiple rather than a signed percentage:
    # these span 1.0x to ~190x, and "+18913 %" is unreadable where "190x" is not.
    ratio = comparison.best_challenger / comparison.best_baseline
    return [
        label,
        format_duration(comparison.best_baseline),
        format_duration(comparison.best_challenger),
        format_ratio(ratio),
        f"{comparison.challenger_wins} of {comparison.rounds}",
        comparison.verdict,
    ]


def _acceleration_table(
    reporter: BenchmarkReporter,
    run: dict[str, Any],
    section: str,
    labels: dict[str, str],
) -> None:
    path = run["machine_info"]["timezonefinder"]["acceleration_path"]
    rows = [
        _acceleration_row(labels.get(key, key), stored)
        for key, stored in run[section].items()
    ]
    reporter.add_table(
        [
            "Workload",
            "C extension (clang)",
            ACCELERATION_PATH_LABELS.get(path, path),
            "Relative to clang",
            "Rounds won",
            "Verdict",
        ],
        rows,
    )


def _anchor_agreement(runs: Sequence[dict[str, Any]], section: str) -> list[list[str]]:
    """How far the runs' clang baselines sit apart, workload by workload.

    Published rather than used as a gate. The two runs are separate experiments and
    nothing on this page divides one into the other, so a divergence here does not
    invalidate a column - it tells the reader how much of the difference between two
    *environments* is not the point-in-polygon path at all.
    """
    keys = list(runs[0][section])
    rows = []
    for key in keys:
        anchors = [_comparison_of(run[section][key]).best_baseline for run in runs]
        spread = max(anchors) / min(anchors) - 1.0
        rows.append(
            [
                key.replace("_", " "),
                *(format_duration(a) for a in anchors),
                f"{spread * 100:.1f} %",
                "yes" if spread <= ANCHOR_AGREEMENT_THRESHOLD else "**no**",
            ]
        )
    return rows


#: The cold-process measurement :mod:`scripts._startup_probe` takes, one step per row.
#: Memory and time are two tables rather than one: four columns of each would not fit,
#: and a reader with a container limit and a reader with a cold-start budget are
#: rarely the same reader.
STARTUP_MEMORY_STEPS = (
    ("import_rss", "added by ``import timezonefinder``"),
    ("init_rss", "added by ``TimezoneFinder()``"),
    ("first_query_rss", "added by the first query"),
    ("ready_rss", "**the whole process, once the first answer is out**"),
)

STARTUP_TIME_STEPS = (
    ("import_seconds", "``import timezonefinder``"),
    ("init_seconds", "``TimezoneFinder()``"),
    ("first_query_seconds", "the first query"),
    ("time_to_first_answer", "**the whole way to the first answer**"),
)

#: Summed rather than measured: no process can time the three steps and the whole at
#: once, and the sum is what a caller waits for.
TIME_TO_FIRST_ANSWER_PARTS = (
    "import_seconds",
    "init_seconds",
    "first_query_seconds",
)


def _startup_value(startup: dict[str, Any], metric: str) -> float | None:
    if metric != "time_to_first_answer":
        return startup.get(metric)
    total = 0.0
    for part in TIME_TO_FIRST_ANSWER_PARTS:
        measured = startup.get(part)
        if measured is None:
            return None
        total += float(measured)
    return total


def _startup_column_label(startup: dict[str, Any]) -> str:
    return "With Numba" if startup["using_numba"] else "Plain install"


def _signed(value: float, formatter: Callable[[float], str]) -> str:
    return f"+{formatter(value)}" if value > 0 else formatter(value)


def _startup_table(
    reporter: BenchmarkReporter,
    startups: Sequence[dict[str, Any]],
    steps: Sequence[tuple[str, str]],
    formatter: Callable[[float], str],
) -> None:
    """One table of cold-process numbers, plain install first and the extra's cost last.

    The last column is a difference rather than a ratio: these are two environments
    and what a reader installing the extra pays is the amount added, not a multiple
    of a baseline they would no longer be running.
    """
    rows = []
    for metric, label in steps:
        values = [_startup_value(startup, metric) for startup in startups]
        cells = [
            MEASUREMENT_UNAVAILABLE if value is None else formatter(value)
            for value in values
        ]
        first, last = values[0], values[-1]
        cost = (
            MEASUREMENT_UNAVAILABLE
            if first is None or last is None
            else _signed(last - first, formatter)
        )
        rows.append([label, *cells, cost])
    reporter.add_table(
        ["Step", *(_startup_column_label(s) for s in startups), "Cost of the extra"],
        rows,
    )


def add_startup_section(
    reporter: BenchmarkReporter, runs: Sequence[dict[str, Any]]
) -> None:
    """What each environment costs from a cold process to its first answer.

    Skipped rather than faked when a run predates the measurement: the renderer is a
    pure function of stored JSON, so a report measured before this section existed
    renders without it instead of renaming its absence into a zero.
    """
    startups = [run["startup"] for run in runs if run.get("startup")]
    if len(startups) != len(runs):
        return
    # Plain install first, so the added column reads as something the extra costs.
    startups = sorted(startups, key=lambda s: s["using_numba"])

    reporter.add_section("What installing Numba costs before any query", level=1)
    reporter.add_text(
        "Speed is only one consequence of installing the ``numba`` extra, and it is "
        "the only one the tables above can see: a paired comparison runs both "
        "candidates in one process, which has already imported whatever its "
        "environment holds. The rows below are therefore not paired - each is a "
        "fresh process that imports the package, constructs a default "
        "``TimezoneFinder()`` and answers one query, measured by "
        "``scripts/_startup_probe.py`` and reported as the median of its repetitions. "
        "Both environments hold the C extension and both *bind* it, so the two "
        "processes run the same kernel and differ in exactly one thing - whether "
        "Numba is installed beside it. The last column is therefore what the extra "
        "costs an installation that already has a working extension, which is what it "
        "buys nothing for."
    )

    reporter.add_section("Resident memory", level=2)
    _startup_table(reporter, startups, STARTUP_MEMORY_STEPS, format_bytes)
    reporter.add_text(
        "Every row but the last is what that step added; the last is the whole "
        "process, which is the figure a container memory limit is set against. The "
        "difference is the Numba and ``llvmlite`` import plus the code it compiles, "
        "and it is paid per process - a worker pool pays it once per worker, and it "
        "does not shrink for ``TimezoneFinderL`` or for the memory-mapped default "
        "mode, because it is not boundary data (:doc:`benchmark_results_memory` "
        "measures that part)."
    )

    reporter.add_section("Time to the first answer", level=2)
    _startup_table(reporter, startups, STARTUP_TIME_STEPS, format_duration)
    reporter.add_text(
        "The compilation lands in the construction row rather than in the query one: "
        "``timezonefinder/utils_numba.py`` declares eager signatures, so the kernels "
        "are compiled when that module is first imported, which constructing a finder "
        "triggers. Numba caches that output on disk beside the installed package, so "
        "the figures here are the steady state - the median over repetitions discards "
        "the one process that compiled - and the *first* process in a fresh "
        "environment pays more. Where the installed package directory is read-only or "
        "thrown away between runs, every process pays it. Later queries are what the "
        "tables above measure; this is what a process pays before the first of them, "
        "and a short-lived process or a cold-started function pays it per invocation."
    )


def render_acceleration_paths(
    runs: Sequence[dict[str, Any]], output_path: Path
) -> None:
    """Render the three-path comparison from one run per measurable pair."""
    if len(runs) < 2:
        raise ValueError(
            "the acceleration-path page needs one run per environment - `make "
            "acceleration-paths` produces both. Got "
            f"{len(runs)}."
        )
    runs = sorted(
        runs, key=lambda r: r["machine_info"]["timezonefinder"]["acceleration_path"]
    )
    # `cpu_model`, not `machine_label`: the label carries the *measured* clock, which
    # a runner reports as whatever the core happened to be boosted to. Both runs of
    # the first CI render came off one EPYC 7763 and read 2.4454 GHz and 3.2435 GHz,
    # so comparing the display form rejected a pair measured on the same machine.
    # Identity is the model; whether the two runs are actually comparable is what the
    # shared clang baseline below answers, and it answers it in the quantity at stake
    # rather than in a proxy for it.
    machines = {cpu_model(run) for run in runs}
    if len(machines) != 1:
        raise ValueError(
            "the acceleration-path runs come from different CPUs "
            f"({sorted(str(m) for m in machines)}), so their columns describe "
            "different hardware and must not be published on one page. Re-measure "
            "both with `make acceleration-paths` on one machine."
        )

    reporter = BenchmarkReporter(
        title="Point-in-Polygon Acceleration Paths", output_path=output_path
    )
    system_info = get_system_info(runs[0])
    paths = [run["machine_info"]["timezonefinder"]["acceleration_path"] for run in runs]

    headlines = []
    lookup_rows = {
        run["machine_info"]["timezonefinder"]["acceleration_path"]: run["lookups"]
        for run in runs
    }
    for path in paths:
        random = _comparison_of(lookup_rows[path]["random"])
        ratio = random.best_challenger / random.best_baseline
        headlines.append(
            f"**{ACCELERATION_PATH_LABELS[path]}: {format_ratio(ratio)} the C "
            f"extension** on ``TimezoneFinder.timezone_at()`` over uniformly random "
            f"points ({random.verdict})."
        )
    for headline in headlines:
        reporter.add_text(headline)
    # Not `add_headline_section`: its banner names *the* acceleration path the numbers
    # came from, which is the right thing to say on a page describing one configuration
    # and a false one here - this page's whole subject is that there are three.
    platform = f"{system_info['platform_system']} {system_info['platform_machine']}"
    reporter.add_text(
        f"*Measured on {platform}, {machine_label(runs[0]) or 'CPU not recorded'}, "
        f"Python {system_info['python_version']}, across "
        f"{len(runs)} environments on one machine.*"
    )

    reporter.add_text(
        "The three point-in-polygon implementations, measured against each other "
        "rather than across commits. ``timezonefinder/utils.py`` binds one of them at "
        "import time, so which one a process runs is decided by its environment: the C "
        "extension wherever it loaded, the Numba-compiled function where it did not "
        "and ``numba`` is importable, and the plain Python function where neither is "
        "available. The rows below are therefore measured by rebinding the kernel "
        "rather than by installing a different environment. See "
        ":doc:`benchmarking_methodology`."
    )
    reporter.add_note(
        "Nothing on this page is on the continuous-integration trend chart, which "
        "tracks the C extension alone - what a plain ``pip install timezonefinder`` "
        "runs. These are on-demand measurements, taken by ``make acceleration-paths``."
    )

    reporter.add_section("How this is measured", level=1)
    reporter.add_text(
        "Numba and pure Python are one source decorated or not, so **no process holds "
        "both**: what a process does hold is the C extension plus whichever of the two "
        "its environment produced. Each row below is therefore a paired comparison "
        "inside one process - the same random draw handed to both candidates, the "
        "order alternating round by round, and two estimators reported so that a "
        "difference neither can demonstrate reads as ``unresolved`` rather than as a "
        "number (``benchmarks/candidate_comparison.py``)."
    )
    reporter.add_text(
        "That also fixes what this page will **not** do: divide one environment's "
        "column into the other's. Two runs in two processes can alternate nothing and "
        "share no draw, so a Numba-against-pure-Python ratio taken that way would rest "
        "on the single estimator this repository has already been misled by "
        "(:doc:`benchmarking_methodology`). The two measured pairs are published; the "
        "third ratio is not derived from them."
    )

    reporter.add_section("The kernel a lookup reaches", level=1)
    reporter.add_text(
        "``PolygonArray.pip`` over the packed payload, one pass over 2,500 committed "
        "(point, ring) pairs per round, split by polygon size so the largest rings are "
        "not hidden behind an average over a mostly-small population."
    )
    for run in runs:
        path = run["machine_info"]["timezonefinder"]["acceleration_path"]
        reporter.add_section(
            f"{ACCELERATION_PATH_LABELS[path]} against the C extension", level=2
        )
        _acceleration_table(reporter, run, "kernels", KERNEL_STRATUM_LABELS)

    reporter.add_section("What a caller actually pays", level=1)
    reporter.add_text(
        "``TimezoneFinder.timezone_at()`` in memory, over the same committed point "
        "fixtures the other pages use. The kernel ratio above **bounds** these and "
        "does not predict them: the H3 shortcut index answers a unique-shortcut query "
        "outright, so no point-in-polygon test runs at all and the two paths are "
        "measuring the same code."
    )
    for run in runs:
        path = run["machine_info"]["timezonefinder"]["acceleration_path"]
        reporter.add_section(
            f"{ACCELERATION_PATH_LABELS[path]} against the C extension", level=2
        )
        _acceleration_table(reporter, run, "lookups", PARAM_LABELS)

    add_startup_section(reporter, runs)

    reporter.add_section("How comparable the two runs are", level=1)
    reporter.add_text(
        "Both runs measure the C extension, so its two timings are the same quantity "
        "measured twice and their spread says how much of the gap between the tables "
        "above is the environment rather than the point-in-polygon path. Published "
        "rather than used as a gate, because nothing here divides one run into the "
        "other."
    )
    headers = [
        "Workload",
        *(f"clang, in the {ACCELERATION_PATH_LABELS[p]} run" for p in paths),
        "Spread",
        "Within 3 %",
    ]
    reporter.add_section("The kernel a lookup reaches", level=2)
    reporter.add_table(headers, _anchor_agreement(runs, "kernels"))
    reporter.add_section("What a caller actually pays", level=2)
    reporter.add_table(headers, _anchor_agreement(runs, "lookups"))
    reporter.add_text(
        "Two things move these rows. The first is ordinary run-to-run variation: the C "
        "kernel is the same compiled code in both runs, so wherever its two timings "
        "differ that is the floor for comparing anything *across* the two processes - "
        "and it is wider than the 3 % a paired comparison inside one process resolves, "
        "which is the whole reason this page does not divide one run into the other."
    )
    reporter.add_text(
        "The second is specific to the Numba run: **a process that merely has Numba "
        "installed is not the process a plain install runs**, even though both bind "
        "the same C-extension kernel. ``timezonefinder/utils.py`` imports "
        "``utils_numba`` either way, so where Numba is importable that import compiles "
        "the helpers a query calls around the geometry (``int2coord`` and the ring "
        "converters) and leaves the process holding the compiler as well. That is a "
        "different allocator and a different resident set to be measured in, which the "
        "section below prices directly."
    )

    reporter.write_report()


# --- the batch break-even sweep ------------------------------------------------------


class BatchBreakEvenSettings(NamedTuple):
    """The thresholds a stored run was taken under."""

    saturation_tolerance: float
    control_spread_threshold: float
    control_spread_min_batch_size: int


def batch_break_even_settings(info: dict[str, Any]) -> BatchBreakEvenSettings:
    """Read the stamped thresholds, defaulting to the constants for an older run."""
    return BatchBreakEvenSettings(
        saturation_tolerance=info.get(
            "saturation_tolerance", DEFAULT_SATURATION_TOLERANCE
        ),
        control_spread_threshold=info.get(
            "control_spread_threshold", CONTROL_SPREAD_THRESHOLD
        ),
        control_spread_min_batch_size=info.get(
            "control_spread_min_batch_size", CONTROL_MIN_BATCH_SIZE
        ),
    )


def _batch_break_even_row(rung: dict[str, Any]) -> list[str]:
    comparison = comparison_of(rung)
    return [
        f"{rung['batch_size']:,}",
        format_duration(per_point_seconds(rung, "best_baseline")),
        format_duration(per_point_seconds(rung, "best_challenger")),
        format_ratio(speedup(rung)),
        f"{comparison.challenger_wins} of {comparison.rounds}",
        comparison.verdict,
    ]


def _batch_break_even_headline(
    sweep: dict[str, Any], batch_api: str, settings: BatchBreakEvenSettings
) -> str:
    """One sentence per point class, stating both answers and their verdicts."""
    rungs = sweep["rungs"]
    crossing = break_even(rungs)
    settles = saturation(rungs, tolerance=settings.saturation_tolerance)
    label = point_class_label(sweep["point_class"])

    if crossing.status == "not_reached":
        opening = f"**{label}: batching is not demonstrably faster at any batch size measured**"
    elif crossing.status == "no_terminal_run":
        # faster at some rungs but not at the top of the ladder: a crossing needs a run
        # that holds to the end, and one noisy top rung is enough to break it
        opening = (
            f"**{label}: no crossing established** - batching won at "
            + ", ".join(f"N={size}" for size in crossing.non_monotone)
            + " but not at the top of the ladder"
        )
    elif crossing.status == "below_ladder":
        opening = (
            f"**{label}: batching already pays at {crossing.upper} point"
            f"{'' if crossing.upper == 1 else 's'}**"
        )
    else:
        opening = (
            f"**{label}: batching starts paying between {crossing.lower} and "
            f"{crossing.upper} points per call**"
        )

    # The saturation figure is withheld from the headline whenever the control says the
    # ladder did not measure one thing. It is read off the batched side's *absolute*
    # per-point time across rungs, which is exactly the quantity cross-rung drift moves,
    # so a run whose scalar baseline wandered cannot support it - three repeat runs of
    # this sweep put it at N=1,000, at N=500 and out of reach as the control went from
    # 5 % to 22 %. The crossing is a within-rung paired comparison and survives that,
    # which is why it stays in the headline either way.
    control = control_spread(
        rungs,
        threshold=settings.control_spread_threshold,
        min_batch_size=settings.control_spread_min_batch_size,
    )
    if not control.within_threshold:
        closing = (
            ". Where it stops improving is **not established on this run**: the scalar "
            f"baseline spread {control.spread * 100:.1f} % across rungs, above the "
            f"{control.threshold * 100:.0f} % this measurement needs before it can "
            "read an absolute quantity along the ladder."
        )
    elif settles.batch_size is not None and settles.speedup is not None:
        closing = (
            f", and stops improving beyond ~{settles.batch_size:,} "
            f"({format_ratio(settles.speedup)} the scalar loop, {settles.verdict})."
        )
    else:
        closing = ", and had not stopped improving at the top of the ladder."
    return f"{opening} for ``{batch_api}()``{closing}"


def render_batch_break_even(
    run: dict[str, Any], output_path: Path, chart_path: Path
) -> None:
    """Render the sweep page and the chart it embeds, from one stored run."""
    # imported here rather than at module scope: seaborn/matplotlib live in the
    # `benchmark` dependency group, which is deliberately absent from the measurement
    # environment, and every other page on this module must keep rendering without them
    from scripts.batch_break_even_chart import render_sweep

    sweeps = run["sweeps"]
    if not sweeps:
        raise ValueError("the batch break-even run holds no sweeps")
    for sweep in sweeps:
        sizes = [rung["batch_size"] for rung in sweep["rungs"]]
        if sizes != sorted(set(sizes)):
            raise ValueError(
                f"the {sweep['point_class']!r} sweep's rungs are not strictly "
                f"ascending ({sizes}); break-even and saturation are both read as runs "
                "along the ladder and would be meaningless out of order."
            )

    info = run["machine_info"]["timezonefinder"]
    system_info = get_system_info(run)
    batch_api = info["batch_api"]
    scalar_api = info["scalar_api"]
    # The settings the *run* was taken under, not this checkout's current constants: a
    # stored run must render as the answers it made. Falling back to the constants keeps
    # a run taken before these were stamped renderable. Same rule `get_batch_size`
    # enforces for `BATCH_SIZE` on the other pages.
    settings = batch_break_even_settings(info)

    reporter = BenchmarkReporter(
        title="When Batched Lookups Pay", output_path=output_path
    )
    for sweep in sweeps:
        reporter.add_text(_batch_break_even_headline(sweep, batch_api, settings))

    platform_label = (
        f"{system_info['platform_system']} {system_info['platform_machine']}"
    )
    reporter.add_text(
        f"*Measured on {platform_label}, {machine_label(run) or 'CPU not recorded'}, "
        f"Python {system_info['python_version']}, using the "
        f"{acceleration_path_label(system_info)} point-in-polygon path.*"
    )
    reporter.add_text(
        f"``{batch_api}()`` amortises validation, the integer scaling and the shortcut "
        f"table read over a whole batch, but still pays one ``h3`` cell lookup per point "
        f"and still resolves ambiguous points one at a time. So it is faster per point "
        f"than calling ``{scalar_api}()`` in a loop only once the batch is large enough "
        f"to pay back its own fixed cost. This page is where that happens, and where "
        f"growing the batch further stops helping. See :doc:`benchmarking_methodology`."
    )
    reporter.add_note(
        "Nothing on this page is on the continuous-integration trend chart, which "
        "tracks one fixed batch size. These are on-demand measurements, taken by "
        "``make batch-break-even``. Both answers move with the machine *and* with the "
        "workload, so read them as this configuration's, and run the script on your own "
        "coordinates to get yours."
    )

    reporter.add_section("How this is measured", level=1)
    reporter.add_text(
        f"Each row below is one paired comparison: a ``{scalar_api}()`` loop over N "
        f"points against a single ``{batch_api}()`` call on the same N points, with the "
        "same draw handed to both candidates, the order alternating round by round, and "
        "two estimators reported so that a difference neither can demonstrate reads as "
        "``unresolved`` rather than as a number "
        "(``benchmarks/candidate_comparison.py``)."
    )
    reporter.add_text(
        f"Every rung times the same amount of work - about "
        f"{info['points_per_round_target']:,} points per round, whatever the batch size "
        f"- so the rungs are comparable to each other, and both answers are read off the "
        "ratio *within* a rung rather than off absolute times across rungs, which is "
        "what keeps drift over the run out of the curve. Points are drawn without "
        "replacement inside a batch: a repeated coordinate would be answered from the "
        "batch's own cell lookup and would flatter exactly the effect being measured."
    )
    reporter.add_text(
        "The coordinate arrays are prepared before the clock starts, in the contiguous "
        "``float64`` form the batch API takes without copying. A caller holding Python "
        "lists pays one conversion per axis per call on top of what these rows show."
    )
    reporter.add_text(
        "**The two answers do not survive a noisy machine equally well.** Where batching "
        "starts paying is a comparison *within* one rung, so drift over the run cancels "
        "out of it and it reproduces. Where it stops improving is the batched call's "
        "per-point time compared *across* rungs, which drift moves directly - so it is "
        "quoted only when the control below certifies that the ladder measured one "
        "thing, and withheld when it does not."
    )

    reporter.add_section("The sweep", level=1)
    render_sweep(run, chart_path)
    reporter.add_text(f".. image:: {chart_path.name}")
    reporter.add_text(
        "The upper panel is the best-round speed-up; the lower one is the share of "
        "rounds the batched call won, which assumes nothing about how the noise is "
        "distributed. A difference is believed only where both agree, so the shaded band "
        "- where the crossing lies - is exactly where the upper panel passes 1.0 and the "
        "lower one passes one half. Hollow markers are rungs neither estimator resolves."
    )
    names_gather = info.get("names_gather_min_batch")
    if names_gather:
        reporter.add_text(
            f"The dotted rule at {names_gather} is not a measurement artefact: "
            "``ZoneNames.names_of`` converts ids to names with a Python loop below that "
            "size and a numpy gather at or above it, so the per-point cost steps there."
        )

    for sweep in sweeps:
        label = point_class_label(sweep["point_class"])
        reporter.add_section(f"Batch size against speed-up, {label}", level=1)
        reporter.add_table(
            [
                "Batch size",
                f"{scalar_api}() loop, per point",
                f"{batch_api}(), per point",
                "Speed-up",
                "Rounds won",
                "Verdict",
            ],
            [_batch_break_even_row(rung) for rung in sweep["rungs"]],
        )

        crossing = break_even(sweep["rungs"])
        bracket = crossing.bracket
        if bracket is not None:
            reporter.add_text(
                f"The crossing is reported as the interval ({bracket[0]}, "
                f"{bracket[1]}] rather than as a number, because that is all a "
                "ladder of discrete sizes can establish. The rungs inside it read "
                "``no difference`` or ``unresolved`` by construction: that is what it "
                "means for the crossing to be in there, not a defect in the run."
            )
        if crossing.status == "no_terminal_run":
            reporter.add_note(
                "This sweep won at "
                + ", ".join(f"N={size}" for size in crossing.non_monotone)
                + " but not at the largest batch size measured, so no crossing is "
                "established: a break-even is the size beyond which batching never "
                "loses again, and this ladder does not end in a win. Re-measure on a "
                "quieter machine before reading anything off it."
            )
        elif crossing.non_monotone:
            reporter.add_note(
                "This sweep won at "
                + ", ".join(f"N={size}" for size in crossing.non_monotone)
                + " and then lost again higher up the ladder. The interval above is the "
                "point beyond which it never loses; a ladder that crosses more than once "
                "is a sign to re-measure rather than a finer answer."
            )

        control = control_spread(
            sweep["rungs"],
            threshold=settings.control_spread_threshold,
            min_batch_size=settings.control_spread_min_batch_size,
        )
        reporter.add_text(
            f"Control: the scalar loop answers the same points at every rung, so its "
            f"per-point time should not depend on the batch size. Across the "
            f"{control.rungs_used} rungs at or above N={control.min_batch_size} it "
            f"spread **{control.spread * 100:.1f} %** "
            f"({format_duration(control.fastest)} to "
            f"{format_duration(control.slowest)}), against a "
            f"{control.threshold * 100:.0f} % threshold - "
            + (
                "so the ladder measured one thing."
                if control.within_threshold
                else "**above the threshold**, so read the curve with suspicion and "
                "re-measure on a quieter machine."
            )
            + " It is published as the reader's check and is never divided into "
            "anything. The smaller rungs are excluded because the harness's own "
            "per-batch cost lands on them divided by a very small N."
        )

    reporter.add_section("What this does not say", level=1)
    reporter.add_text(
        "**Both answers are properties of the workload, not only of the library.** The "
        "batch path answers every point that falls in one H3 cell from a single lookup, "
        "so a clustered stream - a delivery round, a city, a sensor network - amortises "
        "sooner than the uniformly random points measured here, which share almost "
        "nothing. Random points are the conservative case."
    )
    reporter.add_text(
        "They are also properties of this machine and this acceleration path. "
        "``scripts/measure_batch_break_even.py`` takes ``--points your.csv`` (two "
        "columns, ``lng,lat``) and reports the same two numbers for your coordinates on "
        "your hardware, which is the only way to get the answer that applies to you."
    )
    if batch_api == "timezone_names_at":
        reporter.add_text(
            "This page measures name-returning lookups. "
            "``scripts/measure_batch_break_even.py --api ids`` runs the corresponding "
            "like-for-like comparison of ``timezone_ids_at()`` against a "
            "``timezone_id_at()`` loop, with the per-point name conversion absent from "
            "both sides."
        )
    else:
        reporter.add_text(
            "This page measures id-returning lookups. Run the script with ``--api names`` "
            "for the corresponding comparison where both sides return timezone names."
        )

    add_system_status_section(
        reporter,
        system_info,
        additional_info={
            "Rounds per rung": info["rounds"],
            "Points per round": f"~{info['points_per_round_target']:,}",
            "Coordinate access": "in memory"
            if info.get("in_memory")
            else "memory mapped",
        },
        provenance=comparability_info(run),
    )
    reporter.write_report()


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
    if not benches:
        # a spread over nothing is not a spread; the other blocks on every page are
        # conditional on their benchmarks being present and this one has to be too,
        # now that a caller may hand over a filtered subset
        return
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


# How a latency metric is named by ``scripts.measure_query_latency``. Matched rather
# than imported so that a stored JSON still renders from a checkout whose harness has
# moved on - the same reason BATCH_SIZE is read out of the JSON.
LATENCY_NAME_PATTERN = re.compile(r"^latency::(?P<stratum>.+)::(?P<statistic>[^:]+)$")

# The columns of the distribution table, in order. The quantiles are why the harness
# exists; ``p50`` is beside them because a change that improves the tail at the median's
# expense is a bad trade, and only stating both can show which happened.
LATENCY_COLUMNS: tuple[str, ...] = ("p50", "p90", "p99", "p99.9", "mean", "max")


def latency_values_by_stratum(data: dict[str, Any]) -> dict[str, dict[str, float]]:
    """``{stratum: {statistic: seconds}}`` from a query-latency report."""
    values: dict[str, dict[str, float]] = {}
    for bench in data.get("benchmarks", []):
        match = LATENCY_NAME_PATTERN.match(bench.get("fullname", bench.get("name", "")))
        if match is None:
            continue
        values.setdefault(match["stratum"], {})[match["statistic"]] = bench["stats"][
            "mean"
        ]
    return values


def add_latency_section(reporter: BenchmarkReporter, latency: dict[str, Any]) -> None:
    """The per-query distribution, beside the batch tables rather than instead of them.

    The tables above time one pass over a whole batch, so they report what a *workload*
    costs and cannot express what a single unlucky query costs. Both are published
    because they answer different questions - see docs/benchmarking_methodology.rst.
    """
    by_stratum = latency_values_by_stratum(latency)
    if not by_stratum:
        return
    system_info = get_system_info(latency)
    nr_points = system_info.get("latency_points")

    reporter.add_section("Per-Query Latency Distribution", level=2)
    reporter.add_text(
        "Every table above times one pass over a whole batch of points, so it says what "
        "a workload costs on average. This one times each query on its own, in the "
        "default memory-mapped mode, and reports the distribution: the slowest queries "
        "in this package cost tens of times the median, because a point falling in a "
        "very large boundary polygon is answered by one ray cast across that whole "
        "ring. A batch mean cannot show that, which is why both are published "
        "(``scripts/measure_query_latency.py``, ``make latency``)."
    )
    if nr_points:
        reporter.add_text(
            f"{int(nr_points):,} queries per point class, each keeping its fastest of "
            f"{int(system_info.get('latency_repetitions', 1))} passes."
        )
    rows = []
    for stratum, statistics in by_stratum.items():
        rows.append(
            [PARAM_LABELS.get(stratum, stratum)]
            + [
                format_duration(statistics[column])
                if column in statistics
                else MEASUREMENT_UNAVAILABLE
                for column in LATENCY_COLUMNS
            ]
        )
    reporter.add_table(["Point class", *LATENCY_COLUMNS], rows)


def render_timezone_finding(
    data: dict[str, Any], latency: dict[str, Any], output_path: Path
) -> None:
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
    headlines.append(ACCELERATION_PATHS_POINTER)
    add_headline_section(reporter, system_info, headlines, machine_label(data))
    add_ci_tracking_note(reporter, system_info, benches)

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

    reporter.add_text("**Scalar vs batch lookups** (file-based):")
    for point_type in ("random", "unique_shortcut", "ambiguous_shortcut"):
        scalar = by_name.get(f"test_timezone_at[{point_type}-file_based]")
        ids = by_name.get(f"test_timezone_ids_at[{point_type}-file_based]")
        names = by_name.get(f"test_timezone_names_at[{point_type}-file_based]")
        if scalar and ids:
            context = f"{PARAM_LABELS.get(point_type, point_type).capitalize()}, ids"
            add_comparison_bullet(
                reporter, context, scalar, ids, label_fn=_function_label
            )
        if scalar and names:
            context = f"{PARAM_LABELS.get(point_type, point_type).capitalize()}, names"
            add_comparison_bullet(
                reporter, context, scalar, names, label_fn=_function_label
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

    add_latency_section(reporter, latency)

    reporter.write_report()


def render_polygon(data: dict[str, Any], output_path: Path) -> None:
    reporter = BenchmarkReporter(
        title="Point-in-Polygon Algorithm Performance Benchmark",
        output_path=output_path,
    )
    system_info = get_system_info(data)
    with interpreted_kernel_labels(system_info):
        batch_size = get_batch_size(system_info)
        benches = benchmarks_from_file(data, "test_inside_polygon")
        by_name = {b["name"]: b for b in benches}

        # per-check cost of the faster backend in each stratum. The spread between
        # the smallest and largest stratum *is* the finding this suite exists to
        # report, so it is the headline rather than any single number.
        def fastest_per_check(stratum: str, suffix: str) -> float | None:
            measured = [
                by_name[name]["stats"]["mean"]
                for name in (
                    f"test_pt_in_poly_clang{suffix}[{stratum}]",
                    f"test_pt_in_poly_python{suffix}[{stratum}]",
                )
                if name in by_name
            ]
            return min(measured) / batch_size if measured else None

        packed = {s: fastest_per_check(s, "_packed") for s in ("small", "large")}
        bare = {s: fastest_per_check(s, "") for s in ("small", "large")}
        headlines = []
        if packed["small"] and packed["large"]:
            headlines.append(
                f"**~{format_duration(packed['small'])} per check on a small polygon, "
                f"~{format_duration(packed['large'])} on the largest** "
                f"({format_ratio(packed['large'] / packed['small'])}) - the kernel a "
                "lookup reaches, which skips the parts of a ring a horizontal ray cannot "
                "cross and is therefore nearly flat in polygon size."
            )
        if bare["large"] and packed["large"]:
            headlines.append(
                f"The same check over an unindexed coordinate array is "
                f"~{format_duration(bare['large'])} on the largest polygon "
                f"({format_ratio(bare['large'] / packed['large'])} the packed cost) - "
                "which is what the stratification below is for, and what the latitude "
                "block index removed."
            )
        headlines.append(ACCELERATION_PATHS_POINTER)
        add_headline_section(reporter, system_info, headlines, machine_label(data))
        add_ci_tracking_note(reporter, system_info, benches)

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
        reporter.add_note(
            "The point and the polygon in each pair are drawn independently, so many pairs "
            "put the point nowhere near the polygon. That does not matter for the bare "
            "kernel, which scans the whole ring either way, but it means a share of the "
            "block-filtered checks are rejections rather than scans - cheapest on the small "
            "stratum, where a rejection is most of what is left. A real lookup reaches this "
            "stage only after a bounding-box check has passed, so read the block-filtered "
            "figures as a floor and :doc:`benchmark_results_timezonefinding` for what a "
            "query actually pays."
        )

        extra_columns: tuple[ExtraColumn, ...] = (
            ("Throughput", lambda b: format_rate(batch_size / b["stats"]["mean"])),
        )

        reporter.add_section("Results", level=2)
        add_benchmark_table(
            reporter, benches, section_level=3, extra_columns=extra_columns
        )

        reporter.add_section("Performance Summary", level=2)
        reporter.add_text(
            "**What the stored index and payload buy**, per polygon-size stratum - the "
            "same C predicate over the same pairs, reading the packed collection against "
            "reading a plain coordinate array with nothing in front of it:"
        )
        for stratum in ("small", "medium", "large"):
            bare_bench = by_name.get(f"test_pt_in_poly_clang[{stratum}]")
            packed_bench = by_name.get(f"test_pt_in_poly_clang_packed[{stratum}]")
            if bare_bench and packed_bench:
                add_comparison_bullet(
                    reporter,
                    PARAM_LABELS[stratum].capitalize(),
                    packed_bench,
                    bare_bench,
                    label_fn=_function_label,
                )
        interpreted = "Numba" if system_info.get("using_numba") else "pure Python"
        reporter.add_text(
            f"**The C extension against {interpreted}**, on the kernel a lookup reaches. "
            "Which of the two interpreted implementations these rows describe is decided "
            "by the measuring environment, not by the benchmark - see "
            ":doc:`benchmark_results_acceleration_paths`, which measures all three against "
            "each other:"
        )
        for stratum in ("small", "medium", "large"):
            clang = by_name.get(f"test_pt_in_poly_clang_packed[{stratum}]")
            python = by_name.get(f"test_pt_in_poly_python_packed[{stratum}]")
            if clang and python:
                add_comparison_bullet(
                    reporter,
                    PARAM_LABELS[stratum].capitalize(),
                    clang,
                    python,
                    label_fn=_function_label,
                )
        # scoped to one kernel: a spread taken across both forms would be comparing the
        # cheapest rejection against the most expensive full scan, which is not a range
        # anything experiences
        add_fastest_slowest_bullet(
            reporter, [b for b in benches if "_packed[" in b["name"]]
        )

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
    lite_init = by_name.get("test_initialization[TimezoneFinderL]")
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
    add_headline_section(reporter, system_info, headlines, machine_label(data))
    add_ci_tracking_note(reporter, system_info, benches)

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
    # only ``TimezoneFinder`` has two constructions to compare: ``TimezoneFinderL``
    # takes no ``in_memory`` and is measured once
    in_mem = by_name.get("test_initialization[TimezoneFinder-in_memory]")
    file_b = by_name.get("test_initialization[TimezoneFinder-file_based]")
    if in_mem and file_b:
        add_comparison_bullet(
            reporter, "TimezoneFinder", in_mem, file_b, label_fn=_memory_mode_label
        )
    add_fastest_slowest_bullet(reporter, benches)

    reporter.write_report()


# --- cross-package comparison (benchmarks/test_comparison.py) ----------------
#
# The one report whose subject is not this package alone. Everything it needs
# beyond the shared machinery above lives here, next to the renderer that uses
# it, rather than in this module's general display vocabulary: a `tzfpy` node
# id means nothing on any other page.

# The columns of the head-to-head table. The order is "the other package,
# then ours, then our own approximation of its trade", so the table reads as a
# comparison rather than as a ranking - which render time could otherwise flip.
COMPARISON_LOOKUP_FUNCTIONS = (
    "test_lookup_tzfpy",
    "test_lookup_timezonefinder",
    "test_lookup_timezonefinderl",
)

# the column every ratio in that table is taken against
COMPARISON_REFERENCE_FUNCTION = "test_lookup_tzfpy"

# this package's own entry, the one the headline and the verdict column compare
COMPARISON_SUBJECT_FUNCTION = "test_lookup_timezonefinder"

# same order and same ids as `POINT_FIXTURES` in benchmarks/test_comparison.py
COMPARISON_POINT_CLASSES = (
    "random",
    "on_land",
    "unique_shortcut",
    "ambiguous_shortcut",
)

# the point class the headline quotes: the only globally representative one,
# for the reason docs/benchmarking_methodology.rst gives
COMPARISON_HEADLINE_POINT_CLASS = "random"

# the cold-start half of the suite, and the row every other row is read against
FIRST_ANSWER_FUNCTION = "test_first_answer"
FIRST_ANSWER_BASELINE_ID = "baseline"


def get_tzfpy_version(system_info: dict[str, Any]) -> str:
    """Which build of the comparison package produced these numbers.

    An error rather than a quietly omitted line, for the same reason the
    fixture provenance is one: that package releases entirely outside this
    repository, so a report that does not name its version is a page of ratios
    with an unknown denominator - and every number on it still looks fine.
    """
    version = system_info.get("tzfpy_version")
    if version is None:
        raise ValueError(
            "benchmark JSON's machine_info['timezonefinder'] has no "
            f"'{TZFPY_DISTRIBUTION}_version' - the comparison benchmarks were "
            f"skipped because {TZFPY_DISTRIBUTION} is not installed. Install the "
            "`compare` dependency group and re-measure (`make benchmarks`)."
        )
    return version


def relative_speed_label(subject_seconds: float, reference_seconds: float) -> str:
    """Describe ``subject`` against ``reference``, deciding which way round it
    goes from the numbers rather than from an assumption about the two packages.

    A gap under :data:`NEGLIGIBLE_DIFFERENCE_PCT` is reported as parity. This
    table is the one place in these docs where declaring an arbitrary winner
    would read as a claim about somebody else's package.
    """
    if subject_seconds <= reference_seconds:
        ratio = speedup_ratio(reference_seconds, subject_seconds)
        direction = "faster"
    else:
        ratio = speedup_ratio(subject_seconds, reference_seconds)
        direction = "slower"
    if (ratio - 1) * 100 < NEGLIGIBLE_DIFFERENCE_PCT:
        return "about the same"
    return f"{format_ratio(ratio)} {direction}"


def render_comparison(data: dict[str, Any], output_path: Path) -> None:
    reporter = BenchmarkReporter(
        title="Comparison against tzfpy", output_path=output_path
    )
    system_info = get_system_info(data)
    batch_size = get_batch_size(system_info)
    tzfpy_version = get_tzfpy_version(system_info)
    benches = benchmarks_from_file(data, "test_comparison")
    by_name = {b["name"]: b for b in benches}

    def per_query(function: str, point_class: str) -> float | None:
        bench = by_name.get(f"{function}[{point_class}]")
        return (
            None
            if bench is None
            else bench["stats"][DEFAULT_BENCHMARK_ESTIMATOR] / batch_size
        )

    headline_reference = per_query(
        COMPARISON_REFERENCE_FUNCTION, COMPARISON_HEADLINE_POINT_CLASS
    )
    headline_subject = per_query(
        COMPARISON_SUBJECT_FUNCTION, COMPARISON_HEADLINE_POINT_CLASS
    )
    headlines = []
    if headline_reference is not None and headline_subject is not None:
        headlines.append(
            f"**~{format_duration(headline_subject)} per lookup here against "
            f"~{format_duration(headline_reference)} for tzfpy {tzfpy_version}** - "
            f"{relative_speed_label(headline_subject, headline_reference)}, over "
            "uniformly random query points answered by both packages in the same "
            "process on the same machine. That gap is what full-resolution "
            "boundary polygons cost; :doc:`alternatives` is where the trade is "
            "argued rather than measured."
        )
    add_headline_section(reporter, system_info, headlines, machine_label(data))
    add_ci_tracking_note(reporter, system_info, benches)

    add_system_status_section(
        reporter,
        system_info,
        {
            "benchmark_source": "pytest-benchmark",
            "batch_size": batch_size,
            f"{TZFPY_DISTRIBUTION}_version": tzfpy_version,
        },
        provenance=get_fixture_provenance(system_info),
    )
    reporter.add_text(
        "Both packages answer the **same committed query points** (see "
        "benchmarks/conftest.py) in the same process, so the ratios below are a "
        "measurement rather than two figures from two machines set side by side. "
        "Each is called through its own API - ``timezone_at(lng=, lat=)`` and "
        "``get_tz(lng, lat)`` - with no adapter frame on either side, which at "
        "these per-query times would itself be worth tens of percent."
    )
    reporter.add_note(
        "The two packages are not answering quite the same question. This one "
        "stores the boundary polygons exactly as the source dataset provides "
        "them; tzfpy simplifies them. ``TimezoneFinderL`` is measured alongside "
        "as the closest thing in this package to the same bargain - it answers "
        "from the shortcut index alone and does not read polygon data at all. A "
        "speed ratio between different accuracy classes is a price, not a verdict."
    )

    reporter.add_section("Lookup Throughput", level=2)
    reporter.add_text(
        f"Per-query time, derived from one pass over {batch_size:,} points. The last "
        "column states this package against tzfpy, computed from these measurements "
        "at render time rather than asserted."
    )
    reporter.add_text(
        f"Every figure in this section is the **{DEFAULT_BENCHMARK_ESTIMATOR}** over "
        "the measured rounds, not the mean - the estimator this project tracks "
        "everywhere, and the only fair one here. Both packages run the identical "
        "batch every round, so a slow round is the machine rather than the library; "
        "and because tzfpy's rounds are the shorter ones, that noise lands on its "
        "mean hardest. Scoring a competitor on the estimator that flatters this "
        "package would not be a measurement. The mean, median and spread of every "
        "round are in the full statistics below."
    )
    headers = [
        "Query points",
        *(FUNCTION_LABELS[function] for function in COMPARISON_LOOKUP_FUNCTIONS),
        f"vs {FUNCTION_LABELS[COMPARISON_REFERENCE_FUNCTION]}",
    ]
    rows = []
    for point_class in COMPARISON_POINT_CLASSES:
        measured = {
            function: per_query(function, point_class)
            for function in COMPARISON_LOOKUP_FUNCTIONS
        }
        reference = measured[COMPARISON_REFERENCE_FUNCTION]
        subject = measured[COMPARISON_SUBJECT_FUNCTION]
        rows.append(
            [
                PARAM_LABELS.get(point_class, point_class),
                *(
                    MEASUREMENT_UNAVAILABLE if value is None else format_duration(value)
                    for value in measured.values()
                ),
                MEASUREMENT_UNAVAILABLE
                if reference is None or subject is None
                else relative_speed_label(subject, reference),
            ]
        )
    reporter.add_table(headers, rows)

    lookup_benches = [
        b for b in benches if b["name"].startswith(COMPARISON_LOOKUP_FUNCTIONS)
    ]
    if lookup_benches:
        reporter.add_section("Full Statistics", level=2)
        add_benchmark_table(
            reporter,
            lookup_benches,
            section_level=3,
            extra_columns=(
                (
                    f"Time/Query ({DEFAULT_BENCHMARK_ESTIMATOR})",
                    lambda b: format_duration(
                        b["stats"][DEFAULT_BENCHMARK_ESTIMATOR] / batch_size
                    ),
                ),
                (
                    f"Throughput ({DEFAULT_BENCHMARK_ESTIMATOR})",
                    lambda b: format_rate(
                        batch_size / b["stats"][DEFAULT_BENCHMARK_ESTIMATOR]
                    ),
                ),
            ),
        )

    first_answer = [b for b in benches if b["name"].startswith(FIRST_ANSWER_FUNCTION)]
    if first_answer:
        reporter.add_section("Time to First Answer", level=2)
        reporter.add_text(
            "Wall clock of a fresh ``python -c`` that imports one package and "
            "answers exactly one lookup. This is the honest form of a "
            "*startup time* row, because the two packages spend that time in "
            "completely different places: this one imports NumPy and H3 and "
            "builds its index when a finder is constructed, while tzfpy imports "
            "in about a millisecond and deserialises its index inside the "
            "**first query**. Timing construction alone would score the second "
            "as free."
        )
        reporter.add_text(
            "Every row includes interpreter startup, which the baseline row "
            "measures on its own. Process launch has a floor and a long, noisy "
            f"tail, so the bullets below are again the **{DEFAULT_BENCHMARK_ESTIMATOR}** "
            "over the rounds; the mean of a row here can sit tens of percent above "
            "its own median, and reading a ranking off it would be reading the "
            "scheduler."
        )
        # built directly rather than through add_benchmark_table(): that groups
        # by function label and emits a heading per group, which for a single
        # function repeats the section title immediately below itself
        reporter.add_table(
            CONFIG_HEADERS,
            [
                stats_row(split_benchmark_label(bench["name"])[1] or "-", bench)
                for bench in sorted(first_answer, key=lambda b: b["name"])
            ],
        )

        baseline = by_name.get(f"{FIRST_ANSWER_FUNCTION}[{FIRST_ANSWER_BASELINE_ID}]")
        if baseline is not None:
            reporter.add_text("Net of that baseline:")
            for bench in sorted(
                first_answer, key=lambda b: b["stats"][DEFAULT_BENCHMARK_ESTIMATOR]
            ):
                if bench["name"].endswith(f"[{FIRST_ANSWER_BASELINE_ID}]"):
                    continue
                net = (
                    bench["stats"][DEFAULT_BENCHMARK_ESTIMATOR]
                    - baseline["stats"][DEFAULT_BENCHMARK_ESTIMATOR]
                )
                _, params_label = split_benchmark_label(bench["name"])
                reporter.add_text(
                    f"* **{params_label}**: {format_duration(net)} to a first answer"
                )

    reporter.add_section("What This Page Does Not Measure", level=2)
    reporter.add_text(
        "* **Accuracy.** The two packages disagree on a small fraction of points, "
        "and a disagreement count on its own says nothing about which answer is "
        "right - settling that needs ground truth, which neither package carries. "
        ":doc:`alternatives` states the design difference instead of scoring it."
    )
    reporter.add_text(
        "* **Memory footprint and distribution size.** "
        ":doc:`benchmark_results_memory` measures this package only: the harness "
        "behind it (``scripts/measure_memory.py``) constructs finders from this "
        "repository and has no tzfpy configuration."
    )
    reporter.add_text(
        "* **Any other machine.** One CPU, one Python build, one acceleration "
        "path, all named above. The *ratio* survives a change of machine far "
        "better than the absolute numbers do, but neither is a promise - see "
        ":doc:`benchmarking_methodology`."
    )

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
    return MEASUREMENT_UNAVAILABLE if value is None else format_bytes(value)


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
    add_headline_section(reporter, system_info, headlines, machine_label(data))

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
        "--latency-json",
        type=Path,
        required=True,
        help=(
            "Path to a JSON file produced by `scripts.measure_query_latency` "
            "(`make latency`). Required, because the per-query distribution is a "
            "section of the timezone-finding report rather than a page of its own - "
            "rendering without it would silently drop that section."
        ),
    )
    parser.add_argument(
        "--memory-json",
        type=Path,
        help=(
            "Path to a JSON file produced by `scripts.measure_memory` "
            "(`make memory`). Omit to leave the memory report untouched."
        ),
    )
    parser.add_argument(
        "--acceleration-json",
        type=Path,
        action="append",
        default=[],
        help=(
            "Repeatable. Paths to the JSON files produced by "
            "`scripts.measure_acceleration_paths` (`make acceleration-paths`) - one "
            "per environment, since no process holds both the Numba and the "
            "pure-Python kernel. Pass all of them or none; omit to leave the "
            "acceleration-path report untouched."
        ),
    )
    parser.add_argument(
        "--batch-break-even-json",
        type=Path,
        help=(
            "Path to a JSON file produced by `scripts.measure_batch_break_even` "
            "(`make batch-break-even`). Omit to leave the batch break-even report and "
            "its chart untouched. Drawing the chart needs the `benchmark` dependency "
            "group (`uv run --group benchmark ...`)."
        ),
    )
    args = parser.parse_args()

    data = load_benchmark_json(args.benchmark_json)
    latency = load_benchmark_json(args.latency_json)
    render_timezone_finding(data, latency, PERFORMANCE_REPORT_FILE)
    render_polygon(data, POLYGON_REPORT_FILE)
    render_initialization(data, INITIALIZATION_REPORT_FILE)
    render_comparison(data, COMPARISON_REPORT_FILE)
    written = [
        PERFORMANCE_REPORT_FILE,
        POLYGON_REPORT_FILE,
        INITIALIZATION_REPORT_FILE,
        COMPARISON_REPORT_FILE,
    ]
    if args.memory_json is not None:
        render_memory(load_benchmark_json(args.memory_json), MEMORY_REPORT_FILE)
        written.append(MEMORY_REPORT_FILE)
    if args.acceleration_json:
        runs = [load_benchmark_json(path) for path in args.acceleration_json]
        render_acceleration_paths(runs, ACCELERATION_REPORT_FILE)
        written.append(ACCELERATION_REPORT_FILE)
    if args.batch_break_even_json is not None:
        render_batch_break_even(
            load_benchmark_json(args.batch_break_even_json),
            BATCH_BREAK_EVEN_REPORT_FILE,
            BATCH_BREAK_EVEN_CHART_FILE,
        )
        written.extend([BATCH_BREAK_EVEN_REPORT_FILE, BATCH_BREAK_EVEN_CHART_FILE])
    print(f"Wrote {', '.join(str(path) for path in written)}")


if __name__ == "__main__":
    main()
