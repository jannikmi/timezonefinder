"""
Tests for the global functions in timezonefinder
"""

import pytest

from timezonefinder import (
    timezone_at,
    timezone_at_land,
    unique_timezone_at,
    certain_timezone_at,
    get_geometry,
    TimezoneFinder,
)
from tests.locations import BASIC_TEST_LOCATIONS
from timezonefinder.utils import is_ocean_timezone


@pytest.mark.unit
class TestGlobalFunctions:
    """Test the global functions that use the global TimezoneFinder instance"""

    @pytest.mark.parametrize(
        "func",
        [
            timezone_at,
            timezone_at_land,
            unique_timezone_at,
            certain_timezone_at,
        ],
    )
    @pytest.mark.parametrize("lat, lng, description, expected", BASIC_TEST_LOCATIONS)
    def test_global_functions(self, func, lat, lng, description, expected):
        if func is timezone_at_land and is_ocean_timezone(expected):
            expected = None
        result = func(lng=lng, lat=lat)
        func_name = func.__name__
        assert result == expected, (
            f"{func_name}({lng}, {lat}) [{description}] should return {expected}, got {result}"
        )

    def test_get_geometry(self):
        """Test the global get_geometry function"""
        tz_name = "Europe/Berlin"
        tf = TimezoneFinder()
        expected = tf.get_geometry(tz_name=tz_name)
        result = get_geometry(tz_name=tz_name)
        assert isinstance(result, type(expected)), (
            f"Type mismatch: {type(result)} != {type(expected)}"
        )
        assert len(result) == len(expected), (
            f"Length mismatch: {len(result)} != {len(expected)}"
        )
