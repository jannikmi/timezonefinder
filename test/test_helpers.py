# -*- coding:utf-8 -*-
import unittest
from math import degrees, radians, sqrt

import numpy as np
import pytest

from auxiliaries import proto_test_case, random_point
from timezonefinder.global_settings import (
    COORD2INT_FACTOR, DECIMAL_PLACES_ACCURACY, DTYPE_FORMAT_F_NUMPY, DTYPE_FORMAT_H_NUMPY,
    DTYPE_FORMAT_SIGNED_I_NUMPY, INT2COORD_FACTOR, MAX_ALLOWED_COORD_VAL,
)


def poly_conversion_fct(coords):
    array = np.array(coords)
    array *= COORD2INT_FACTOR
    assert (not np.any(array > MAX_ALLOWED_COORD_VAL))
    array = np.ndarray.astype(array, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY)
    return array


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
        'convert2coords': helpers.convert2coords,
        'convert2coord_pairs': helpers.convert2coord_pairs,
    }
    print('\ntesting helpers.py functions...')

    def test_coord2shortcut(self):

        coord2shortcut = self.fct_dict['coord2shortcut']
        if coord2shortcut is None:
            print('test coord2shortcut skipped.')
            return

        def coord2shortcut_test_fct(input):
            (lng, lat) = input
            return coord2shortcut(lng, lat)

        data = [
            # shortcut numbering starts at "the top left" with x,y= 0,0
            # always (only) the "top" and "left" borders belong to a shortcut
            # the other borders belong to the next neighbouring shortcut
            ((-180.0, 90.0), (0, 0)),
            # shortcuts are constant for every 1 degree lng and 0.5 degree lat
            # defined with NR_SHORTCUTS_PER_LNG, NR_SHORTCUTS_PER_LAT in timezonefinder.file_converter
            ((-180.0 + INT2COORD_FACTOR, 90.0 - INT2COORD_FACTOR), (0, 0)),

            # shortcut numbering follows the lng, lat coordinate grid
            ((-179.0, 90.0), (1, 0)),
            ((-178.9, 89.9), (1, 0)),
            ((-180.0, 89.5), (0, 1)),
            ((-179.9, 89.4), (0, 1)),
            ((-180.0, 89.0), (0, 2)),
            ((-179.9, 88.9), (0, 2)),

            # shortcut numbering end at "the top left" with x,y= 359, 359
            # lng= 180.0 == -180.0
            # lat =-90.0 is not allowed (=bottom border of a shortcut)
            ((180.0 - INT2COORD_FACTOR, -90 + INT2COORD_FACTOR), (359, 359)),
            ((179.8, -89.8), (359, 359)),
        ]

        proto_test_case(data, coord2shortcut_test_fct)

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

    def test_convert2coord_pairs(self):

        convert2coord_pairs = self.fct_dict['convert2coord_pairs']
        if convert2coord_pairs is None:
            print('test convert2coord_pairs skipped.')
            return

        coord_values = [float(x) for x in range(-2, 3, 1)]
        coord_polygon = (coord_values, coord_values)
        polygon_int = poly_conversion_fct(coord_polygon)
        assert (convert2coord_pairs(polygon_int) == list(zip(coord_values, coord_values)))

    def test_convert2coords(self):

        convert2coords = self.fct_dict['convert2coords']
        if convert2coords is None:
            print('test convert2coord_pairs skipped.')
            return

        coord_values = [float(x) for x in range(-2, 3, 1)]
        coord_polygon = (coord_values, coord_values)
        polygon_int = poly_conversion_fct(coord_polygon)
        assert (convert2coords(polygon_int) == [coord_values, coord_values])

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

    def test_rectify_coords(self):
        rectify_coordinates = self.fct_dict['rectify_coordinates']
        if rectify_coordinates is None:
            print('test rectify_coordinates() skipped.')
            return

        with pytest.raises(ValueError):  # coords out of bounds
            rectify_coordinates(lng=180.0 + INT2COORD_FACTOR, lat=90.0)
            rectify_coordinates(lng=-180.0 - INT2COORD_FACTOR, lat=90.0 + INT2COORD_FACTOR)
            rectify_coordinates(lng=-180.0, lat=90.0 + INT2COORD_FACTOR)
            rectify_coordinates(lng=180.0 + INT2COORD_FACTOR, lat=-90.0)
            rectify_coordinates(lng=180.0, lat=-90.0 - INT2COORD_FACTOR)
            rectify_coordinates(lng=-180.0 - INT2COORD_FACTOR, lat=-90.0)
            rectify_coordinates(lng=-180.0 - INT2COORD_FACTOR, lat=-90.01 - INT2COORD_FACTOR)

        test_cases = [
            # input (lng, lat), expected output
            ((180.0, 30.0), (-180.0, 30.0)),
            ((100.0, -90), (100.0, -90 + INT2COORD_FACTOR)),
        ]

        for i, (inp, expected_output) in enumerate(test_cases):
            output = rectify_coordinates(*inp)
            assert output == expected_output, f'results do not match: {output} != {expected_output}'

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
            'convert2coords': helpers.convert2coords,
            'convert2coord_pairs': helpers.convert2coord_pairs,
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
            'convert2coords': None,
            'convert2coord_pairs': None,
        }
        print('\nNumba installation NOT found.')


if __name__ == '__main__':
    # suite = unittest.TestLoader().loadTestsFromTestCase(HelperTest)
    # unittest.TextTestRunner(verbosity=2).run(suite)
    unittest.main()
