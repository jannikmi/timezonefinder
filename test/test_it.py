# -*- coding:utf-8 -*-
import timeit
import unittest
from math import floor, log10

import pytest

from auxiliaries import list_of_random_points, random_point
from timezonefinder.global_settings import INT2COORD_FACTOR
from timezonefinder.timezonefinder import TimezoneFinder

# from .auxiliaries import random_point, list_of_random_points


# number of points to test (in each test, realistic and random ones)
N = int(1e2)

# mistakes in these zones don't count as mistakes
excluded_zones_timezonefinder = []

tf = None
point_list = []
in_memory_mode = False


def eval_time_fct():
    global tf, point_list
    for point in point_list:
        tf.timezone_at(lng=point[0], lat=point[1])


def time_preprocess(time):
    valid_digits = 4
    zero_digits = abs(min(0, int(log10(time))))
    digits_to_print = zero_digits + valid_digits
    return str(round(time, digits_to_print)) + 's'


TEST_LOCATIONS = [
    # lat, lng, description, correct output
    (35.295953, -89.662186, 'Arlington, TN', 'America/Chicago'),
    (35.1322601, -90.0902499, 'Memphis, TN', 'America/Chicago'),
    (61.17, -150.02, 'Anchorage, AK', 'America/Anchorage'),
    (44.12, -123.22, 'Eugene, OR', 'America/Los_Angeles'),
    (42.652647, -73.756371, 'Albany, NY', 'America/New_York'),
    (55.743749, 37.6207923, 'Moscow', 'Europe/Moscow'),
    (34.104255, -118.4055591, 'Los Angeles', 'America/Los_Angeles'),
    (55.743749, 37.6207923, 'Moscow', 'Europe/Moscow'),
    (39.194991, -106.8294024, 'Aspen, Colorado', 'America/Denver'),
    (50.438114, 30.5179595, 'Kiev', 'Europe/Kiev'),
    (12.936873, 77.6909136, 'Jogupalya', 'Asia/Kolkata'),
    (38.889144, -77.0398235, 'Washington DC', 'America/New_York'),
    (59.932490, 30.3164291, 'St Petersburg', 'Europe/Moscow'),
    (50.300624, 127.559166, 'Blagoveshchensk', 'Asia/Yakutsk'),
    (42.439370, -71.0700416, 'Boston', 'America/New_York'),
    (41.84937, -87.6611995, 'Chicago', 'America/Chicago'),
    (28.626873, -81.7584514, 'Orlando', 'America/New_York'),
    (47.610615, -122.3324847, 'Seattle', 'America/Los_Angeles'),
    (51.499990, -0.1353549, 'London', 'Europe/London'),
    (51.256241, -0.8186531, 'Church Crookham', 'Europe/London'),
    (51.292215, -0.8002638, 'Fleet', 'Europe/London'),
    (48.868743, 2.3237586, 'Paris', 'Europe/Paris'),
    (22.158114, 113.5504603, 'Macau', 'Asia/Macau'),
    (56.833123, 60.6097054, 'Russia', 'Asia/Yekaterinburg'),
    (60.887496, 26.6375756, 'Salo', 'Europe/Helsinki'),
    (52.799992, -1.8524408, 'Staffordshire', 'Europe/London'),
    (5.016666, 115.0666667, 'Muara', 'Asia/Brunei'),
    (-41.466666, -72.95, 'Puerto Montt seaport', 'America/Santiago'),
    (34.566666, 33.0333333, 'Akrotiri seaport', 'Asia/Nicosia'),
    (37.466666, 126.6166667, 'Inchon seaport', 'Asia/Seoul'),
    (42.8, 132.8833333, 'Nakhodka seaport', 'Asia/Vladivostok'),
    (50.26, -5.051, 'Truro', 'Europe/London'),

    # test cases for hole handling:
    (41.0702284, 45.0036352, 'Aserbaid. Enklave', 'Asia/Yerevan'),
    (39.8417402, 70.6020068, 'Tajikistani Enklave', 'Asia/Dushanbe'),
    (47.7024174, 8.6848462, 'Busingen Ger', 'Europe/Busingen'),
    (46.2085101, 6.1246227, 'Genf', 'Europe/Zurich'),
    (-29.391356857138753, 28.50989829115889, 'Lesotho', 'Africa/Maseru'),
    (39.93143377877638, 71.08546583764965, 'usbekish enclave', 'Asia/Tashkent'),
    (40.0736177, 71.0411812, 'usbekish enclave', 'Asia/Tashkent'),
    (35.7396116, -110.15029571, 'Arizona Desert 1', 'America/Denver'),
    (36.4091869, -110.7520236, 'Arizona Desert 2', 'America/Phoenix'),
    (36.10230848, -111.1882385, 'Arizona Desert 3', 'America/Phoenix'),

    (50.26, -9.051, 'Far off Cornwall', None),

    # Not sure about the right result:
    # (68.3597987,-133.745786, 'America', 'America/Inuvik'),
]

# certain algorithm should give the same results for all normal test cases
TEST_LOCATIONS_CERTAIN = TEST_LOCATIONS + [
    # add some test cases for testing if None is being returned outside of timezone polygons
    # the polygons in the new data do not follow the coastlines any more
    # these tests are not meaningful at the moment

    # (40.7271, -73.98, 'Shore Lake Michigan', None),
    # (51.032593, 1.4082031, 'English Channel1',  None),
    # (50.9623651, 1.5732592, 'English Channel2',  None),
    # (55.5609615, 12.850585, 'Oresund Bridge1',  None),
    # (55.6056074, 12.7128568, 'Oresund Bridge2',  None),
]

TEST_LOCATIONS_PROXIMITY = [
    # the polygons in the new data do not follow the coastlines any more
    # proximity tests are not meaningful at the moment

    # (35.295953, -89.662186, 'Arlington, TN', 'America/Chicago'),
    # (33.58, -85.85, 'Memphis, TN', 'America/Chicago'),
    # (61.17, -150.02, 'Anchorage, AK', 'America/Anchorage'),
    # (40.7271, -73.98, 'Shore Lake Michigan', 'America/New_York'),
    # (51.032593, 1.4082031, 'English Channel1', 'Europe/London'),
    # (50.9623651, 1.5732592, 'English Channel2', 'Europe/Paris'),
    # (55.5609615, 12.850585, 'Oresund Bridge1', 'Europe/Stockholm'),
    # (55.6056074, 12.7128568, 'Oresund Bridge2', 'Europe/Copenhagen'),
]


class MainPackageTest(unittest.TestCase):
    in_memory_mode = False

    def print_tf_class_props(self):
        print("in memory mode:", self.in_memory_mode)
        if TimezoneFinder.using_numba():
            print('Numba: ON (precompiled functions in use)')
        else:
            print('Numba: OFF (precompiled functions NOT in use)')

    @classmethod
    def setUpClass(cls):
        # preparations which have to be made only once
        print("\nSTARTING PACKAGE TESTS\n\n")
        cls.print_tf_class_props(cls)

        global in_memory_mode
        in_memory_mode = cls.in_memory_mode
        t = timeit.timeit("TimezoneFinder(in_memory=in_memory_mode)", globals=globals(), number=1)
        print('startup time:', time_preprocess(t), '\n')

        cls.timezone_finder = TimezoneFinder(in_memory=cls.in_memory_mode)

        # create an array of points where timezone_finder finds something (realistic queries)
        print('collecting and storing', N, 'realistic points for the tests...')
        cls.realistic_points = []
        ps_for_10percent = int(N / 10)
        percent_done = 0

        i = 0
        while i < N:
            lng, lat = random_point()
            # a realistic point is a point where certain_timezone_at() finds something
            if cls.timezone_finder.certain_timezone_at(lng=lng, lat=lat):
                i += 1
                cls.realistic_points.append((lng, lat))
                if i % ps_for_10percent == 0:
                    percent_done += 10
                    print(percent_done, '%')

        print("Done.\n")

    def test_speed(self):
        print('\n\nSpeed Tests:\n-------------\n"realistic points": points included in a timezone\n')
        self.print_tf_class_props()

        def print_speed_test(type_of_points, list_of_points):
            global tf, point_list
            tf = self.timezone_finder
            point_list = list_of_points
            t = timeit.timeit("eval_time_fct()", globals=globals(), number=1)
            print('\ntesting', N, type_of_points)
            print('total time:', time_preprocess(t))
            pts_p_sec = len(list_of_points) / t
            exp = floor(log10(pts_p_sec))
            pts_p_sec = round(pts_p_sec / 10 ** exp, 1)  # normalize
            print('avg. points per second: {} * 10^{}'.format(pts_p_sec, exp))

        print_speed_test('realistic points', self.realistic_points)
        print_speed_test('random points', list_of_random_points(length=N))

    def test_shortcut_boundary(self):
        # at the boundaries of the shortcut grid (coordinate system) the algorithms should still be well defined!
        assert self.timezone_finder.timezone_at(lng=-180.0, lat=90.0) is None
        assert self.timezone_finder.timezone_at(lng=180.0, lat=90.0) is None
        assert self.timezone_finder.timezone_at(lng=180.0, lat=-90.0) == 'Antarctica/McMurdo'
        assert self.timezone_finder.timezone_at(lng=-180.0, lat=-90.0) == 'Antarctica/McMurdo'

        with pytest.raises(ValueError):
            self.timezone_finder.timezone_at(lng=180.0 + INT2COORD_FACTOR, lat=90.0)
            self.timezone_finder.timezone_at(lng=-180.0 - INT2COORD_FACTOR, lat=90.0 + INT2COORD_FACTOR)
            self.timezone_finder.timezone_at(lng=-180.0, lat=90.0 + INT2COORD_FACTOR)
            self.timezone_finder.timezone_at(lng=180.0 + INT2COORD_FACTOR, lat=-90.0)
            self.timezone_finder.timezone_at(lng=180.0, lat=-90.0 - INT2COORD_FACTOR)
            self.timezone_finder.timezone_at(lng=-180.0 - INT2COORD_FACTOR, lat=-90.0)
            self.timezone_finder.timezone_at(lng=-180.0 - INT2COORD_FACTOR, lat=-90.01 - INT2COORD_FACTOR)

    def test_kwargs_only(self):
        # calling timezonefinder fcts without keyword arguments should raise an error
        with pytest.raises(TypeError):
            self.timezone_finder.timezone_at(23.0, 42.0)
            self.timezone_finder.timezone_at(23.0, lng=42.0)
            self.timezone_finder.timezone_at(23.0, lat=42.0)

    def test_correctness(self):
        no_mistakes_made = True
        template = '{0:20s} | {1:20s} | {2:20s} | {3:2s}'

        print('\nresults timezone_at()')
        print(template.format('LOCATION', 'EXPECTED', 'COMPUTED', '=='))
        print('====================================================================')
        for (lat, lng, loc, expected) in TEST_LOCATIONS:
            computed = self.timezone_finder.timezone_at(lng=lng, lat=lat)

            if computed == expected:
                ok = 'OK'
            else:
                print(lat, lng)
                ok = 'XX'
                no_mistakes_made = False
            print(template.format(loc, str(expected), str(computed), ok))

        print('\ncertain_timezone_at():')
        print(template.format('LOCATION', 'EXPECTED', 'COMPUTED', 'Status'))
        print('====================================================================')
        for (lat, lng, loc, expected) in TEST_LOCATIONS_CERTAIN:
            computed = self.timezone_finder.certain_timezone_at(lng=lng, lat=lat)
            if computed == expected:
                ok = 'OK'
            else:
                print(lat, lng)
                ok = 'XX'
                no_mistakes_made = False
            print(template.format(loc, str(expected), str(computed), ok))

        print('\nclosest_timezone_at():')
        print(template.format('LOCATION', 'EXPECTED', 'COMPUTED', 'Status'))
        print('====================================================================')
        print('testing this function does not make sense any more, because the tz polygons do not follow the shoreline')
        for (lat, lng, loc, expected) in TEST_LOCATIONS_PROXIMITY:
            computed = self.timezone_finder.closest_timezone_at(lng=lng, lat=lat)
            if computed == expected:
                ok = 'OK'
            else:
                print(lat, lng)
                ok = 'XX'
                no_mistakes_made = False
            print(template.format(loc, str(expected), str(computed), ok))

        assert no_mistakes_made

    def test_overflow(self):
        longitude = -123.2
        latitude = 48.4
        # make numpy overflow runtime warning raise an error
        import numpy as np
        np.seterr(all='warn')
        import warnings
        warnings.filterwarnings('error')
        # must not raise a warning
        self.timezone_finder.certain_timezone_at(lat=float(latitude), lng=float(longitude))


class MainPackageTest2(MainPackageTest):
    in_memory_mode = True
