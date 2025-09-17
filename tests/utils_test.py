from typing import Callable, Tuple

import numpy as np
import pytest

from scripts.configs import ZONE_ID_DTYPE
from scripts.utils import convert2ints, convert_polygon
from tests.auxiliaries import (
    convert_inside_polygon_input,
    get_rnd_poly,
    get_rnd_poly_int,
    get_rnd_query_pt,
)
from timezonefinder import utils_clang, utils_numba, utils
from timezonefinder.configs import INT2COORD_FACTOR

POINT_IN_POLYGON_TESTCASES = [
    # (polygon, list of test points, expected results)
    (
        # square
        ([0.5, 0.5, -0.5, -0.5, 0.5], [0.0, 0.5, 0.5, -0.5, -0.5]),
        [
            # (x,y),
            # inside
            (0.0, 0.000),
            # outside
            (-1.0, 1.0),
            (0.0, 1.0),
            (1.0, 1.0),
            (-1.0, 0.0),
            (1.0, 0.0),
            (-1.0, -1.0),
            (0.0, -1.0),
            (1.0, -1.0),
            # on the line test cases
            # inclusion is not defined if point lies on the line
            # (0.0, -0.5),
            # (0, 0.5),
            # (-0.5, 0),
            # (0.5, 0),
        ],
        [True, False, False, False, False, False, False, False, False],
    ),
    (
        # more complex polygon with sloped edges
        ([1, 5, 7, 8, 7, 6, 1, 1, 5, 1], [1, 4, 1, 3, 3, 6, 6, 2, 5, 1]),
        [
            # (x,y),
            # inside (14 cases)
            (7, 1.0001),
            (7, 1.1),
            (7, 1.5),
            (7, 2.9),
            (7, 2.999),
            (1.1, 3),
            (3.1, 3),
            (6, 3),
            (2, 4),
            (3, 4),
            (4.5, 4),
            (6, 4),
            (6.5, 4),
            (2, 5.5),
            # outside (21 cases)
            (0.0, 0.0),
            (5.0, 0.0),
            (9.0, 0.0),
            (7, 0.9),
            (7, 0.9999),
            (0.0, 1.0),
            (5.0, 1.0),
            (8.0, 1.0),
            (0.9, 3),
            (2.5, 3),
            (4, 3),
            (5, 3),
            (8.1, 3),
            (7, 3.00001),
            (7, 3.1),
            (0, 4),
            (7, 4),
            (0, 6),
            (7, 6),
            (0, 7),
            (7, 7),
            # on the line test cases
            # inclusion is not defined if point lies on the line
        ],
        [True] * 14 + [False] * 21,
    ),
    (
        # test for overflow, use maximum valid domain (of the coordinates)
        # ATTENTION: only values \in [-180, 180] allowed!
        # delta_y_max * delta_x_max = 180x10^7 * 360x10^7
        [[-180.0, 180.0, -180.0], [-90.0, 90.0, 90.0]],
        [
            # choose query points so (x-x_i) and (y-y_i) get big!
            # inside
            (
                -179.9999999,
                -89.9999998,
            ),
            (-179.9999, -89.9998),
            (-179.9999, 89.9999),
            # TODO uncertain case:
            # (179.9998, 89.9999),
        ],
        [True] * 3,
    ),
]


def test_dtype_conversion():
    # coordinates (float) to int
    lng, lat = get_rnd_query_pt()
    x_int = utils.coord2int(lng)
    y_int = utils.coord2int(lat)
    lng2 = utils.int2coord(x_int)
    lat2 = utils.int2coord(y_int)
    np.testing.assert_almost_equal(lng, lng2)
    np.testing.assert_almost_equal(lat, lat2)


def test_convert2coord_pairs():
    x_ints, y_ints = get_rnd_poly_int()
    polygon_int = np.array((x_ints, y_ints))
    pairs = utils.convert2coord_pairs(polygon_int)
    assert isinstance(pairs, list)
    for pair in pairs:
        assert isinstance(pair, tuple)
        assert len(pair) == 2
        lng, lat = pair
        assert isinstance(lng, float)
        assert isinstance(lat, float)
        utils.validate_coordinates(lng, lat)

    coords_converted = np.array(pairs).T
    longitudes = [utils.int2coord(x) for x in x_ints]
    latitudes = [utils.int2coord(y) for y in y_ints]
    coords_true = np.array((longitudes, latitudes))
    np.testing.assert_almost_equal(coords_converted, coords_true)


def test_convert2coords():
    x_ints, y_ints = get_rnd_poly_int()
    polygon_int = np.array((x_ints, y_ints))
    coord_lists = utils.convert2coords(polygon_int)
    assert isinstance(coord_lists, list)
    assert len(coord_lists) == 2
    x_coords, y_coords = coord_lists
    assert len(x_coords) == len(y_coords)
    for lng, lat in zip(x_coords, y_coords):
        assert isinstance(lng, float)
        assert isinstance(lat, float)
        utils.validate_coordinates(lng, lat)

    coords_converted = np.array(coord_lists)
    longitudes = [utils.int2coord(x) for x in x_ints]
    latitudes = [utils.int2coord(y) for y in y_ints]
    coords_true = np.array((longitudes, latitudes))
    np.testing.assert_almost_equal(coords_converted, coords_true)


def test_convert2ints():
    coords_true = get_rnd_poly()
    poly_int = convert2ints(coords_true)
    assert isinstance(poly_int, list)
    assert len(poly_int) == 2
    x_coords, y_coords = poly_int
    assert len(x_coords) == len(y_coords)

    ints_converted = np.array(poly_int)
    longitudes, latitudes = coords_true
    x_ints = [utils.coord2int(x) for x in longitudes]
    y_ints = [utils.coord2int(y) for y in latitudes]
    ints_true = np.array((x_ints, y_ints))
    np.testing.assert_almost_equal(ints_converted, ints_true)


def test_clang_extension_loaded():
    # testing the Clang version of the Point in Polygon algorithm requires the C extension to be loaded
    assert utils.clang_extension_loaded, "the clang extension not loaded, "


# TODO test equal results of both implementation
@pytest.mark.parametrize(
    "inside_poly_func",
    [
        utils_numba.pt_in_poly_python,
        utils_clang.pt_in_poly_clang,
    ],
)
@pytest.mark.parametrize(
    "test_case",
    POINT_IN_POLYGON_TESTCASES,
)
def test_inside_polygon(inside_poly_func: Callable, test_case: Tuple):
    # print(f"\ntesting function {inside_poly_func.__name__}")

    # test for overflow:
    # make numpy overflow runtime warning raise an error
    np.seterr(all="warn")
    import warnings

    warnings.filterwarnings("error")
    nr_mistakes = 0
    template = "{:12s} | {:10s} | {:10s} | {:2s}"
    print()
    print(template.format("#test point", "EXPECTED", "COMPUTED", "  "))
    # print("=" * 50)
    coords, query_points, expected_results = test_case
    coords_int = convert_polygon(coords)
    for i, ((lng, lat), expected_result) in enumerate(
        zip(query_points, expected_results)
    ):
        utils.validate_coordinates(lng, lat)  # check the range of lng, lat
        x, y = convert_inside_polygon_input(lng, lat)
        actual_result = inside_poly_func(x, y, coords_int)
        if actual_result == expected_result:
            ok = "OK"
        else:
            print((lng, lat), "-->", (x, y))
            print(coords)
            ok = "XX"
            nr_mistakes += 1
        print(template.format(str(i), str(expected_result), str(actual_result), ok))

    print(f"{nr_mistakes} mistakes made")
    assert nr_mistakes == 0


@pytest.mark.parametrize(
    "lng, lat",
    [
        (180.0, 90.0),
        (-180.0, 90.0),
        (-180.0, 90.0),
        (180.0, -90.0),
        (180.0, -90.0),
        (-180.0, -90.0),
        (-180.0, -90.0),
    ],
)
def test_rectify_coords_valid(lng, lat):
    utils.validate_coordinates(lng=lng, lat=lat)


@pytest.mark.parametrize(
    "lng, lat",
    [
        (180.0 + INT2COORD_FACTOR, 90.0),
        (-180.0 - INT2COORD_FACTOR, 90.0 + INT2COORD_FACTOR),
        (-180.0, 90.0 + INT2COORD_FACTOR),
        (180.0 + INT2COORD_FACTOR, -90.0),
        (180.0, -90.0 - INT2COORD_FACTOR),
        (-180.0 - INT2COORD_FACTOR, -90.0),
        (-180.0 - INT2COORD_FACTOR, -90.01 - INT2COORD_FACTOR),
    ],
)
def test_rectify_coords_invalid(lng, lat):
    with pytest.raises(ValueError):
        utils.validate_coordinates(lng=lng, lat=lat)


@pytest.mark.parametrize(
    "entry_list, expected",
    [
        ([], 0),
        ([1], 0),
        ([2], 0),
        ([1, 1], 0),
        ([1, 2], 1),
        ([1, 3], 1),
        ([1, 3, 3], 1),
        ([1, 3, 3, 0], 3),
        ([1, 3, 3, 0, 0, 0, 0], 3),
    ],
)
def test_get_last_change_idx(entry_list, expected):
    array = np.array(entry_list, dtype=ZONE_ID_DTYPE)
    assert utils.get_last_change_idx(array) == expected


if __name__ == "__main__":
    pytest.main([__file__])
