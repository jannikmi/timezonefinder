"""
Configuration constants for TimezoneFinder.

This module defines all configuration constants, paths, and type aliases used throughout
the TimezoneFinder package. It includes spatial indexing parameters, coordinate precision,
and type definitions.

Coordinate System:
    - Longitude: -180.0 to 180.0 degrees
    - Latitude: -90.0 to 90.0 degrees
    - Internal representation: scaled to integer values for precision
    - Scaling factor: 10^7 (COORD2INT_FACTOR)
"""

import os
from pathlib import Path
from typing import Any, TypeAlias

import numpy as np

__all__ = [
    "DEFAULT_DATA_DIR",
    "PACKAGE_DIR",
    "SHORTCUT_H3_RES",
    "OCEAN_TIMEZONE_PREFIX",
    "COORD2INT_FACTOR",
    "INT2COORD_FACTOR",
    "MAX_LNG_VAL",
    "MAX_LAT_VAL",
    "MAX_LNG_VAL_INT",
    "MAX_LAT_VAL_INT",
    # Type aliases
    "IntegerLike",
    "ShortcutMapping",
    "CoordPairs",
    "CoordLists",
    "IntLists",
]

# SHORTCUT SETTINGS
# H3 resolution level for spatial indexing shortcuts
# Determines the granularity of the H3 cell grid used for fast lookups
SHORTCUT_H3_RES: int = 3

# Pattern for identifying ocean timezones (fixed-offset zones for international waters)
OCEAN_TIMEZONE_PREFIX = r"Etc/GMT"

# PATHS
PACKAGE_DIR = Path(__file__).parent
DEFAULT_DATA_DIR = PACKAGE_DIR / "data"


# COORDINATE SCALING AND PRECISION
# Integer representation uses signed 4-byte (32-bit) integers
# Allows storing coordinate values multiplied by 10^7 for microdegree precision
# i = signed 4byte integer
NR_BYTES_I = 4
# IMPORTANT: all values between -180 and 180 degree must fit into the domain of i4!
# is the same as testing if 360 fits into the domain of I4 (unsigned!)
MAX_ALLOWED_COORD_VAL = 2 ** (8 * NR_BYTES_I - 1)

# from math import floor,log10
# DECIMAL_PLACES_SHIFT = floor(log10(MAX_ALLOWED_COORD_VAL/180.0)) # == 7
# This value is critical: changing it invalidates all precomputed data
DECIMAL_PLACES_SHIFT = 7
INT2COORD_FACTOR = 10 ** (
    -DECIMAL_PLACES_SHIFT
)  # Convert from int to degrees: divide by 10^7
COORD2INT_FACTOR = (
    10**DECIMAL_PLACES_SHIFT
)  # Convert from degrees to int: multiply by 10^7
MAX_LNG_VAL = 180.0
MAX_LAT_VAL = 90.0
MAX_LNG_VAL_INT = int(MAX_LNG_VAL * COORD2INT_FACTOR)
MAX_LAT_VAL_INT = int(MAX_LAT_VAL * COORD2INT_FACTOR)
MAX_INT_VAL = MAX_LNG_VAL_INT
assert MAX_INT_VAL < MAX_ALLOWED_COORD_VAL

# TYPES
# used in Numba JIT compiled function signatures in utils_numba.py
# NOTE: Changes in the global settings might not immediately affect
#  the functions due to caching!

# Type alias for flexibility with integer types (pure int or numpy integer scalars)
IntegerLike: TypeAlias = int | np.integer

# hexagon id to list of polygon ids
ShortcutMapping: TypeAlias = dict[int, np.ndarray]
CoordPairs: TypeAlias = list[tuple[float, float]]
CoordLists: TypeAlias = list[list[float]]
IntLists: TypeAlias = list[list[int]]


# zone id storage settings ---------------------------------------------------

_ZONE_ID_DTYPE_ALIASES: dict[str, "np.dtype[Any]"] = {
    "uint8": np.dtype("<u1"),
    "uint16": np.dtype("<u2"),
}


def _normalise_zone_id_dtype_key(key: str) -> str:
    """Normalise user provided dtype keys to canonical form."""
    return key.lower().strip()


def get_zone_id_dtype(name: str) -> "np.dtype[Any]":
    """Return the configured numpy dtype for storing zone IDs."""

    try:
        return _ZONE_ID_DTYPE_ALIASES[_normalise_zone_id_dtype_key(name)]
    except KeyError as exc:  # pragma: no cover - defensive, validated on import
        valid = ", ".join(sorted(_ZONE_ID_DTYPE_ALIASES))
        raise ValueError(
            f"Unsupported zone id dtype '{name}'. Choose one of: {valid}"
        ) from exc


def zone_id_dtype_to_string(dtype: np.dtype) -> str:
    """Return the little-endian numpy dtype string for serialisation."""

    return dtype.newbyteorder("<").str


def available_zone_id_dtype_names() -> tuple[str, ...]:
    """Return the supported zone id dtype names."""

    return tuple(sorted(_ZONE_ID_DTYPE_ALIASES))


DEFAULT_ZONE_ID_DTYPE_NAME = os.getenv("TIMEZONEFINDER_ZONE_ID_DTYPE", "uint16")
DEFAULT_ZONE_ID_DTYPE = get_zone_id_dtype(DEFAULT_ZONE_ID_DTYPE_NAME)
