#!/usr/bin/env python3

"""Benchmark script to measure TimezoneFinder initialization performance.

This script benchmarks the initialization time of different TimezoneFinder classes
and modes. Can be run as a standalone script to generate RST reports or for pytest execution.
"""

import timeit
from pathlib import Path
from typing import Dict, Any

import pytest

from scripts.benchmark_utils import (
    BenchmarkReporter,
    create_cli_parser,
    add_system_status_section,
)
from scripts.configs import INITIALIZATION_REPORT_FILE, DEBUG
from timezonefinder import TimezoneFinder, TimezoneFinderL

N = 10 if DEBUG else int(1e2)


def format_speedup_analysis(
    faster_time: float, slower_time: float, faster_name: str, slower_name: str
) -> str:
    """Format speedup analysis with both multiplier and percentage."""
    relative_improvement = (slower_time - faster_time) / slower_time
    return f"**{faster_name}** is {relative_improvement:.0%} faster ({faster_time:.1f} ms vs {slower_time:.1f} ms)"


def run_initialization_benchmark(n_runs: int = N) -> Dict[str, Any]:
    """Run initialization benchmark and return results for RST formatting."""
    print(f"Running {n_runs} initialization benchmarks...")

    results = []

    # Test configurations: (class_name, class, in_memory_mode)
    test_configs = [
        ("TimezoneFinder", TimezoneFinder, False),
        ("TimezoneFinder", TimezoneFinder, True),
        ("TimezoneFinderL", TimezoneFinderL, False),
        ("TimezoneFinderL", TimezoneFinderL, True),
    ]

    for class_name, class_under_test, in_memory_mode in test_configs:
        mode_desc = "In-Memory" if in_memory_mode else "File-Based"
        config_name = f"{class_name} ({mode_desc})"

        def initialise_instance():
            class_under_test(in_memory=in_memory_mode)

        # Run benchmark
        t = timeit.timeit(
            "initialise_instance()",
            globals={"initialise_instance": initialise_instance},
            number=n_runs,
        )
        t_avg = t / n_runs

        # Convert to milliseconds for better readability
        t_avg_ms = t_avg * 1000

        results.append((config_name, f"{t_avg_ms:.1f}", f"{t_avg:.3f}"))

    return {"n_runs": n_runs, "results": results}


def write_initialization_report(output_path: Path, n_runs: int = N) -> None:
    """Write a comprehensive initialization benchmark report in RST format."""
    print(f"Generating initialization benchmark report at {output_path}...")

    benchmark_data = run_initialization_benchmark(n_runs)

    reporter = BenchmarkReporter(
        title="TimezoneFinder Initialization Performance Benchmark",
        output_path=output_path,
    )

    # Add comprehensive system status section
    add_system_status_section(
        reporter,
        {
            "test_runs_per_configuration": benchmark_data["n_runs"],
            "algorithm_type": "Class Initialization",
            "test_configurations": "TimezoneFinder and TimezoneFinderL with file-based and in-memory modes",
        },
    )

    # Add performance results
    reporter.add_section("Initialization Performance Results")
    headers = ["Configuration", "Average Time (ms)", "Average Time (s)"]
    reporter.add_table(headers, benchmark_data["results"])

    # Add analysis section
    reporter.add_section("Performance Analysis")
    results = benchmark_data["results"]

    if len(results) >= 2:
        # Find fastest and slowest
        fastest = min(results, key=lambda x: float(x[1]))  # Compare by ms
        slowest = max(results, key=lambda x: float(x[1]))

        fastest_time_ms = float(fastest[1])
        slowest_time_ms = float(slowest[1])
        relative_improvement = (slowest_time_ms - fastest_time_ms) / slowest_time_ms

        reporter.add_text(
            f"* **Fastest configuration**: {fastest[0]} ({fastest[1]} ms)"
        )
        reporter.add_text(
            f"* **Slowest configuration**: {slowest[0]} ({slowest[1]} ms)"
        )
        reporter.add_text(
            f"* **Performance difference**: {relative_improvement:.0%} faster"
        )
        reporter.add_text("")

        # Analyze by mode
        file_based_results = [r for r in results if "File-Based" in r[0]]
        in_memory_results = [r for r in results if "In-Memory" in r[0]]

        if file_based_results and in_memory_results:
            avg_file_based = sum(float(r[1]) for r in file_based_results) / len(
                file_based_results
            )
            avg_in_memory = sum(float(r[1]) for r in in_memory_results) / len(
                in_memory_results
            )

            if avg_file_based < avg_in_memory:
                reporter.add_text(
                    f"* {format_speedup_analysis(avg_file_based, avg_in_memory, 'File-based mode', 'in-memory mode')}"
                )
            else:
                reporter.add_text(
                    f"* {format_speedup_analysis(avg_in_memory, avg_file_based, 'In-memory mode', 'file-based mode')}"
                )

    reporter.add_note(
        "Initialization times may vary based on system I/O performance, "
        "available memory, and background system activity. "
        "In-memory mode loads all data into RAM during initialization, "
        "while file-based mode opens files but defers data loading."
    )

    reporter.write_report()

    print(f"Report generated successfully at {output_path}")
    print(
        "Report will be included in documentation at docs/benchmark_results_initialization.rst"
    )


@pytest.mark.parametrize("in_memory_mode", [True, False])
@pytest.mark.parametrize(
    "class_under_test",
    [
        TimezoneFinder,
        TimezoneFinderL,
    ],
)
def test_initialisation_speed(class_under_test, in_memory_mode: bool):
    print()
    print(
        f"testing initialiation: {class_under_test.__name__}(in_memory={in_memory_mode})"
    )

    def initialise_instance():
        class_under_test(in_memory=in_memory_mode)

    t = timeit.timeit(
        "initialise_instance()",
        globals={"initialise_instance": initialise_instance},
        number=N,
    )
    t_avg = t / N
    print(f"avg. startup time: {t_avg:.3f}s ({N} runs)\n")


def main():
    """CLI entry point for standalone script execution."""
    parser = create_cli_parser(
        description="Benchmark TimezoneFinder initialization performance",
        script_name="Initialization Benchmark",
    )

    # Add additional arguments specific to this benchmark
    parser.add_argument(
        "--runs",
        "-r",
        type=int,
        default=N,
        help=f"Number of initialization runs per configuration (default: {N})",
    )

    args = parser.parse_args()

    if args.rst:
        # Generate RST report
        output_path = INITIALIZATION_REPORT_FILE
        write_initialization_report(output_path, args.runs)
    else:
        # Run console benchmark (pytest mode)
        print("Running initialization performance benchmark...")
        print("Use --rst flag to generate RST report")
        pytest.main([__file__])


if __name__ == "__main__":
    main()
