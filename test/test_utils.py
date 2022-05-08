# -*- coding:utf-8 -*-

import numpy as np
import pytest

from timezonefinder import utils
from timezonefinder.configs import (
    COORD2INT_FACTOR,
    DTYPE_FORMAT_H_NUMPY,
    DTYPE_FORMAT_SIGNED_I_NUMPY,
    INT2COORD_FACTOR,
    MAX_ALLOWED_COORD_VAL,
)


def poly_conversion_fct(coords):
    array = np.array(coords)
    array *= COORD2INT_FACTOR
    assert not np.any(array > MAX_ALLOWED_COORD_VAL)
    array = np.ndarray.astype(array, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY)
    return array


def test_dtype_conversion():
    # coordinates (float) to int
    coord_values = [float(x) for x in range(-2, 3, 1)]
    coord_polygon = (coord_values, coord_values)
    polygon_int = poly_conversion_fct(coord_polygon)
    int_values = [utils.coord2int(x) for x in coord_values]
    polygon_comparison = np.array((int_values, int_values))
    assert np.all(polygon_int == polygon_comparison)

    # backwards: int to coord
    values_converted_coords = [utils.int2coord(x) for x in int_values]
    assert np.all(np.array(values_converted_coords) == np.array(coord_values))


def test_convert2coord_pairs():
    coord_values = [float(x) for x in range(-2, 3, 1)]
    coord_polygon = (coord_values, coord_values)
    polygon_int = poly_conversion_fct(coord_polygon)
    assert utils.convert2coord_pairs(polygon_int) == list(
        zip(coord_values, coord_values)
    )


def test_convert2coords():
    coord_values = [float(x) for x in range(-2, 3, 1)]
    coord_polygon = (coord_values, coord_values)
    polygon_int = poly_conversion_fct(coord_polygon)
    assert utils.convert2coords(polygon_int) == [coord_values, coord_values]


# use only numpy data structures, because the functions are reused for testing the numba helpers
def test_inside_polygon():
    # test for overflow:
    # make numpy overflow runtime warning raise an error
    np.seterr(all="warn")
    import warnings

    warnings.filterwarnings("error")

    test_cases = [
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
                # inside (#14)
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
                # outside (#21)
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
                # inside (#4)
                (
                    -179.9999999,
                    -89.9999998,
                ),  # choose so (x-x_i) and (y-y_i) get big!
                # (-179.9999, -89.9998),
                (179.9998, 89.9999),
                (-179.9999, 89.9999),
            ],
            [True] * 3,
        ),
    ]

    no_mistakes_made = True
    template = "{0:10s} | {1:10s} | {2:10s} | {3:10s} | {4:2s}"

    print("\nresults inside_polygon():")
    print(template.format("#test poly", "#test point", "EXPECTED", "COMPUTED", "  "))
    print("=" * 50)
    for n, (coords, p_test_cases, expected_results) in enumerate(test_cases):
        coords = poly_conversion_fct(coords)
        for i, (lng, lat) in enumerate(p_test_cases):
            utils.validate_coordinates(lng, lat)  # check the range of lng, lat
            x, y = utils.coord2int(lng), utils.coord2int(lat)
            actual_result = utils.inside_polygon(x, y, coords)
            expected_result = expected_results[i]
            if actual_result == expected_result:
                ok = "OK"
            else:
                print((x, y))
                print(coords)
                ok = "XX"
                no_mistakes_made = False
            print(
                template.format(
                    str(n), str(i), str(expected_result), str(actual_result), ok
                )
            )

        print("\n")

    assert no_mistakes_made


def test_rectify_coords():
    # within bounds -> no exception
    utils.validate_coordinates(lng=180.0, lat=90.0)
    utils.validate_coordinates(lng=-180.0, lat=90.0)
    utils.validate_coordinates(lng=-180.0, lat=90.0)
    utils.validate_coordinates(lng=180.0, lat=-90.0)
    utils.validate_coordinates(lng=180.0, lat=-90.0)
    utils.validate_coordinates(lng=-180.0, lat=-90.0)
    utils.validate_coordinates(lng=-180.0, lat=-90.0)

    with pytest.raises(ValueError):  # coords out of bounds
        utils.validate_coordinates(lng=180.0 + INT2COORD_FACTOR, lat=90.0)
        utils.validate_coordinates(
            lng=-180.0 - INT2COORD_FACTOR, lat=90.0 + INT2COORD_FACTOR
        )
        utils.validate_coordinates(lng=-180.0, lat=90.0 + INT2COORD_FACTOR)
        utils.validate_coordinates(lng=180.0 + INT2COORD_FACTOR, lat=-90.0)
        utils.validate_coordinates(lng=180.0, lat=-90.0 - INT2COORD_FACTOR)
        utils.validate_coordinates(lng=-180.0 - INT2COORD_FACTOR, lat=-90.0)
        utils.validate_coordinates(
            lng=-180.0 - INT2COORD_FACTOR, lat=-90.01 - INT2COORD_FACTOR
        )


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
    array = np.array(entry_list, dtype=DTYPE_FORMAT_H_NUMPY)
    assert utils.get_last_change_idx(array) == expected
