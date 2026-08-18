"""
script for parsing the timezone data from https://github.com/evansiroky/timezone-boundary-builder to the binary format required by `timezonefinder`

the usage is described in docs/2_use_cases.rst (parse_data)

the used data format is described in the documentation under docs/data_format.rst

IMPORTANT: all coordinates (floats) of the timezone polygons are being converted to int32 (multiplied by 10^7).
This makes computations faster and it takes lot less space,
    without loosing too much accuracy (min accuracy (=at the equator) is still 1cm !)


[SHORTCUTS:] hybrid spatial index: coordinate to potential polygon id candidates or direct zone IDs
shortcuts drastically reduce the amount of polygons which need to be checked in order to
    decide which timezone a point is located in.
the surface of the world is split up into a grid of hexagons (h3 library)
hybrid shortcut here means storing for every cell in a grid of the world map either:
    - a direct zone ID (when all polygons in that cell belong to the same timezone)
    - an array of polygon IDs that need to be checked (when the cell contains multiple timezones)

Note: the poly ids within one shortcut entry are sorted for optimal performance


Uber H3 findings:
replacing the polygon data with hexagon key mappings failed (filling up the polygon with hexagons of different resolutions),
    since the amount of required entries becomes too large in the resolutions required for sufficient accuracy.
    hypothesis: "boundary regions" where multiple zones meet and no unique shortcut can be found are very large.
    also: storing one single hexagon id takes 8 byte
still h3 hexagons can be used to index the timezone polygons ("shortcuts") in a clean way
observation: some small region of children protrudes the parent cell and
      is not covered by the children of the neighbouring parent cell!
    but "complete coverage" required: for every point on earth there is a zone match (mapping to None)
    -> inefficient to store mappings of different resolutions
in res=3 it takes only slightly more space to store just the highest resolution ids (= complete coverage!),
    than also storing the lower resolution shortcuts (when there is a unique or no timezone match).
    -> only use one resolution, because of the higher simplicity of the lookup algorithms
"""

from pathlib import Path
from typing import Any
from numpy.typing import NDArray

import numpy as np

from scripts.timezone_data import TimezoneData
from scripts.shortcuts import compile_shortcuts
from scripts.helper_classes import Boundaries

from scripts.configs import (
    DEFAULT_INPUT_PATH,
    DTYPE_FORMAT_H_NUMPY,
    DTYPE_FORMAT_SIGNED_I_NUMPY,
    ZONE_ID_DTYPE,
    ZONE_ID_DTYPE_CHOICES,
    ZONE_ID_DTYPE_NAME,
    BoundaryArray,
    read_data_version,
    resolve_zone_id_dtype,
)
from scripts.data_integrity import validate_hole_references
from scripts.reporting import write_data_report_from_binary
from scripts.utils import time_execution, write_json
from timezonefinder.flatbuf.io.polygons import (
    get_coordinate_path,
    write_polygon_collection_flatbuffer,
)
from timezonefinder.configs import DEFAULT_DATA_DIR, DATA_VERSION_FILENAME
from timezonefinder.np_binary_helpers import (
    get_poly_ref_path,
    get_xmax_path,
    get_xmin_path,
    get_ymax_path,
    get_ymin_path,
    get_zone_ids_path,
    get_zone_positions_path,
    store_per_polygon_vector,
)
from timezonefinder.utils import (
    get_boundaries_dir,
    get_hole_registry_path,
    get_holes_dir,
)
from timezonefinder.zone_names import write_zone_names


def create_and_write_hole_registry(data: TimezoneData, output_path: Path) -> None:
    """
    Writes the hole registry as JSON to the output path.
    The hole registry is a property of TimezoneData.
    """
    path: Path = get_hole_registry_path(output_path)
    write_json(data.hole_registry, path)


def to_numpy_array(values: list[Any], dtype: str) -> NDArray[Any]:
    """
    Converts a list of values to a numpy array with the specified dtype.
    Args:
        values: List of values to convert
        dtype: Numpy dtype string (e.g., 'int32', 'float64')
    Returns:
        Numpy array with the specified dtype
    """
    return np.array(values, dtype=dtype)


def to_bbox_vector(values: list[float]) -> BoundaryArray:
    return to_numpy_array(values, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY)


def convert_bboxes_to_numpy(
    bboxes: list[Boundaries],
) -> tuple[BoundaryArray, BoundaryArray, BoundaryArray, BoundaryArray]:
    """Converts a list of Boundaries to numpy arrays for xmax, xmin, ymax, ymin.
    Args:
        bboxes: List of Boundaries objects
    Returns:
        Tuple of numpy arrays (xmax, xmin, ymax, ymin)
    """
    xmax_list: list[float] = []
    xmin_list: list[float] = []
    ymax_list: list[float] = []
    ymin_list: list[float] = []
    for bounds in bboxes:
        xmax_list.append(bounds.xmax)
        xmin_list.append(bounds.xmin)
        ymax_list.append(bounds.ymax)
        ymin_list.append(bounds.ymin)
    xmax: BoundaryArray = to_bbox_vector(xmax_list)
    xmin: BoundaryArray = to_bbox_vector(xmin_list)
    ymax: BoundaryArray = to_bbox_vector(ymax_list)
    ymin: BoundaryArray = to_bbox_vector(ymin_list)
    return xmax, xmin, ymax, ymin


def _coerce_zone_id_dtype(zone_id_dtype: str | np.dtype | None) -> np.dtype:
    """Normalise zone id dtype configuration into a numpy dtype."""

    if zone_id_dtype is None:
        return ZONE_ID_DTYPE
    if isinstance(zone_id_dtype, str):
        return resolve_zone_id_dtype(zone_id_dtype)
    return np.dtype(zone_id_dtype)


def write_numpy_binaries(data: TimezoneData, output_path: Path) -> None:
    print("Writing binary data to separate Numpy binary .npy files...")
    # some properties are very small but essential for the performance of the package
    # -> store them directly as numpy arrays (overhead is negligible) and read them into memory at runtime

    # ZONE_POSITIONS: where each timezone starts and ends
    zone_positions_arr: NDArray[Any] = to_numpy_array(
        data.zone_positions, dtype=DTYPE_FORMAT_H_NUMPY
    )
    zone_positions_path: Path = get_zone_positions_path(output_path)
    store_per_polygon_vector(zone_positions_path, zone_positions_arr)

    # BOUNDARY_ZONE_IDS: the zone id for every polygon
    # NOTE: zone ids are stored idependently from boundaries or holes
    zone_id_file: Path = get_zone_ids_path(output_path)
    np.save(zone_id_file, data.poly_zone_ids)

    # properties which are "per polygon" (boundary/hole) vectors
    # separate output directories for holes and boundaries
    holes_dir: Path = get_holes_dir(output_path)
    boundaries_dir: Path = get_boundaries_dir(output_path)

    holes_dir.mkdir(parents=True, exist_ok=True)
    boundaries_dir.mkdir(parents=True, exist_ok=True)

    # save 4 bbox vectors for holes and polygons to the respective directories
    boundary_sources = [
        (holes_dir, data.hole_boundaries),
        (boundaries_dir, data.poly_boundaries),
    ]

    for output_dir, bounds in boundary_sources:
        # Convert Boundaries to numpy arrays
        boundary_xmax, boundary_xmin, boundary_ymax, boundary_ymin = (
            convert_bboxes_to_numpy(bounds)
        )
        # Save bounding box properties using store_per_polygon_vector
        store_per_polygon_vector(get_xmax_path(output_dir), boundary_xmax)
        store_per_polygon_vector(get_xmin_path(output_dir), boundary_xmin)
        store_per_polygon_vector(get_ymax_path(output_dir), boundary_ymax)
        store_per_polygon_vector(get_ymin_path(output_dir), boundary_ymin)

    # HOLE POLYGON REFERENCES: which boundary polygon each hole duplicates, or where
    # its own ring sits in the (much smaller) hole coordinate file. Written per hole id,
    # so the ids stay dense and the hole registry is unaffected.
    store_per_polygon_vector(
        get_poly_ref_path(holes_dir),
        to_numpy_array(data.hole_poly_refs, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY),
    )

    print("Numpy binary files written successfully")


def write_flatbuffer_files(data: TimezoneData, output_path: Path) -> None:
    # separate output directories for holes and boundaries
    holes_dir: Path = get_holes_dir(output_path)
    boundaries_dir: Path = get_boundaries_dir(output_path)

    holes_dir.mkdir(parents=True, exist_ok=True)
    boundaries_dir.mkdir(parents=True, exist_ok=True)

    print("Writing binary data to flatbuffer files...")
    # Write polygon boundary coordinates to flatbuffer
    boundary_polygon_file: Path = get_coordinate_path(boundaries_dir)
    write_polygon_collection_flatbuffer(boundary_polygon_file, data.polygons)

    hole_polygon_file: Path = get_coordinate_path(holes_dir)
    # Write hole coordinates to flatbuffer. Only the rings that are not a verbatim copy
    # of a boundary polygon: the rest are resolved through poly_ref.npy at runtime.
    write_polygon_collection_flatbuffer(hole_polygon_file, data.inline_holes)
    print("Flatbuffer files written successfully")


def write_binary_files(data: TimezoneData, output_path: Path) -> None:
    """
    Write all binary files for the timezonefinder package.

    This uses FlatBuffers for all data structures to ensure consistent formats.

    Args:
        output_path: Directory where binary files will be written
    """
    write_numpy_binaries(data, output_path)
    write_flatbuffer_files(data, output_path)
    # Check the artifact rather than the in-memory model it came from: the hole
    # reference vector, the hole coordinate file and the hole bboxes are three separate
    # files, and only reading them back proves they agree. This is where the coherence
    # of a data directory is established - the runtime trusts it and does not re-derive it.
    print("Verifying the integrity of the written data...")
    validate_hole_references(output_path)
    print("Binary files written successfully")


@time_execution
def compile_data_files(data: TimezoneData, output_path: Path) -> None:
    write_zone_names(data.all_tz_names, output_path)

    # Write registry for holes (which polygon each hole belongs to)
    create_and_write_hole_registry(data, output_path)

    # Write binary files
    write_binary_files(data, output_path)

    # Stamp the dataset version into the data directory so an installed
    # timezonefinder can state which boundary data release it answers from
    # (AbstractTimezoneFinder.data_version). Mirrors the repo-root DATA_VERSION
    # this parse was built from; update_data.sh re-stamps both together after a
    # successful upstream release, and a standalone `make parse` against the
    # committed DATA_VERSION leaves the two in agreement.
    (output_path / DATA_VERSION_FILENAME).write_text(
        f"{read_data_version()}\n", encoding="utf-8"
    )


@time_execution
def parse_data(
    input_path: Path | str = DEFAULT_INPUT_PATH,
    output_path: Path | str = DEFAULT_DATA_DIR,
    zone_id_dtype: str | np.dtype | None = ZONE_ID_DTYPE_NAME,
) -> None:
    input_path_obj: Path = Path(input_path)
    output_path_obj: Path = Path(output_path)
    output_path_obj.mkdir(parents=True, exist_ok=True)

    resolved_zone_id_dtype = _coerce_zone_id_dtype(zone_id_dtype)
    print(f"Using zone id dtype: {resolved_zone_id_dtype}")

    data: TimezoneData = TimezoneData.from_path(
        input_path_obj, zone_id_dtype=resolved_zone_id_dtype
    )
    compile_data_files(data, output_path_obj)

    _ = compile_shortcuts(output_path_obj, data)

    print(f"\n\nfinished parsing timezonefinder data to {output_path_obj}")
    print("Generating data report from binary files...")
    # NOTE: the report's provenance stamp reads the *current* DATA_VERSION,
    # which update_data.sh does not write until this script has returned - so
    # the report written here still names the previous release. That is why
    # update_data.sh re-runs this generator via `make reports` afterwards, and
    # why a standalone `make parse` of a newer dataset leaves a report stamped
    # with the old version until DATA_VERSION is updated and it is re-run.
    write_data_report_from_binary(output_path_obj, zone_id_dtype=resolved_zone_id_dtype)

    # the pytest-benchmark reports (docs/benchmark_results_*.rst) are NOT
    # regenerated here: they need the committed benchmark fixtures pinned to
    # DATA_VERSION, which isn't updated until after this script returns.
    # update_data.sh runs `make reports` automatically once DATA_VERSION and
    # the fixtures are back in sync; a standalone `make parse`/`make testparse`
    # invocation of this script does not, and must be followed by `make
    # reports` manually if the reports need to reflect the newly parsed data.


if __name__ == "__main__":
    import argparse

    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="parse data directories"
    )
    parser.add_argument(
        "-inp", help="path to input JSON file", default=DEFAULT_INPUT_PATH
    )
    parser.add_argument(
        "-out",
        help="path to output folder for storing the parsed data files",
        default=DEFAULT_DATA_DIR,
    )
    parser.add_argument(
        "--zone-id-dtype",
        choices=ZONE_ID_DTYPE_CHOICES,
        default=ZONE_ID_DTYPE_NAME,
        help="unsigned integer dtype for timezone IDs",
    )
    parsed_args: argparse.Namespace = parser.parse_args()

    parse_data(
        input_path=parsed_args.inp,
        output_path=parsed_args.out,
        zone_id_dtype=parsed_args.zone_id_dtype,
    )
