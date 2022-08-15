import random
import timeit
from math import log10
from typing import Callable, List, Tuple

import numpy as np

from timezonefinder import utils
from timezonefinder.configs import (
    COORD2INT_FACTOR,
    DTYPE_FORMAT_SIGNED_I_NUMPY,
    MAX_ALLOWED_COORD_VAL,
    MAX_LAT_VAL,
    MAX_LNG_VAL,
)


def timefunc(function: Callable, *args):
    def wrap():
        function(*args)

    t = timeit.Timer(wrap)
    nr_runs = 1
    return t.timeit(nr_runs)


def proto_test_case(data, fct):
    for input, expected_output in data:
        # print(input, expected_output, fct(input))
        actual_output = fct(input)
        if actual_output != expected_output:
            print("input: {} expected: {} got: {}".format(input, expected_output, actual_output))
        assert actual_output == expected_output


def time_preprocess(time):
    valid_digits = 4
    zero_digits = abs(min(0, int(log10(time))))
    digits_to_print = zero_digits + valid_digits
    return str(round(time, digits_to_print)) + "s"


def get_rnd_query_pt() -> Tuple[float, float]:
    lng = random.uniform(-MAX_LNG_VAL, MAX_LNG_VAL)
    lat = random.uniform(-MAX_LAT_VAL, MAX_LAT_VAL)
    return lng, lat


def get_rnd_poly(nr_max_coords: int = 150000) -> Tuple[np.ndarray, np.ndarray]:
    # maximal amount of coordinates in one polygon
    nr_coords = random.randint(3, nr_max_coords)
    x_coords = np.random.uniform(-MAX_LNG_VAL, MAX_LNG_VAL, nr_coords)
    y_coords = np.random.uniform(-MAX_LAT_VAL, MAX_LAT_VAL, nr_coords)
    return x_coords, y_coords


def gen_test_input():
    # one test polygon + one query point
    longitudes, latitudes = get_rnd_poly()
    lng, lat = get_rnd_query_pt()
    x, y, x_coords, y_coords = convert_inside_polygon_input(lng, lat, longitudes, latitudes)
    return x, y, x_coords, y_coords


def poly_conversion_fct(x_coords, y_coords):
    x_coords = np.array(x_coords)
    y_coords = np.array(y_coords)
    x_coords *= COORD2INT_FACTOR
    y_coords *= COORD2INT_FACTOR
    dtype = DTYPE_FORMAT_SIGNED_I_NUMPY
    x_coords = np.array(x_coords, dtype=dtype)
    y_coords = np.array(y_coords, dtype=dtype)
    y_coords = np.ascontiguousarray(y_coords, dtype=dtype)
    assert not np.any(x_coords > MAX_ALLOWED_COORD_VAL)
    assert not np.any(x_coords < -MAX_ALLOWED_COORD_VAL)
    assert not np.any(y_coords > MAX_ALLOWED_COORD_VAL)
    assert not np.any(y_coords < -MAX_ALLOWED_COORD_VAL)
    return x_coords, y_coords


def convert_inside_polygon_input(lng, lat, longitudes, latitudes):
    x_coords, y_coords = poly_conversion_fct(longitudes, latitudes)
    x, y = utils.coord2int(lng), utils.coord2int(lat)
    return x, y, x_coords, y_coords
