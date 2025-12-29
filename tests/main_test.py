from importlib.util import find_spec
from typing import Optional

import numpy as np
import pytest

from scripts.configs import THRES_DTYPE_H
from tests.auxiliaries import (
    check_geometry,
    check_pairwise_geometry,
    ocean2land,
    validate_polygon_coordinates,
)
from tests.global_functions_test import single_location_test
from tests.locations import BASIC_TEST_LOCATIONS, EDGE_TEST_CASES, TEST_LOCATIONS
from timezonefinder.configs import (
    DEFAULT_DATA_DIR,
    INT2COORD_FACTOR,
)
from timezonefinder.zone_names import read_zone_names
from timezonefinder.timezonefinder import (
    TimezoneFinder,
    TimezoneFinderL,
)
from timezonefinder.utils import is_ocean_timezone

DEBUG = False
# more extensive testing (e.g. get geometry for every single zone), switch off for CI/CD
# DEBUG = True

PACKAGE_NAME = "timezonefinder"

# Load all timezone names for parameterization
all_timezone_names = read_zone_names(DEFAULT_DATA_DIR)

RESULT_TEMPLATE = "{0:25s} | {1:20s} | {2:20s} | {3:2s}"


# tests for both classes: TimezoneFinderL and TimezoneFinder
class TestBaseTimezoneFinderClass:
    class_under_test = TimezoneFinderL
    # NOTE: setting memory mode does not make a difference for TimezoneFinderL (relevant only for polygon data)
    in_memory_mode = False
    bin_file_dir = None
    on_land_pt_fct_name = "timezone_at"
    test_locations = BASIC_TEST_LOCATIONS

    @pytest.fixture(scope="class", autouse=True)
    def _init_test_instance(
        self, request, timezonefinder_in_memory, timezonefinder_disk
    ):
        cls = request.cls
        cls.print_tf_class_props(cls)
        if cls.class_under_test is TimezoneFinder:
            cls.test_instance = (
                timezonefinder_in_memory if cls.in_memory_mode else timezonefinder_disk
            )
        else:
            cls.test_instance = cls.class_under_test(
                bin_file_location=cls.bin_file_dir, in_memory=cls.in_memory_mode
            )

    def test_using_numba(self):
        spec = find_spec("numba")
        numba_installed = spec is not None
        assert self.test_instance.using_numba() == numba_installed

    def test_using_clang_pip(self):
        res = self.test_instance.using_clang_pip()
        assert isinstance(res, bool)

    def print_tf_class_props(self):
        print("test properties:")
        print(f"testing class {self.class_under_test}")
        print(
            f"using_numba()=={self.class_under_test.using_numba()} (JIT compiled functions {'NOT ' if not self.class_under_test.using_numba() else ''}in use)"
        )
        print(f"in_memory={self.in_memory_mode}")
        print(f"file location={self.bin_file_dir}\n")

    def check_timezone_at_results(self, lng, lat, expected: Optional[str] = ""):
        # at the edges of the coordinate system the algorithms should still be well defined!

        print(
            [
                self.test_instance.zone_name_from_boundary_id(b_id)
                for b_id in self.test_instance._iter_boundaries_in_shortcut(
                    lng=lng, lat=lat
                )
            ]
        )

        result = self.test_instance.timezone_at(lng=lng, lat=lat)
        if isinstance(expected, str) and len(expected) == 0:
            # zone_name="" is interpreted as "don't care"
            return
        assert result == expected

    def test_edge_shortcut_validity(self):
        for lng, lat, _expected in EDGE_TEST_CASES:
            self.check_timezone_at_results(lng, lat)

        with pytest.raises(ValueError):
            self.check_timezone_at_results(lng=180.0 + INT2COORD_FACTOR, lat=90.0)
            self.check_timezone_at_results(
                lng=-180.0 - INT2COORD_FACTOR, lat=90.0 + INT2COORD_FACTOR
            )
            self.check_timezone_at_results(lng=-180.0, lat=90.0 + INT2COORD_FACTOR)
            self.check_timezone_at_results(lng=180.0 + INT2COORD_FACTOR, lat=-90.0)
            self.check_timezone_at_results(lng=180.0, lat=-90.0 - INT2COORD_FACTOR)
            self.check_timezone_at_results(lng=-180.0 - INT2COORD_FACTOR, lat=-90.0)
            self.check_timezone_at_results(
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
    def run_location_tests(test_fct, lat, lng, loc, expected_orig):
        single_location_test(test_fct, lat, lng, loc, expected_orig)

    @classmethod
    def pytest_generate_tests(cls, metafunc):
        # Dynamically generate test parameters based on the test method
        if metafunc.function.__name__ == "test_timezone_at":
            metafunc.parametrize("lat, lng, loc, expected", cls.test_locations)
        elif metafunc.function.__name__ == "test_timezone_at_land":
            metafunc.parametrize(
                "lat, lng, loc, expected", list(ocean2land(cls.test_locations))
            )
        elif metafunc.function.__name__ == "test_unambiguous_timezone_at":
            metafunc.parametrize("lat, lng, loc, expected", BASIC_TEST_LOCATIONS)

    def test_timezone_at(self, lat, lng, loc, expected):
        self.run_location_tests(self.test_instance.timezone_at, lat, lng, loc, expected)

    def test_timezone_at_land(self, lat, lng, loc, expected):
        self.run_location_tests(
            self.test_instance.timezone_at_land, lat, lng, loc, expected
        )

    def test_unambiguous_timezone_at(self, lat, lng, loc, expected):
        self.run_location_tests(
            self.test_instance.unique_timezone_at, lat, lng, loc, expected
        )

    def test_timezone_names(self):
        timezone_names_stored = self.test_instance.timezone_names
        assert isinstance(timezone_names_stored, list)
        assert len(timezone_names_stored) > 0, "no timezone names found"
        # test if all timezone names are strings
        assert all(isinstance(name, str) for name in timezone_names_stored), (
            "not all timezone names are strings"
        )
        # test if all timezone names are unique
        assert len(set(timezone_names_stored)) == len(timezone_names_stored), (
            "not all timezone names are unique"
        )
        # test if all timezone names are valid
        for name in timezone_names_stored:
            assert len(name) > 0, f"empty timezone name found: {name}"
            assert "/" in name or is_ocean_timezone(name), (
                f"invalid timezone name: {name}. It should contain a '/' or be an ocean timezone."
            )

            # TODO further checks for valid timezone names


# tests for Timezonefinder class
class TestTimezonefinderClass(TestBaseTimezoneFinderClass):
    class_under_test = TimezoneFinder
    on_land_pt_fct_name = "timezone_at_land"
    test_locations = TEST_LOCATIONS

    def test_kwargs_only(self):
        super().test_kwargs_only()

        with pytest.raises(TypeError):
            self.test_instance.certain_timezone_at(23.0, 42.0)
            self.test_instance.certain_timezone_at(23.0, lng=42.0)
            self.test_instance.certain_timezone_at(23.0, lat=42.0)

    def test_nr_of_polygons(self):
        res = self.test_instance.nr_of_polygons
        assert isinstance(res, int)
        assert res > 0
        assert res < THRES_DTYPE_H

    # test if all polygon coordinates can be retrieved
    # NOTE: too many polygons, so this test is not parametrized
    @pytest.mark.slow
    def test_coords_of(self):
        nr_of_polygons = self.test_instance.nr_of_polygons
        for poly_id in range(nr_of_polygons):
            print(f"Testing polygon ID: {poly_id}")
            coords = self.test_instance.coords_of(poly_id)
            validate_polygon_coordinates(coords)

    @pytest.mark.slow
    def test_holes_of_poly(self):
        print("test retrieving all holes for each polygon using _holes_of_poly:")
        nr_of_polygons = self.test_instance.nr_of_polygons
        for poly_id in range(nr_of_polygons):
            print(f"polygon ID: {poly_id + 1}/{nr_of_polygons}", end="\r", flush=True)
            for i, hole_coords in enumerate(self.test_instance._holes_of_poly(poly_id)):
                print(
                    f"polygon ID: {poly_id + 1}/{nr_of_polygons}, hole {i + 1}",
                    end="\r",
                    flush=True,
                )
                validate_polygon_coordinates(hole_coords)
        print()  # move to next line after progress output

    def test_edge_shortcut_result(self):
        for lng, lat, expected in EDGE_TEST_CASES:
            # NOTE: for TimezoneFinder (using polygon data) the results must match!
            self.check_timezone_at_results(lng, lat, expected)

    def test_certain_timezone_at(self, lat, lng, loc, expected):
        self.run_location_tests(
            self.test_instance.certain_timezone_at, lat, lng, loc, expected
        )

    @classmethod
    def pytest_generate_tests(cls, metafunc):
        # call the super class method
        super().pytest_generate_tests(metafunc)
        if metafunc.function.__name__ == "test_certain_timezone_at" and hasattr(
            cls, "test_certain_timezone_at"
        ):
            metafunc.parametrize("lat, lng, loc, expected", cls.test_locations)

    def test_overflow(self):
        longitude = -123.2
        latitude = 48.4
        # make numpy overflow runtime warning raise an error

        np.seterr(all="warn")
        import warnings

        warnings.filterwarnings("error")
        # must not raise a warning
        self.test_instance.certain_timezone_at(
            lat=float(latitude), lng=float(longitude)
        )

    @pytest.mark.slow
    @pytest.mark.parametrize("tz_name", all_timezone_names)
    def test_get_geometry(self, tz_name):
        """Test get_geometry() for all timezones"""
        print(f"testing get_geometry() for {tz_name}")
        timezone_names_stored = self.test_instance.timezone_names
        zone_id = timezone_names_stored.index(tz_name)

        geometry_from_name = self.test_instance.get_geometry(
            tz_name=tz_name, tz_id=None, use_id=False, coords_as_pairs=False
        )
        check_geometry(geometry_from_name)

        # conduct extensive testing only with active debugging
        geometry_from_id = self.test_instance.get_geometry(
            tz_name=tz_name,
            tz_id=zone_id,
            use_id=False,
            coords_as_pairs=False,
        )
        # not necessary:
        # assert nested_list_equal(geometry_from_id, geometry_from_name), \
        assert len(geometry_from_name) == len(geometry_from_id), (
            "the results for querying the geometry for a zone with zone name or zone id are NOT equal."
        )
        check_geometry(geometry_from_id)

        geometry_from_name = self.test_instance.get_geometry(
            tz_name=tz_name, tz_id=None, use_id=False, coords_as_pairs=True
        )
        geometry_from_id = self.test_instance.get_geometry(
            tz_name=tz_name, tz_id=zone_id, use_id=False, coords_as_pairs=True
        )
        assert len(geometry_from_name) == len(geometry_from_id), (
            "the results for querying the geometry for a zone with zone name or zone id are NOT equal."
        )

        check_pairwise_geometry(geometry_from_id)
        check_pairwise_geometry(geometry_from_name)

    def test_get_geometry_error_handling(self):
        """Test error handling for get_geometry() with invalid inputs"""
        nr_timezones = len(self.test_instance.timezone_names)
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


class TestTimezonefinderClassTestMEM(TestTimezonefinderClass):
    in_memory_mode = True


# TEST equality for all results. in_memory_mode = True/False must not change the results
# TEST equality for all results. in_memory_mode = True/False must not change the results
