from pathlib import Path
from typing import TypeAlias
from numpy.typing import NDArray
import numpy as np

from timezonefinder.configs import (
    DEFAULT_ZONE_ID_DTYPE,
    DEFAULT_ZONE_ID_DTYPE_NAME,
    SHORTCUT_H3_RES,
    available_zone_id_dtype_names,
    get_zone_id_dtype,
    zone_id_dtype_to_string,
)

SCRIPT_FOLDER = Path(__file__).parent
PROJECT_ROOT = SCRIPT_FOLDER.parent
DOC_ROOT = PROJECT_ROOT / "docs"
DATA_REPORT_FILE = DOC_ROOT / "data_report.rst"
PERFORMANCE_REPORT_FILE = DOC_ROOT / "benchmark_results_timezonefinding.rst"
POLYGON_REPORT_FILE = DOC_ROOT / "benchmark_results_polygon.rst"
INITIALIZATION_REPORT_FILE = DOC_ROOT / "benchmark_results_initialization.rst"
MEMORY_REPORT_FILE = DOC_ROOT / "benchmark_results_memory.rst"
DEFAULT_INPUT_PATH = PROJECT_ROOT / "tmp" / "combined-with-oceans.json"

# The timezone-boundary-builder release the packaged binary data was built
# from, written by update_data.sh once a parse has succeeded. Declared here
# because three unrelated consumers stamp or validate against it - the
# benchmark fixture metadata (scripts/generate_benchmark_fixtures.py), the data
# report (scripts/reporting.py) and the fixture loader (tests/auxiliaries.py) -
# and a second copy of the path would silently stop tracking this one.
DATA_VERSION_FILE = PROJECT_ROOT / "DATA_VERSION"


def read_data_version() -> str:
    """The release tag of the boundary data currently packaged, e.g. ``"2026c"``."""
    return DATA_VERSION_FILE.read_text(encoding="utf-8").strip()


DEBUG = False
# DEBUG = True

# lower the shortcut resolution for debugging
SHORTCUT_H3_RES = 0 if DEBUG else SHORTCUT_H3_RES


# Lower bound on the share of holes stored as a reference to an identical boundary
# polygon rather than as their own copy of the ring (see HoleCollection.poly_refs).
# The deduplication is worth ~7% of the packaged coordinate data, and it rests on how
# the upstream builder emits enclaves - which is a convention, not a guarantee. A
# release that changed it would still compile and still return correct timezones, just
# with the shipped data quietly re-inflated, so the ratio is asserted rather than
# reported. Measured 96.4% on release 2026c; the floor sits well below that so that
# ordinary dataset churn does not trip it.
MIN_HOLE_DEDUP_RATIO = 0.9

DEBUG_ZONE_CTR_STOP = 5  # parse only some polygons in debugging mode
HexIdSet: TypeAlias = set[int]
PolyIdSet: TypeAlias = set[int]
ZoneIdSet: TypeAlias = set[int]

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
CoordinateArray: TypeAlias = NDArray[np.int32]  # Polygon coordinate arrays
PolygonList: TypeAlias = list[CoordinateArray]  # List of polygon coordinate arrays
HoleRegistry: TypeAlias = dict[
    int, tuple[int, int]
]  # Polygon ID -> (num_holes, first_hole_id)
ZoneIdArray: TypeAlias = NDArray[np.unsignedinteger]
BoundaryArray: TypeAlias = NDArray[np.int32]  # Boundary coordinate array
LengthList: TypeAlias = list[int]  # List of coordinate counts
HoleLengthList: TypeAlias = list[int]  # List of hole coordinate counts
PolynrHolesList: TypeAlias = list[int]  # List of polygon numbers that have holes
ShortcutMapping: TypeAlias = dict[int, list[int]]


ZONE_ID_DTYPE = DEFAULT_ZONE_ID_DTYPE
ZONE_ID_DTYPE_NUMPY_FORMAT = zone_id_dtype_to_string(ZONE_ID_DTYPE)
ZONE_ID_DTYPE_NAME = DEFAULT_ZONE_ID_DTYPE_NAME
ZONE_ID_DTYPE_CHOICES = available_zone_id_dtype_names()


def resolve_zone_id_dtype(name: str) -> np.dtype:
    """Return the numpy dtype for zone ids based on user configuration."""

    return get_zone_id_dtype(name)
