from __future__ import absolute_import, division, print_function, unicode_literals

import random
import unittest
from math import degrees, radians, sqrt

from six.moves import range

from timezonefinder.helpers import (
    all_the_same, coord2int, distance_to_point_on_equator, distance_to_polygon, distance_to_polygon_exact, haversine,
    inside_polygon,
)


def random_point():
    # tzwhere does not work for points with more latitude!
    return random.uniform(-180, 180), random.uniform(-84, 84)


def list_of_random_points(length):
    return [random_point() for i in range(length)]


class HelperTest(unittest.TestCase):
    def test_inside_polygon(self):

        polygon_test_cases = [
            ([0.5, 0.5, -0.5, -0.5, 0.5], [0.0, 0.5, 0.5, -0.5, -0.5]),

        ]
        p_test_cases = [

            # (x,y),
            # inside
            (0, 0.000),
            #
            # # outside
            (-1, 1),
            (0, 1),
            (1, 1),
            (-1, 0),
            (1, 0),
            (-1, -1),
            (0, -1),
            (1, -1),

            # on the line test cases
            # inclusion is not defined if point lies on the line
            # (0.0, -0.5),
            # (0, 0.5),
            # (-0.5, 0),
            # (0.5, 0),
        ]
        expected_results = [
            (True, False, False, False, False, False, False, False, False),
            # (True, True, True, True)
        ]

        n = 0
        for coords in polygon_test_cases:
            i = 0
            for x, y in p_test_cases:
                assert inside_polygon(x, y, coords) == expected_results[n][i]
                i += 1
            n += 1

    def test_all_the_same(self):

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
            assert all_the_same(pointer, length, id_list) == expected_results[i]
            i += 1

    def test_distance_computation(self):

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
            if abs(hav_result - result) > 0.000001:
                raise AssertionError(i, 'should be equal:', hav_result, result, rnd_point, lng_rnd_point2)

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

        print(km2deg(haversine(x_rad, y_rad, p1_lng_rad, p1_lat_rad)))
        assert km2deg(haversine(x_rad, y_rad, p1_lng_rad, p1_lat_rad)) == 1

        distance_exact = distance_to_polygon_exact(x_rad, y_rad, len(x_coords), points, trans_points)
        print(km2deg(distance_exact))
        assert km2deg(distance_exact) == 0.5
        print('=====')
        distance = distance_to_polygon(x_rad, y_rad, len(x_coords), points)
        print(km2deg(distance))
        assert abs(km2deg(distance) - sqrt(2) / 2) < 0.00001
