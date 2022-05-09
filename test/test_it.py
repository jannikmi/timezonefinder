# -*- coding:utf-8 -*-
import json
import timeit
import unittest
from math import floor, log10
from os.path import abspath, join, pardir
from test.auxiliaries import list_equal, list_of_random_points, random_point
from test.locations import BASIC_TEST_LOCATIONS, BOUNDARY_TEST_CASES, TEST_LOCATIONS
from typing import List, Optional

import pytest

from timezonefinder.configs import INT2COORD_FACTOR, TIMEZONE_NAMES_FILE
from timezonefinder.timezonefinder import (
    AbstractTimezoneFinder,
    TimezoneFinder,
    TimezoneFinderL,
)
from timezonefinder.utils import is_ocean_timezone

DEBUG = False
# more extensive testing (e.g. get geometry for every single zone), switch off for CI/CD
# DEBUG = True

PACKAGE_NAME = "timezonefinder"

# number of points to test (in each test, on land and random ones)
N = int(1e1)

class_under_test = TimezoneFinder
tf: AbstractTimezoneFinder = class_under_test()
point_list = []
in_memory_mode = False

RESULT_TEMPLATE = "{0:25s} | {1:20s} | {2:20s} | {3:2s}"


def eval_time_fct():
    global tf, point_list
    for point in point_list:
        tf.timezone_at(lng=point[0], lat=point[1])


def time_preprocess(time):
    valid_digits = 4
    zero_digits = abs(min(0, int(log10(time))))
    digits_to_print = zero_digits + valid_digits
    return str(round(time, digits_to_print)) + "s"


def ocean2land(test_locations):
    for lat, lng, description, expected in test_locations:
        if is_ocean_timezone(expected):
            expected = None
        yield lat, lng, description, expected


def check_geometry(geometry_obj: List):
    coords = geometry_obj[0][0]
    assert (
        len(coords) == 2
    ), "the polygon does not consist of two latitude longitude lists"
    x_coords, y_coords = coords
    nr_x_coords = len(x_coords)
    nr_y_coords = len(y_coords)
    assert nr_x_coords > 2, "a polygon must consist of more than 2 coordinates"
    assert (
        nr_x_coords == nr_y_coords
    ), "the amount of x and y coordinates (lng, lat) must be equal"


def check_pairwise_geometry(geometry_obj: List):
    # list of all coord pairs of the first polygon
    cord_pairs = geometry_obj[0][0]
    assert len(cord_pairs) > 2, "a polygon must consist of more than 2 coordinates"
    first_coord_pair = cord_pairs[0]
    assert (
        len(first_coord_pair) == 2
    ), "the polygon does not consist of coordinate pairs as expected."


# tests for TimezonefinderL class
class BaseTimezoneFinderClassTest(unittest.TestCase):
    in_memory_mode = False
    bin_file_dir = None
    class_under_test = TimezoneFinderL
    on_land_pt_fct_name = "timezone_at"
    test_locations = BASIC_TEST_LOCATIONS

    def test_using_numba(self):
        numba_installed = False
        try:
            import numba

            numba_installed = True
        except ImportError:
            pass

        if numba_installed:
            try:
                from numba import b1, f8, i2, i4, njit, typeof, u2
            except ImportError as exc:
                raise ValueError("numba import failed:", exc) from exc

        assert self.test_instance.using_numba() == numba_installed

    def print_tf_class_props(self):
        print("\n\ntest properties:")
        print(f"testing class {self.class_under_test}")
        if self.class_under_test.using_numba():
            print("using_numba()==True (JIT compiled functions in use)")
        else:
            print("using_numba()==False (JIT compiled functions NOT in use)")
        print(f"in_memory={self.in_memory_mode}")
        print(f"file location={self.bin_file_dir}\n")

    @classmethod
    def setUpClass(cls):
        # preparations which have to be made only once
        cls.print_tf_class_props(cls)

        global in_memory_mode, class_under_test
        in_memory_mode = cls.in_memory_mode
        class_under_test = cls.class_under_test
        t = timeit.timeit(
            "class_under_test(in_memory=in_memory_mode)", globals=globals(), number=10
        )
        print("startup time:", time_preprocess(t), "\n")

        cls.test_instance = cls.class_under_test(
            bin_file_location=cls.bin_file_dir, in_memory=cls.in_memory_mode
        )

        # create an array of points where timezone_finder finds something (on_land queries)
        print("collecting and storing", N, "on land points for the tests...")
        cls.on_land_points = []
        ps_for_10percent = int(N / 10)
        percent_done = 0

        i = 0
        on_land_pt_fct = getattr(cls.test_instance, cls.on_land_pt_fct_name)
        while i < N:
            lng, lat = random_point()
            if on_land_pt_fct(lng=lng, lat=lat):
                i += 1
                cls.on_land_points.append((lng, lat))
                if i % ps_for_10percent == 0:
                    percent_done += 10
                    print(percent_done, "%")

        print("Done.\n")

    def test_speed(self):
        print(
            '\n\nSpeed Tests:\n-------------\n"on land points": points included in a timezone\n'
        )
        self.print_tf_class_props()

        def print_speed_test(type_of_points, list_of_points):
            global tf, point_list
            tf = self.test_instance
            point_list = list_of_points
            t = timeit.timeit("eval_time_fct()", globals=globals(), number=1)
            print("\ntesting", N, type_of_points)
            print("total time:", time_preprocess(t))
            pts_p_sec = len(list_of_points) / t
            exp = floor(log10(pts_p_sec))
            pts_p_sec = round(pts_p_sec / 10**exp, 1)  # normalize
            print("avg. points per second: {} * 10^{}".format(pts_p_sec, exp))

        print_speed_test("on land points", self.on_land_points)
        print_speed_test("random points", list_of_random_points(length=N))

    def check_boundary(self, lng, lat, expected: Optional[str] = ""):
        # at the boundaries of the coordinate system the algorithms should still be well defined!

        print(
            [
                self.test_instance.zone_name_from_poly_id(p)
                for p in self.test_instance.get_shortcut_polys(lng=lng, lat=lat)
            ]
        )

        result = self.test_instance.timezone_at(lng=lng, lat=lat)
        if isinstance(expected, str) and len(expected) == 0:
            # zone_name="" is interpreted as "don't care"
            return
        assert result == expected

    def test_shortcut_boundary_validity(self):
        for lng, lat, _expected in BOUNDARY_TEST_CASES:
            self.check_boundary(lng, lat)

        with pytest.raises(ValueError):
            self.check_boundary(lng=180.0 + INT2COORD_FACTOR, lat=90.0)
            self.check_boundary(
                lng=-180.0 - INT2COORD_FACTOR, lat=90.0 + INT2COORD_FACTOR
            )
            self.check_boundary(lng=-180.0, lat=90.0 + INT2COORD_FACTOR)
            self.check_boundary(lng=180.0 + INT2COORD_FACTOR, lat=-90.0)
            self.check_boundary(lng=180.0, lat=-90.0 - INT2COORD_FACTOR)
            self.check_boundary(lng=-180.0 - INT2COORD_FACTOR, lat=-90.0)
            self.check_boundary(
                lng=-180.0 - INT2COORD_FACTOR, lat=-90.01 - INT2COORD_FACTOR
            )

    def test_kwargs_only(self):
        # calling timezonefinder fcts without keyword arguments should raise an error
        with pytest.raises(TypeError):
            self.test_instance.timezone_at(23.0, 42.0)
            self.test_instance.timezone_at(23.0, lng=42.0)
            self.test_instance.timezone_at(23.0, lat=42.0)

            self.test_instance.timezone_at_land(23.0, 42.0)
            self.test_instance.timezone_at_land(23.0, lng=42.0)
            self.test_instance.timezone_at_land(23.0, lat=42.0)

    @staticmethod
    def run_location_tests(test_fct, test_data):
        no_mistakes_made = True
        print(RESULT_TEMPLATE.format("LOCATION", "EXPECTED", "COMPUTED", "Status"))
        print("====================================================================")
        for (lat, lng, loc, expected) in test_data:
            computed = test_fct(lng=lng, lat=lat)
            results_equal = computed == expected
            if results_equal:
                ok = "OK"
            else:
                ok = "XX"
                no_mistakes_made = False
            print(RESULT_TEMPLATE.format(loc, str(expected), str(computed), ok))
            if not results_equal:
                print(f"different results. coords: {lat} lat, {lng} lng")
        assert no_mistakes_made

    def test_timezone_at(self):
        print("\ntesting timezone_at():")
        self.run_location_tests(self.test_instance.timezone_at, self.test_locations)

    def test_timezone_at_land(self):
        print("\ntesting timezone_at_land():")
        self.run_location_tests(
            self.test_instance.timezone_at_land, ocean2land(self.test_locations)
        )

    def test_unambiguous_timezone_at(self):
        print("\ntesting unambiguous_timezone_at():")
        self.run_location_tests(
            self.test_instance.unique_timezone_at, BASIC_TEST_LOCATIONS
        )

    def test_timezone_name_attribute(self):
        timezone_names_stored = self.test_instance.timezone_names
        with open(join(abs_default_path, TIMEZONE_NAMES_FILE), "r") as json_file:
            timezone_names_json = json.loads(json_file.read())
        assert list_equal(
            timezone_names_stored, timezone_names_json
        ), f"the content of the {TIMEZONE_NAMES_FILE} and the attribute {timezone_names_stored} are different."


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
    on_land_pt_fct_name = "timezone_at_land"
    test_locations = TEST_LOCATIONS

    def test_kwargs_only(self):
        super(TimezonefinderClassTest, self).test_kwargs_only()

        with pytest.raises(TypeError):
            self.test_instance.certain_timezone_at(23.0, 42.0)
            self.test_instance.certain_timezone_at(23.0, lng=42.0)
            self.test_instance.certain_timezone_at(23.0, lat=42.0)

    def test_shortcut_boundary_result(self):
        for lng, lat, expected in BOUNDARY_TEST_CASES:
            # NOTE: for TimezoneFinder (using polygon data) the results must match!
            self.check_boundary(lng, lat, expected)

    def test_certain_timezone_at(self):
        print(
            "\ntestin certain_timezone_at():"
        )  # expected equal results to timezone_at(), is just slower
        self.run_location_tests(
            self.test_instance.certain_timezone_at, self.test_locations
        )

    def test_overflow(self):
        longitude = -123.2
        latitude = 48.4
        # make numpy overflow runtime warning raise an error
        import numpy as np

        np.seterr(all="warn")
        import warnings

        warnings.filterwarnings("error")
        # must not raise a warning
        self.test_instance.certain_timezone_at(
            lat=float(latitude), lng=float(longitude)
        )

    def test_get_geometry(self):
        print("testing get_geometry():")
        timezone_names_stored = self.test_instance.timezone_names
        nr_timezones = len(timezone_names_stored)
        for zone_id, zone_name in enumerate(timezone_names_stored):
            print(zone_id, zone_name)
            geometry_from_name = self.test_instance.get_geometry(
                tz_name=zone_name, tz_id=None, use_id=False, coords_as_pairs=False
            )
            check_geometry(geometry_from_name)

            if not DEBUG:
                continue

            # conduct extensive testing only with active debugging
            geometry_from_id = self.test_instance.get_geometry(
                tz_name=zone_name,
                tz_id=zone_id,
                use_id=False,
                coords_as_pairs=False,
            )
            # not necessary:
            # assert nested_list_equal(geometry_from_id, geometry_from_name), \
            assert len(geometry_from_name) == len(
                geometry_from_id
            ), "the results for querying the geometry for a zone with zone name or zone id are NOT equal."
            check_geometry(geometry_from_id)

            geometry_from_name = self.test_instance.get_geometry(
                tz_name=zone_name, tz_id=None, use_id=False, coords_as_pairs=True
            )
            geometry_from_id = self.test_instance.get_geometry(
                tz_name=zone_name, tz_id=zone_id, use_id=False, coords_as_pairs=True
            )
            assert len(geometry_from_name) == len(
                geometry_from_id
            ), "the results for querying the geometry for a zone with zone name or zone id are NOT equal."

            check_pairwise_geometry(geometry_from_id)
            check_pairwise_geometry(geometry_from_name)

        with pytest.raises(ValueError):
            self.test_instance.get_geometry(
                tz_name="", tz_id=None, use_id=False, coords_as_pairs=False
            )
            self.test_instance.get_geometry(
                tz_name="", tz_id=0, use_id=False, coords_as_pairs=False
            )
            self.test_instance.get_geometry(
                tz_name="wrong_tz_name", tz_id=None, use_id=False, coords_as_pairs=False
            )
            self.test_instance.get_geometry(
                tz_name="wrong_tz_name", tz_id=0, use_id=False, coords_as_pairs=False
            )
            # id does not exist
            self.test_instance.get_geometry(
                tz_name=None, tz_id=nr_timezones, use_id=True, coords_as_pairs=False
            )
            self.test_instance.get_geometry(
                tz_name="", tz_id=-1, use_id=True, coords_as_pairs=False
            )


class TimezonefinderClassTestMEM(TimezonefinderClassTest):
    in_memory_mode = True


class TimezonefinderClassTestDIR(BaseTimezoneFinderClassTest):
    # point to a dir where all bin files are located:
    bin_file_dir = abs_default_path


class TimezonefinderClassTestMEMDIR(BaseTimezoneFinderClassTest):
    in_memory_mode = True
    bin_file_dir = abs_default_path
