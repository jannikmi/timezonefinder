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
from typing import Any, List, Tuple, Union
from numpy.typing import NDArray

import numpy as np

from scripts.timezone_data import TimezoneData
from scripts.shortcuts import compile_shortcuts
from scripts.helper_classes import Boundaries

from scripts.configs import (
    DEFAULT_INPUT_PATH,
    DTYPE_FORMAT_H_NUMPY,
    DTYPE_FORMAT_SIGNED_I_NUMPY,
    INITIALIZATION_REPORT_FILE,
    POLYGON_REPORT_FILE,
    ZONE_ID_DTYPE,
    ZONE_ID_DTYPE_CHOICES,
    ZONE_ID_DTYPE_NAME,
    BoundaryArray,
    resolve_zone_id_dtype,
)
from scripts.reporting import write_data_report_from_binary
from scripts.check_speed_timezone_finding import write_performance_report
from scripts.check_speed_inside_polygon import write_polygon_report
from scripts.check_speed_initialisation import write_initialization_report
from scripts.utils import time_execution, write_json
from timezonefinder.flatbuf.io.polygons import (
    get_coordinate_path,
    write_polygon_collection_flatbuffer,
)
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.np_binary_helpers import (
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


def to_numpy_array(values: List[Any], dtype: str) -> NDArray[Any]:
    """
    Converts a list of values to a numpy array with the specified dtype.
    Args:
        values: List of values to convert
        dtype: Numpy dtype string (e.g., 'int32', 'float64')
    Returns:
        Numpy array with the specified dtype
    """
    return np.array(values, dtype=dtype)


def to_bbox_vector(values: List[int]) -> BoundaryArray:
    return to_numpy_array(values, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY)


def convert_bboxes_to_numpy(
    bboxes: List[Boundaries],
) -> Tuple[BoundaryArray, BoundaryArray, BoundaryArray, BoundaryArray]:
    """Converts a list of Boundaries to numpy arrays for xmax, xmin, ymax, ymin.
    Args:
        bboxes: List of Boundaries objects
    Returns:
        Tuple of numpy arrays (xmax, xmin, ymax, ymin)
    """
    xmax_list: List[int] = []
    xmin_list: List[int] = []
    ymax_list: List[int] = []
    ymin_list: List[int] = []
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


def _coerce_zone_id_dtype(zone_id_dtype: Union[str, np.dtype, None]) -> np.dtype:
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

    for dir, bounds in boundary_sources:
        # Convert Boundaries to numpy arrays
        boundary_xmax, boundary_xmin, boundary_ymax, boundary_ymin = (
            convert_bboxes_to_numpy(bounds)
        )
        # Save bounding box properties using store_per_polygon_vector
        store_per_polygon_vector(get_xmax_path(dir), boundary_xmax)
        store_per_polygon_vector(get_xmin_path(dir), boundary_xmin)
        store_per_polygon_vector(get_ymax_path(dir), boundary_ymax)
        store_per_polygon_vector(get_ymin_path(dir), boundary_ymin)

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
    # Write holes coordinates to flatbuffer
    write_polygon_collection_flatbuffer(hole_polygon_file, data.holes)
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
    print("Binary files written successfully")


@time_execution
def compile_data_files(data: TimezoneData, output_path: Path) -> None:
    write_zone_names(data.all_tz_names, output_path)

    # Write registry for holes (which polygon each hole belongs to)
    create_and_write_hole_registry(data, output_path)

    # Write binary files
    write_binary_files(data, output_path)


@time_execution
def parse_data(
    input_path: Union[Path, str] = DEFAULT_INPUT_PATH,
    output_path: Union[Path, str] = DEFAULT_DATA_DIR,
    zone_id_dtype: Union[str, np.dtype, None] = ZONE_ID_DTYPE_NAME,
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
    write_data_report_from_binary(output_path_obj, zone_id_dtype=resolved_zone_id_dtype)

    print("Generating performance benchmark report...")
    write_performance_report()

    print("Generating point-in-polygon benchmark report...")
    write_polygon_report(POLYGON_REPORT_FILE)

    print("Generating initialization benchmark report...")
    write_initialization_report(INITIALIZATION_REPORT_FILE, data_path=output_path_obj)


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
