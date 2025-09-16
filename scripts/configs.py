from pathlib import Path
from typing import Set
from typing import Dict, List, Tuple
from numpy.typing import NDArray
import numpy as np

from timezonefinder.configs import SHORTCUT_H3_RES

SCRIPT_FOLDER = Path(__file__).parent
PROJECT_ROOT = SCRIPT_FOLDER.parent
DOC_ROOT = PROJECT_ROOT / "docs"
DATA_REPORT_FILE = DOC_ROOT / "data_report.rst"
DEFAULT_INPUT_PATH = PROJECT_ROOT / "tmp" / "combined-with-oceans-now.json"

# DEBUG = False
DEBUG = True

# lower the shortcut resolution for debugging
SHORTCUT_H3_RES = 0 if DEBUG else SHORTCUT_H3_RES


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


# Type aliases for better readability and conciseness
CoordinateArray = NDArray[np.int32]  # Polygon coordinate arrays
PolygonList = List[CoordinateArray]  # List of polygon coordinate arrays
HoleRegistry = Dict[int, Tuple[int, int]]  # Polygon ID -> (num_holes, first_hole_id)
ZoneIdArray = NDArray[np.uint16]  # Zone ID array
BoundaryArray = NDArray[np.int32]  # Boundary coordinate array
LengthList = List[int]  # List of coordinate counts
HoleLengthList = List[int]  # List of hole coordinate counts
PolynrHolesList = List[int]  # List of polygon numbers that have holes
ShortcutMapping = Dict[int, List[int]]
