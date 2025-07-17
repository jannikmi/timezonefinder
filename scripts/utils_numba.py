"""utility functions

JIT compiled for efficiency in case `numba` is installed

"""

import numpy as np

from timezonefinder.utils_numba import (
    CoordType,
    is_valid_lat,
    is_valid_lng,
    pt_in_poly_python,
)

try:
    from numba import njit, boolean, f8
    from numba.types import Array

    using_numba = True
except ImportError:
    using_numba = False
    # replace Numba functionality with "transparent" implementations
    from timezonefinder._numba_replacements import njit, boolean, Array, f8

FloatCoordType1D = Array(f8, 1, "A")


@njit(boolean(CoordType, CoordType), cache=True)
def any_pt_in_poly(coords1: np.ndarray, coords2: np.ndarray) -> bool:
    # pt = points[:, i]
    for pt in coords1.T:
        if pt_in_poly_python(pt[0], pt[1], coords2):
            return True
    return False


@njit(boolean(CoordType, CoordType), cache=True)
def fully_contained_in_hole(poly: np.ndarray, hole: np.ndarray) -> bool:
    for pt in poly.T:
        if not pt_in_poly_python(pt[0], pt[1], hole):
            return False
    return True


@njit(boolean(FloatCoordType1D), cache=True)
def is_valid_lat_vec(lats: np.ndarray) -> bool:
    for lat in lats:
        if not is_valid_lat(lat):
            return False
    return True


@njit(boolean(FloatCoordType1D), cache=True)
def is_valid_lng_vec(lngs: np.ndarray) -> bool:
    for lng in lngs:
        if not is_valid_lng(lng):
            return False
    return True
