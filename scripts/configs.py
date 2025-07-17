from pathlib import Path
from typing import Set

SCRIPT_FOLDER = Path(__file__).parent
PROJECT_ROOT = SCRIPT_FOLDER.parent
DEFAULT_INPUT_PATH = PROJECT_ROOT / "tmp" / "combined-with-oceans.json"

DEBUG = False
# DEBUG = True
DEBUG_ZONE_CTR_STOP = 5  # parse only some polygons in debugging mode
MAX_LAT = 90.0
MAX_LNG = 180.0
HexIdSet = Set[int]
PolyIdSet = Set[int]
ZoneIdSet = Set[int]

# BINARY DATA TYPES
# https://docs.python.org/3/library/struct.html#format-characters
# H = unsigned short (2 byte integer)
NR_BYTES_H = 2
DTYPE_FORMAT_H_NUMPY = "<u2"
THRES_DTYPE_H = 2 ** (NR_BYTES_H * 8)  # = 65536

# i = signed 4byte integer
DTYPE_FORMAT_SIGNED_I_NUMPY = "<i4"

# f = 8byte signed float
DTYPE_FORMAT_F_NUMPY = "<f8"
