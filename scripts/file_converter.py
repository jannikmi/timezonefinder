"""
script for parsing the timezone data from https://github.com/evansiroky/timezone-boundary-builder to the binary format required by `timezonefinder`

the usage is described in docs/2_use_cases.rst (parse_data)

the used data format is described in the documentation under docs/data_format.rst

IMPORTANT: all coordinates (floats) of the timezone polygons are being converted to int32 (multiplied by 10^7).
This makes computations faster and it takes lot less space,
    without loosing too much accuracy (min accuracy (=at the equator) is still 1cm !)


[SHORTCUTS:] spacial index: coordinate to potential polygon id candidates
shortcuts drastically reduce the amount of polygons which need to be checked in order to
    decide which timezone a point is located in.
the surface of the world is split up into a grid of hexagons (h3 library)
shortcut here means storing for every cell in a grid of the world map which polygons are located in that cell.

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
from typing import Any, Dict, List, NamedTuple, Tuple, Union

import numpy as np
from numpy.typing import NDArray
from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)

from scripts.shortcuts import compile_shortcut_mapping
from scripts.geojson_schema import GeoJSON, PolygonGeometry

from scripts.configs import (
    DEBUG,
    DEBUG_ZONE_CTR_STOP,
    DEFAULT_INPUT_PATH,
    DTYPE_FORMAT_H_NUMPY,
    DTYPE_FORMAT_SIGNED_I_NUMPY,
)
from scripts.reporting import write_data_report
from scripts.utils import (
    time_execution,
    to_numpy_polygon_repr,
    write_json,
)
from timezonefinder.flatbuf.polygon_utils import (
    get_coordinate_path,
    write_polygon_collection_flatbuffer,
)
from timezonefinder.flatbuf.shortcut_utils import (
    get_shortcut_file_path,
    write_shortcuts_flatbuffers,
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


class Boundaries(NamedTuple):
    xmax: float
    xmin: float
    ymax: float
    ymin: float

    def overlaps(self, other: "Boundaries") -> bool:
        if not isinstance(other, Boundaries):
            raise TypeError
        if self.xmin > other.xmax:
            return False
        if self.xmax < other.xmin:
            return False
        if self.ymin > other.ymax:
            return False
        if self.ymax < other.ymin:
            return False
        return True


def compile_bboxes(coord_list: PolygonList) -> List[Boundaries]:
    print("compiling the bounding boxes of the polygons from the coordinates...")
    boundaries: List[Boundaries] = []
    for coords in coord_list:
        x_coords, y_coords = coords
        y_coords = coords[1]
        bounds = Boundaries(
            np.max(x_coords), np.min(x_coords), np.max(y_coords), np.min(y_coords)
        )
        boundaries.append(bounds)
    return boundaries


class TimezoneData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    all_tz_names: List[str]
    poly_zone_ids: ZoneIdArray
    polygons: PolygonList
    polygon_lengths: LengthList
    nr_of_holes: int
    polynrs_of_holes: PolynrHolesList
    holes: PolygonList
    all_hole_lengths: HoleLengthList

    @classmethod
    def _process_hole(
        cls,
        hole: List[List[Tuple[float, float]]],
        poly_id: int,
        hole_nr: int,
        nr_of_holes: int,
        tz_name: str,
        polynrs_of_holes: PolynrHolesList,
        holes: PolygonList,
        all_hole_lengths: HoleLengthList,
    ) -> int:
        """Process a single hole within a polygon.

        Args:
            hole: Hole coordinates
            poly_id: ID of the parent polygon
            hole_nr: Hole number within the polygon (0-based)
            nr_of_holes: Current total number of holes processed
            tz_name: Timezone name for logging
            polynrs_of_holes: List to append polygon IDs that have holes
            holes: List to append processed hole polygons
            all_hole_lengths: List to append hole coordinate counts

        Returns:
            Updated number of holes processed
        """
        nr_of_holes += 1
        print(
            f"\rpolygon {poly_id}, zone {tz_name}, hole number {nr_of_holes}, {hole_nr + 1} in polygon",
            end="",
            flush=True,
        )
        polynrs_of_holes.append(poly_id)
        hole_poly = to_numpy_polygon_repr(hole)
        holes.append(hole_poly)
        nr_coords = hole_poly.shape[1]
        all_hole_lengths.append(nr_coords)
        return nr_of_holes

    @classmethod
    def _process_polygon_with_holes(
        cls,
        poly_with_hole: List[List[List[Tuple[float, float]]]],
        zone_id: int,
        tz_name: str,
        poly_id: int,
        polygons: PolygonList,
        polygon_lengths: LengthList,
        poly_zone_ids: List[int],
        nr_of_holes: int,
        polynrs_of_holes: PolynrHolesList,
        holes: PolygonList,
        all_hole_lengths: HoleLengthList,
    ) -> int:
        """Process a polygon and all its holes.

        Args:
            poly_with_hole: List containing boundary polygon and holes
            zone_id: Timezone zone ID
            tz_name: Timezone name
            poly_id: Polygon ID
            polygons: List to append processed polygons
            polygon_lengths: List to append polygon coordinate counts
            poly_zone_ids: List to append zone IDs for each polygon
            nr_of_holes: Current number of holes processed
            polynrs_of_holes: List to append polygon IDs that have holes
            holes: List to append processed hole polygons
            all_hole_lengths: List to append hole coordinate counts

        Returns:
            Updated number of holes processed
        """
        # the first entry is the boundary polygon
        # NOTE: starting from here, only coordinates converted into int32 will be considered!
        # this allows using the Numba JIT util functions already here
        poly = to_numpy_polygon_repr(poly_with_hole.pop(0))
        polygons.append(poly)
        x_coords = poly[0]
        polygon_lengths.append(len(x_coords))
        poly_zone_ids.append(zone_id)

        # everything else is interpreted as a hole!
        for hole_nr, hole in enumerate(poly_with_hole):
            nr_of_holes = cls._process_hole(
                hole,
                poly_id,
                hole_nr,
                nr_of_holes,
                tz_name,
                polynrs_of_holes,
                holes,
                all_hole_lengths,
            )

        return nr_of_holes

    @classmethod
    def _process_timezone_feature(
        cls,
        zone_id: int,
        timezone: Any,  # GeoJSON Feature type
        poly_id: int,
        all_tz_names: List[str],
        polygons: PolygonList,
        polygon_lengths: LengthList,
        poly_zone_ids: List[int],
        nr_of_holes: int,
        polynrs_of_holes: PolynrHolesList,
        holes: PolygonList,
        all_hole_lengths: HoleLengthList,
    ) -> Tuple[int, int]:
        """Process a single timezone feature with all its polygons and holes.

        Args:
            zone_id: Timezone zone ID
            timezone: Timezone feature from GeoJSON
            poly_id: Current polygon ID counter
            all_tz_names: List to append timezone names
            polygons: List to append processed polygons
            polygon_lengths: List to append polygon coordinate counts
            poly_zone_ids: List to append zone IDs for each polygon
            nr_of_holes: Current number of holes processed
            polynrs_of_holes: List to append polygon IDs that have holes
            holes: List to append processed hole polygons
            all_hole_lengths: List to append hole coordinate counts

        Returns:
            Tuple of (updated poly_id, updated nr_of_holes)
        """
        tz_name = timezone.id
        all_tz_names.append(tz_name)
        tz_geometry = timezone.geometry
        multipolygon = tz_geometry.coordinates
        # case: MultiPolygon -> depth is 4
        if isinstance(tz_geometry, PolygonGeometry):
            # depth is 3 (only one polygon, possibly with holes!)
            multipolygon = [multipolygon]

        for poly_with_hole in multipolygon:
            nr_of_holes = cls._process_polygon_with_holes(
                poly_with_hole,
                zone_id,
                tz_name,
                poly_id,
                polygons,
                polygon_lengths,
                poly_zone_ids,
                nr_of_holes,
                polynrs_of_holes,
                holes,
                all_hole_lengths,
            )
            poly_id += 1

        return poly_id, nr_of_holes

    @classmethod
    def create_validated(cls, **kwargs) -> "TimezoneData":
        """Create a TimezoneData instance with proper validation error handling.

        Args:
            **kwargs: Keyword arguments for TimezoneData creation

        Returns:
            TimezoneData instance

        Raises:
            ValidationError: If data validation fails with detailed error information
        """
        try:
            return cls(**kwargs)
        except ValidationError as e:
            print("Data validation failed:")
            for error in e.errors():
                print(f"  - {error['loc']}: {error['msg']}")
            raise

    @classmethod
    def from_geojson(cls, geo_json: GeoJSON) -> "TimezoneData":
        """Parse GeoJSON timezone data into TimezoneData model.

        Args:
            geo_json: Parsed GeoJSON timezone data

        Returns:
            TimezoneData instance with processed polygon and hole data
        """
        # Initialize data containers
        all_tz_names: List[str] = []
        polygons: PolygonList = []
        polygon_lengths: LengthList = []
        poly_zone_ids: List[int] = []
        nr_of_holes: int = 0
        polynrs_of_holes: PolynrHolesList = []
        holes: PolygonList = []
        all_hole_lengths: HoleLengthList = []

        poly_id: int = 0
        print("parsing data...\nprocessing holes:")

        # Process each timezone feature
        for zone_id, timezone in enumerate(geo_json.features):
            poly_id, nr_of_holes = cls._process_timezone_feature(
                zone_id,
                timezone,
                poly_id,
                all_tz_names,
                polygons,
                polygon_lengths,
                poly_zone_ids,
                nr_of_holes,
                polynrs_of_holes,
                holes,
                all_hole_lengths,
            )

            if DEBUG and zone_id >= DEBUG_ZONE_CTR_STOP:
                break

        print("\n")

        return cls.create_validated(
            all_tz_names=all_tz_names,
            poly_zone_ids=np.array(poly_zone_ids, dtype=DTYPE_FORMAT_H_NUMPY),
            polygons=polygons,
            polygon_lengths=polygon_lengths,
            nr_of_holes=nr_of_holes,
            polynrs_of_holes=polynrs_of_holes,
            holes=holes,
            all_hole_lengths=all_hole_lengths,
        )

    @field_validator("polygons", "holes")
    @classmethod
    def check_polygon_shapes(cls, v: PolygonList) -> PolygonList:
        for poly in v:
            if not isinstance(poly, np.ndarray):
                raise TypeError("Polygon must be a numpy array")
            if poly.ndim != 2:
                raise ValueError("Polygon array must have 2 dimensions")
            if poly.shape[0] != 2:
                raise ValueError("Polygon array must have shape (2, N)")
        return v

    def _validate_count_consistency(self, count: int, data_list: List[Any]) -> None:
        """Validate that a count field matches the length of its corresponding list.

        Args:
            count: The count value to validate
            data_list: The list whose length should match the count
        """
        if count != len(data_list):
            raise ValueError(
                f"{count.__name__} ({count}) does not match length of {data_list.__name__} list ({len(data_list)})"
            )

    def _validate_non_negative(self, value: int) -> None:
        """Validate that a value is non-negative.

        Args:
            value: The value to validate
        """
        if value < 0:
            raise ValueError(f"{value.__name__} cannot be negative")

    def _validate_minimum_coordinates(
        self, lengths: LengthList, min_coords: int, item_type: str
    ) -> None:
        """Validate that all items have minimum required coordinates.

        Args:
            lengths: List of coordinate counts
            min_coords: Minimum required coordinates
            item_type: Type of item (e.g., "polygon", "hole") for error messages
        """
        if any(length == 0 for length in lengths):
            raise ValueError(f"Found a {item_type} with no coordinates")

        if any(length < min_coords for length in lengths):
            raise ValueError(
                f"All {item_type}s must have at least {min_coords} coordinates"
            )

    @model_validator(mode="after")
    def validate_basic_counts(self) -> "TimezoneData":
        self._validate_non_negative(self.nr_of_polygons)
        self._validate_non_negative(self.nr_of_zones)
        self._validate_non_negative(self.nr_of_holes)

        if self.nr_of_polygons < self.nr_of_zones:
            raise ValueError(
                f"Number of polygons ({self.nr_of_polygons}) cannot be less than number of zones ({self.nr_of_zones})"
            )
        return self

    @model_validator(mode="after")
    def validate_polygon_data_consistency(self) -> "TimezoneData":
        self._validate_count_consistency(self.nr_of_polygons, self.polygons)
        self._validate_count_consistency(self.nr_of_polygons, self.polygon_lengths)
        self._validate_count_consistency(self.nr_of_polygons, self.poly_boundaries)
        self._validate_count_consistency(self.nr_of_polygons, self.poly_zone_ids)
        return self

    @model_validator(mode="after")
    def validate_zone_data_consistency(self) -> "TimezoneData":
        self._validate_count_consistency(self.nr_of_zones, self.all_tz_names)
        return self

    @model_validator(mode="after")
    def validate_hole_data_consistency(self) -> "TimezoneData":
        self._validate_count_consistency(self.nr_of_holes, self.holes)
        self._validate_count_consistency(self.nr_of_holes, self.all_hole_lengths)
        self._validate_count_consistency(self.nr_of_holes, self.polynrs_of_holes)
        return self

    @model_validator(mode="after")
    def validate_geometric_constraints(self) -> "TimezoneData":
        self._validate_minimum_coordinates(self.polygon_lengths, 3, "polygon")
        self._validate_minimum_coordinates(self.all_hole_lengths, 3, "hole")
        return self

    @model_validator(mode="after")
    def validate_zone_id_constraints(self) -> "TimezoneData":
        if len(self.poly_zone_ids) == 0:
            return self

        max_zone_id = int(max(self.poly_zone_ids))
        if max_zone_id != self.nr_of_zones - 1:
            raise ValueError(
                f"Maximum zone ID ({max_zone_id}) should equal nr_of_zones - 1 ({self.nr_of_zones - 1})"
            )

        min_zone_id = int(min(self.poly_zone_ids))
        if min_zone_id < 0:
            raise ValueError(f"Zone IDs cannot be negative, found {min_zone_id}")

        last_zone_id: int = -1
        for zone_id in self.poly_zone_ids:
            if zone_id < last_zone_id:
                raise ValueError(
                    f"Zone IDs must be in non-decreasing order, found {zone_id} after {last_zone_id}"
                )
            last_zone_id = int(zone_id)
        return self

    @model_validator(mode="after")
    def validate_hole_references(self) -> "TimezoneData":
        if not self.polynrs_of_holes:
            return self

        max_poly_ref: int = max(self.polynrs_of_holes)
        if max_poly_ref >= self.nr_of_polygons:
            raise ValueError(
                f"Hole references polygon {max_poly_ref} but only {self.nr_of_polygons} polygons exist"
            )

        min_poly_ref: int = min(self.polynrs_of_holes)
        if min_poly_ref < 0:
            raise ValueError(
                f"Hole polygon references cannot be negative, found {min_poly_ref}"
            )
        return self

    @property
    def nr_of_polygons(self) -> int:
        """the number of boundary polygons"""
        return len(self.polygon_lengths)

    @property
    def nr_of_zones(self) -> int:
        """the number of timezones"""
        return len(self.all_tz_names)

    @property
    def poly_boundaries(self) -> List[Boundaries]:
        """Compute bounding boxes for polygon boundaries."""
        return compile_bboxes(self.polygons)

    @property
    def hole_boundaries(self) -> List[Boundaries]:
        """Compute bounding boxes for holes."""
        return compile_bboxes(self.holes)

    @property
    def zone_positions(self) -> List[int]:
        """Compute where each timezone starts and ends in the polygon array.

        Returns:
            List of polygon indices where each zone starts, plus one final entry
            indicating where the last zone ends (i.e., total number of polygons).
        """
        poly_nr2zone_id: List[int] = []
        print("Computing where zones start and end...")
        last_id: int = -1
        for poly_nr, zone_id in enumerate(self.poly_zone_ids):
            if zone_id != last_id:
                poly_nr2zone_id.append(poly_nr)
                if zone_id < last_id:
                    raise ValueError(
                        f"Zone IDs must be in non-decreasing order, found {zone_id} after {last_id}"
                    )
                last_id = int(zone_id)

        # ATTENTION: add one more entry for knowing where the last zone ends!
        poly_nr2zone_id.append(self.nr_of_polygons)
        print("...Done.\n")
        return poly_nr2zone_id


def parse_polygons_from_json(input_path: Path) -> TimezoneData:
    """Parse the timezone polygons from the input JSON file."""
    print(f"parsing input file: {input_path}\n...\n")
    geo_json = GeoJSON.model_validate_json(input_path.read_text())
    return TimezoneData.from_geojson(geo_json)


def create_and_write_hole_registry(data: TimezoneData, output_path: Path) -> None:
    """
    Creates a registry mapping each polygon id to a tuple (number of holes, first hole id),
    and writes it as JSON to the output path.
    """
    hole_registry: HoleRegistry = {}
    for i, poly_id in enumerate(data.polynrs_of_holes):
        try:
            amount_of_holes, hole_id = hole_registry[poly_id]
            hole_registry[poly_id] = (amount_of_holes + 1, hole_id)
        except KeyError:
            hole_registry[poly_id] = (1, i)
    path: Path = get_hole_registry_path(output_path)
    write_json(hole_registry, path)


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
    for dir, bounds in zip(
        [holes_dir, boundaries_dir], [data.hole_boundaries, data.poly_boundaries]
    ):
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
) -> None:
    input_path_obj: Path = Path(input_path)
    output_path_obj: Path = Path(output_path)
    output_path_obj.mkdir(parents=True, exist_ok=True)

    data: TimezoneData = parse_polygons_from_json(input_path_obj)

    compile_data_files(data, output_path_obj)
    shortcuts: ShortcutMapping = compile_shortcut_mapping(data)
    output_file: Path = get_shortcut_file_path(output_path_obj)
    write_shortcuts_flatbuffers(shortcuts, output_file)

    print(f"\n\nfinished parsing timezonefinder data to {output_path_obj}")
    write_data_report(
        shortcuts,
        output_path_obj,
        data.nr_of_polygons,
        data.nr_of_zones,
        data.polygon_lengths,
        data.all_hole_lengths,
        data.polynrs_of_holes,
        data.poly_zone_ids.tolist(),
        data.all_tz_names,
    )


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
    parsed_args: argparse.Namespace = parser.parse_args()

    parse_data(input_path=parsed_args.inp, output_path=parsed_args.out)
