from __future__ import absolute_import, division, print_function, unicode_literals

import random
import time
from datetime import datetime

from tzwhere.tzwhere import tzwhere

# sets if tzwhere should be used with shapely
SHAPELY = True

duration_idle_mem_test = 5
duration_in_use_mem_test = 20


def random_point():
    # tzwhere does not work for points with higher latitude!
    return random.uniform(-180, 180), random.uniform(-84, 84)


def list_of_random_points(length):
    return [random_point() for i in range(length)]


if __name__ == '__main__':

    if SHAPELY:
        print('shapely: ON (tzwhere)')
    else:
        print('shapely: OFF (tzwhere)')

    print('Starting tz_where. This could take a while...')
    start_time = datetime.now()
    tz_where = tzwhere(shapely=SHAPELY)
    end_time = datetime.now()
    his_time = end_time - start_time

    print('\nStartup time:')
    print('tzwhere:', his_time)

    print("package is now available and idle.")
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
            result = tz_where.tzNameAt(lat, lng)
        seconds_passed = (datetime.now() - start_time).seconds

'''


   tzwhere:
        64,5MB shapely off, idle
        64,5 MB shapely off, in use
        111,7MB shapely on, idle
        450MB shapely on, in use



'''
