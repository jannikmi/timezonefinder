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


@pytest.mark.unit
class TestGlobalFunctions:
    """Test the global functions that use the global TimezoneFinder instance"""

    def test_timezone_at(self):
        """Test the global timezone_at function"""
        # Create a reference TimezoneFinder to compare results
        tf = TimezoneFinder()

        for lat, lng, description, expected in BASIC_TEST_LOCATIONS:
            expected_result = tf.timezone_at(lng=lng, lat=lat)
            result = timezone_at(lng=lng, lat=lat)
            assert result == expected_result, (
                f"timezone_at({lng}, {lat}) should return {expected_result}, got {result}"
            )

    def test_timezone_at_land(self):
        """Test the global timezone_at_land function"""
        # Create a reference TimezoneFinder to compare results
        tf = TimezoneFinder()

        for lat, lng, description, expected in BASIC_TEST_LOCATIONS:
            expected_result = tf.timezone_at_land(lng=lng, lat=lat)
            result = timezone_at_land(lng=lng, lat=lat)
            assert result == expected_result, (
                f"timezone_at_land({lng}, {lat}) should return {expected_result}, got {result}"
            )

    def test_unique_timezone_at(self):
        """Test the global unique_timezone_at function"""
        # Create a reference TimezoneFinder to compare results
        tf = TimezoneFinder()

        for lat, lng, description, expected in BASIC_TEST_LOCATIONS:
            expected_result = tf.unique_timezone_at(lng=lng, lat=lat)
            result = unique_timezone_at(lng=lng, lat=lat)
            assert result == expected_result, (
                f"unique_timezone_at({lng}, {lat}) should return {expected_result}, got {result}"
            )

    def test_certain_timezone_at(self):
        """Test the global certain_timezone_at function"""
        # Create a reference TimezoneFinder to compare results
        tf = TimezoneFinder()

        for lat, lng, description, expected in BASIC_TEST_LOCATIONS:
            expected_result = tf.certain_timezone_at(lng=lng, lat=lat)
            result = certain_timezone_at(lng=lng, lat=lat)
            assert result == expected_result, (
                f"certain_timezone_at({lng}, {lat}) should return {expected_result}, got {result}"
            )

    def test_get_geometry(self):
        """Test the global get_geometry function"""
        # Test with a known timezone name
        tz_name = "Europe/Berlin"

        # Create a reference TimezoneFinder to compare results
        tf = TimezoneFinder()

        expected = tf.get_geometry(tz_name=tz_name)
        result = get_geometry(tz_name=tz_name)

        # Basic check that the structure is similar
        assert isinstance(result, type(expected)), (
            f"Type mismatch: {type(result)} != {type(expected)}"
        )
        assert len(result) == len(expected), (
            f"Length mismatch: {len(result)} != {len(expected)}"
        )
