"""utility functions

JIT compiled for efficiency in case `numba` is installed

"""

import numpy as np

from timezonefinder.configs import (
    MAX_LAT_VAL,
    MAX_LNG_VAL,
    MIN_LAT_VAL,
    MIN_LNG_VAL,
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


# The bounds test is written out here rather than calling ``is_valid_lat`` /
# ``is_valid_lng``, which are plain Python functions: numba cannot call one from nopython
# mode. They are plain because a scalar comparison is not worth a dispatch boundary - see
# their comment in ``timezonefinder/utils_numba.py`` - and these are the compiled form of
# the same test, over a whole ring at a time, where the dispatch amortises to nothing.
#
# The bounds are the same module-level constants those read, so the two forms cannot
# disagree about where the world ends;
# ``tests/test_property_validation.py`` holds them to each other over the whole float
# domain.
@njit(boolean(FloatCoordType1D), cache=True)
def is_valid_lat_vec(lats: np.ndarray) -> bool:
    for lat in lats:
        if not (MIN_LAT_VAL <= lat <= MAX_LAT_VAL):
            return False
    return True


@njit(boolean(FloatCoordType1D), cache=True)
def is_valid_lng_vec(lngs: np.ndarray) -> bool:
    for lng in lngs:
        if not (MIN_LNG_VAL <= lng <= MAX_LNG_VAL):
            return False
    return True
