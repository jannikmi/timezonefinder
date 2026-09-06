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
from typing import Any, Final, Literal, TypeAlias

import numpy as np
import numpy.typing as npt

import timezonefinder_data

__all__ = [
    "DEFAULT_DATA_DIR",
    "PACKAGE_DIR",
    "SHORTCUT_H3_RES",
    "OCEAN_TIMEZONE_PREFIX",
    "COORD2INT_FACTOR",
    "INT2COORD_FACTOR",
    "SOURCE_COORD_STEP",
    "MIN_LNG_VAL",
    "MIN_LAT_VAL",
    "MAX_LNG_VAL",
    "MAX_LAT_VAL",
    "MAX_LNG_VAL_INT",
    "MAX_LAT_VAL_INT",
    "DATA_VERSION_FILENAME",
    "UNKNOWN_DATA_VERSION",
    "DATA_FORMAT_VERSION",
    "DATA_FORMAT_LAYOUT_VERSIONS",
    "POLYGON_BLOCK_SIZE",
    "BLOCK_RANGE_DTYPE",
    "BLOCK_OFFSET_DTYPE",
    "BLOCK_BASE_DTYPE",
    "BLOCK_WIDTH_DTYPE",
    "BLOCK_PAYLOAD_OFFSET_DTYPE",
    "VERTEX_COUNT_DTYPE",
    "NO_ZONE_ID",
    "ZONE_ID_RESULT_DTYPE",
    # Type aliases
    "CoordArrayLike",
    "IdArrayLike",
    "OnInvalid",
    "IntegerLike",
    "ShortcutMapping",
    "CoordPairs",
    "CoordLists",
    "IntLists",
]

# SHORTCUT SETTINGS
# H3 resolution level for spatial indexing shortcuts
# Determines the granularity of the H3 cell grid used for fast lookups
SHORTCUT_H3_RES: int = 4

# Pattern for identifying ocean timezones (fixed-offset zones for international waters)
OCEAN_TIMEZONE_PREFIX = r"Etc/GMT"

# What an array of zone ids holds where the scalar methods answer ``None``: a cell no
# timezone covers, or - under ``on_invalid="skip"`` - a coordinate that was rejected.
# One sentinel for both is what lets a batch answer stay a single integer array; a
# caller that needs to tell the two apart can re-derive the bounds check in one
# vectorised comparison, which is cheaper than the second array it would otherwise cost
# every caller that does not care.
#
# -1 rather than a large value because it is what an id lookup conventionally answers
# with, and because the public id-taking methods now *reject* negative ids - so a
# sentinel fed back in raises instead of silently selecting the last zone from the end.
NO_ZONE_ID: Final[int] = -1

# dtype of a batch of zone ids. Signed, because NO_ZONE_ID is negative, and 16-bit
# because that is the narrowest width the dataset fits: a zone id is an index into the
# zone names, of which the packaged data has ~450 against this width's 32,767, and the
# shortcut table already stores those same ids as int16. The bound is not left to hold
# by luck - ``timezonefinder._data_integrity.validate_shortcut_index`` refuses a data directory
# whose zone count outgrows it, at build time and over the committed data, which is
# where a width chosen by fit has to be checked. A wider dtype would double the answer
# array for headroom no dataset can reach.
ZONE_ID_RESULT_DTYPE: Final[np.dtype] = np.dtype(np.int16)

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
DATA_FORMAT_VERSION: Final[int] = 3

# What this generation is made of: the per-file layout versions in force when
# DATA_FORMAT_VERSION was last bumped. Restated rather than imported, because
# ``flatbuf.io`` imports *this* module - and because the point is to pin the pairing,
# not to derive one side from the other. The implication runs one way only: a moved
# per-file version requires a moved DATA_FORMAT_VERSION, or data in a format no
# released bound can express ships under a version that claims the old one.
# tests/test_data_version.py asserts it; nothing else would notice.
DATA_FORMAT_LAYOUT_VERSIONS: Final[dict[str, int]] = {
    "POLYGON_LAYOUT_VERSION": 3,
    "SHORTCUT_LAYOUT_VERSION": 2,
}


# POLYGON BLOCK INDEX
# How many vertices of a ring share one entry of the latitude block index, which is
# what lets the point-in-polygon kernels skip the parts of a ring a horizontal ray
# cannot cross (``scripts/block_index.py`` builds it, ``docs/data_format.rst``
# describes it). Part of what polygon layout 2 *means*: the stored ranges are only
# interpretable together with this number, and the rings are rotated to suit it, so
# changing it changes every boundary file and must move POLYGON_LAYOUT_VERSION with it.
#
# 128 is measured rather than assumed. Over the real (point, polygon) pairs the
# committed fixtures produce, it minimises edge tests plus block tests; 32 and 512 both
# cost more (`prototypes/polygon_block_encoding.py`, section `skip`, and
# `scripts/tune_block_size.py` re-runs the sweep over the packaged data). Smaller
# blocks skip more finely and cost more range comparisons; larger ones the reverse.
POLYGON_BLOCK_SIZE: Final[int] = 128

# One block's stored ``[min, max]`` latitude pair. Same width as a coordinate because
# that is what it is - a latitude out of the ring it indexes, compared directly against
# the query's scaled latitude with no conversion on the lookup path.
BLOCK_RANGE_DTYPE: Final[np.dtype] = np.dtype("<i4")

# Where each ring's blocks start in the flat range array. Unsigned and 32 bit because
# the packaged boundaries hold ~62.6k blocks and a 16-bit column would already have
# wrapped; the converter refuses a collection that outgrows this one
# (``scripts.block_index.build_block_index``).
BLOCK_OFFSET_DTYPE: Final[np.dtype] = np.dtype("<u4")


# POLYGON BLOCK PAYLOAD
# What the coordinates themselves are stored as, since polygon layout 3: bit-packed
# residuals against one coordinate frame per block. ``timezonefinder/block_payload.py``
# describes the encoding and owns both directions of it.

# A block frame's x origin, one per block. The same width as a coordinate because that
# is what it is - the minimum longitude the block's vertices take. There is no y column:
# the latitude index's ``[min, max]`` pair already opens with the y origin, and storing
# it twice would hold ~0.24 MiB of duplicate numbers resident (see
# ``timezonefinder/block_payload.py``).
BLOCK_BASE_DTYPE: Final[np.dtype] = np.dtype("<i4")

# How many bits one residual occupies, per block and axis. A bit *length*, so 0 means an
# axis the block is constant on and stores nothing for; 32 is the ceiling, reached by
# the blocks of rings that straddle the antimeridian.
BLOCK_WIDTH_DTYPE: Final[np.dtype] = np.dtype("u1")

# Where a block's residuals begin. Derived when a collection is loaded rather than
# stored - the widths and the vertex counts already say it.
#
# **The bound is the whole collection's payload, not one ring's.** The derivation
# (``timezonefinder.block_payload.derive_payload_offsets``) produces ring-relative
# offsets, and ``PolygonArray.__init__`` then adds each ring's own start so the kernels
# take one array and no per-ring rebasing - so what this width has to hold is a word
# index into the entire coordinate buffer. For the packaged 2026c boundaries that is
# 7,933,908 of the 4,294,967,295 this dtype addresses; the largest single ring's payload,
# ~1.2 MB, is the wrong quantity to check it against and was what this comment used to
# name. ``timezonefinder._data_integrity.validate_payload_offset_width`` is what checks
# the right one, over the data as it is produced - the addition in ``PolygonArray`` is
# unsigned arithmetic that would wrap rather than raise.
BLOCK_PAYLOAD_OFFSET_DTYPE: Final[np.dtype] = np.dtype("<u4")

# How many vertices a ring holds. Stored per ring because a packed payload's length no
# longer says it: the byte count depends on the block widths, so the ragged last block's
# vertex count cannot be read back out of it.
VERTEX_COUNT_DTYPE: Final[np.dtype] = np.dtype("<u4")


# COORDINATE SCALING AND PRECISION
# Integer representation uses signed 4-byte (32-bit) integers
# Coordinate values are stored multiplied by 10^7, so one unit is 10^-7 degrees -
# a tenth of a microdegree, ~1.11 cm of longitude at the equator, which is the
# worst case. `timezonefinder.utils.coordinate_resolution` derives that figure and
# `tests/test_coordinate_precision.py` holds the documented claims to it.
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
# What one step of the *source* grid is, in the units above. timezone-boundary-builder
# publishes at most six decimal places, so every boundary coordinate it states is a
# multiple of ten of our tenth-of-a-microdegree steps. The packaged data is stored on
# that grid rather than on the finer one: the seventh digit carries no information the
# source has, and storing it costs ~6.4 MB of residual width to reproduce a truncation
# artifact. `scripts.utils.source_coord2int` is what holds the conversion to it, and
# `timezonefinder/block_payload.py` what stores residuals in units of it.
#
# Queries are NOT quantised, and the asymmetry is deliberate. A boundary is the polygon
# *through* those vertices, so its edges are continuous lines between them and a point's
# side of one is determined at any precision the caller can supply - a query 1.1 cm from
# an edge is genuinely on one side of it, however coarsely the edge's endpoints are
# stated. Rounding the query onto this grid too would discard up to half a step of the
# caller's own position and flip the answer for points within ~5.5 cm of an edge, to buy
# nothing: the kernel's arithmetic is exact integer either way, since a residual is
# scaled back by this constant rather than the query being divided by it.
SOURCE_COORD_STEP: Final[int] = 10

MAX_LNG_VAL = 180.0
MAX_LAT_VAL = 90.0
# Declared negative rather than derived with a `-` where they are read, because the
# negation is what costs. `validate_coordinates` with the pure-Python validators the
# tracked no-numba configuration runs, three forms rotated round by round, min/median
# ns per call: literals 244/249, `MIN_LAT_VAL <= lat <= MAX_LAT_VAL` 250/253, and
# `-MAX_LAT_VAL <= lat <= MAX_LAT_VAL` 295/299. The global load is a few nanoseconds on
# a specialising interpreter - ~0.5 % of a unique-shortcut query, which no benchmark
# here can resolve - while the `UNARY_NEGATIVE` costs ten times that. So do not
# "simplify" these into negations at the call sites: `validate_coordinates` runs on
# every query.
MIN_LNG_VAL = -180.0
MIN_LAT_VAL = -90.0
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

# What the batch lookup accepts per coordinate axis: anything ``np.asarray`` turns into
# a 1-D float array - a list, a tuple, an ``array.array``, a numpy array, a pandas
# Series. Deliberately not narrowed, to ``np.ndarray`` or to a ``Sequence`` either: an
# API that only served numpy users would make every other caller convert before it can
# ask, which is the loop this replaces, and a ``Sequence`` bound would reject the pandas
# Series that is the single most likely thing to be handed to a batch lookup. The
# contract is ``__array__`` and the sequence protocol, which is why no library is named
# in the code - `test_anything_exposing_array_is_accepted` pins it without importing one.
CoordArrayLike: TypeAlias = npt.ArrayLike

# The same, for a batch of zone *ids* rather than coordinates. A separate name for the
# same underlying type on purpose: the two are converted with different dtypes and reject
# different things, and an annotation reading "coordinates" on an id argument would be
# taken at its word.
IdArrayLike: TypeAlias = npt.ArrayLike

# What a batch lookup does with a coordinate no lookup can answer. A ``Literal`` rather
# than ``str`` so that a mistyped policy is a type error at the call site instead of a
# ``ValueError`` after the caller has shipped - mypy runs in this repository's
# pre-commit hook, so the check costs nothing. The runtime tuple the error message
# lists is derived from this alias rather than written out again.
OnInvalid: TypeAlias = Literal["raise", "skip"]

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
