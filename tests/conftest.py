"""
Pytest configuration and shared fixtures.
"""

from __future__ import annotations

import pytest

from timezonefinder import TimezoneFinder
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.io.hybrid_shortcuts import (
    get_hybrid_shortcut_file_path,
    read_hybrid_shortcuts_binary,
)
from timezonefinder.np_binary_helpers import get_zone_ids_path, read_per_polygon_vector
from timezonefinder.polygon_array import PolygonArray
from timezonefinder.utils import get_boundaries_dir


def pytest_configure(config):
    """
    Register custom markers for different types of tests.
    """
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "examples: mark test as examples cli test")
    config.addinivalue_line(
        "markers", "slow: mark test as slow (deselect with '-m \"not slow\"')"
    )


@pytest.fixture(scope="session")
def timezonefinder_in_memory() -> TimezoneFinder:
    """Shared in-memory TimezoneFinder instance to avoid repeated initialisation."""
    return TimezoneFinder(in_memory=True)


@pytest.fixture(scope="session")
def timezonefinder_disk() -> TimezoneFinder:
    """Shared on-disk TimezoneFinder instance for parity with disk-backed paths."""
    return TimezoneFinder(in_memory=False)


@pytest.fixture(scope="session")
def polygon_array() -> PolygonArray:
    """Shared PolygonArray instance loaded once per session."""
    return PolygonArray(data_location=get_boundaries_dir(), in_memory=True)


@pytest.fixture(scope="session")
def zone_ids():
    """Zone ID vector loaded once for shortcut tests."""
    zone_ids_path = get_zone_ids_path(DEFAULT_DATA_DIR)
    return read_per_polygon_vector(zone_ids_path)


@pytest.fixture(scope="session")
def zone_id_dtype(zone_ids):
    """Convenience fixture exposing the dtype of the zone_ids array."""
    return zone_ids.dtype


@pytest.fixture(scope="session")
def hybrid_shortcut_file_path(zone_id_dtype):
    """Path to the hybrid shortcuts file matching the zone ID dtype."""
    return get_hybrid_shortcut_file_path(zone_id_dtype, DEFAULT_DATA_DIR)


@pytest.fixture(scope="session")
def hybrid_shortcuts(hybrid_shortcut_file_path):
    """Hybrid shortcut mapping loaded once per session."""
    return read_hybrid_shortcuts_binary(hybrid_shortcut_file_path)


@pytest.fixture(scope="session")
def tf(timezonefinder_in_memory):
    """Alias fixture for the shared in-memory TimezoneFinder."""
    return timezonefinder_in_memory
