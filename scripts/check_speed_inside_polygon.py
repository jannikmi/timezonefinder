from typing import Callable, Iterable

import numpy as np
from auxiliaries import gen_test_input, timefunc

from timezonefinder import utils

nr_of_runs = int(1e4)


def check_inside_polygon_speed():
    print(f"testing the speed of the different point in polygon test algorithms for {nr_of_runs} points...")

    # test for overflow:
    # make numpy overflow runtime warning raise an error
    np.seterr(all="warn")
    import warnings

    warnings.filterwarnings("error")

    # reuse the same inputs for comparable results
    test_inputs = [gen_test_input() for _ in range(nr_of_runs)]

    def time_inside_poly_func(inside_poly_func: Callable, test_inputs: Iterable):
        for test_input in test_inputs:
            _ = inside_poly_func(*test_input)

    def time_func(test_func):
        func_name = test_func.__name__
        t = timefunc(time_inside_poly_func, test_func, test_inputs)
        t_avg = t / nr_of_runs
        print(f"{func_name}: {t_avg:.1e} s / query")
        return t_avg

    print()
    t_clang = time_func(utils.inside_clang)
    t_python = time_func(utils.inside_python)
    if t_clang < t_python:
        speedup = (t_python / t_clang) - 1
        print(f"C implementation is {speedup:.1f}x faster than pure Python")
    else:
        speedup = (t_clang / t_python) - 1
        print(f"Pure Python implementation is {speedup:.1f}x faster than the C implementation")


if __name__ == "__main__":
    check_inside_polygon_speed()
