from ast import List
import random
import timeit
from math import log10
from typing import Callable, Tuple

import numpy as np

from scripts.utils import validate_coord_array_shape
from timezonefinder import utils
from timezonefinder.configs import (
    MAX_LAT_VAL,
    MAX_LAT_VAL_INT,
    MAX_LNG_VAL,
    MAX_LNG_VAL_INT,
)
from timezonefinder.polygon_array import PolygonArray

# for reading coordinates
boundaries_dir = utils.get_boundaries_dir()
boundaries = PolygonArray(data_location=boundaries_dir, in_memory=True)


def ocean2land(test_locations):
    for lat, lng, description, expected in test_locations:
        if utils.is_ocean_timezone(expected):
            expected = None
        yield lat, lng, description, expected


def check_geometry(geometry_obj: List):
    coords = geometry_obj[0][0]
    assert len(coords) == 2, (
        "the polygon does not consist of two latitude longitude lists"
    )
    x_coords, y_coords = coords
    nr_x_coords = len(x_coords)
    nr_y_coords = len(y_coords)
    assert nr_x_coords > 2, "a polygon must consist of more than 2 coordinates"
    assert nr_x_coords == nr_y_coords, (
        "the amount of x and y coordinates (lng, lat) must be equal"
    )


def check_pairwise_geometry(geometry_obj: List):
    # list of all coord pairs of the first polygon
    cord_pairs = geometry_obj[0][0]
    assert len(cord_pairs) > 2, "a polygon must consist of more than 2 coordinates"
    first_coord_pair = cord_pairs[0]
    assert len(first_coord_pair) == 2, (
        "the polygon does not consist of coordinate pairs as expected."
    )


def is_valid_lng_int(x: int) -> bool:
    return -MAX_LNG_VAL_INT <= x <= MAX_LNG_VAL_INT


def is_valid_lat_int(y: int) -> bool:
    return -MAX_LAT_VAL_INT <= y <= MAX_LAT_VAL_INT


def is_valid_lng_int_vec(arr) -> bool:
    return np.all((-MAX_LNG_VAL_INT <= arr) & (arr <= MAX_LNG_VAL_INT))


def is_valid_lat_int_vec(arr) -> bool:
    return np.all((-MAX_LAT_VAL_INT <= arr) & (arr <= MAX_LAT_VAL_INT))


def validate_polygon_coordinates(coords: np.ndarray):
    """Helper function to validate polygon coordinates format and values."""
    validate_coord_array_shape(coords)

    # test whether the coordinates are within valid ranges
    x_coords, y_coords = coords
    # apply to every coordinate

    assert is_valid_lng_int_vec(x_coords)
    assert is_valid_lat_int_vec(y_coords)


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
            print(
                "input: {} expected: {} got: {}".format(
                    input, expected_output, actual_output
                )
            )
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
    max_poly_id = len(boundaries) - 1
    poly_id = random.randint(0, max_poly_id)
    poly = boundaries.coords_of(poly_id)
    return poly


def get_rnd_poly() -> np.ndarray:
    poly = get_rnd_poly_int()
    coords = utils.convert2coords(poly)
    return np.array(coords)


def convert_inside_polygon_input(lng: float, lat: float):
    x, y = utils.coord2int(lng), utils.coord2int(lat)
    return x, y


def get_pip_test_input() -> Tuple[int, int, np.ndarray]:
    # one test polygon + one query point
    lng, lat = get_rnd_query_pt()
    x, y = convert_inside_polygon_input(lng, lat)
    poly_int = get_rnd_poly_int()
    return x, y, poly_int
