from typing import Callable, Iterable, List, Tuple

import pytest
from scripts.configs import DEBUG
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


test_points_land = get_on_land_pts(N)
test_points_rnd = get_random_points(N)


def eval_time_fct():
    global tf, point_list
    for point in point_list:
        tf.timezone_at(lng=point[0], lat=point[1])


points_and_descr = [
    (test_points_land, "'on land points' (points included in a land timezone)"),
    (test_points_rnd, "random points (anywhere on earth)"),
]


@pytest.mark.parametrize(
    "test_points, points_descr",
    points_and_descr,
)
@pytest.mark.parametrize(
    "in_memory_mode",
    [
        False,
        True,
    ],
)
def test_timezone_finding_speed(
    test_points,
    points_descr: str,
    in_memory_mode: bool,
):
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
                f"{pts_p_sec_k:.1f}k",
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
