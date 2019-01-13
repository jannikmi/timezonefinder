from __future__ import absolute_import, division, print_function, unicode_literals

import random
import unittest
from math import degrees, radians, sqrt

import numpy as np
from six.moves import range

from timezonefinder.global_settings import DTYPE_FORMAT_SIGNED_I_NUMPY, DTYPE_FORMAT_B_NUMPY, DTYPE_FORMAT_H_NUMPY, \
    DTYPE_FORMAT_F_NUMPY, DECIMAL_PLACES_ACCURACY, COORD2INT_FACTOR, MAX_ALLOWED_COORD_VAL, INT2COORD_FACTOR


def random_point():
    # tzwhere does not work for points with more latitude!
    return random.uniform(-180, 180), random.uniform(-84, 84)


def list_of_random_points(length):
    return [random_point() for i in range(length)]


def poly_conversion_fct(coords):
    array = np.array(coords)
    array *= COORD2INT_FACTOR
    assert (not np.any(array > MAX_ALLOWED_COORD_VAL))
    array = np.ndarray.astype(array, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY)
    return array


# from timezonefinder.helpers import (
#     all_the_same, coord2int, distance_to_point_on_equator, distance_to_polygon, distance_to_polygon_exact,
#     haversine,
#     inside_polygon,
# )

class HelperTest(unittest.TestCase):
    import timezonefinder.helpers as helpers
    fct_dict = {
        "all_the_same": helpers.all_the_same,
        "coord2int": helpers.coord2int,
        "int2coord": helpers.int2coord,
        "distance_to_point_on_equator": helpers.distance_to_point_on_equator,
        "distance_to_polygon": helpers.distance_to_polygon,
        "distance_to_polygon_exact": helpers.distance_to_polygon_exact,
        "haversine": helpers.haversine,
        "inside_polygon": helpers.inside_polygon,
        "coord2shortcut": helpers.coord2shortcut,
        "rectify_coordinates": helpers.rectify_coordinates,
    }
    print('\ntesting helpers.py functions...')

    def test_dtype_conversion(self):
        coord2int = self.fct_dict['coord2int']
        if coord2int is None:
            print('test dtype_conversion skipped.')
            return

        int2coord = self.fct_dict['int2coord']

        # coordinates (float) to int
        coord_values = [float(x) for x in range(-2, 3, 1)]
        coord_polygon = (coord_values, coord_values)
        polygon_int = poly_conversion_fct(coord_polygon)
        int_values = [coord2int(x) for x in coord_values]
        polygon_comparison = np.array((int_values, int_values))
        assert (np.all(polygon_int == polygon_comparison))

        # backwards: int to coord
        values_converted_coords = [int2coord(x) for x in int_values]
        assert (np.all(np.array(values_converted_coords) == np.array(coord_values)))

    # use only numpy data structures, because the functions are reused for testing the numba helpers
    def test_inside_polygon(self):

        inside_polygon = self.fct_dict['inside_polygon']
        if inside_polygon is None:
            print('test inside polygon skipped.')
            return

        coord2int = self.fct_dict['coord2int']
        rectify_coordinates = self.fct_dict['rectify_coordinates']

        # test for overflow:
        # make numpy overflow runtime warning raise an error
        np.seterr(all='warn')
        import warnings
        warnings.filterwarnings('error')

        test_cases = [
            # (polygon, list of test points, expected results)
            (
                # square
                ([0.5, 0.5, -0.5, -0.5, 0.5],
                 [0.0, 0.5, 0.5, -0.5, -0.5]),
                [
                    # (x,y),
                    # inside
                    (0.0, 0.000),

                    # outside
                    (-1.0, 1.0),
                    (0.0, 1.0),
                    (1.0, 1.0),
                    (-1.0, .0),
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
                ([1, 5, 7, 8, 7, 6, 1, 1, 5, 1],
                 [1, 4, 1, 3, 3, 6, 6, 2, 5, 1]),
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
                [[-180.0, 180.0, -180.0],
                 [-90.0, 90.0, 90.0]],
                [
                    # inside (#4)
                    (-179.9999999, -89.9999998),  # choose so (x-x_i) and (y-y_i) get big!
                    # (-179.9999, -89.9998),
                    (179.9998, 89.9999),
                    (-179.9999, 89.9999),
                ],
                [True] * 3,

            ),
        ]

        no_mistakes_made = True
        template = '{0:10s} | {1:10s} | {2:10s} | {3:10s} | {4:2s}'

        print('\nresults inside_polygon():')
        print(template.format('#test poly', '#test point', 'EXPECTED', 'COMPUTED', '  '))
        print('=' * 50)
        for n, (coords, p_test_cases, expected_results) in enumerate(test_cases):
            coords = poly_conversion_fct(coords)
            for i, (lng, lat) in enumerate(p_test_cases):
                x, y = rectify_coordinates(lng, lat)  # check the range of lng, lat
                x, y = coord2int(x), coord2int(y)
                actual_result = inside_polygon(x, y, coords)
                expected_result = expected_results[i]
                if actual_result == expected_result:
                    ok = 'OK'
                else:
                    print((x, y))
                    print(coords)
                    ok = 'XX'
                    no_mistakes_made = False
                print(template.format(str(n), str(i), str(expected_result), str(actual_result), ok))

            print('\n')

        assert no_mistakes_made

    def test_all_the_same(self):

        all_the_same_fct = self.fct_dict['all_the_same']
        if all_the_same_fct is None:
            print('test all_the_same skipped.')
            return

        test_cases = [
            (0, 3, [1, 3, 2]),
            (1, 3, [1, 3, 2]),
            (2, 3, [1, 3, 2]),
            (1, 3, [1, 2, 2]),
            (0, 1, [1]),

        ]

        expected_results = [
            -1,
            -1,
            2,
            2,
            1,
        ]

        i = 0

        for pointer, length, id_list in test_cases:
            # print(pointer, length, id_list, all_the_same(pointer, length, id_list) )
            assert all_the_same_fct(pointer, length, np.array(
                id_list, dtype=DTYPE_FORMAT_H_NUMPY)) == expected_results[i]
            i += 1

    def test_distance_computation(self):

        distance_to_point_on_equator = self.fct_dict['distance_to_point_on_equator']
        haversine = self.fct_dict['haversine']
        coord2int = self.fct_dict['coord2int']
        distance_to_polygon_exact = self.fct_dict['distance_to_polygon_exact']
        distance_to_polygon = self.fct_dict['distance_to_polygon']
        if distance_to_point_on_equator is None:
            print('test distance computation skipped.')
            return

        def km2rad(km):
            return km / 6371

        def km2deg(km):
            return degrees(km2rad(km))

        p_test_cases = [
            # (x,y),
            (0, 1),
            (1, 0),
            (0, -1),
            (-1, 0),

            # on the line test cases
            # (-0.5, 0.5),
            # (0, 0.5),
            # (-0.5, 0),
            # (0.5, 0),
        ]

        p1_lng_rad = radians(0.0)
        p1_lat_rad = radians(0.0)

        for x, y in p_test_cases:
            result = distance_to_point_on_equator(radians(x), radians(y), p1_lng_rad)
            if km2deg(result) != 1:
                raise AssertionError('should be equal:', km2deg(result), 1)
            hav_result = haversine(radians(x), radians(y), p1_lng_rad, 0)
            if km2deg(hav_result) != 1.0:
                raise AssertionError('should be equal:', km2deg(hav_result), 1.0)

        for i in range(1000):
            rnd_point = random_point()
            lng_rnd_point2 = random_point()[0]
            hav_result = degrees(haversine(radians(rnd_point[0]), radians(rnd_point[1]), lng_rnd_point2, 0))
            result = degrees(distance_to_point_on_equator(radians(rnd_point[0]), radians(rnd_point[1]), lng_rnd_point2))
            self.assertAlmostEqual(hav_result, result, places=DECIMAL_PLACES_ACCURACY)
            # if abs(hav_result - result) > 0.000001:
            #     raise AssertionError(i, 'should be equal:', hav_result, result, rnd_point, lng_rnd_point2)

        x_coords = [0.5, -0.5, -0.5, 0.5]
        y_coords = [0.5, 0.5, -0.5, -0.5]
        points = [
            [coord2int(x) for x in x_coords],
            [coord2int(x) for x in y_coords],
        ]
        trans_points = [
            [None for x in x_coords],
            [None for x in y_coords],
        ]

        x_rad = radians(1.0)
        y_rad = radians(0.0)

        # print(km2deg(haversine(x_rad, y_rad, p1_lng_rad, p1_lat_rad)))
        assert km2deg(haversine(x_rad, y_rad, p1_lng_rad, p1_lat_rad)) == 1

        distance_exact = distance_to_polygon_exact(x_rad, y_rad, len(x_coords),
                                                   np.array(points, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY),
                                                   np.array(trans_points, dtype=DTYPE_FORMAT_F_NUMPY))
        # print(km2deg(distance_exact))
        assert km2deg(distance_exact) == 0.5
        # print('=====')
        distance = distance_to_polygon(x_rad, y_rad, len(x_coords), np.array(points, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY))
        # print(km2deg(distance))
        assert abs(km2deg(distance) - sqrt(2) / 2) < 0.00001


class HelperTestNumba(HelperTest):
    # all Numba compiled functions have to receive their arguments in the proper data type (and numpy array shape)
    try:
        import timezonefinder.helpers_numba as helpers
        fct_dict = {
            "all_the_same": helpers.all_the_same,
            "coord2int": helpers.coord2int,
            "int2coord": helpers.int2coord,
            "distance_to_point_on_equator": helpers.distance_to_point_on_equator,
            "distance_to_polygon": helpers.distance_to_polygon,
            "distance_to_polygon_exact": helpers.distance_to_polygon_exact,
            "haversine": helpers.haversine,
            "inside_polygon": helpers.inside_polygon,
            "coord2shortcut": helpers.coord2shortcut,
            "rectify_coordinates": helpers.rectify_coordinates,
        }

        print('\nNumba installation found.\ntesting helpers_numba.py functions...')

    except ImportError:
        fct_dict = {
            "all_the_same": None,
            "coord2int": None,
            "int2coord": None,
            "distance_to_point_on_equator": None,
            "distance_to_polygon": None,
            "distance_to_polygon_exact": None,
            "haversine": None,
            "inside_polygon": None,
            "coord2shortcut": None,
            "rectify_coordinates": None,
        }
        print('\nNumba installation NOT found.')


if __name__ == '__main__':
    # suite = unittest.TestLoader().loadTestsFromTestCase(HelperTest)
    # unittest.TextTestRunner(verbosity=2).run(suite)
    unittest.main()
