from collections.abc import Sequence
from pathlib import Path
from typing import TypeAlias, TypedDict
from numpy.typing import NDArray
import numpy as np

from timezonefinder.configs import (
    DEFAULT_ZONE_ID_DTYPE,
    UNKNOWN_DATA_VERSION,
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


def resolve_data_version(input_path: Path | str, explicit: str | None = None) -> str:
    """The boundary data release a parse of ``input_path`` may claim to come from.

    Only the caller knows which upstream release a GeoJSON was downloaded from, so an
    ``explicit`` tag wins - ``update_data.sh`` passes the one it recorded at download
    time, which is also why the stamp is correct before ``DATA_VERSION`` is updated.

    Without it, :data:`DATA_VERSION_FILE` describes exactly one input - the packaged
    :data:`DEFAULT_INPUT_PATH`, which *is* the release it names - and nothing else.
    Stamping it onto an arbitrary GeoJSON would make ``TimezoneFinder.data_version``
    answer with a release the data did not come from, silently and with nothing to
    catch it, so an unattributed parse is stamped
    :data:`~timezonefinder.configs.UNKNOWN_DATA_VERSION` instead.

    The comparison resolves both sides: ``update_data.sh`` and ``make parse`` pass the
    default input as the relative ``./tmp/combined-with-oceans.json``.
    """
    if explicit:
        return explicit
    if Path(input_path).resolve() == DEFAULT_INPUT_PATH.resolve():
        return read_data_version()
    return UNKNOWN_DATA_VERSION


DEBUG = False
# DEBUG = True

# lower the shortcut resolution for debugging
SHORTCUT_H3_RES = 0 if DEBUG else SHORTCUT_H3_RES


# Lower bound on the share of holes stored as a reference to an identical boundary
# polygon rather than as their own copy of the ring (see HoleCollection.poly_refs).
# The deduplication is worth ~7% of the packaged coordinate data, and it rests on how
# the upstream builder emits enclaves - which is a convention, not a guarantee. A
# release that changed it would still compile and still return correct timezones, just
# with the shipped data quietly re-inflated, which is why it is asserted somewhere
# rather than left to be noticed. Measured 96.4% on release 2026c; the floor sits well
# below that so that ordinary dataset churn does not trip it.
#
# It is a statement about *this* dataset, so it is enforced only against the packaged
# data (scripts.data_integrity.validate_hole_dedup_ratio, exercised by the test suite).
# The converter merely reports it: compiling custom data whose holes are not enclaves
# is a supported use case, and those rings are stored inline and answer correctly.
MIN_HOLE_DEDUP_RATIO = 0.9

DEBUG_ZONE_CTR_STOP = 5  # parse only some polygons in debugging mode
HexIdSet: TypeAlias = set[int]
PolyIdSet: TypeAlias = set[int]
ZoneIdSet: TypeAlias = set[int]

# ``scripts.reporting.print_rst_table`` renders every cell through ``str()``,
# so a row is not a list of strings - counts and percentages are passed through
# as numbers and formatted by the renderer.
TableCell: TypeAlias = str | int | float
TableRow: TypeAlias = list[TableCell]
# Read-only parameter type. ``list`` is invariant, so a plain ``list[list[str]]``
# of already-formatted cells is not a ``list[TableRow]``; ``Sequence`` is
# covariant and accepts both.
TableRows: TypeAlias = Sequence[Sequence[TableCell]]


class BinaryData(TypedDict):
    """The packaged binaries the data report describes.

    ``scripts.reporting.load_binary_data`` returns this and the rest of that
    module indexes it by string literal, so an untyped ``dict`` turned a
    mistyped key into a ``KeyError`` raised part-way through writing the report.
    """

    shortcuts: dict[int, int | np.ndarray]
    nr_of_polygons: int
    nr_of_zones: int
    polygon_lengths: list[int]
    all_hole_lengths: list[int]
    polynrs_of_holes: list[int]
    poly_zone_ids: list[int]
    all_tz_names: list[str]
    output_path: Path


class ShortcutIndexStats(TypedDict):
    """What ``scripts.reporting.calculate_shortcut_index_stats`` measures.

    The last two members are distributions, one entry per shortcut cell. The
    ``dict[str, int | float]`` this replaces could not describe them, so the
    two ``print_frequencies`` calls consuming them were passing a ``list`` to a
    parameter the annotation said was a scalar.
    """

    # basic counts
    total_entries: int
    zone_entries: int
    polygon_entries: int
    empty_entries: int
    polygon_id_count: int
    # H3 coverage
    h3_resolution: int
    stored_cells: int
    possible_cells: int
    missing_cells: int
    coverage_ratio: float
    # efficiency metrics
    unique_entry_fraction: float
    unique_surface_fraction: float
    zone_distribution_efficiency: float
    avg_polygons_per_entry: float
    # storage efficiency
    zone_storage_bytes: int
    polygon_storage_bytes: int
    total_storage_bytes: int
    compression_ratio: float
    # frequency distributions
    polygons_per_shortcut: list[int]
    zones_per_shortcut: list[int]


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
