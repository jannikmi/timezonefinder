from pathlib import Path
from typing import Set

SCRIPT_FOLDER = Path(__file__).parent
PROJECT_ROOT = SCRIPT_FOLDER.parent
DEFAULT_INPUT_PATH = SCRIPT_FOLDER / "combined-with-oceans.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "timezonefinder"  # overwrite the old data files

DEBUG = False
# DEBUG = True
DEBUG_ZONE_CTR_STOP = 5  # parse only some polygons in debugging mode
MAX_LAT = 90.0
MAX_LNG = 180.0
HexIdSet = Set[int]
PolyIdSet = Set[int]
ZoneIdSet = Set[int]
