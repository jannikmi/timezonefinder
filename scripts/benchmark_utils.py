#!/usr/bin/env python3

"""Shared utilities for benchmark reporting and RST generation.

This module contains common functionality used by various benchmark scripts
to generate RST reports and handle CLI interfaces.
"""

import importlib.metadata
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Final, Literal, get_args

import numpy as np

from scripts.reporting import (
    DATA_VERSION_LABEL,
    FIXTURE_VERSION_LABEL,
    join_lines,
    render_rst_table,
    rst_title,
)
from timezonefinder import TimezoneFinder, __version__ as timezonefinder_version

# Which pytest-benchmark ``stats`` field is treated as *the* number for a
# benchmark. Defined here rather than in each consumer because the CI
# normalisation step and the noise analysis must agree on it - see
# scripts/normalize_benchmark_json.py and scripts/benchmark_noise.py.
BenchmarkEstimator = Literal["min", "median", "mean"]
BENCHMARK_ESTIMATORS: tuple[str, ...] = get_args(BenchmarkEstimator)
# min is the least noise-sensitive estimator for this workload: every round
# performs the exact same fixed batch of work (see benchmarks/conftest.py's
# BATCH_SIZE), so the fastest round is the one least perturbed by whatever
# else the shared, virtualised CI machine happened to be doing.
DEFAULT_BENCHMARK_ESTIMATOR: BenchmarkEstimator = "min"

# Fields of ``machine_info["timezonefinder"]`` (written by
# ``benchmarks/conftest.py``'s ``pytest_benchmark_update_machine_info``) that
# two reports must agree on before their numbers may be compared at all:
# a different batch size or fixture set means a different amount of work, and
# a different acceleration path means a different implementation. Deliberately
# *not* including ``timezonefinder_version`` - comparing two versions is the
# whole point of a base/head comparison.
COMPARABILITY_KEYS: tuple[str, ...] = (
    "batch_size",
    "fixture_version",
    "data_version",
    "using_clang_pip",
    "using_numba",
    # how many lookups a memory measurement performed before its steady-state
    # footprint was read (scripts/measure_memory.py). Absent from timing
    # reports, where it compares equal as None on both sides.
    "memory_workload_size",
)


# The alternative package this project is compared against
# (benchmarks/test_comparison.py, docs/alternatives.rst). Named once here
# because three consumers need it - the benchmark suite that imports it, the
# conftest hook that stamps its version into every report, and the renderer
# that prints that stamp - and a retyped distribution name in the third place
# is the copy that goes stale.
TZFPY_DISTRIBUTION: Final[str] = "tzfpy"


def tzfpy_version() -> str | None:
    """The installed version of :data:`TZFPY_DISTRIBUTION`, or ``None``.

    Recorded into every benchmark JSON so the rendered comparison report can
    name the build it measured. That package releases on its own schedule,
    entirely outside this repository, so a figure on that page describes a
    *version* rather than a package - and nothing else in the pipeline would
    say which one. ``None`` when it is not installed, which is the normal case
    for every run except ``make benchmarks``.
    """
    try:
        return importlib.metadata.version(TZFPY_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        return None


def decimals_for_magnitude(value: float) -> int:
    """Decimal places giving ~3 significant figures for ``value``.

    Fewer digits as the value grows (0 decimals at >=100, 1 at >=10, else 2),
    so a table doesn't show false precision on a large number (``"192.30x"``)
    or too few significant digits on a small one. This is the "human
    friendly rounding" shared by every formatter in this project.
    """
    abs_value = abs(value)
    if abs_value >= 100:
        return 0
    if abs_value >= 10:
        return 1
    return 2


def format_bytes(num_bytes: float) -> str:
    """Format a byte count in the most readable binary unit.

    Binary units (KiB/MiB) rather than decimal ones, because every figure
    these reports carry is either an allocation or a page count, and both are
    powers of two - reporting a 64 MiB mapping as "67.1 MB" invites the reader
    to compare it against a file size that was never measured that way.
    """
    abs_bytes = abs(num_bytes)
    if abs_bytes >= 1024**3:
        value, unit = num_bytes / 1024**3, "GiB"
    elif abs_bytes >= 1024**2:
        value, unit = num_bytes / 1024**2, "MiB"
    elif abs_bytes >= 1024:
        value, unit = num_bytes / 1024, "KiB"
    else:
        return f"{num_bytes:.0f} B"
    return f"{value:.{decimals_for_magnitude(value)}f} {unit}"


@dataclass(frozen=True)
class MetricSpec:
    """What a tracked number *is*, for the scripts that only ratio it.

    ``scripts.compare_benchmark_runs`` and
    ``scripts.describe_benchmark_machine`` do nothing that depends on the unit:
    they reduce repeated passes, divide head by base, and check that both sides
    came off the same machine. Only the rendering knows about seconds. Passing
    one of these in is what lets the memory report reuse that machinery -
    including the same-runner check and the fork-trust-boundary name
    sanitisation - instead of growing a parallel copy of it for bytes.
    """

    key: str
    #: heading a rendered report is titled with
    heading: str
    #: what one row of a comparison table is ("benchmark", "metric")
    row_noun: str
    #: renders one measured value for a markdown cell
    format_value: Callable[[float], str]
    #: what an increase means, and what a decrease means
    worse: str
    better: str
    #: names the estimator's origin; formatted with ``estimator=``
    estimator_phrase: str
    #: one sentence explaining the `change` and `x` columns of a comparison
    change_help: str
    #: the caveat a reader needs before acting on a small difference
    noise_note: str


DURATION_METRIC = MetricSpec(
    key="duration",
    heading="Benchmark",
    row_noun="benchmark",
    # kept as a fixed-precision millisecond value rather than routed through
    # `format_duration`: this is the form every stored comparison has used, and
    # a rendering that does not move is easier to read across runs
    format_value=lambda seconds: f"{seconds * 1e3:.3f} ms",
    worse="slower",
    better="faster",
    estimator_phrase="tracking pytest-benchmark's `{estimator}`",
    change_help=(
        "`change` is the head duration relative to base - negative is faster. "
        "The `x` factor is `base / head`, so 1.20x means head does the same "
        "work in 1.20 times fewer seconds."
    ),
    noise_note=(
        "Same-runner comparison removes the machine-to-machine term but not "
        "the runner's own jitter, so a change of a few percent is still noise. "
        "See contributing/development/benchmarking-and-performance-validation.md."
    ),
)

MEMORY_METRIC = MetricSpec(
    key="memory",
    heading="Memory footprint",
    row_noun="metric",
    format_value=format_bytes,
    worse="larger",
    better="smaller",
    estimator_phrase="tracking the `{estimator}` of repeated measurements",
    change_help=(
        "`change` is the head footprint relative to base - negative is smaller. "
        "The `x` factor is `base / head`, so 1.20x means head holds 1.20 times "
        "fewer bytes."
    ),
    noise_note=(
        "`*_heap` metrics come from `tracemalloc` and are near-deterministic, "
        "so a change there is signal rather than jitter. `*_rss` reflects the "
        "resident set, which also counts memory-mapped pages the kernel may "
        "reclaim under pressure - read it as an order of magnitude, not an "
        "exact figure. See contributing/development/benchmarking-and-performance-validation.md."
    ),
)

METRIC_SPECS: dict[str, MetricSpec] = {
    spec.key: spec for spec in (DURATION_METRIC, MEMORY_METRIC)
}
DEFAULT_METRIC_KEY = DURATION_METRIC.key


def load_benchmark_json(json_path: Path) -> dict[str, Any]:
    """Load a JSON file produced by ``pytest benchmarks/ --benchmark-json=...``."""
    with open(json_path) as f:
        return json.load(f)


def cpu_info() -> dict[str, Any]:
    """The ``machine_info["cpu"]`` block pytest-benchmark records, when available.

    Read through ``py-cpuinfo``, which pytest-benchmark itself uses, so a report
    written by one of the standalone measurement scripts names its machine in exactly
    the form :func:`machine_label` and :func:`cpu_model` already know how to read. An
    environment without it produces a report that says "not recorded" rather than
    failing the measurement. Declared here, beside those two readers, because every
    script that writes this shape needs it and three copies of a try/import is three
    chances for one of them to drift.
    """
    try:
        import cpuinfo  # noqa: PLC0415 - optional, and only needed here
    except ImportError:
        return {}
    return cpuinfo.get_cpu_info()


def cpu_model(data: dict[str, Any]) -> str | None:
    """The CPU model that produced ``data``, or ``None`` if not recorded.

    This is the field to compare two reports on. The measured clock is
    deliberately excluded: ``hz_actual`` is sampled once per pytest-benchmark
    startup and jitters by a megahertz or so between two runs *on the same
    machine*, so requiring it to match would report a machine change on every
    single comparison.
    """
    cpu = data.get("machine_info", {}).get("cpu") or {}
    return str(cpu.get("brand_raw") or "").strip() or None


def machine_label(data: dict[str, Any]) -> str | None:
    """Name the machine that produced ``data``, model and measured clock.

    ``runs-on: ubuntu-latest`` pins the runner *image*, not the hardware: the
    pool serves several CPU models whose clocks differ by up to ~1.6x, which
    is far more than any change this project is likely to make. Every report
    therefore has to say which machine it came from, and this is the one-line
    form of that (``machine_info["cpu"]``, captured by pytest-benchmark). Use
    :func:`cpu_model` to compare two reports; this one is for display.
    """
    model = cpu_model(data)
    if model is None:
        return None
    cpu = data.get("machine_info", {}).get("cpu") or {}
    clock = str(cpu.get("hz_actual_friendly") or "").strip()
    return f"{model} @ {clock}" if clock else model


def comparability_info(data: dict[str, Any]) -> dict[str, Any]:
    """Extract the :data:`COMPARABILITY_KEYS` recorded in ``data``.

    Missing keys are reported as ``None`` rather than dropped, so a report
    written before a key existed compares unequal against one that has it
    instead of silently agreeing.
    """
    recorded = data.get("machine_info", {}).get("timezonefinder") or {}
    return {key: recorded.get(key) for key in COMPARABILITY_KEYS}


class BenchmarkReporter:
    """Helper class for generating benchmark RST reports with a fluent API."""

    def __init__(self, title: str, output_path: Path):
        self.title = title
        self.output_path = Path(output_path)
        # Heterogeneous, tagged by item[0]: ('section', title, level),
        # ('text', text), ('table', headers, rows), ('note', text).
        self.content: list[tuple[Any, ...]] = []

    def add_section(self, title: str, level: int = 1):
        """Add a new section with the given title and RST level."""
        self.content.append(("section", title, level))
        return self

    def add_text(self, text: str):
        """Add text content."""
        self.content.append(("text", text))
        return self

    def add_table(self, headers: list[str], rows: list[list[str]]):
        """Add a table to the report."""
        self.content.append(("table", headers, rows))
        return self

    def add_note(self, text: str):
        """Add a note directive."""
        self.content.append(("note", text))
        return self

    def render(self) -> str:
        """Render the accumulated content as one RST page."""
        parts = [join_lines(rst_title(self.title, 0), "")]

        for item in self.content:
            if item[0] == "section":
                _, title, level = item
                parts.append(join_lines(rst_title(title, level), ""))
            elif item[0] == "text":
                _, text = item
                # Only add a blank line if the text is not the empty string
                parts.append(join_lines(text, "") if text else join_lines(text))
            elif item[0] == "table":
                _, headers, rows = item
                parts.append(render_rst_table(headers, rows) + join_lines(""))
            elif item[0] == "note":
                _, text = item
                parts.append(join_lines(".. note::", "", f"   {text}", ""))

        return "".join(parts)

    def write_report(self):
        """Write the complete report to the output file."""
        print(f"Writing {self.title.lower()} report to: {self.output_path}")

        # Every section ends with a blank line, so the last one leaves the file
        # with a trailing one that end-of-file-fixer then strips - which made
        # every freshly rendered report differ from the committed one until the
        # hook had run, hiding real changes behind a repair nobody sees. Same
        # normalisation as scripts/reporting.py applies to the data report.
        self.output_path.write_text(self.render().rstrip("\n") + "\n", encoding="utf-8")


def get_system_status() -> dict[str, Any]:
    """Get comprehensive system status information for benchmark reports."""
    tf_instance = TimezoneFinder()

    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "platform_processor": platform.processor() or "Unknown",
        "numpy_version": np.__version__,
        "using_clang_pip": tf_instance.using_clang_pip(),
        "using_numba": tf_instance.using_numba(),
        # ``timezonefinder.__version__`` is the installed package version, read
        # from distribution metadata. The previous ``getattr(tf_instance,
        # "__version__", "Unknown")`` read a non-existent attribute on a class
        # with ``__slots__``, so every report carried ``"Unknown"`` instead.
        "timezonefinder_version": timezonefinder_version,
    }


def add_system_status_section(
    reporter: BenchmarkReporter,
    system_info: dict[str, Any],
    additional_info: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
):
    """Add a comprehensive system status section to a benchmark report.

    ``system_info`` (shape: :func:`get_system_status`) is accepted rather than
    computed here so callers can report the environment that actually
    produced the numbers - e.g. ``scripts/render_benchmark_reports.py`` reads
    it back out of a pytest-benchmark JSON file's ``machine_info`` instead of
    describing whichever machine happens to be rendering the report.

    ``provenance`` (shape:
    ``tests.auxiliaries.benchmark_fixture_provenance``) states which fixture
    set and boundary data the timings describe, so a regenerated fixture set
    or a data update leaves the committed report visibly - rather than
    silently - out of date.
    """
    reporter.add_section("System Status")

    # Python environment
    reporter.add_section("Python Environment", level=2)
    reporter.add_text(
        f"**Python Version**: {system_info['python_version']} ({system_info['python_implementation']})"
    )
    reporter.add_text(f"**NumPy Version**: {system_info['numpy_version']}")
    reporter.add_text(
        f"**Platform**: {system_info['platform_system']} {system_info['platform_machine']}"
    )
    if system_info["platform_processor"] != "Unknown":
        reporter.add_text(f"**Processor**: {system_info['platform_processor']}")

    # TimezoneFinder configuration
    reporter.add_section("TimezoneFinder Configuration", level=2)
    reporter.add_text(
        f"**C Implementation Available**: {system_info['using_clang_pip']}"
    )
    reporter.add_text(f"**Numba JIT Available**: {system_info['using_numba']}")

    # Performance optimizations status
    reporter.add_section("Performance Optimizations", level=2)
    optimizations = []
    if system_info["using_clang_pip"]:
        optimizations.append("✓ Compiled C extension for point-in-polygon operations")
    else:
        optimizations.append("✗ Using pure Python point-in-polygon implementation")

    if system_info["using_numba"]:
        optimizations.append("✓ Numba JIT compilation enabled")
    else:
        optimizations.append("✗ Numba JIT compilation not available")

    for opt in optimizations:
        reporter.add_text(f"* {opt}")

    # Which workload the numbers describe (fixture set + boundary data)
    if provenance:
        reporter.add_section("Benchmark Input Provenance", level=2)
        reporter.add_text(f"{FIXTURE_VERSION_LABEL}: {provenance['fixture_version']}")
        reporter.add_text(f"{DATA_VERSION_LABEL}: {provenance['data_version']}")

    # Additional benchmark-specific information
    if additional_info:
        reporter.add_section("Benchmark Configuration", level=2)
        for key, value in additional_info.items():
            if isinstance(value, (int, float)) and value >= 1000:
                formatted_value = f"{value:,}"
            else:
                formatted_value = str(value)
            reporter.add_text(f"**{key.replace('_', ' ').title()}**: {formatted_value}")

    return reporter
