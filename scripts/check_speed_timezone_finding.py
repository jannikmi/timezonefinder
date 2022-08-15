from typing import Callable, Iterable, List, Tuple

import pytest
from auxiliaries import get_rnd_query_pt, timefunc

from timezonefinder import TimezoneFinder, TimezoneFinderL

N = int(1e4)
tf_instance = TimezoneFinder()


def get_on_land_pts(length: int):
    # create an array of points where timezone_finder finds something (on_land queries)
    print(f"collecting and storing {N} on land points for the tests...")
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
    print(f"using C implementation: {tf_instance.using_clang_pip()}")
    print(f"using Numba: {tf_instance.using_numba()}")

    tf = TimezoneFinder(in_memory=in_memory_mode)
    tfL = TimezoneFinderL(in_memory=in_memory_mode)
    classes_and_function_names = [
        (tf, "timezone_at"),
        (tf, "timezone_at_land"),
        (tfL, "timezone_at"),
        (tfL, "timezone_at_land"),
    ]
    print(f"\n{N} {points_descr}")

    print(f"in memory mode: {in_memory_mode}")
    print()

    def time_all_runs(func2time: Callable, test_inputs: Iterable):
        for lng, lat in test_inputs:
            tz = func2time(lng=lng, lat=lat)  # 'Europe/Berlin'

    def time_func(test_instance, test_func_name):
        test_func = test_instance.__getattribute__(test_func_name)
        t = timefunc(time_all_runs, test_func, test_points)
        t_avg = t / N
        # print("total time:", time_preprocess(t))
        pts_p_sec = t_avg**-1
        class_name = test_instance.__class__.__name__
        print(
            RESULT_TEMPLATE.format(
                f"{class_name}.{test_func_name}()",
                f"{t_avg:.1e}",
                f"{pts_p_sec:.1e}",
            )
        )

    RESULT_TEMPLATE = "{:35s} | {:10s} | {:10s}"
    print(
        RESULT_TEMPLATE.format(
            "function name",
            "s/query",
            "pts/s",
        )
    )
    print("-" * 60)
    for test_instance, test_func_name in classes_and_function_names:
        time_func(test_instance, test_func_name)
    print()
