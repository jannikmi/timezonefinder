"""Utility functions for TimezoneFinder.

This module provides coordinate validation, resource management, and helper functions
for timezone operations.
"""

from collections.abc import Callable
from pathlib import Path
import re
from typing import Any

import numpy as np

from timezonefinder.configs import (
    DEFAULT_DATA_DIR,
    OCEAN_TIMEZONE_PREFIX,
)
from timezonefinder import utils_numba, utils_clang

__all__ = [
    "validate_lat",
    "validate_lng",
    "validate_coordinates",
    "close_resource",
    "is_ocean_timezone",
    "get_boundaries_dir",
    "get_holes_dir",
    "get_hole_registry_path",
    # Re-exported from submodules
    "inside_polygon",
    "using_numba",
    "clang_extension_loaded",
]


# make numba functions available via utils
using_numba = utils_numba.using_numba
clang_extension_loaded = utils_clang.clang_extension_loaded
is_valid_lat = utils_numba.is_valid_lat
is_valid_lng = utils_numba.is_valid_lng
coord2int = utils_numba.coord2int
int2coord = utils_numba.int2coord
convert2coords = utils_numba.convert2coords
convert2coord_pairs = utils_numba.convert2coord_pairs
get_last_change_idx = utils_numba.get_last_change_idx


inside_polygon: Callable[[int, int, np.ndarray], bool]
# at import time fix which "point-in-polygon" implementation will be used
if clang_extension_loaded and not using_numba:
    # use the C implementation only if Numba is not present
    inside_polygon = utils_clang.pt_in_poly_clang
else:
    # use the (JIT compiled) python function if Numba is present or the C extension cannot be loaded
    inside_polygon = utils_numba.pt_in_poly_python


def validate_lat(lat: float) -> None:
    """
    Validate that a latitude value is within valid bounds.

    :param lat: Latitude value to validate (must be in range [-90.0, 90.0])
    :raises ValueError: If latitude is outside valid bounds (-90 to 90)
    """
    if not is_valid_lat(lat):
        raise ValueError(f"Invalid latitude {lat}: must be in range [-90.0, 90.0]")


def validate_lng(lng: float) -> None:
    """
    Validate that a longitude value is within valid bounds.

    :param lng: Longitude value to validate (must be in range [-180.0, 180.0])
    :raises ValueError: If longitude is outside valid bounds (-180 to 180)
    """
    if not is_valid_lng(lng):
        raise ValueError(f"Invalid longitude {lng}: must be in range [-180.0, 180.0]")


def validate_coordinates(lng: float, lat: float) -> tuple[float, float]:
    """
    Validate and convert coordinates to floats with bounds checking.

    Validates both longitude and latitude are within acceptable ranges.
    Accepts numeric types and converts them to float.

    :param lng: Longitude value (-180.0 to 180.0)
    :param lat: Latitude value (-90.0 to 90.0)
    :return: Tuple of (lng, lat) as floats
    :raises ValueError: If coordinates are invalid or out of bounds
    :raises TypeError: If coordinates cannot be converted to float
    """
    try:
        lng, lat = float(lng), float(lat)
    except (TypeError, ValueError) as e:
        raise TypeError(
            f"Coordinates must be numeric. Got lng={type(lng).__name__}, "
            f"lat={type(lat).__name__}"
        ) from e
    validate_lng(lng)
    validate_lat(lat)
    return lng, lat


def close_resource(obj: Any) -> None:
    """
    Safely close a resource object, suppressing expected errors.

    Attempts to call the close() method on the given object. If the object is None
    or doesn't have a close() method, this is silently ignored. Expected errors during
    closure (AttributeError, OSError, ValueError) are also suppressed.

    This is useful for cleanup operations where some resources may not exist or may fail
    to close without affecting program flow.

    :param obj: Object to close (typically a file or stream), can be None
    """
    if obj is None:
        return
    try:
        obj.close()
    except (AttributeError, OSError, ValueError):
        # Suppress expected errors during resource closure
        pass


def is_ocean_timezone(timezone_name: str) -> bool:
    """
    Check if a timezone name represents an ocean timezone.

    Ocean timezones follow the pattern 'Etc/GMT±XX' and represent fixed-offset
    zones used in oceans and international waters.

    :param timezone_name: The timezone name to check
    :return: True if the timezone is an ocean timezone, False otherwise
    :raises TypeError: If timezone_name is not a string
    """
    if not isinstance(timezone_name, str):
        raise TypeError(
            f"timezone_name must be a string, got {type(timezone_name).__name__}"
        )
    return re.match(OCEAN_TIMEZONE_PREFIX, timezone_name) is not None


def get_boundaries_dir(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the boundaries directory."""
    return data_dir / "boundaries"


def get_holes_dir(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the holes directory."""
    return data_dir / "holes"


def get_hole_registry_path(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the hole registry file."""
    return data_dir / "hole_registry.json"
