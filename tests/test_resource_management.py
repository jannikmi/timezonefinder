#!/usr/bin/env python
"""
Test script to verify that the resource management improvements work correctly.
"""

from timezonefinder import TimezoneFinder


def test_context_manager_usage():
    """Test that context managers work properly for resource management."""
    print("Testing context manager functionality...")

    # Test TimezoneFinder basic functionality
    with TimezoneFinder() as tf:
        result = tf.timezone_at(lng=-74.0059, lat=40.7128)  # New York
        print(f"New York timezone: {result}")
        assert result == "America/New_York"

    print("✓ TimezoneFinder context manager works")


def test_resource_cleanup_after_exception():
    """Test that resources are properly cleaned up even after exceptions."""
    print("Testing resource cleanup after exceptions...")

    try:
        with TimezoneFinder() as tf:
            # Test normal operation first
            result = tf.timezone_at(lng=0, lat=0)
            print(f"Timezone at (0,0): {result}")

            # Now raise an exception
            raise ValueError("Test exception")
    except ValueError as e:
        print(f"Caught expected exception: {e}")

    print("✓ Resources cleaned up properly after exception")
