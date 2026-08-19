from importlib.util import find_spec
import warnings

import pytest

from scripts.configs import THRES_DTYPE_H
from tests.auxiliaries import (
    check_geometry,
    check_pairwise_geometry,
    ocean2land,
    validate_polygon_coordinates,
)
from tests.global_functions_test import single_location_test
from tests.locations import (
    BASIC_TEST_LOCATIONS,
    EDGE_TEST_CASES,
    OUT_OF_RANGE_COORDINATES,
    TEST_LOCATIONS,
)
from timezonefinder.configs import (
    DEFAULT_DATA_DIR,
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
    # the lookup methods this class exposes that take lng/lat keyword-only
    keyword_only_methods = ("timezone_at", "timezone_at_land")

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

    def check_timezone_at_results(self, lng, lat, expected: str | None = ""):
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

    @pytest.mark.parametrize("lng, lat", OUT_OF_RANGE_COORDINATES)
    def test_out_of_range_coordinates_rejected(self, lng, lat):
        """One test case per coordinate: sharing a ``pytest.raises`` block would
        leave it at the first coordinate to raise and never reach the others."""
        with pytest.raises(ValueError):
            self.test_instance.timezone_at(lng=lng, lat=lat)

    def test_kwargs_only(self, method_name):
        """lng/lat are keyword-only, so every positional call shape must be
        rejected - each in its own ``pytest.raises`` block, since the first one
        to raise ends the block."""
        method = getattr(self.test_instance, method_name)
        with pytest.raises(TypeError):
            method(23.0, 42.0)
        with pytest.raises(TypeError):
            method(23.0, lng=42.0)
        with pytest.raises(TypeError):
            method(23.0, lat=42.0)

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
        elif metafunc.function.__name__ == "test_kwargs_only":
            metafunc.parametrize("method_name", cls.keyword_only_methods)

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
    keyword_only_methods = (
        *TestBaseTimezoneFinderClass.keyword_only_methods,
        "certain_timezone_at",
    )

    def test_nr_of_polygons(self):
        res = self.test_instance.nr_of_polygons
        assert isinstance(res, int)
        assert res > 0
        assert res < THRES_DTYPE_H

    @pytest.mark.unit
    def test_packaged_coordinate_layout(self):
        """Every packaged polygon must decode to longitudes in row 0, latitudes in row 1.

        Coordinates are stored one axis at a time; reading a file written in the old
        interleaved layout produces a correctly shaped array of nonsense, which the
        range checks below catch. Deliberately not marked ``slow``: a stale or
        unmigrated ``coordinates.bin`` should fail in ``make test``, and sweeping the
        whole dataset without the per-polygon printing below costs well under a second.
        """
        for polygons in (self.test_instance.boundaries, self.test_instance.holes):
            for poly_id in range(len(polygons)):
                coords = polygons.coords_of(poly_id)
                assert coords.flags["C_CONTIGUOUS"]
                validate_polygon_coordinates(coords)

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

    @pytest.mark.usefixtures("strict_numpy_warnings")
    def test_overflow(self):
        longitude = -123.2
        latitude = 48.4
        # the fixture promotes numpy overflow warnings to errors: this lookup
        # must complete without raising one
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

    # with use_id=False the zone is looked up by name and tz_id is irrelevant,
    # so an unknown name must be rejected whether or not an id accompanies it
    @pytest.mark.parametrize("tz_id", [None, 0])
    @pytest.mark.parametrize("tz_name", ["", "wrong_tz_name"])
    def test_get_geometry_rejects_unknown_zone_name(self, tz_name, tz_id):
        with pytest.raises(ValueError):
            self.test_instance.get_geometry(
                tz_name=tz_name, tz_id=tz_id, use_id=False, coords_as_pairs=False
            )

    def test_get_geometry_rejects_zone_id_past_the_last_zone(self):
        nr_timezones = len(self.test_instance.timezone_names)
        with pytest.raises(ValueError):
            self.test_instance.get_geometry(
                tz_name=None, tz_id=nr_timezones, use_id=True, coords_as_pairs=False
            )

    def test_get_geometry_rejects_negative_zone_id(self):
        """A negative id is a valid Python index into the zone list, so the range
        check has to reject it rather than relying on the lookup to fail."""
        with pytest.raises(ValueError):
            self.test_instance.get_geometry(
                tz_name=None, tz_id=-1, use_id=True, coords_as_pairs=False
            )

    def test_get_geometry_invalid_timezone_error_message(self):
        """Test that get_geometry raises clear error message for invalid timezone"""
        invalid_tz = "Invalid/Timezone"

        with pytest.raises(ValueError) as exc_info:
            self.test_instance.get_geometry(tz_name=invalid_tz)

        # Verify error message is a string, not a tuple
        error_msg = str(exc_info.value)
        assert isinstance(error_msg, str)
        assert invalid_tz in error_msg
        assert "does not exist" in error_msg


class TestTimezonefinderClassTestMEM(TestTimezonefinderClass):
    in_memory_mode = True


@pytest.mark.unit
class TestTimezonefinderCleanup:
    """Test cleanup behavior and exception handling in ``__del__``."""

    # Must match the `except` tuple in `TimezoneFinder.__del__`: these are the
    # errors a not-fully-initialised or already-cleaned-up resource raises, and
    # they are swallowed. Adding one there without adding it here leaves the new
    # exception untested.
    SUPPRESSED_ERRORS = (AttributeError, FileNotFoundError, OSError, ValueError)
    # Everything else must reach the caller as a ResourceWarning instead.
    WARNED_ERRORS = (RuntimeError, TypeError)

    @staticmethod
    def _finder_failing_cleanup(error: Exception) -> TimezoneFinder:
        """Return a finder whose ``cleanup()`` raises ``error``."""

        class FailingCleanupTimezoneFinder(TimezoneFinder):
            # bound as a default argument, not captured from the enclosing
            # scope: the instance is collected (re-entering __del__) after this
            # call has returned, and a closure would raise whatever the name
            # refers to by then
            def cleanup(self, error=error):
                raise error

        return FailingCleanupTimezoneFinder()

    @staticmethod
    def _resource_warnings_of_del(tf: TimezoneFinder) -> list:
        """Call ``__del__`` and return only the ResourceWarnings it emitted."""
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            tf.__del__()
            return [w for w in recorded if issubclass(w.category, ResourceWarning)]

    def test_cleanup_no_error(self):
        """A cleanup that succeeds emits no ResourceWarning."""
        assert self._resource_warnings_of_del(TimezoneFinder()) == []

    @pytest.mark.parametrize("error_type", SUPPRESSED_ERRORS)
    def test_expected_cleanup_error_is_suppressed(self, error_type):
        tf = self._finder_failing_cleanup(error_type("expected during cleanup"))
        assert self._resource_warnings_of_del(tf) == []

    @pytest.mark.parametrize("error_type", WARNED_ERRORS)
    def test_unexpected_cleanup_error_warns(self, error_type):
        tf = self._finder_failing_cleanup(error_type("unexpected during cleanup"))
        assert len(self._resource_warnings_of_del(tf)) == 1

    def test_cleanup_warning_names_the_cause(self):
        """The ResourceWarning has to be debuggable from its text alone."""
        error_msg = "specific error details"
        recorded = self._resource_warnings_of_del(
            self._finder_failing_cleanup(RuntimeError(error_msg))
        )
        assert len(recorded) == 1
        warning_text = str(recorded[0].message)
        assert "Error during TimezoneFinder cleanup" in warning_text
        assert error_msg in warning_text

    @pytest.mark.parametrize("error_type", SUPPRESSED_ERRORS + WARNED_ERRORS)
    def test_cleanup_does_not_raise_to_user(self, error_type):
        """``__del__`` never raises to user code, whichever error cleanup hits."""
        tf = self._finder_failing_cleanup(error_type("error during cleanup"))
        try:
            tf.__del__()
        except Exception as e:
            pytest.fail(
                f"__del__ raised {type(e).__name__} when cleanup raised "
                f"{error_type.__name__}: {e}"
            )
