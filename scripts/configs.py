from pathlib import Path
from typing import Set

SCRIPT_FOLDER = Path(__file__).parent
DEFAULT_INPUT_PATH = SCRIPT_FOLDER / "combined-with-oceans.json"
# DEFAULT_INPUT_PATH = SCRIPT_FOLDER / "combined.json"
DEFAULT_OUTPUT_PATH = SCRIPT_FOLDER  # store parsed data in same directory as default

DEBUG = False
DEBUG_POLY_STOP = 71  # parse only some polygons in debugging mode
MAX_LAT = 90.0
MAX_LNG = 180.0
HexIdSet = Set[int]
PolyIdSet = Set[int]
ZoneIdSet = Set[int]
