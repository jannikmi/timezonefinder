from __future__ import absolute_import, division, print_function, unicode_literals

import random
import unittest
from datetime import datetime

from timezonefinder.timezonefinder import TimezoneFinder
from tzwhere.tzwhere import tzwhere

# number of points to test (in each test, realistic and random ones)
N = 1000

# number of times the n number of random points should be tested in the speedtest
RUNS = 1

SHAPELY = False

if SHAPELY:
    print('shapely: ON (tzwhere)')
else:
    print('shapely: OFF (tzwhere)')

# mistakes in these zones dont count as mistakes
excluded_zones_timezonefinder = []
# ['Asia/Srednekolymsk', 'Asia/Chita', 'Europe/Astrakhan', ]
# 'Africa/Johannesburg', "America/Phoenix", 'America/Denver', ]
excluded_zones_tzwhere = []


# 'Asia/Yakutsk', 'Asia/Magadan', 'Europe/Volgograd', ]


# 'Africa/Maseru', "America/Phoenix", 'America/Denver', ]


def random_point():
    # tzwhere does not work for points with more latitude!
    return random.uniform(-180, 180), random.uniform(-84, 84)


class PackageEqualityTest(unittest.TestCase):
    # do the preparations which have to be made only once

    if TimezoneFinder.using_numba():
        print('Numba: ON (timezonefinder)')
    else:
        print('Numba: OFF (timezonefinder)')

    timezone_finder = TimezoneFinder()

    tz_where = tzwhere(shapely=SHAPELY)

    # create an array of n points where tzwhere finds something (realistic queries)
    print('collecting', N, 'realistic points...')
    realistic_points = []
    real_ps_results_tzwhere = []
    real_ps_results_certain = []

    ps_for_10percent = int(N / 10)
    percent_done = 0

    i = 0
    while i < N:
        point = random_point()
        # lng, lat = random_point()
        # result_certain = tz_where.tzNameAt(lat, lng)
        result_certain = timezone_finder.certain_timezone_at(*point)
        if result_certain is not None:
            lng = point[0]
            lat = point[1]
            result = tz_where.tzNameAt(lat, lng)
            if result is not None:
                i += 1
                realistic_points.append(point)
                real_ps_results_certain.append(result_certain)
                real_ps_results_tzwhere.append(result)

                if i % ps_for_10percent == 0:
                    percent_done += 10
                    print(percent_done, '%')

    print("Done.")

    # Test Points for equality-test of the algorithms:
    equality_test_data = {

        # invalid cause this is no zone so also no ID (-52.9883809, 29.6183884): '',

        (-44.7402611, 70.2989263): 'America/Godthab',

        (-4.8663325, 40.0663485): 'Europe/Madrid',

        (-60.968888, -3.442172): 'America/Manaus',

        (14.1315716, 2.99999): 'Africa/Douala',

        (14.1315716, 0.2350623): 'Africa/Brazzaville',

        (-71.9996885, -52.7868679): 'America/Santiago',

        (-152.4617352, 62.3415036): 'America/Anchorage',

        (37.0720767, 55.74929): 'Europe/Moscow',

        (103.7069307, 1.3150701): 'Asia/Singapore',

        (12.9125913, 50.8291834): 'Europe/Berlin',

        (-106.1706459, 23.7891123): 'America/Mazatlan',

        # (-110.29080, 35.53587): 'America/Phoenix',

        (33, -84): 'uninhabited',

    }

    def test_correctness(self):
        # Test correctness
        print('\ntest correctness:')
        print('Results:\n[point, target, tzwere is correct, timezonefinder is correct]')
        for point, tz_name in self.equality_test_data.items():
            lng = point[0]
            lat = point[1]
            my_result = self.timezone_finder.timezone_at(lng, lat)
            his_result = self.tz_where.tzNameAt(latitude=lat, longitude=lng)
            print(point, tz_name, my_result == tz_name, his_result == tz_name)
            assert my_result == tz_name

            assert his_result == tz_name

    def test_equality(self):
        # Test the equality if the two algorithms

        mistakes = 0
        print('\ntesting', N, 'realistic points')
        print('MISMATCHES:')

        i = 0
        for p in self.realistic_points:

            # his_result = self.tz_where.tzNameAt(latitude=p[1], longitude=p[0])
            his_result = self.real_ps_results_tzwhere[i]
            i += 1

            my_result = self.timezone_finder.timezone_at(*p)
            if my_result != his_result:

                if his_result in excluded_zones_tzwhere and my_result in excluded_zones_timezonefinder:
                    print(p, my_result, his_result, '(not counted, see issue section)')
                else:
                    mistakes += 1
                    # mistake_point_nrs.append(i)
                    print(p, my_result, his_result)
                    # raise AssertionError('There was a mistake')

        print('\ntesting', N, 'random points')
        print('MISMATCHES:')

        i = 0
        while i < N:
            p = random_point()

            his_result = self.tz_where.tzNameAt(latitude=p[1], longitude=p[0])

            if his_result is not None:
                i += 1
                my_result = self.timezone_finder.timezone_at(*p)

                if my_result != his_result:
                    if his_result in excluded_zones_tzwhere and my_result in excluded_zones_timezonefinder:
                        print(p, my_result, his_result, '(not counted, see issue section)')
                    else:
                        mistakes += 1
                        # mistake_point_nrs.append(i)
                        print(p, my_result, his_result)
                        # raise AssertionError('There was a mistake')

                        # assert my_result == his_result

        print('\nin', 2 * N, 'tries', mistakes, 'mismatches were made')
        fail_percentage = mistakes * 100 / (2 * N)
        # Cannot be tested strictly because data is different now
        assert fail_percentage < 10.0

    def test_equality_certain(self):
        # Test the equality of the tzwhere with the certain_timezone_at() algorithms
        # they should both yield exactly the same results

        mistakes = 0
        print('\ntesting certain_timezone_at():')
        print('\ntesting', N, 'realistic points')
        print('MISMATCHES:')

        i = 0
        for his_result in self.real_ps_results_tzwhere:
            my_result = self.real_ps_results_certain[i]

            if my_result != his_result:
                if his_result in excluded_zones_tzwhere and my_result in excluded_zones_timezonefinder:
                    print(self.realistic_points[i], my_result, his_result, '(not counted, see issue section)')
                else:
                    mistakes += 1
                    # mistake_point_nrs.append(i)
                    print(self.realistic_points[i], my_result, his_result)
                    # raise AssertionError('There was a mistake')

            i += 1

        print('\ntesting', N, 'random points')
        print('MISMATCHES:')

        i = 0
        while i < N:
            p = random_point()
            my_result = self.timezone_finder.certain_timezone_at(*p)

            his_result = self.tz_where.tzNameAt(latitude=p[1], longitude=p[0])

            i += 1

            if my_result != his_result:
                if his_result in excluded_zones_tzwhere and my_result in excluded_zones_timezonefinder:
                    print(p, my_result, his_result, '(not counted, see issue section)')
                else:
                    mistakes += 1
                    # mistake_point_nrs.append(i)
                    print(p, my_result, his_result)
                    # raise AssertionError('There was a mistake')

        print('\nin', 2 * N, 'tries', mistakes, 'mismatches were made')
        fail_percentage = mistakes * 100 / (2 * N)
        print('fail percentage is:', fail_percentage)

        # Cannot be tested strictly because data is different now
        assert fail_percentage < 10.0

    def test_speed(self):

        def check_speed_his_algor(points):
            start_time = datetime.now()

            # old algorithm (tzwhere)
            for point in points:
                self.tz_where.tzNameAt(latitude=point[1], longitude=point[0])

            end_time = datetime.now()

            return end_time - start_time

            # test my first algorithm (boundaries, csv)

            # test second algorithm ( double, .bin)

        def check_speed_my_algor(points):
            # test final algorithm ( long long, .bin)

            start_time = datetime.now()

            for point in points:
                self.timezone_finder.timezone_at(*point)

            end_time = datetime.now()

            return end_time - start_time

        runs = 1

        my_time = check_speed_my_algor(self.realistic_points)
        his_time = check_speed_his_algor(self.realistic_points)
        for i in range(runs - 1):
            my_time += check_speed_my_algor(self.realistic_points)
            his_time += check_speed_his_algor(self.realistic_points)

        try:
            my_time /= RUNS
            his_time /= RUNS

            print('')
            print('\n\nTIMES for ', N, 'realistic queries:')
            print('tzwhere:', his_time)
            print('timezonefinder:', my_time)

            print(round(his_time / my_time, 2), 'times faster')
        except TypeError:
            pass

            # assert his_time > my_time

    def test_speed_random(self):

        def check_speed_his_algor(points):
            start_time = datetime.now()

            # old algorithm (tzwhere)
            for point in points:
                self.tz_where.tzNameAt(latitude=point[1], longitude=point[0])

            end_time = datetime.now()

            return end_time - start_time

            # test my first algorithm (boundaries, csv)

            # test second algorithm ( double, .bin)

        def check_speed_my_algor(points):
            # test final algorithm ( long long, .bin)

            start_time = datetime.now()

            for point in points:
                self.timezone_finder.timezone_at(*point)

            end_time = datetime.now()

            return end_time - start_time

        random_points = []

        for i in range(N):
            random_points.append(random_point())

        my_time = check_speed_my_algor(random_points)
        his_time = check_speed_his_algor(random_points)
        for i in range(RUNS - 1):
            my_time += check_speed_my_algor(random_points)
            his_time += check_speed_his_algor(random_points)

        try:
            my_time /= RUNS
            his_time /= RUNS

            print('')
            print('\n\nTIMES for ', N, 'random queries:')
            print('tzwhere:', his_time)
            print('timezonefinder:', my_time)

            print(round(his_time / my_time, 2), 'times faster')
        except TypeError:
            pass

            # assert his_time > my_time

    def test_startup_time(self):

        def check_speed_his_algor():
            start_time = datetime.now()

            tz_where = tzwhere()

            end_time = datetime.now()

            tz_where.tzNameAt(latitude=13.3, longitude=53.2)

            return end_time - start_time

        def check_speed_my_algor():
            start_time = datetime.now()

            timezonefinder = TimezoneFinder()

            end_time = datetime.now()

            timezonefinder.timezone_at(13.3, 53.2)

            return end_time - start_time

        my_time = check_speed_my_algor()
        his_time = check_speed_his_algor()

        print('\nStartup times:')
        print('tzwhere:', his_time)
        print('timezonefinder:', my_time)

        try:
            print(round(his_time / my_time, 2), 'times faster')
        except TypeError:
            pass

        assert his_time > my_time
