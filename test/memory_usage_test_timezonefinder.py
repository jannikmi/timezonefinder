from __future__ import absolute_import, division, print_function, unicode_literals

import random
import time
from datetime import datetime

from timezonefinder.timezonefinder import TimezoneFinder


def random_point():
    # tzwhere does not work for points with more latitude!
    return random.uniform(-180, 180), random.uniform(-84, 84)


def list_of_random_points(length):
    return [random_point() for i in range(length)]


duration_idle_mem_test = 20
duration_in_use_mem_test = 20

if __name__ == '__main__':

    if TimezoneFinder.using_numba():
        print('Numba: ON (timezonefinder)')
    else:
        print('Numba: OFF (timezonefinder)')

    start_time = datetime.now()
    timezone_finder = TimezoneFinder()
    end_time = datetime.now()
    my_time = end_time - start_time

    print('\nStartup time:')
    print('timezonefinder:', my_time)

    print("Check the memory usage of python in your process list (Task Manager, Activity Manager...)")
    print("time remaining:")
    while duration_idle_mem_test > 0:
        print(duration_idle_mem_test, 's')
        time.sleep(1)
        duration_idle_mem_test -= 1

    print("package is now in use.")
    print("Check the memory usage of python in your process list (Task Manager, Activity Manager)")
    seconds_registered = 0
    start_time = datetime.now()
    print("seconds passed:")
    seconds_passed = 0
    while seconds_passed < duration_in_use_mem_test:
        if seconds_passed > seconds_registered:
            print(seconds_passed)
            seconds_registered = seconds_passed
        point_list = list_of_random_points(100)
        for lng, lat in point_list:
            result = timezone_finder.timezone_at(lng=lng, lat=lat)
        seconds_passed = (datetime.now() - start_time).seconds

'''
    Peak RAM usage:

    timezonefinder:
        16,4MB Numba off, in use
        15,4MB numba off, idle
'''
