"""Utility functions for TimezoneFinder.

This module provides coordinate validation, resource management, and helper functions
for timezone operations.
"""

from collections.abc import Callable
import math
from pathlib import Path
import re
from typing import Any, Final, get_args

import numpy as np
import numpy.typing as npt

from timezonefinder.configs import (
    COORD2INT_FACTOR,
    DEFAULT_DATA_DIR,
    MAX_LAT_VAL,
    MAX_LNG_VAL,
    NO_ZONE_ID,
    OCEAN_TIMEZONE_PREFIX,
    CoordArrayLike,
    OnInvalid,
)
from timezonefinder import utils_numba, utils_clang

__all__ = [
    "validate_lat",
    "validate_lng",
    "validate_coordinates",
    "coordinate_arrays",
    "out_of_bounds",
    "ON_INVALID_POLICIES",
    "coordinate_resolution",
    "degrees_to_metres",
    "EARTH_EQUATORIAL_RADIUS_M",
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


inside_polygon: Callable[[int, int, np.ndarray], bool]
# at import time fix which "point-in-polygon" implementation will be used
if clang_extension_loaded and not using_numba:
    # use the C implementation only if Numba is not present
    inside_polygon = utils_clang.pt_in_poly_clang
else:
    # use the (JIT compiled) python function if Numba is present or the C extension cannot be loaded
    inside_polygon = utils_numba.pt_in_poly_python


def _validate_coordinate(
    value: float,
    validator: Callable[[float], bool],
    name: str,
    min_bound: float,
    max_bound: float,
) -> None:
    """
    Internal helper for coordinate validation.

    :param value: The coordinate value to validate
    :param validator: Function that returns True if coordinate is valid
    :param name: Name of the coordinate (e.g., 'latitude', 'longitude')
    :param min_bound: Minimum valid bound (for error message)
    :param max_bound: Maximum valid bound (for error message)
    :raises ValueError: If coordinate is outside valid bounds
    """
    if not validator(value):
        raise ValueError(
            f"Invalid {name} {value}: must be in range [{min_bound}, {max_bound}]"
        )


def validate_lat(lat: float) -> None:
    """
    Validate that a latitude value is within valid bounds.

    :param lat: Latitude value to validate (must be in range [-90.0, 90.0])
    :raises ValueError: If latitude is outside valid bounds (-90 to 90)
    """
    _validate_coordinate(lat, is_valid_lat, "latitude", -90.0, 90.0)


def validate_lng(lng: float) -> None:
    """
    Validate that a longitude value is within valid bounds.

    :param lng: Longitude value to validate (must be in range [-180.0, 180.0])
    :raises ValueError: If longitude is outside valid bounds (-180 to 180)
    """
    _validate_coordinate(lng, is_valid_lng, "longitude", -180.0, 180.0)


def validate_coordinates(lng: float, lat: float) -> tuple[float, float]:
    """
    Validate and convert coordinates to floats with bounds checking.

    Validates both longitude and latitude are within acceptable ranges and are finite.
    Accepts numeric types and converts them to float. Rejects NaN and infinity values.

    :param lng: Longitude value (-180.0 to 180.0)
    :param lat: Latitude value (-90.0 to 90.0)
    :return: Tuple of (lng, lat) as floats
    :raises ValueError: If coordinates are invalid, out of bounds, or not finite (NaN/Inf)
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


# --- the same validation, one batch at a time -------------------------------------
#
# The scalar and array forms sit together because they are one contract at two arities,
# and the one place they deliberately differ has to be visible from both: a ``None``
# coordinate. ``float(None)`` raises above, while ``np.asarray(..., dtype=float64)``
# turns it into NaN, so the array form rejects it explicitly rather than letting a
# missing value become an out-of-range coordinate.

#: What ``on_invalid`` accepts on the batch lookups. ``"raise"`` is the default because
#: it is what the scalar methods do, and a batch call is not the place to quietly change
#: the contract; ``"skip"`` exists because raising on element 999,999 and discarding the
#: 999,998 answers already computed is hostile. Derived from
#: :data:`~timezonefinder.configs.OnInvalid` rather than written out again, so the two
#: cannot drift; that alias is also what lets a type checker reject a mistyped policy at
#: the call site instead of leaving it to raise at runtime.
ON_INVALID_POLICIES: Final[tuple[str, ...]] = get_args(OnInvalid)


def coordinate_arrays(
    lngs: CoordArrayLike, lats: CoordArrayLike
) -> tuple[np.ndarray, np.ndarray]:
    """The two input axes as 1-D float64 arrays.

    ``np.asarray`` is what makes the zero-copy path real: a C-contiguous float64 array
    is passed straight through, and anything else is converted once for the whole batch
    rather than per point.

    :raises TypeError: if either axis holds something that is not convertible to float.
    :raises ValueError: if either axis is not one-dimensional, or the two differ in length.
    """
    arrays = []
    for name, values in (("lngs", lngs), ("lats", lats)):
        raw = np.asarray(values)
        # ``None`` is the one unconvertible value numpy does not refuse: an explicit
        # float cast turns it into NaN, which every later stage then reads as an
        # out-of-range coordinate - so under ``on_invalid="skip"`` a null in the
        # caller's data would come back as NO_ZONE_ID, indistinguishable from a point
        # no zone covers. Reject it here, as the scalar methods' ``float()`` does.
        # Only an object array can hold one, which the float64 fast path never is.
        if raw.dtype == object and any(v is None for v in raw.reshape(-1).tolist()):
            raise TypeError(
                f"{name} must hold numbers, but holds None. A missing coordinate has "
                "to be dropped or replaced by the caller: read as a number it would "
                f"become NaN and be answered with {NO_ZONE_ID}, which is also what a "
                "point no timezone covers is answered with."
            )
        try:
            array = np.asarray(raw, dtype=np.float64)
        except (TypeError, ValueError) as e:
            raise TypeError(
                f"{name} must hold numbers convertible to float: {e}"
            ) from e
        if array.ndim != 1:
            raise ValueError(
                f"{name} must be one-dimensional, got shape {array.shape}. "
                "Coordinates are passed one axis per argument, never as an (N, 2) array "
                "whose column order would have to be guessed."
            )
        arrays.append(array)
    lng_array, lat_array = arrays
    if lng_array.shape != lat_array.shape:
        raise ValueError(
            "lngs and lats must hold the same number of coordinates, got "
            f"{lng_array.shape[0]} and {lat_array.shape[0]}"
        )
    return lng_array, lat_array


def out_of_bounds(lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
    """Which coordinates no lookup can answer, as a boolean mask.

    A bound comparison rejects NaN and infinity as a side effect - both compare ``False``
    against everything - so this is the whole of what ``utils.validate_coordinates`` does
    per point, in two vectorised passes instead of 2N calls.
    """
    return ~((np.abs(lngs) <= MAX_LNG_VAL) & (np.abs(lats) <= MAX_LAT_VAL))


# --- how finely a coordinate can be represented -----------------------------------
#
# Two dtypes carry a coordinate in this package and they degrade in opposite ways: a
# float resolves *relative* to magnitude, so it is worst near +-180, while the packaged
# int32 is fixed point and resolves the same everywhere. The functions below compute
# both, so the resolution this package claims is derived rather than restated -
# `tests/test_coordinate_precision.py` checks the documented figures against them.

#: WGS84 semi-major axis. The metre figures here are quoted at the equator, where a
#: degree of longitude is longest and the ground error of a fixed step is therefore
#: worst - so a distance derived from it is an upper bound, which is what a resolution
#: claim needs to be.
EARTH_EQUATORIAL_RADIUS_M: Final[float] = 6_378_137.0


def degrees_to_metres(degrees: float, at_latitude: float = 0.0) -> float:
    """Ground distance spanned by an angle of longitude, on a WGS84-radius sphere.

    Longitude, because that is the axis whose degree is longest and whose quantisation
    error is therefore the worst case. A degree of longitude shrinks with ``cos(lat)``,
    so the default of the equator is the bound rather than a typical value.

    Spherical, not ellipsoidal: the difference is ~0.3 %, far below the precision any
    claim here is stated to, and an exact geodesic would need a dependency for a figure
    used only to describe an order of magnitude.

    :param degrees: the angle to convert, in degrees.
    :param at_latitude: latitude at which to measure, in degrees. Default: the equator.
    :return: the distance in metres.
    """
    metres_per_degree = math.pi * EARTH_EQUATORIAL_RADIUS_M / 180.0
    return degrees * metres_per_degree * math.cos(math.radians(at_latitude))


def coordinate_resolution(
    dtype: npt.DTypeLike, at_degrees: float = MAX_LNG_VAL
) -> float:
    """The smallest difference in degrees that ``dtype`` can represent - its ULP.

    The two storage forms answer this differently, which is the whole point of asking:

    * **A floating-point dtype** spaces its values relative to their magnitude, so the
      answer depends on ``at_degrees`` and is worst at the largest coordinate, +-180.
      This is what decides whether a caller's array is precise enough to be worth
      looking up: ``float32`` resolves ~1.7 m there, over a hundred times coarser than
      the packaged data, so a point near a border can round to the wrong side of it.
    * **An integer dtype** is read as fixed point scaled by ``COORD2INT_FACTOR``, so one
      unit is one step everywhere on the globe and ``at_degrees`` does not enter. That
      even spacing is why the packaged data is stored this way.

    :param dtype: anything ``numpy.dtype`` accepts - a floating or integer type.
    :param at_degrees: the coordinate magnitude to measure at. Ignored for integer
        dtypes, which are evenly spaced. Default: the largest valid longitude, the
        worst case for a float.
    :return: the representable step at that point, in degrees. Pair it with
        :func:`degrees_to_metres` for a ground distance.
    :raises TypeError: if ``dtype`` is neither floating nor integer.
    :raises ValueError: if an integer ``dtype`` is too narrow to hold the scaled
        coordinate range at all, since its step would then be beside the point.

    Example:
        >>> import numpy as np
        >>> round(degrees_to_metres(coordinate_resolution(np.int32)) * 100, 2)
        1.11
    """
    dtype = np.dtype(dtype)
    if np.issubdtype(dtype, np.floating):
        return float(np.spacing(np.asarray(abs(at_degrees), dtype=dtype)))
    if np.issubdtype(dtype, np.integer):
        widest = int(np.iinfo(dtype).max)
        needed = int(MAX_LNG_VAL * COORD2INT_FACTOR)
        if widest < needed:
            raise ValueError(
                f"{dtype.name} cannot hold a scaled coordinate: +-180 degrees scaled by "
                f"{COORD2INT_FACTOR:,} needs {needed:,} and {dtype.name} holds at most "
                f"{widest:,}. Its step is not the limiting factor - it cannot address "
                "the globe."
            )
        return 1.0 / COORD2INT_FACTOR
    raise TypeError(
        f"a coordinate is stored as a float or as a scaled integer, not as {dtype.name}"
    )


def close_resource(obj: Any) -> None:
    """
    Safely close a resource object, suppressing expected errors.

    Attempts to call the close() method on the given object. If the object is None
    or doesn't have a close() method, this is silently ignored. Expected errors during
    closure (AttributeError, OSError, ValueError, BufferError) are also suppressed.

    ``BufferError`` is raised by ``mmap.close()`` ("cannot close exported pointers
    exist") while zero-copy views onto the mapping are still alive - polygon
    coordinate arrays are such views (see ``flatbuf.io.polygons``). Refusing to close
    is a safety guarantee rather than a failure: unmapping while views reference the
    memory would leave them dangling. Closing is then merely deferred - the mapping is
    released once the last view is dropped and nothing else references the mmap object.
    Callers that suppress this must therefore also drop their own references to the
    mmap, as ``FileCoordAccessor.cleanup()`` does, otherwise the mapping stays alive
    for as long as the caller does.

    This is useful for cleanup operations where some resources may not exist or may fail
    to close without affecting program flow.

    :param obj: Object to close (typically a file or stream), can be None
    """
    if obj is None:
        return
    try:
        obj.close()
    except (AttributeError, OSError, ValueError, BufferError):
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
