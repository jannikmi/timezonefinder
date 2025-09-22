#!/usr/bin/env python3

"""Benchmark script to measure point-in-polygon performance.

This script benchmarks the performance of different point-in-polygon algorithm implementations.
Can be run as a standalone script to generate RST reports or for console output.
"""

import platform
import warnings
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from scripts.benchmark_utils import BenchmarkReporter, create_cli_parser
from scripts.configs import POLYGON_REPORT_FILE
from tests.auxiliaries import (
    get_pip_test_input,
    timefunc,
)
from timezonefinder import utils, utils_clang, utils_numba

# test for overflow:
# make numpy overflow runtime warning raise an error

np.seterr(all="warn")

warnings.filterwarnings("error")

nr_of_runs = int(1e4)


def gen_test_input():
    return get_pip_test_input()


def check_inside_polygon_speed():
    print(
        "testing the speed of the different point in polygon algorithm implementations"
    )
    print(f"testing {nr_of_runs} queries: random points and timezone polygons")
    print(f"Python implementation using Numba JIT compilation: {utils.using_numba}")

    # reuse the same inputs for comparable results
    test_inputs = [gen_test_input() for _ in range(nr_of_runs)]

    def time_inside_poly_func(inside_poly_func: Callable, test_inputs: Iterable):
        for test_input in test_inputs:
            _ = inside_poly_func(*test_input)

    def time_func(test_func):
        func_name = test_func.__name__
        t = timefunc(time_inside_poly_func, test_func, test_inputs)
        t_avg = t / nr_of_runs
        pts_per_second = t_avg**-1
        print(f"{func_name}: {t_avg:.1e} s/query, {pts_per_second:.1e} queries/s")
        return t_avg

    print()
    t_clang = time_func(utils_clang.pt_in_poly_clang)
    t_python = time_func(utils_numba.pt_in_poly_python)
    py_func_descr = (
        f"Python implementation {'WITH' if utils.using_numba else 'WITHOUT'} Numba"
    )
    if t_clang < t_python:
        speedup = (t_python / t_clang) - 1
        print(f"C implementation is {speedup:.1f}x faster than the {py_func_descr}")
    else:
        speedup = (t_clang / t_python) - 1
        print(f"{py_func_descr} is {speedup:.1f}x faster than the C implementation")


def run_benchmark_for_rst(n_runs: int = nr_of_runs) -> dict:
    """Run benchmark and return results for RST formatting."""
    print(f"Running {n_runs:,} point-in-polygon queries...")

    # Generate test inputs
    test_inputs = [gen_test_input() for _ in range(n_runs)]

    def time_inside_poly_func(inside_poly_func: Callable, test_inputs: Iterable):
        for test_input in test_inputs:
            _ = inside_poly_func(*test_input)

    def time_func(test_func):
        t = timefunc(time_inside_poly_func, test_func, test_inputs)
        t_avg = t / n_runs
        pts_per_second = t_avg**-1
        return test_func.__name__, t_avg, pts_per_second

    # Run benchmarks
    clang_name, t_clang, pts_clang = time_func(utils_clang.pt_in_poly_clang)
    python_name, t_python, pts_python = time_func(utils_numba.pt_in_poly_python)

    # Determine which is faster
    py_func_descr = (
        f"Python implementation {'WITH' if utils.using_numba else 'WITHOUT'} Numba"
    )
    if t_clang < t_python:
        speedup = (t_python / t_clang) - 1
        speedup_desc = (
            f"C implementation is {speedup:.1f}x faster than the {py_func_descr}"
        )
    else:
        speedup = (t_clang / t_python) - 1
        speedup_desc = (
            f"{py_func_descr} is {speedup:.1f}x faster than the C implementation"
        )

    return {
        "numba_enabled": utils.using_numba,
        "n_runs": n_runs,
        "results": [
            (clang_name, f"{t_clang:.1e}", f"{pts_clang:.1e}"),
            (python_name, f"{t_python:.1e}", f"{pts_python:.1e}"),
        ],
        "speedup_description": speedup_desc,
    }


def write_polygon_report(output_path: Path, n_queries: int = nr_of_runs) -> None:
    """Write a comprehensive polygon benchmark report in RST format."""
    print(f"Generating polygon benchmark report at {output_path}...")

    benchmark_data = run_benchmark_for_rst(n_queries)

    reporter = BenchmarkReporter(
        title="Point-in-Polygon Algorithm Performance Benchmark",
        output_path=output_path,
    )

    # Add system configuration
    reporter.add_section("System Configuration")
    reporter.add_text(f"* Python version: {platform.python_version()}")
    reporter.add_text(f"* NumPy version: {np.__version__}")
    reporter.add_text(f"* Numba enabled: {benchmark_data['numba_enabled']}")
    reporter.add_text(f"* Test queries: {benchmark_data['n_runs']:,}")

    # Add performance results
    reporter.add_section("Performance Results")
    headers = ["Implementation", "Average Time (s)", "Throughput (queries/sec)"]
    reporter.add_table(headers, benchmark_data["results"])

    # Add performance summary
    reporter.add_section("Performance Summary")
    reporter.add_text(benchmark_data["speedup_description"])

    reporter.add_note(
        "Performance results may vary based on system configuration, "
        "compiler optimizations, and runtime conditions."
    )

    reporter.write_report()

    print(f"Report generated successfully at {output_path}")
    print(
        "Report will be included in documentation at docs/benchmark_results_polygon.rst"
    )


def main():
    """CLI entry point for standalone script execution."""
    parser = create_cli_parser(
        description="Benchmark point-in-polygon algorithm performance",
        script_name="Point-in-Polygon Benchmark",
    )

    # Add additional arguments specific to this benchmark
    parser.add_argument(
        "--queries",
        "-n",
        type=int,
        default=nr_of_runs,
        help=f"Number of test queries to run (default: {nr_of_runs})",
    )

    args = parser.parse_args()

    if args.rst:
        # Generate RST report
        output_path = POLYGON_REPORT_FILE
        write_polygon_report(output_path, args.queries)
    else:
        # Run console benchmark (default behavior)
        print("Running point-in-polygon performance benchmark...")
        check_inside_polygon_speed()
        print("Benchmark complete!")


if __name__ == "__main__":
    main()
