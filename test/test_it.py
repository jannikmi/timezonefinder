# -*- coding:utf-8 -*-
import timeit
import unittest
from math import floor, log10
from os.path import abspath, join, pardir

import pytest

from auxiliaries import list_of_random_points, random_point
from timezonefinder.global_settings import INT2COORD_FACTOR, PACKAGE_NAME
from timezonefinder.timezonefinder import TimezoneFinder, TimezoneFinderL

# number of points to test (in each test, realistic and random ones)
N = int(1e2)

# mistakes in these zones don't count as mistakes
excluded_zones_timezonefinder = []

tf = None
point_list = []
in_memory_mode = False
class_under_test = TimezoneFinder


def eval_time_fct():
    global tf, point_list
    for point in point_list:
        tf.timezone_at(lng=point[0], lat=point[1])


def time_preprocess(time):
    valid_digits = 4
    zero_digits = abs(min(0, int(log10(time))))
    digits_to_print = zero_digits + valid_digits
    return str(round(time, digits_to_print)) + 's'


EASY_TEST_LOCATIONS = [
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
]

# certain algorithm should give the same results for all normal test cases
TEST_LOCATIONS = EASY_TEST_LOCATIONS + [
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
    (37.81, -122.35, 'San Francisco Bay', 'America/Los_Angeles'),

    (65.2, 179.9999, 'lng 180', 'Asia/Anadyr'),
    # lng 180 == -180
    # disabled because they fail for certain_timezone_at()
    # <- right on the timezone boundary polygon edge, return value uncertain (None in this case)
    # being tested in test_helpers.py
    # (65.2, 180.0, 'lng 180', 'Asia/Anadyr'),
    # (65.2, -180.0, 'lng -180', 'Asia/Anadyr'),

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
TEST_LOCATIONS_CERTAIN = TEST_LOCATIONS + [
    # add some test cases for testing if None is being returned outside of timezone polygons
    # the polygons in the new data do not follow the coastlines any more
    # these tests are not meaningful at the moment
    #
    # (40.7271, -73.98, 'Shore Lake Michigan', None),
    # (51.032593, 1.4082031, 'English Channel1',  None),
    # (50.9623651, 1.5732592, 'English Channel2',  None),
    # (55.5609615, 12.850585, 'Oresund Bridge1',  None),
    # (55.6056074, 12.7128568, 'Oresund Bridge2',  None),
]

TEST_LOCATIONS_PROXIMITY = [
    # the polygons in the new data do not follow the coastlines any more
    # proximity tests are not meaningful at the moment

    (35.295953, -89.662186, 'Arlington, TN', 'America/Chicago'),
    (33.58, -85.85, 'Memphis, TN', 'America/Chicago'),
    (61.17, -150.02, 'Anchorage, AK', 'America/Anchorage'),
    (40.7271, -73.98, 'Shore Lake Michigan', 'America/New_York'),
    (51.032593, 1.4082031, 'English Channel1', 'Europe/London'),
    # (50.9623651, 1.5732592, 'English Channel2', 'Europe/Paris'),
    (55.5609615, 12.850585, 'Oresund Bridge1', 'Europe/Stockholm'),
    # (55.6056074, 12.7128568, 'Oresund Bridge2', 'Europe/Copenhagen'),
]


# tests for TimezonefinderL class
class BaseTimezoneFinderClassTest(unittest.TestCase):
    in_memory_mode = False
    bin_file_dir = None
    class_under_test = TimezoneFinderL
    realistic_pt_fct_name = 'timezone_at'
    test_locations = EASY_TEST_LOCATIONS

    def print_tf_class_props(self):
        print('\n\ntest properties:')
        print(f'testing class {self.class_under_test}')
        if self.class_under_test.using_numba():
            print('using_numba()==True (JIT compiled functions in use)')
        else:
            print('using_numba()==False (JIT compiled functions NOT in use)')
        print(f"in_memory={self.in_memory_mode}")
        print(f"file location={self.bin_file_dir}\n")

    @classmethod
    def setUpClass(cls):
        # preparations which have to be made only once
        cls.print_tf_class_props(cls)

        global in_memory_mode, class_under_test
        in_memory_mode = cls.in_memory_mode
        class_under_test = cls.class_under_test
        t = timeit.timeit("class_under_test(in_memory=in_memory_mode)", globals=globals(), number=10)
        print('startup time:', time_preprocess(t), '\n')

        cls.test_instance = cls.class_under_test(bin_file_location=cls.bin_file_dir, in_memory=cls.in_memory_mode)

        # create an array of points where timezone_finder finds something (realistic queries)
        print('collecting and storing', N, 'realistic points for the tests...')
        cls.realistic_points = []
        ps_for_10percent = int(N / 10)
        percent_done = 0

        i = 0
        realistic_pt_fct = getattr(cls.test_instance, cls.realistic_pt_fct_name)
        while i < N:
            lng, lat = random_point()
            # a realistic point is a point where certain_timezone_at() finds something
            if realistic_pt_fct(lng=lng, lat=lat):
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
            tf = self.test_instance
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
        assert self.test_instance.timezone_at(lng=-180.0, lat=90.0) is None
        assert self.test_instance.timezone_at(lng=180.0, lat=90.0) is None
        assert self.test_instance.timezone_at(lng=180.0, lat=-90.0) == 'Antarctica/McMurdo'
        assert self.test_instance.timezone_at(lng=-180.0, lat=-90.0) == 'Antarctica/McMurdo'

        with pytest.raises(ValueError):
            self.test_instance.timezone_at(lng=180.0 + INT2COORD_FACTOR, lat=90.0)
            self.test_instance.timezone_at(lng=-180.0 - INT2COORD_FACTOR, lat=90.0 + INT2COORD_FACTOR)
            self.test_instance.timezone_at(lng=-180.0, lat=90.0 + INT2COORD_FACTOR)
            self.test_instance.timezone_at(lng=180.0 + INT2COORD_FACTOR, lat=-90.0)
            self.test_instance.timezone_at(lng=180.0, lat=-90.0 - INT2COORD_FACTOR)
            self.test_instance.timezone_at(lng=-180.0 - INT2COORD_FACTOR, lat=-90.0)
            self.test_instance.timezone_at(lng=-180.0 - INT2COORD_FACTOR, lat=-90.01 - INT2COORD_FACTOR)

    def test_kwargs_only(self):
        # calling timezonefinder fcts without keyword arguments should raise an error
        with pytest.raises(TypeError):
            self.test_instance.timezone_at(23.0, 42.0)
            self.test_instance.timezone_at(23.0, lng=42.0)
            self.test_instance.timezone_at(23.0, lat=42.0)

    def test_correctness(self):
        no_mistakes_made = True
        template = '{0:20s} | {1:20s} | {2:20s} | {3:2s}'

        print('\nresults timezone_at()')
        print(template.format('LOCATION', 'EXPECTED', 'COMPUTED', '=='))
        print('====================================================================')
        for (lat, lng, loc, expected) in self.test_locations:
            computed = self.test_instance.timezone_at(lng=lng, lat=lat)

            if computed == expected:
                ok = 'OK'
            else:
                print(lat, lng)
                ok = 'XX'
                no_mistakes_made = False
            print(template.format(loc, str(expected), str(computed), ok))

        assert no_mistakes_made

        return no_mistakes_made, template


class BaseClassTestMEM(BaseTimezoneFinderClassTest):
    in_memory_mode = True


abs_default_path = abspath(join(__file__, pardir, pardir, PACKAGE_NAME))


class BaseClassTestDIR(BaseTimezoneFinderClassTest):
    # point to a dir where all bin files are located:
    bin_file_dir = abs_default_path


class BaseClassTestMEMDIR(BaseTimezoneFinderClassTest):
    in_memory_mode = True
    bin_file_dir = abs_default_path


# tests for Timezonefinder class
class TimezonefinderClassTest(BaseTimezoneFinderClassTest):
    class_under_test = TimezoneFinder
    realistic_pt_fct_name = 'certain_timezone_at'
    test_locations = TEST_LOCATIONS

    def test_kwargs_only(self):
        super(TimezonefinderClassTest, self).test_kwargs_only()

        with pytest.raises(TypeError):
            self.test_instance.certain_timezone_at(23.0, 42.0)
            self.test_instance.certain_timezone_at(23.0, lng=42.0)
            self.test_instance.certain_timezone_at(23.0, lat=42.0)

            self.test_instance.closest_timezone_at(23.0, 42.0)
            self.test_instance.closest_timezone_at(23.0, lng=42.0)
            self.test_instance.closest_timezone_at(23.0, lat=42.0)

    def test_correctness(self):
        no_mistakes_made, template = super(TimezonefinderClassTest, self).test_correctness()

        print('\ncertain_timezone_at():')
        print(template.format('LOCATION', 'EXPECTED', 'COMPUTED', 'Status'))
        print('====================================================================')
        for (lat, lng, loc, expected) in TEST_LOCATIONS_CERTAIN:
            computed = self.test_instance.certain_timezone_at(lng=lng, lat=lat)
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
            computed = self.test_instance.closest_timezone_at(lng=lng, lat=lat)
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
        self.test_instance.certain_timezone_at(lat=float(latitude), lng=float(longitude))


class TimezonefinderClassTestMEM(TimezonefinderClassTest):
    in_memory_mode = True


class TimezonefinderClassTestDIR(BaseTimezoneFinderClassTest):
    # point to a dir where all bin files are located:
    bin_file_dir = abs_default_path


class TimezonefinderClassTestMEMDIR(BaseTimezoneFinderClassTest):
    in_memory_mode = True
    bin_file_dir = abs_default_path
