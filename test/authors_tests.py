from __future__ import absolute_import, division, print_function, unicode_literals

import random
import unittest

from timezonefinder import TimezoneFinder

from timezonefinder.timezone_names import timezone_names

from pytz import timezone
from pytz.exceptions import UnknownTimeZoneError


def random_point():
    # tzwhere does not work for points with more latitude!
    return random.uniform(-180, 180), random.uniform(-84, 84)


class PackageEqualityTest(unittest.TestCase):
    # do the preparations which have to be made only once
    timezone_finder = TimezoneFinder()
    # tz_where = tzwhere()

    # number of points to test (in each test, realistic and random ones)
    n = 1000

    # number of times the n number of random points should be tested in the speedtest
    runs = 1

    # create an array of n points where tzwhere finds something (realistic queries)
    print('collecting', n, 'realistic points...')
    realistic_points = []
    realistic_points_results = []

    i = 0
    while i < n:
        point = random_point()
        # lng, lat = random_point()
        # result = tz_where.tzNameAt(lat, lng)
        result = timezone_finder.certain_timezone_at(*point)
        if result is not None:
            realistic_points.append(point)
            i += 1

            # lng = point[0]
            # lat = point[1]
            # result = tz_where.tzNameAt(lat, lng)
            # if result is not None:
            #     i += 1
            #     realistic_points.append(point)
            #     realistic_points_results.append(result)

    print('Done.')

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

        (33, -84): 'uninhabited',

    }

    def setUp(self):
        # preparations for every test case
        pass

    def tearDown(self):
        pass

    '''
    def test_equality_endless(self):
    # Test the equality of the two algorithms

    print('Endlessly testing for equality:')
    # print('valid points checked:')
    i = 0

    while 1:
        point = random_point()

        my_result_certain = self.timezone_finder.certain_timezone_at(*point)

        if my_result_certain is not None:

            i += 1
            if i % 1000 == 0:
                print(i)

            his_result = self.tz_where.tzNameAt(latitude=point[1], longitude=point[0])
            my_result = self.timezone_finder.timezone_at(point[0], point[1])
            if my_result != his_result or my_result != my_result_certain:
                output_file = open('found_missmatches.txt', 'a')
                print('mistake at point:', i , point)
                print('my_result:', my_result, my_result_certain, 'should be equal to', his_result)
                output_file.write(str([i,point,my_result,my_result_certain,his_result]))
                output_file.write('\n')
                output_file.close()

                    # assert my_result == his_result

            # print('mistake made when testing the ', mistake_after, 'th non empty random point')
    '''

    def test_timezone_names(self):
        """
        Test if pytz can create a timezone object from all the listed tz_names
        :return:
        """

        unknown_timezones = []

        for timezone_name in timezone_names:
            try:
                timezone(timezone_name)

            except UnknownTimeZoneError:
                unknown_timezones.append(timezone_name)

        print('\nThese timezones are currently in use, but cannot be recognized by pytz:')
        print(unknown_timezones)

# if __name__ == '__main__':
#     PackageEqualityTest().test_equality_endless()
