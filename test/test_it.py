# -*- coding:utf-8 -*-
import json
import timeit
import unittest
from math import floor, log10
from os.path import abspath, join, pardir

import pytest
from auxiliaries import list_equal, list_of_random_points, random_point

from timezonefinder.global_settings import (
    INT2COORD_FACTOR,
    PACKAGE_NAME,
    TIMEZONE_NAMES,
    TIMEZONE_NAMES_FILE, DEBUG,
)
from timezonefinder.timezonefinder import (
    TimezoneFinder,
    TimezoneFinderL,
    is_ocean_timezone,
)

# number of points to test (in each test, on land and random ones)
N = int(1e2)

tf = None
point_list = []
in_memory_mode = False
class_under_test = TimezoneFinder

RESULT_TEMPLATE = "{0:20s} | {1:20s} | {2:20s} | {3:2s}"


def eval_time_fct():
    global tf, point_list
    for point in point_list:
        tf.timezone_at(lng=point[0], lat=point[1])


def time_preprocess(time):
    valid_digits = 4
    zero_digits = abs(min(0, int(log10(time))))
    digits_to_print = zero_digits + valid_digits
    return str(round(time, digits_to_print)) + "s"


# for TimezoneFinderL:
BASIC_TEST_LOCATIONS = [
    # lat, lng, description, expected
    (35.295953, -89.662186, "Arlington, TN", "America/Chicago"),
    (35.1322601, -90.0902499, "Memphis, TN", "America/Chicago"),
    (61.17, -150.02, "Anchorage, AK", "America/Anchorage"),
    (44.12, -123.22, "Eugene, OR", "America/Los_Angeles"),
    (42.652647, -73.756371, "Albany, NY", "America/New_York"),
    (55.743749, 37.6207923, "Moscow", "Europe/Moscow"),
    (34.104255, -118.4055591, "Los Angeles", "America/Los_Angeles"),
    (55.743749, 37.6207923, "Moscow", "Europe/Moscow"),
    (39.194991, -106.8294024, "Aspen, Colorado", "America/Denver"),
    (50.438114, 30.5179595, "Kiev", "Europe/Kiev"),
    (12.936873, 77.6909136, "Jogupalya", "Asia/Kolkata"),
    (38.889144, -77.0398235, "Washington DC", "America/New_York"),
    (19, -135, "pacific ocean", "Etc/GMT+9"),
    (30, -33, "atlantic ocean", "Etc/GMT+2"),
    (-24, 79, "indian ocean", "Etc/GMT-5"),
]

# for TimezoneFinder:
# certain algorithm should give the same results for all normal test cases
TEST_LOCATIONS = BASIC_TEST_LOCATIONS + [
    (59.932490, 30.3164291, "St Petersburg", "Europe/Moscow"),
    (50.300624, 127.559166, "Blagoveshchensk", "Asia/Yakutsk"),
    (42.439370, -71.0700416, "Boston", "America/New_York"),
    (41.84937, -87.6611995, "Chicago", "America/Chicago"),
    (28.626873, -81.7584514, "Orlando", "America/New_York"),
    (47.610615, -122.3324847, "Seattle", "America/Los_Angeles"),
    (51.499990, -0.1353549, "London", "Europe/London"),
    (51.256241, -0.8186531, "Church Crookham", "Europe/London"),
    (51.292215, -0.8002638, "Fleet", "Europe/London"),
    (48.868743, 2.3237586, "Paris", "Europe/Paris"),
    (22.158114, 113.5504603, "Macau", "Asia/Macau"),
    (56.833123, 60.6097054, "Russia", "Asia/Yekaterinburg"),
    (60.887496, 26.6375756, "Salo", "Europe/Helsinki"),
    (52.799992, -1.8524408, "Staffordshire", "Europe/London"),
    (5.016666, 115.0666667, "Muara", "Asia/Brunei"),
    (-41.466666, -72.95, "Puerto Montt seaport", "America/Santiago"),
    (34.566666, 33.0333333, "Akrotiri seaport", "Asia/Nicosia"),
    (37.466666, 126.6166667, "Inchon seaport", "Asia/Seoul"),
    (42.8, 132.8833333, "Nakhodka seaport", "Asia/Vladivostok"),
    (50.26, -5.051, "Truro", "Europe/London"),
    (37.790792, -122.389980, "San Francisco", "America/Los_Angeles"),
    (37.81, -122.35, "San Francisco Bay", "America/Los_Angeles"),
    (68.3597987, -133.745786, "America", "America/Inuvik"),
    # lng 180 == -180
    # 180.0: right on the timezone boundary polygon edge, the return value is uncertain (None in this case)
    # being tested in test_helpers.py
    (65.2, 179.9999, "lng 180", "Asia/Anadyr"),
    (65.2, -179.9999, "lng -180", "Asia/Anadyr"),
    # test cases for hole handling:
    (41.0702284, 45.0036352, "Aserbaid. Enklave", "Asia/Yerevan"),
    (39.8417402, 70.6020068, "Tajikistani Enklave", "Asia/Dushanbe"),
    (47.7024174, 8.6848462, "Busingen Ger", "Europe/Busingen"),
    (46.2085101, 6.1246227, "Genf", "Europe/Zurich"),
    (-29.391356857138753, 28.50989829115889, "Lesotho", "Africa/Maseru"),
    (39.93143377877638, 71.08546583764965, "Uzbek enclave1", "Asia/Tashkent"),
    (39.969915, 71.134060, "Uzbek enclave2", "Asia/Tashkent"),
    (39.862402, 70.568449, "Tajik enclave", "Asia/Dushanbe"),
    (35.7396116, -110.15029571, "Arizona Desert 1", "America/Denver"),
    (36.4091869, -110.7520236, "Arizona Desert 2", "America/Phoenix"),
    (36.10230848, -111.1882385, "Arizona Desert 3", "America/Phoenix"),
    # ocean:
    (37.81, -123.5, "Far off San Fran.", "Etc/GMT+8"),
    (50.26, -9.0, "Far off Cornwall", "Etc/GMT+1"),
    (50.5, 1, "English Channel1", "Etc/GMT"),
    (56.218, 19.4787, "baltic sea", "Etc/GMT-1"),
]

TEST_LOCATIONS_PROXIMITY = [
    # TODO the data now contains ocean timezones, every point lies within a zone!
    #  -> proximity tests are not meaningful at the moment
    # (35.295953, -89.662186, 'Arlington, TN', 'America/Chicago'),
    # (33.58, -85.85, 'Memphis, TN', 'America/Chicago'),
    # (61.17, -150.02, 'Anchorage, AK', 'America/Anchorage'),
    # (40.7271, -73.98, 'Shore Lake Michigan', 'America/New_York'),
    # (51.032593, 1.4082031, 'English Channel1', 'Europe/London'),
    # (50.9623651, 1.5732592, 'English Channel2', 'Europe/Paris'),
    # (55.5609615, 12.850585, 'Oresund Bridge1', 'Europe/Stockholm'),
    # (55.6056074, 12.7128568, 'Oresund Bridge2', 'Europe/Copenhagen'),
]


def ocean2land(test_locations):
    for lat, lng, description, expected in test_locations:
        if is_ocean_timezone(expected):
            expected = None
        yield lat, lng, description, expected


# tests for TimezonefinderL class
class BaseTimezoneFinderClassTest(unittest.TestCase):
    in_memory_mode = False
    bin_file_dir = None
    class_under_test = TimezoneFinderL
    on_land_pt_fct_name = "timezone_at"
    test_locations = BASIC_TEST_LOCATIONS

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
            pts_p_sec = round(pts_p_sec / 10 ** exp, 1)  # normalize
            print("avg. points per second: {} * 10^{}".format(pts_p_sec, exp))

        print_speed_test("on land points", self.on_land_points)
        print_speed_test("random points", list_of_random_points(length=N))

    def test_shortcut_boundary(self):
        # at the boundaries of the shortcut grid (coordinate system) the algorithms should still be well defined!
        assert self.test_instance.timezone_at(lng=-180.0, lat=90.0) == "Etc/GMT+12"
        assert self.test_instance.timezone_at(lng=180.0, lat=90.0) == "Etc/GMT+12"
        assert (
            self.test_instance.timezone_at(lng=180.0, lat=-90.0) == "Antarctica/McMurdo"
        )
        assert (
            self.test_instance.timezone_at(lng=-180.0, lat=-90.0)
            == "Antarctica/McMurdo"
        )

        with pytest.raises(ValueError):
            self.test_instance.timezone_at(lng=180.0 + INT2COORD_FACTOR, lat=90.0)
            self.test_instance.timezone_at(
                lng=-180.0 - INT2COORD_FACTOR, lat=90.0 + INT2COORD_FACTOR
            )
            self.test_instance.timezone_at(lng=-180.0, lat=90.0 + INT2COORD_FACTOR)
            self.test_instance.timezone_at(lng=180.0 + INT2COORD_FACTOR, lat=-90.0)
            self.test_instance.timezone_at(lng=180.0, lat=-90.0 - INT2COORD_FACTOR)
            self.test_instance.timezone_at(lng=-180.0 - INT2COORD_FACTOR, lat=-90.0)
            self.test_instance.timezone_at(
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

    def run_location_tests(self, test_fct, test_data):
        no_mistakes_made = True
        print(RESULT_TEMPLATE.format("LOCATION", "EXPECTED", "COMPUTED", "Status"))
        print("====================================================================")
        for (lat, lng, loc, expected) in test_data:
            computed = test_fct(lng=lng, lat=lat)
            if computed == expected:
                ok = "OK"
            else:
                print(lat, lng)
                ok = "XX"
                no_mistakes_made = False
            print(RESULT_TEMPLATE.format(loc, str(expected), str(computed), ok))
        assert no_mistakes_made

    def test_timezone_at(self):
        print("\ntesting timezone_at():")
        self.run_location_tests(self.test_instance.timezone_at, self.test_locations)

    def test_timezone_at_land(self):
        print("\ntesting timezone_at_land():")
        self.run_location_tests(
            self.test_instance.timezone_at_land, ocean2land(self.test_locations)
        )

    def test_timezone_name_attribute(self):
        timezone_names_stored = getattr(self.test_instance, TIMEZONE_NAMES)
        with open(join(abs_default_path, TIMEZONE_NAMES_FILE), "r") as json_file:
            timezone_names_json = json.loads(json_file.read())
        assert list_equal(
            timezone_names_stored, timezone_names_json
        ), f"the content of the {TIMEZONE_NAMES_FILE} and the attribute {TIMEZONE_NAMES} are different."


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

            self.test_instance.closest_timezone_at(23.0, 42.0)
            self.test_instance.closest_timezone_at(23.0, lng=42.0)
            self.test_instance.closest_timezone_at(23.0, lat=42.0)

    def test_certain_timezone_at(self):
        print(
            "\ntestin certain_timezone_at():"
        )  # expected equal results to timezone_at(), is just slower
        self.run_location_tests(
            self.test_instance.certain_timezone_at, self.test_locations
        )

    def test_closest_timezone_at(self):
        print("\ntestin closest_timezone_at():")
        self.run_location_tests(
            self.test_instance.closest_timezone_at, TEST_LOCATIONS_PROXIMITY
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
        timezone_names_stored = getattr(self.test_instance, TIMEZONE_NAMES)
        nr_timezones = len(timezone_names_stored)
        for zone_id, zone_name in enumerate(timezone_names_stored):
            print(zone_id, zone_name)
            geometry_from_name = self.test_instance.get_geometry(
                tz_name=zone_name, tz_id=None, use_id=False, coords_as_pairs=False
            )
            poly1 = geometry_from_name[0][0]
            assert (
                len(poly1) == 2
            ), "the polygon does not consist of two latitude longitude lists"
            assert (
                len(poly1[0]) > 2
            ), "a polygon must consist of more than 2 coordinates"
            assert (
                len(poly1[1]) > 2
            ), "a polygon must consist of more than 2 coordinates"

            if DEBUG: # only with active debugging conduct extensive testing (requ
                geometry_from_id = self.test_instance.get_geometry(
                    tz_name=zone_name, tz_id=zone_id, use_id=False, coords_as_pairs=False
                )
                # not necessary:
                # assert nested_list_equal(geometry_from_id, geometry_from_name), \
                assert len(geometry_from_name) == len(
                    geometry_from_id
                ), "the results for querying the geometry for a zone with zone name or zone id are NOT equal."
                poly1 = geometry_from_id[0][0]
                assert (
                    len(poly1) == 2
                ), "the polygon does not consist of two latitude longitude lists"
                assert (
                    len(poly1[0]) > 2
                ), "a polygon must consist of more than 2 coordinates"
                assert (
                    len(poly1[1]) > 2
                ), "a polygon must consist of more than 2 coordinates"

                geometry_from_name = self.test_instance.get_geometry(
                    tz_name=zone_name, tz_id=None, use_id=False, coords_as_pairs=True
                )
                geometry_from_id = self.test_instance.get_geometry(
                    tz_name=zone_name, tz_id=zone_id, use_id=False, coords_as_pairs=True
                )
                assert len(geometry_from_name) == len(
                    geometry_from_id
                ), "the results for querying the geometry for a zone with zone name or zone id are NOT equal."

                # first polygon, first coord pair
                poly1 = geometry_from_id[0][0]
                assert len(poly1) > 2, "a polygon must consist of more than 2 coordinates"
                assert len(poly1) > 2, "a polygon must consist of more than 2 coordinates"
                assert (
                    len(poly1[0]) == 2
                ), "the polygon does not consist of coordinate pairs as expected."
                poly1 = geometry_from_name[0][0]
                assert len(poly1) > 2, "a polygon must consist of more than 2 coordinates"
                assert len(poly1) > 2, "a polygon must consist of more than 2 coordinates"
                assert (
                    len(poly1[0]) == 2
                ), "the polygon does not consist of coordinate pairs as expected."

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
