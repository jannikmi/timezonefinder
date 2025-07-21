"""
script for parsing the timezone data from https://github.com/evansiroky/timezone-boundary-builder to the binary format required by `timezonefinder`

the used data format is described in the documentation under docs/data_format.rst


USAGE:

- download the latest timezones.geojson.zip file from github.com/evansiroky/timezone-boundary-builder/releases
- unzip and place the combined.json inside the `scripts` folder
- run this `file_converter.py` script to compile the data files.


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

import functools
import itertools
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, NamedTuple, Optional, Set, Tuple, Union


import h3.api.numpy_int as h3
import numpy as np

from scripts.configs import (
    DATA_REPORT_FILE,
    DEBUG,
    DEBUG_ZONE_CTR_STOP,
    DEFAULT_INPUT_PATH,
    MAX_LAT,
    MAX_LNG,
    HexIdSet,
    PolyIdSet,
    ZoneIdSet,
    DTYPE_FORMAT_H_NUMPY,
    DTYPE_FORMAT_SIGNED_I_NUMPY,
)
from scripts.utils import (
    check_shortcut_sorting,
    print_rst_table,
    print_shortcut_statistics,
    redirect_output_to_file,
    rst_title,
    time_execution,
    to_numpy_polygon_repr,
    write_json,
    load_json,
)

from scripts.utils_numba import fully_contained_in_hole, any_pt_in_poly
from timezonefinder.flatbuf.polygon_utils import (
    get_coordinate_path,
    write_polygon_collection_flatbuffer,
)
from timezonefinder.flatbuf.shortcut_utils import (
    get_shortcut_file_path,
    write_shortcuts_flatbuffers,
)
from timezonefinder.configs import DEFAULT_DATA_DIR, SHORTCUT_H3_RES
from timezonefinder.np_binary_helpers import (
    get_xmax_path,
    get_xmin_path,
    get_ymax_path,
    get_ymin_path,
    get_zone_ids_path,
    get_zone_positions_path,
    store_per_polygon_vector,
)
from timezonefinder.utils_numba import (
    coord2int,
    int2coord,
)
from timezonefinder.utils import (
    get_hole_registry_path,
    get_holes_dir,
    get_boundaries_dir,
)
from timezonefinder.zone_names import write_zone_names


# lower the shortcut resolution for debugging
SHORTCUT_H3_RES = 1 if DEBUG else SHORTCUT_H3_RES

ShortcutMapping = Dict[int, List[int]]

nr_of_polygons = -1
nr_of_zones = -1
all_tz_names = []
poly_zone_ids = []
poly_boundaries = []
polygons: List[np.ndarray] = []
polygon_lengths = []
nr_of_holes = 0
polynrs_of_holes = []
holes = []
all_hole_lengths = []
list_of_pointers = []


def _holes_in_poly(poly_nr):
    for i, nr in enumerate(polynrs_of_holes):
        if nr == poly_nr:
            yield holes[i]


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


def compile_bboxes(coord_list: List[np.ndarray]) -> List[Boundaries]:
    print("compiling the bounding boxes of the polygons from the coordinates...")
    boundaries = []
    for coords in coord_list:
        x_coords, y_coords = coords
        y_coords = coords[1]
        bounds = Boundaries(
            np.max(x_coords), np.min(x_coords), np.max(y_coords), np.min(y_coords)
        )
        boundaries.append(bounds)
    return boundaries


def parse_polygons_from_json(input_path: Path) -> None:
    """Parse the timezone polygons from the input JSON file."""
    global nr_of_holes, nr_of_polygons, nr_of_zones, poly_zone_ids
    global polygons, polygon_lengths, poly_zone_ids, poly_boundaries

    print(f"parsing input file: {input_path}\n...\n")
    input_json = load_json(input_path)
    tz_list = input_json["features"]

    poly_id = 0
    zone_id = 0
    print("parsing data...\nprocessing holes:")
    for zone_id, tz_dict in enumerate(tz_list):
        tz_name = tz_dict.get("properties").get("tzid")
        all_tz_names.append(tz_name)
        geometry = tz_dict.get("geometry")
        if geometry.get("type") == "MultiPolygon":
            # depth is 4
            multipolygon = geometry.get("coordinates")
        else:
            # depth is 3 (only one polygon, possibly with holes!)
            multipolygon = [geometry.get("coordinates")]
        # multipolygon has depth 4
        # assert depth_of_array(multipolygon) == 4
        for poly_with_hole in multipolygon:
            # the first entry is the outer polygon
            # NOTE: starting from here, only coordinates converted into int32 will be considered!
            # this allows using the JIT util function already here
            poly = to_numpy_polygon_repr(poly_with_hole.pop(0))
            polygons.append(poly)
            x_coords = poly[0]
            polygon_lengths.append(len(x_coords))
            poly_zone_ids.append(zone_id)

            # everything else is interpreted as a hole!
            for hole_nr, hole in enumerate(poly_with_hole):
                nr_of_holes += 1  # keep track of how many holes there are
                print(
                    f"\rpolygon {poly_id}, zone {tz_name}, hole number {nr_of_holes}, {hole_nr + 1} in polygon",
                    end="",
                    flush=True,
                )
                polynrs_of_holes.append(poly_id)
                hole_poly = to_numpy_polygon_repr(hole)
                holes.append(hole_poly)
                nr_coords = hole_poly.shape[1]
                assert nr_coords >= 3
                all_hole_lengths.append(nr_coords)

            poly_id += 1

        if DEBUG and zone_id >= DEBUG_ZONE_CTR_STOP:
            break

    print("\n")

    poly_boundaries = compile_bboxes(polygons)

    nr_of_polygons = len(polygon_lengths)
    nr_of_zones = len(all_tz_names)
    assert nr_of_polygons >= 0
    assert nr_of_polygons >= nr_of_zones
    assert zone_id == nr_of_zones - 1
    assert poly_id == nr_of_polygons, (
        f"polygon counter {poly_id} and entry amount in all_length {nr_of_polygons} are different."
    )
    assert 0 not in polygon_lengths, "found a polygon with no coordinates"


def compute_zone_positions() -> List[int]:
    poly_nr2zone_id = []
    print("Computing where zones start and end...")
    last_id = -1
    zone_id = 0
    poly_nr = 0
    for poly_nr, zone_id in enumerate(poly_zone_ids):
        if zone_id != last_id:
            poly_nr2zone_id.append(poly_nr)
            assert zone_id >= last_id
            last_id = zone_id
    assert nr_of_polygons == len(poly_zone_ids)

    # TODO
    # assert (
    #         zone_id == nr_of_zones - 1
    # ), f"not pointing to the last zone with id {nr_of_zones - 1}"
    # assert (
    #         poly_nr == nr_of_polygons - 1
    # ), f"not pointing to the last polygon with id {nr_of_polygons - 1}"
    # ATTENTION: add one more entry for knowing where the last zone ends!
    # ATTENTION: the last entry is one higher than the last polygon id (to be consistant with the
    poly_nr2zone_id.append(nr_of_polygons)
    # assert len(poly_nr2zone_id) == nr_of_zones + 1
    print("...Done.\n")
    return poly_nr2zone_id


# TODO extract in own h3 utils module
def lies_in_h3_cell(h: int, lng: float, lat: float) -> bool:
    res = h3.get_resolution(h)
    return h3.latlng_to_cell(lat, lng, res) == h


def any_pt_in_cell(h: int, poly_nr: int) -> bool:
    def pt_in_cell(pt: np.ndarray) -> bool:
        # ATTENTION: must first convert integers back to coord floats!
        lng = int2coord(pt[0])
        lat = int2coord(pt[1])
        return lies_in_h3_cell(h, lng, lat)

    poly = polygons[poly_nr]
    return any(map(pt_in_cell, poly.T))


def get_corrected_hex_boundaries(
    x_coords, y_coords, surr_n_pole, surr_s_pole
) -> Tuple["Boundaries", bool]:
    """boundaries of a hex cell used for pre-filtering the polygons
        which have to be checked with expensive point-in-polygon algorithm

    ATTENTION: a h3 polygon may cross the boundaries of the lat/lng coordinate plane (only in lng=x direction)
    -> cannot use usual geometry assumptions (polygon algorithm, min max boundary check etc.)
    -> rectify boundaries

    ATTENTION: only using coordinates converted to integers!
    NOTE: convert to regular int type to prevent overflow

    Observation: except for cells close to the poles,
        h3 hexagons can usually only span a fraction of the globe (<< 360 degree lng)
    high longitude difference observed without surrounding a pole
    -> indicates crossing the +-180 deg lng boundary
    ATTENTION: min and max of the coordinates would only  pick the points closest to the +-180 deg lng boundary,
      but not the points furthest apart!
    getting this "pre-filtering" based on boundaries right across the +-180 deg lng boundary is tricky
        -> do not exclude any longitudes for simplicity and correctness
    this is only relevant for a fraction of hex cells plus filtering will still happen based on the latitude!
    """
    xmax0, xmin0, ymax0, ymin0 = (
        int(max(x_coords)),
        int(min(x_coords)),
        int(max(y_coords)),
        int(min(y_coords)),
    )
    max_latitude = coord2int(MAX_LAT)
    max_longitude = coord2int(MAX_LNG)

    delta_y = abs(ymax0 - ymin0)
    assert delta_y < max_latitude, f"longitude difference {int2coord(delta_y)} too high"
    delta_x = abs(xmax0 - xmin0)
    x_overflow = delta_x > max_longitude

    if surr_n_pole:
        # clip to max lat
        ymax0 = max_latitude
    elif surr_s_pole:
        # clip to min lat
        ymin0 = -max_latitude

    if surr_n_pole or surr_s_pole or x_overflow:
        # search all lngs for cells close to the poles or crossing the +-180 deg lng boundary
        xmin0 = -max_longitude
        xmax0 = max_longitude

    return Boundaries(xmax0, xmin0, ymax0, ymin0), x_overflow


@dataclass
class Hex:
    id: int
    res: int
    coords: np.ndarray
    bounds: Boundaries
    x_overflow: bool
    surr_n_pole: bool
    surr_s_pole: bool
    _poly_candidates: Optional[PolyIdSet] = None
    _polys_in_cell: Optional[PolyIdSet] = None
    _zones_in_cell: Optional[ZoneIdSet] = None

    @classmethod
    def from_id(cls, id: int):
        res = h3.get_resolution(id)
        coord_pairs = h3.cell_to_boundary(id)
        # ATTENTION: (lat, lng)! pairs
        coords = to_numpy_polygon_repr(coord_pairs, flipped=True)
        x_coords, y_coords = coords[0], coords[1]
        surr_n_pole = lies_in_h3_cell(id, lng=0.0, lat=MAX_LAT)
        surr_s_pole = lies_in_h3_cell(id, lng=0.0, lat=-MAX_LAT)
        bounds, x_overflow = get_corrected_hex_boundaries(
            x_coords, y_coords, surr_n_pole, surr_s_pole
        )
        return cls(id, res, coords, bounds, x_overflow, surr_n_pole, surr_s_pole)

    @property
    def is_special(self) -> bool:
        return self.x_overflow or self.surr_n_pole or self.surr_s_pole

    def _init_candidates(self):
        """
        here one might be tempted to only consider the actual detected zones of the parent cell
        to narrow down choice and speed up the computation up.
        however, the child hexagon cells protrude from the parent (cf. https://h3geo.org/docs/highlights/indexing)
            and hence the candidate zones are different
        solution: take the "true" parents not just the single parent
        note: do not just take the true included polygons,
            but only the candidates to avoid expensive point-in-polygon computations

        Note: also the root level hexagon cells are too large to easily check for polygon in hex inclusion
        (might overlap without included vertices but just intersecting edges!).
        Taking just the smaller set of candidates is still valid (no point in polygon check)
        """
        if self._poly_candidates is not None:
            # avoid overwriting initialised values
            return
        # self._poly_candidates = set(range(nr_of_polygons))
        # return
        if self.res == 0:
            # at the highest level all polygons should be tested
            self._poly_candidates = set(range(nr_of_polygons))
            return

        candidates: HexIdSet = set()
        for parent_id in self.true_parents:
            parent_hex = get_hex(parent_id)
            parent_polys = parent_hex.poly_candidates
            candidates.update(parent_polys)

        self._poly_candidates = candidates

    def is_poly_candidate(self, poly_id: int) -> bool:
        cell_bounds = self.bounds
        poly_bounds = poly_boundaries[poly_id]
        overlapping = cell_bounds.overlaps(poly_bounds)
        return overlapping

    @property
    def poly_candidates(self) -> Set[int]:
        self._init_candidates()
        real_candidates = set(filter(self.is_poly_candidate, self._poly_candidates))
        self._poly_candidates = real_candidates
        return self._poly_candidates

    def lies_in_cell(self, poly_nr: int) -> bool:
        hex_coords = self.coords
        poly_coords = polygons[poly_nr]
        overlap = any_pt_in_poly(hex_coords, poly_coords)
        if not overlap:
            # also test the inverse: if any point of the polygon lies inside the hex cell
            # ATTENTION: some hex cells cannot be used as polygons in regular point in polygon algorithm!
            overlap = any_pt_in_cell(self.id, poly_nr)

        # ATTENTION: in general polygons can overlap without having included vertices
        # usually the polygon edges would need to be checked for intersections
        # assumption: the polygons and cells have a similar size
        # and are small enough to just check vertex inclusion
        # valid simplification

        # account for holes in polygon
        # only check if found overlapping
        if overlap:
            for hole in _holes_in_poly(poly_nr):
                # check all hex point within hole
                if fully_contained_in_hole(hex_coords, hole):
                    return False
        return overlap

    @property
    def polys_in_cell(self) -> Set[int]:
        if self._polys_in_cell is None:
            # lazy evaluation, caching
            self._polys_in_cell = set(filter(self.lies_in_cell, self.poly_candidates))
        return self._polys_in_cell

    @property
    def zones_in_cell(self) -> Set[int]:
        if self._zones_in_cell is None:
            # lazy evaluation, caching
            self._zones_in_cell = set(
                map(lambda p: poly_zone_ids[p], self.polys_in_cell)
            )
        return self._zones_in_cell

    @property
    def children(self) -> Set[int]:
        return set(h3.cell_to_children(self.id))

    @property
    def outer_children(self) -> Set[int]:
        child_set = self.children
        center_child = h3.cell_to_center_child(self.id)
        child_set.remove(center_child)
        return child_set

    @property
    def neighbours(self) -> HexIdSet:
        return set(h3.grid_ring(self.id, k=1))

    @property
    def true_parents(self) -> HexIdSet:
        """
        hexagons do not cleanly subdivide into seven finer hexagons.
        the child hexagon cells protrude from the parent (cf. https://h3geo.org/docs/highlights/indexing)
            and hence a cell does not have a single, but actually up to 2 "true" parents

        returns: the hex ids of all parent cells which any of the cell points belong
        """
        if self.res == 0:
            raise ValueError("not defined for resolution 0")
        lower_res = self.res - 1
        # NOTE: (lat,lng) pairs!
        coord_pairs = h3.cell_to_boundary(self.id)
        return {h3.latlng_to_cell(pt[0], pt[1], lower_res) for pt in coord_pairs}


@functools.lru_cache(maxsize=int(1e6))
def get_hex(hex_id: int) -> Hex:
    # NOTE: do not evaluate constructor when value has been stored already!
    # return id2hex.get(hex_id) or id2hex.setdefault(hex_id, Hex.from_id(hex_id))
    return Hex.from_id(hex_id)


def optimise_shortcut_ordering(poly_ids: List[int]) -> List[int]:
    """optimises the order of polygon ids for faster timezone checks

    observation: as soon as just polygons of one zone are left, this zone can be returned
    -> try to "rule out" zones fast
    polygons from different zones should not get mixed up (group by zone id)
    point in polygon test is faster with smaller polygons (fewer coordinates)
    -> polygons of zones with fewer coordinates should come first!
    -> sort the list of polygon ids in each shortcut after the size of the corresponding polygons
    """
    if len(poly_ids) <= 1:
        return poly_ids
    global polygon_lengths

    poly_sizes = [polygon_lengths[i] for i in poly_ids]
    zone_ids = [poly_zone_ids[i] for i in poly_ids]
    zone_ids_unique = list(set(zone_ids))
    zipped = list(zip(poly_ids, zone_ids, poly_sizes))
    zone2size = {
        i: sum(map(lambda e: e[2], filter(lambda e: e[1] == i, zipped)))
        for i in zone_ids_unique
    }
    zone_ids_sorted = sorted(zone_ids_unique, key=lambda x: zone2size[x])
    poly_ids_sorted = []
    for zone_id in zone_ids_sorted:
        # smaller polygons can be ruled out faster -> smaller polygons should come first
        zone_entries = filter(lambda e: e[1] == zone_id, zipped)
        zone_entries_sorted = sorted(zone_entries, key=lambda x: x[2])
        zone_poly_ids_sorted, _, _ = zip(*zone_entries_sorted)
        poly_ids_sorted += list(zone_poly_ids_sorted)
    return poly_ids_sorted


def compile_h3_map(candidates: Set) -> ShortcutMapping:
    """
    operate on one hex resolution
    also store results separately to divide the output data files
    """
    global poly_zone_ids

    # convert to numpy array for advanced indexing
    poly_zone_ids = np.array(poly_zone_ids, dtype=DTYPE_FORMAT_H_NUMPY)

    mapping: ShortcutMapping = {}
    total_candidates = len(candidates)

    def report_progress():
        nr_candidates = len(candidates)
        processed = total_candidates - nr_candidates
        print(
            f"\r{processed:,} processed\t{nr_candidates:,} remaining\t",
            end="",
            flush=True,
        )

    while candidates:
        hex_id = candidates.pop()
        cell = get_hex(hex_id)
        polys = list(cell.polys_in_cell)
        # TODO separate optimisation into separate function
        polys_optimised = optimise_shortcut_ordering(polys)
        check_shortcut_sorting(polys_optimised, poly_zone_ids)
        mapping[hex_id] = polys_optimised
        report_progress()

    return mapping


def all_res_candidates(res: int) -> HexIdSet:
    print(f"compiling hex candidates for resolution {res}.")
    if res == 0:
        return set(h3.get_res0_cells())
    parent_res_candidates = all_res_candidates(res - 1)
    child_iter = (h3.cell_to_children(h) for h in parent_res_candidates)
    return set(itertools.chain.from_iterable(child_iter))


@time_execution
def compile_shortcut_mapping() -> ShortcutMapping:
    """compiles h3 hexagon shortcut mapping

    returns: mapping from hexagon id to list of polygon ids

    cf. https://eng.uber.com/h3/
    """
    print("\n\ncomputing timezone polygon index ('shortcuts')...")
    candidates = all_res_candidates(SHORTCUT_H3_RES)
    print(
        f"reached desired resolution {SHORTCUT_H3_RES}.\n"
        "storing mapping to timezone polygons for every hexagon candidate at this resolution (-> 'full coverage')"
    )
    shortcuts = compile_h3_map(candidates=candidates)
    print_shortcut_statistics(shortcuts, poly_zone_ids)
    return shortcuts


def create_and_write_hole_registry(polynrs_of_holes, output_path):
    """
    Creates a registry mapping each polygon id to a tuple (number of holes, first hole id),
    and writes it as JSON to the output path.
    """
    hole_registry = {}
    for i, poly_id in enumerate(polynrs_of_holes):
        try:
            amount_of_holes, hole_id = hole_registry[poly_id]
            hole_registry[poly_id] = (amount_of_holes + 1, hole_id)
        except KeyError:
            hole_registry[poly_id] = (1, i)
    path = get_hole_registry_path(output_path)
    write_json(hole_registry, path)


def to_numpy_array(values: List, dtype: str) -> np.ndarray:
    """
    Converts a list of values to a numpy array with the specified dtype.
    Args:
        values: List of values to convert
        dtype: Numpy dtype string (e.g., 'int32', 'float64')
    Returns:
        Numpy array with the specified dtype
    """
    return np.array(values, dtype=dtype)


def to_bbox_vector(values: List[int]) -> np.ndarray:
    return to_numpy_array(values, dtype=DTYPE_FORMAT_SIGNED_I_NUMPY)


def convert_bboxes_to_numpy(
    bboxes: List[Boundaries],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Converts a list of Boundaries to numpy arrays for xmax, xmin, ymax, ymin.
    Args:
        bboxes: List of Boundaries objects
    Returns:
        Tuple of numpy arrays (xmax, xmin, ymax, ymin)
    """
    xmax_list = []
    xmin_list = []
    ymax_list = []
    ymin_list = []
    for bounds in bboxes:
        xmax_list.append(bounds.xmax)
        xmin_list.append(bounds.xmin)
        ymax_list.append(bounds.ymax)
        ymin_list.append(bounds.ymin)
    xmax = to_bbox_vector(xmax_list)
    xmin = to_bbox_vector(xmin_list)
    ymax = to_bbox_vector(ymax_list)
    ymin = to_bbox_vector(ymin_list)
    return xmax, xmin, ymax, ymin


def write_numpy_binaries(output_path):
    print("Writing binary data to separate Numpy binary .npy files...")
    # some properties are very small but essential for the performance of the package
    # -> store them directly as numpy arrays (overhead is negligible) and read them into memory at runtime

    # ZONE_POSITIONS: where each timezone starts and ends
    zone_positions = compute_zone_positions()
    zone_positions_arr = to_numpy_array(zone_positions, dtype=DTYPE_FORMAT_H_NUMPY)
    zone_positions_path = get_zone_positions_path(output_path)
    store_per_polygon_vector(zone_positions_path, zone_positions_arr)

    # BOUNDARY_ZONE_IDS: the zone id for every polygon
    boundary_zone_ids = np.array(poly_zone_ids, dtype=DTYPE_FORMAT_H_NUMPY)
    # NOTE: zone ids are stored idependently from boundaries or holes
    zone_id_file = get_zone_ids_path(output_path)
    np.save(zone_id_file, boundary_zone_ids)

    # properties which are "per polygon" (boundary/hole) vectors
    # separate output directories for holes and boundaries
    holes_dir = get_holes_dir(output_path)
    boundaries_dir = get_boundaries_dir(output_path)

    holes_dir.mkdir(parents=True, exist_ok=True)
    boundaries_dir.mkdir(parents=True, exist_ok=True)

    hole_boundaries = compile_bboxes(holes)
    # save 4 bbox vectors for holes and polygons to the respective directories
    for dir, bounds in zip(
        [holes_dir, boundaries_dir], [hole_boundaries, poly_boundaries]
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


def get_file_size_in_mb(file_path: Path) -> float:
    """
    Returns the size of a file in megabytes.
    Args:
        file_path: Path to the file

    Returns:
        Size of the file in megabytes
    """
    size_in_bytes = file_path.stat().st_size
    size_in_mb = size_in_bytes / (1024**2)
    return size_in_mb


def write_flatbuffer_files(output_path: Path):
    # separate output directories for holes and boundaries
    holes_dir = get_holes_dir(output_path)
    boundaries_dir = get_boundaries_dir(output_path)

    holes_dir.mkdir(parents=True, exist_ok=True)
    boundaries_dir.mkdir(parents=True, exist_ok=True)

    print("Writing binary data to flatbuffer files...")
    # Write polygon boundary coordinates to flatbuffer
    boundary_polygon_file = get_coordinate_path(boundaries_dir)
    write_polygon_collection_flatbuffer(boundary_polygon_file, polygons)

    hole_polygon_file = get_coordinate_path(holes_dir)
    # Write holes coordinates to flatbuffer
    write_polygon_collection_flatbuffer(hole_polygon_file, holes)
    print("Flatbuffer files written successfully")


def write_binary_files(output_path: Path) -> None:
    """
    Write all binary files for the timezonefinder package.

    This uses FlatBuffers for all data structures to ensure consistent formats.

    Args:
        output_path: Directory where binary files will be written
    """
    write_numpy_binaries(output_path)
    write_flatbuffer_files(output_path)
    print("Binary files written successfully")


@time_execution
def compile_data_files(output_path):
    write_zone_names(all_tz_names, output_path)

    # Write registry for holes (which polygon each hole belongs to)
    create_and_write_hole_registry(polynrs_of_holes, output_path)

    # Write binary files
    write_binary_files(output_path)


def generate_polygon_statistics_table(
    polygon_type: str, count: int, length_list: List[int], additional_rows: List = None
) -> None:
    """
    Generate and print a table with statistics for a polygon collection.

    Args:
        polygon_type: Type of polygon ("Boundary" or "Hole")
        count: Number of polygons
        length_list: List of coordinate lengths for each polygon
        additional_rows: Optional additional rows to add to the table
    """
    # Safe handling for empty or missing data
    length_list = length_list or []
    polygon_type_lower = polygon_type.lower()

    if count == 0 or not length_list:
        print(f"No {polygon_type_lower} polygons found.")
        # Still print a table with zeros for consistency
        headers = [f"{polygon_type} Metric", "Value"]
        rows = [
            [f"Total {polygon_type_lower} polygons", "0"],
            [f"Total {polygon_type_lower} coordinates", "0"],
            [f"Total {polygon_type_lower} coordinate values (2 per point)", "0"],
        ]
        if additional_rows:
            rows.extend(additional_rows)
        print_rst_table(headers, rows)
        return

    # Calculate statistics
    total_coords = sum(length_list)
    total_floats = 2 * total_coords
    avg_length = round(sum(length_list) / len(length_list), 2)
    max_length = max(length_list)
    min_length = min(length_list)

    # Create table
    headers = [f"{polygon_type} Metric", "Value"]
    rows = [
        [f"Total {polygon_type_lower} polygons", f"{count:,}"],
        [f"Total {polygon_type_lower} coordinates", f"{total_coords:,}"],
        [
            f"Total {polygon_type_lower} coordinate values (2 per point)",
            f"{total_floats:,}",
        ],
        [f"Average coordinates per {polygon_type_lower} polygon", f"{avg_length:,}"],
        [f"Maximum coordinates in one {polygon_type_lower} polygon", f"{max_length:,}"],
        [f"Minimum coordinates in one {polygon_type_lower} polygon", f"{min_length:,}"],
    ]

    # Add any additional rows
    if additional_rows:
        rows.extend(additional_rows)

    print_rst_table(headers, rows)


def generate_metrics_rows(metric_type: str, metrics_dict: Dict) -> List[List]:
    """
    Generate additional metric rows for tables based on a dictionary of metrics.

    Args:
        metric_type: Type of metrics (e.g., "boundary", "hole")
        metrics_dict: Dictionary of metric names and values

    Returns:
        List of rows for a table
    """
    rows = []
    for label, value in metrics_dict.items():
        # Format numbers with commas and add % to percentages
        if isinstance(value, (int, float)):
            if "percentage" in label.lower() or "%" in label:
                formatted_value = f"{value}%"
            else:
                formatted_value = f"{value:,}" if value == int(value) else f"{value}"
        else:
            formatted_value = str(value)

        rows.append([label, formatted_value])
    return rows


@redirect_output_to_file(DATA_REPORT_FILE)
def report_data_statistics():
    """
    prints a report of the statistics of the timezone data.
    """
    print(".. _data_report:\n")
    print(rst_title("Data Report", level=0))
    print(rst_title("Data Statistics", level=1))

    # General statistics
    total_floats_boundaries = 2 * sum(polygon_lengths) if polygon_lengths else 0
    total_floats_holes = 2 * sum(all_hole_lengths) if all_hole_lengths else 0
    total_floats = total_floats_boundaries + total_floats_holes

    # Create a table of overall dataset statistics
    general_metrics = {"Total coordinate values (2 per point)": total_floats}

    print_rst_table(
        ["General Metric", "Value"], generate_metrics_rows("general", general_metrics)
    )

    print(rst_title("Boundary Polygon Statistics", level=2))

    # Additional boundary-specific statistics
    boundary_metrics = {}
    boundary_rows = generate_metrics_rows("boundary", boundary_metrics)
    generate_polygon_statistics_table(
        "Boundary", nr_of_polygons, polygon_lengths, boundary_rows
    )

    print(rst_title("Hole Polygon Statistics", level=2))
    # Hole-specific additional statistics
    polygons_with_holes = len(set(polynrs_of_holes)) if polynrs_of_holes else 0

    hole_metrics = {
        "Number of boundary polygons with holes": polygons_with_holes,
        "Percentage of boundary polygons with holes": round(
            (polygons_with_holes / nr_of_polygons) * 100, 2
        )
        if nr_of_polygons > 0 and polygons_with_holes > 0
        else 0,
        "Average holes per boundary polygon (with holes)": round(
            nr_of_holes / polygons_with_holes, 2
        )
        if polygons_with_holes > 0
        else 0,
    }

    hole_rows = generate_metrics_rows("hole", hole_metrics)
    generate_polygon_statistics_table("Hole", nr_of_holes, all_hole_lengths, hole_rows)

    # Add timezone statistics table
    print(rst_title("Timezone Statistics", level=2))

    # Count polygons per timezone
    polygons_per_timezone = Counter(poly_zone_ids)

    # Calculate statistics about timezones
    timezone_metrics = {
        "Total timezones": nr_of_zones,
        "Average boundary polygons per timezone": round(nr_of_polygons / nr_of_zones, 2)
        if nr_of_zones > 0
        else 0,
        "Maximum polygons in one timezone": max(polygons_per_timezone.values())
        if polygons_per_timezone
        else 0,
        "Minimum polygons in one timezone": min(polygons_per_timezone.values())
        if polygons_per_timezone
        else 0,
        "Median polygons per timezone": sorted(list(polygons_per_timezone.values()))[
            len(polygons_per_timezone) // 2
        ]
        if polygons_per_timezone
        else 0,
        "Timezones with single polygon": sum(
            1 for count in polygons_per_timezone.values() if count == 1
        ),
        "Percentage of single-polygon timezones": round(
            (
                sum(1 for count in polygons_per_timezone.values() if count == 1)
                / nr_of_zones
            )
            * 100,
            2,
        )
        if nr_of_zones > 0
        else 0,
        "Timezones with 10+ polygons": sum(
            1 for count in polygons_per_timezone.values() if count >= 10
        ),
        "Percentage of timezones with 10+ polygons": round(
            (
                sum(1 for count in polygons_per_timezone.values() if count >= 10)
                / nr_of_zones
            )
            * 100,
            2,
        )
        if nr_of_zones > 0
        else 0,
        "Most complex timezone (polygons)": f"{all_tz_names[max(polygons_per_timezone.items(), key=lambda x: x[1])[0]]} ({max(polygons_per_timezone.values())} polygons)"
        if polygons_per_timezone
        else "None",
        "Least complex timezone (polygons)": f"{all_tz_names[min(polygons_per_timezone.items(), key=lambda x: x[1])[0]]} ({min(polygons_per_timezone.values())} polygons)"
        if polygons_per_timezone
        else "None",
    }

    # Print timezone statistics table
    timezone_rows = generate_metrics_rows("timezone", timezone_metrics)
    print_rst_table(["Timezone Metric", "Value"], timezone_rows)


@redirect_output_to_file(DATA_REPORT_FILE)
def report_file_sizes(output_path: Path):
    """
    Reports the sizes of the biggest generated binary files.

    NOTE: smaller .npy files are not reported here, since their size is negligible

    Args:
        output_path: Path to the output directory containing the binary files
    """
    print(rst_title("Binary File Sizes", level=1))
    holes_dir = get_holes_dir(output_path)
    boundaries_dir = get_boundaries_dir(output_path)

    boundary_polygon_file = get_coordinate_path(boundaries_dir)
    hole_polygon_file = get_coordinate_path(holes_dir)

    names_and_paths = {
        "boundary polygon data": boundary_polygon_file,
        "hole polygon data": hole_polygon_file,
        "shortcuts": get_shortcut_file_path(output_path),
    }
    names_and_sizes = {
        name: get_file_size_in_mb(path) for name, path in names_and_paths.items()
    }
    total_space = sum(names_and_sizes.values())

    # Print total size summary
    print(
        f"Total space used by polygon and shortcut binary files: {total_space:.2f} MB\n"
    )

    # Create table for file sizes
    headers = ["File Type", "Size (MB)", "Percentage"]
    rows = [
        [name, f"{size:.2f}", f"{size / total_space:.2%}"]
        for name, size in names_and_sizes.items()
    ]

    # Add total row
    rows.append(["Total", f"{total_space:.2f}", "100.00%"])

    # Print the table
    print_rst_table(headers, rows)


def write_data_report(shortcuts: ShortcutMapping, output_path: Path):
    if DATA_REPORT_FILE.exists():
        print(f"Removing old data report file: {DATA_REPORT_FILE}")
        DATA_REPORT_FILE.unlink()

    print("Writing data report to:", DATA_REPORT_FILE)
    report_data_statistics()
    report_file_sizes(output_path)
    print_shortcut_statistics(shortcuts, poly_zone_ids)


@time_execution
def parse_data(
    input_path: Union[Path, str] = DEFAULT_INPUT_PATH,
    output_path: Union[Path, str] = DEFAULT_DATA_DIR,
):
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    parse_polygons_from_json(input_path)

    compile_data_files(output_path)
    shortcuts = compile_shortcut_mapping()
    write_shortcuts_flatbuffers(shortcuts, output_path)

    print(f"\n\nfinished parsing timezonefinder data to {output_path}")

    write_data_report(shortcuts, output_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="parse data directories")
    parser.add_argument(
        "-inp", help="path to input JSON file", default=DEFAULT_INPUT_PATH
    )
    parser.add_argument(
        "-out",
        help="path to output folder for storing the parsed data files",
        default=DEFAULT_DATA_DIR,
    )
    parsed_args = parser.parse_args()

    parse_data(input_path=parsed_args.inp, output_path=parsed_args.out)
