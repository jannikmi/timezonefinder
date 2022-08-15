import random
import timeit
from math import log10
from typing import Callable, Tuple

import numpy as np

from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import (
    DTYPE_FORMAT_SIGNED_I_NUMPY,
    MAX_ALLOWED_COORD_VAL,
    MAX_LAT_VAL,
    MAX_LNG_VAL,
)

# for reading coordinates

tf_instance = TimezoneFinder()


def timefunc(function: Callable, *args):
    def wrap():
        function(*args)

    timer = timeit.Timer(wrap)
    nr_runs = 1
    t_in_sec = timer.timeit(nr_runs)
    return t_in_sec


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


def get_rnd_poly_int() -> np.ndarray:
    max_poly_id = tf_instance.nr_of_polygons - 1
    poly_id = random.randint(0, max_poly_id)
    poly = tf_instance.coords_of(poly_id)
    return poly


def get_rnd_poly() -> np.ndarray:
    poly = get_rnd_poly_int()
    coords = utils.convert2coords(poly)
    return np.array(coords)


def poly_conversion_fct(coords: np.ndarray) -> np.ndarray:
    x_ints, y_ints = utils.convert2ints(coords)
    dtype = DTYPE_FORMAT_SIGNED_I_NUMPY
    x_ints = np.array(x_ints, dtype=dtype)
    y_ints = np.array(y_ints, dtype=dtype)
    assert not np.any(x_ints > MAX_ALLOWED_COORD_VAL)
    assert not np.any(x_ints < -MAX_ALLOWED_COORD_VAL)
    assert not np.any(y_ints > MAX_ALLOWED_COORD_VAL)
    assert not np.any(y_ints < -MAX_ALLOWED_COORD_VAL)
    return np.stack((x_ints, y_ints))


def convert_inside_polygon_input(lng: float, lat: float, coords: np.ndarray):
    coords_ints = poly_conversion_fct(coords)
    x, y = utils.coord2int(lng), utils.coord2int(lat)
    return x, y, coords_ints


def get_pip_test_input() -> Tuple[int, int, np.ndarray]:
    # one test polygon + one query point
    lng, lat = get_rnd_query_pt()
    x, y = utils.coord2int(lng), utils.coord2int(lat)
    poly_int = get_rnd_poly_int()
    return x, y, poly_int
