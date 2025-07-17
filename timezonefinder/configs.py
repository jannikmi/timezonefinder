from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# SHORTCUT SETTINGS
# h3 library
SHORTCUT_H3_RES: int = 3

OCEAN_TIMEZONE_PREFIX = r"Etc/GMT"

# PATHS
DEFAULT_DATA_DIR = Path(__file__).parent / "data"


# i = signed 4byte integer
NR_BYTES_I = 4
# IMPORTANT: all values between -180 and 180 degree must fit into the domain of i4!
# is the same as testing if 360 fits into the domain of I4 (unsigned!)
MAX_ALLOWED_COORD_VAL = 2 ** (8 * NR_BYTES_I - 1)

# from math import floor,log10
# DECIMAL_PLACES_SHIFT = floor(log10(MAX_ALLOWED_COORD_VAL/180.0)) # == 7
DECIMAL_PLACES_SHIFT = 7
INT2COORD_FACTOR = 10 ** (-DECIMAL_PLACES_SHIFT)
COORD2INT_FACTOR = 10**DECIMAL_PLACES_SHIFT
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

# hexagon id to list of polygon ids
ShortcutMapping = Dict[int, np.ndarray]
CoordPairs = List[Tuple[float, float]]
CoordLists = List[List[float]]
IntLists = List[List[int]]
