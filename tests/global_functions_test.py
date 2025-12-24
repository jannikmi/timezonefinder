"""
Tests for the global functions in timezonefinder
"""

import pytest

from tests.auxiliaries import single_location_test
from tests.locations import BASIC_TEST_LOCATIONS, TEST_LOCATIONS_AT_LAND, TEST_LOCATIONS
from timezonefinder import (
    TimezoneFinder,
    certain_timezone_at,
    get_geometry,
    timezone_at,
    timezone_at_land,
    unique_timezone_at,
)
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.zone_names import read_zone_names

# Load all timezone names for parameterization
all_timezone_names = read_zone_names(DEFAULT_DATA_DIR)

FUNC2TEST_CASES = {
    timezone_at: TEST_LOCATIONS,
    certain_timezone_at: TEST_LOCATIONS,
    unique_timezone_at: BASIC_TEST_LOCATIONS,
    timezone_at_land: TEST_LOCATIONS_AT_LAND,
}


@pytest.fixture(scope="session")
def timezonefinder_instance() -> TimezoneFinder:
    """Provide a single, reusable TimezoneFinder instance for all tests.

    Using in_memory=True avoids repeated disk I/O and initialization overhead
    while preserving the behaviour of the public API.
    """
    return TimezoneFinder(in_memory=True)


# Create parameterized test data from FUNC2TEST_CASES mapping
def create_test_params():
    """Create test parameters from FUNC2TEST_CASES mapping"""
    params = []
    ids = []
    for func, test_cases in FUNC2TEST_CASES.items():
        for lat, lng, description, expected in test_cases:
            params.append((func, lat, lng, description, expected))
            ids.append(f"{func.__name__}-{description}")
    return params, ids


# Generate test parameters and IDs once
TEST_PARAMS, TEST_IDS = create_test_params()


@pytest.mark.unit
class TestGlobalFunctions:
    """Test the global functions that use the global TimezoneFinder instance"""

    @pytest.mark.parametrize(
        "func, lat, lng, description, expected", TEST_PARAMS, ids=TEST_IDS
    )
    def test_global_functions_parameterized(
        self, func, lat, lng, description, expected
    ):
        """Test global functions with their respective test cases defined in FUNC2TEST_CASES"""
        single_location_test(func, lat, lng, description, expected)

    @pytest.mark.slow
    @pytest.mark.parametrize("tz_name", all_timezone_names)
    def test_get_geometry(self, tz_name, timezonefinder_instance: TimezoneFinder):
        """Test the global get_geometry function for all timezones"""
        expected = timezonefinder_instance.get_geometry(tz_name=tz_name)
        result = get_geometry(tz_name=tz_name)
        assert isinstance(result, type(expected)), (
            f"Type mismatch for {tz_name}: {type(result)} != {type(expected)}"
        )
        assert len(result) == len(expected), (
            f"Length mismatch for {tz_name}: {len(result)} != {len(expected)}"
        )
