#!/usr/bin/env python3

"""Benchmark script to measure timezone finding performance.

This script benchmarks the performance of different timezone finding functions.
Can be run as a standalone script to generate RST reports or for pytest execution.
"""

from pathlib import Path
from typing import List, Tuple, Callable, Iterable

import pytest

from scripts.benchmark_utils import BenchmarkReporter, create_cli_parser
from scripts.configs import DOC_ROOT, PERFORMANCE_REPORT_FILE, DEBUG
from tests.auxiliaries import get_rnd_query_pt, timefunc
from timezonefinder import (
    TimezoneFinder,
    TimezoneFinderL,
    timezone_at,
    timezone_at_land,
    certain_timezone_at,
    unique_timezone_at,
)

N = 10 if DEBUG else int(1e4)
tf_instance = TimezoneFinder()


def get_on_land_pts(length: int):
    # create an array of points where timezone_finder finds something (on_land queries)
    print(f"collecting and storing {N:,} on land points for the tests...")
    on_land_points = []
    ps_for_10percent = int(N / 10)
    percent_done = 0

    i = 0
    while i < length:
        lng, lat = get_rnd_query_pt()
        if tf_instance.timezone_at_land(lng=lng, lat=lat) is not None:
            i += 1
            on_land_points.append((lng, lat))
            if i % ps_for_10percent == 0:
                percent_done += 10
                print(percent_done, "%")

    print("Done.\n")
    return on_land_points


def get_random_points(length: int) -> List[Tuple[float, float]]:
    return [get_rnd_query_pt() for _ in range(length)]


# Test data will be generated lazily when needed


def eval_time_fct():
    global tf, point_list
    for point in point_list:
        tf.timezone_at(lng=point[0], lat=point[1])


# Test point generation for pytest - using indirect parametrization to avoid
# generating data on module import
points_and_descr_names = [
    ("on_land", "'on land points' (points included in a land timezone)"),
    ("random", "random points (anywhere on earth)"),
]


@pytest.mark.parametrize(
    "point_type, points_descr",
    points_and_descr_names,
)
@pytest.mark.parametrize(
    "in_memory_mode",
    [
        False,
        True,
    ],
)
def test_timezone_finding_speed(
    point_type: str,
    points_descr: str,
    in_memory_mode: bool,
):
    # Generate test points based on type
    if point_type == "on_land":
        test_points = get_on_land_pts(N)
    elif point_type == "random":
        test_points = get_random_points(N)
    else:
        raise ValueError(f"Unknown point type: {point_type}")

    print("\nSTATUS:")
    print(f"using C implementation: {tf_instance.using_clang_pip()}")
    print(f"using Numba: {tf_instance.using_numba()}")
    print(f"in memory mode: {in_memory_mode}\n")
    print(f"{N:,} {points_descr}")

    tf = TimezoneFinder(in_memory=in_memory_mode)
    test_functions = [
        # sorted by class then speed (increases readability)
        tf.certain_timezone_at,
        tf.timezone_at_land,
        tf.timezone_at,
    ]
    if in_memory_mode:
        print(
            "NOTE: global functions and TimezoneFinderL do not support (or ignore) in_memory mode"
        )
        test_functions = [
            # sorted by increasing speed (increases readability)
            tf.certain_timezone_at,
            tf.timezone_at_land,
            tf.timezone_at,
            tf.unique_timezone_at,
        ]
    else:
        tfL = TimezoneFinderL()
        test_functions = [
            # sorted by increasing speed (increases readability)
            certain_timezone_at,
            tf.certain_timezone_at,
            timezone_at_land,
            tf.timezone_at_land,
            timezone_at,
            tf.timezone_at,
            unique_timezone_at,
            tf.unique_timezone_at,
            tfL.unique_timezone_at,
            tfL.timezone_at_land,
            tfL.timezone_at,
        ]

    def time_all_runs(func2time: Callable, test_inputs: Iterable):
        for lng, lat in test_inputs:
            _ = func2time(lng=lng, lat=lat)

    def time_func(test_func: Callable):
        t = timefunc(time_all_runs, test_func, test_points)
        t_avg = t / N
        # print("total time:", time_preprocess(t))
        pts_p_sec = t_avg**-1
        pts_p_sec_k = pts_p_sec / 1000  # convert to thousands
        test_func_name = test_func.__name__
        # Handle global functions (no __self__)
        try:
            class_name = test_func.__self__.__class__.__name__
            func_label = f"{class_name}.{test_func_name}()"
        except AttributeError:  # global function or static method
            func_label = f"{test_func_name}()"
        print(
            RESULT_TEMPLATE.format(
                func_label,
                f"{t_avg:.1e}",
                f"{pts_p_sec_k:.0f}k",
            )
        )

    RESULT_TEMPLATE = "{:38s} | {:10s} | {:10s}"
    print(
        RESULT_TEMPLATE.format(
            "function name",
            "s/query",
            "pts/s",
        )
    )
    print("-" * 60)
    for test_func in test_functions:
        time_func(test_func)
    print()


# RST Report Generation Functions
def run_benchmark_for_rst(
    test_points: List[Tuple[float, float]],
    points_descr: str,
    in_memory_mode: bool,
    n_queries: int,
) -> List[Tuple[str, str, str]]:
    """Run benchmark and return results as list of tuples for RST formatting."""
    results = []

    tf = TimezoneFinder(in_memory=in_memory_mode)
    test_functions = []

    if in_memory_mode:
        test_functions = [
            tf.certain_timezone_at,
            tf.timezone_at_land,
            tf.timezone_at,
            tf.unique_timezone_at,
        ]
    else:
        tfL = TimezoneFinderL()
        test_functions = [
            certain_timezone_at,
            tf.certain_timezone_at,
            timezone_at_land,
            tf.timezone_at_land,
            timezone_at,
            tf.timezone_at,
            unique_timezone_at,
            tf.unique_timezone_at,
            tfL.unique_timezone_at,
            tfL.timezone_at_land,
            tfL.timezone_at,
        ]

    def time_all_runs(func2time: Callable, test_inputs: Iterable):
        for lng, lat in test_inputs:
            _ = func2time(lng=lng, lat=lat)

    for test_func in test_functions:
        t = timefunc(time_all_runs, test_func, test_points)
        t_avg = t / n_queries
        pts_p_sec = t_avg**-1
        pts_p_sec_k = pts_p_sec / 1000

        test_func_name = test_func.__name__
        try:
            class_name = test_func.__self__.__class__.__name__
            func_label = f"{class_name}.{test_func_name}()"
        except AttributeError:
            func_label = f"{test_func_name}()"

        results.append((func_label, f"{t_avg:.1e}", f"{pts_p_sec_k:.0f}k"))

    return results


def write_performance_report(
    output_path: Path = PERFORMANCE_REPORT_FILE, n_queries: int = None
) -> None:
    """Generate comprehensive performance report in RST format."""
    print(f"Generating performance report with {n_queries:,} queries...")
    print(f"Output will be written to: {output_path}")
    if n_queries is None:
        n_queries = N

    output_path = Path(output_path)

    # Generate test points
    print("Generating test data...")
    test_points_land = get_on_land_pts(n_queries)
    test_points_rnd = get_random_points(n_queries)

    points_and_descr = [
        (test_points_land, "'on land points' (points included in a land timezone)"),
        (test_points_rnd, "random points (anywhere on earth)"),
    ]

    tf_instance = TimezoneFinder()

    reporter = BenchmarkReporter(
        title="Timezone Finding Performance Benchmark", output_path=output_path
    )

    # Add system configuration
    reporter.add_section("System Configuration")
    reporter.add_text(f"**C Implementation**: {tf_instance.using_clang_pip()}")
    reporter.add_text("")
    reporter.add_text(f"**Numba JIT**: {tf_instance.using_numba()}")
    reporter.add_text("")
    reporter.add_text(f"**Test Queries**: {n_queries:,}")

    for in_memory_mode in [False, True]:
        mode_desc = "In-Memory Mode" if in_memory_mode else "File-Based Mode"
        reporter.add_section(mode_desc, level=2)

        if in_memory_mode:
            reporter.add_note(
                "Global functions and TimezoneFinderL do not support in-memory mode."
            )

        for test_points, points_descr in points_and_descr:
            reporter.add_section(f"Results for {points_descr}", level=3)

            results = run_benchmark_for_rst(
                test_points, points_descr, in_memory_mode, n_queries
            )

            # Table formatting
            headers = ["Function Name", "Seconds/Query", "Points/Second"]
            rows = [
                [func_label, time_per_query, pts_per_sec]
                for func_label, time_per_query, pts_per_sec in results
            ]

            reporter.add_table(headers, rows)

    reporter.write_report()
    print("Performance report generated successfully!")


def main():
    """CLI entry point for standalone script execution."""
    parser = create_cli_parser(
        description="Benchmark timezone finding performance",
        script_name="Timezone Finding Benchmark",
    )

    # Add additional arguments specific to this benchmark
    parser.add_argument(
        "--queries",
        "-n",
        type=int,
        default=N,
        help=f"Number of test queries to run (default: {N})",
    )

    args = parser.parse_args()

    if args.rst:
        # Generate RST report
        output_path = DOC_ROOT / "benchmark_results_timezonefinding.rst"
        write_performance_report(output_path, args.queries)
    else:
        # Run console benchmark (pytest mode)
        print("Running timezone finding performance benchmark...")
        print("Use --rst flag to generate RST report")
        pytest.main([__file__])


if __name__ == "__main__":
    main()
