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
from typing import Any, Final, TypeAlias

import numpy as np

import timezonefinder_data

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
    "DATA_VERSION_FILENAME",
    "UNKNOWN_DATA_VERSION",
    "DATA_FORMAT_VERSION",
    "DATA_FORMAT_LAYOUT_VERSIONS",
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

# Where the packaged boundary data lives. It ships in its own distribution
# (``timezonefinder-data``) so that a dataset update needs no release of
# this package, which is why this is an import rather than ``PACKAGE_DIR / "data"``.
# The name stays: seven path helpers across four modules take it as their default
# argument, and ``AbstractTimezoneFinder`` is the only consumer for which it is more
# than a default. A real filesystem path is required - ``FileCoordAccessor`` mmaps
# through ``fileno()`` - which a normal wheel install provides.
DEFAULT_DATA_DIR = timezonefinder_data.DATA_DIR

# The dataset version stamp written into each generated data directory by
# ``scripts/file_converter.py`` (mirroring the repo-root ``DATA_VERSION`` the
# data was built from). Declared here so the runtime side (``AbstractTimezoneFinder``
# .data_version) and the build side (``scripts/file_converter.py``) share one
# filename - a second copy would silently stop tracking this one.
DATA_VERSION_FILENAME = "data_version.txt"

# What that stamp reads when the data was compiled from an input whose upstream
# release nobody stated (``scripts/file_converter.py`` without ``--data-version``, on
# anything but the packaged input). Naming a release the data may not come from would
# be worse than admitting the gap: the value exists to be trusted.
UNKNOWN_DATA_VERSION = "unknown"


# DATASET FORMAT GENERATION
# The generation of the binary data format as a whole, and the major version of the
# ``timezonefinder-data`` distribution (``1.2026.3`` is format 1 built from upstream
# release 2026c). That is what it is for: `timezonefinder` requires
# ``timezonefinder-data>=<floor>,<DATA_FORMAT_VERSION + 1>``, so every future release
# of this format still satisfies the bound - a data update needs no code release -
# while data written in the *next* format is refused by the resolver rather than at
# the first lookup. Bump it whenever either per-file layout version below moves.
#
# Packaging-level and dataset-wide, and deliberately a separate number from the
# per-file ``POLYGON_LAYOUT_VERSION`` / ``SHORTCUT_LAYOUT_VERSION``. Merging the three
# into one field written into every binary would rewrite the 63 MB coordinate file to
# record a shortcut-format change that did not touch its layout, and those binaries
# are committed.
DATA_FORMAT_VERSION: Final[int] = 1

# What this generation is made of: the per-file layout versions in force when
# DATA_FORMAT_VERSION was last bumped. Restated rather than imported, because
# ``flatbuf.io`` imports *this* module - and because the point is to pin the pairing,
# not to derive one side from the other. The implication runs one way only: a moved
# per-file version requires a moved DATA_FORMAT_VERSION, or data in a format no
# released bound can express ships under a version that claims the old one.
# tests/test_data_version.py asserts it; nothing else would notice.
DATA_FORMAT_LAYOUT_VERSIONS: Final[dict[str, int]] = {
    "POLYGON_LAYOUT_VERSION": 1,
    "SHORTCUT_LAYOUT_VERSION": 1,
}


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
