"""
USAGE:

- download the latest timezones.geojson.zip file from github.com/evansiroky/timezone-boundary-builder/releases
- unzip and place the combined.json inside the `scripts` folder
- run this `file_converter.py` script to compile the data files.


IMPORTANT: all coordinates (floats) of the timezone polygons are being converted to int32 (multiplied by 10^7).
This makes computations faster and it takes lot less space,
    without loosing too much accuracy (min accuracy (=at the equator) is still 1cm !)


https://docs.python.org/3/library/struct.html#format-characters
B = unsigned char (1byte integer)
H = unsigned short (2 byte integer)
I = unsigned 4byte integer
i = signed 4byte integer
Q = unsigned 8byte integer

Binaries being written:

[POLYGONS:]
poly_zone_ids: the related zone_id for every polygon ('<H')
poly_coord_amount: the amount of coordinates in every polygon ('<I')
poly_adr2data: address in poly_data.bin where data for every polygon starts ('<I')
poly_bounds: boundaries for every polygon ('<iiii': xmax, xmin, ymax, ymin)
poly_data: coordinates for every polygon (N coordinates: 2N '<i'), first all x then all y values
poly_nr2zone_id: the polygon number of the first polygon from every zone ('<H'),
    used for reading all polygons of one zone

[HOLES:]
hole_poly_ids: the related polygon_nr (=id) for every hole ('<H')
hole_coord_amount: the amount of coordinates in every hole ('<H')
hole_adr2data: address in hole_data.bin where data for every hole starts ('<I')
hole_data: coordinates for every hole (multiple times '<i')

[SHORTCUTS:] coordinate to polygon id indexing
shortcuts drastically reduce the amount of polygons which need to be checked in order to
    decide which timezone a point is located in.
the surface of the world is split up into a grid of hexagons (h3 library)
shortcut here means storing for every cell in a grid of the world map which polygons are located in that cell.

shortcuts.bin: per entry : hex id "<Q", nr of entries "<B", poly ids of entry "<H".
Note: the poly ids within one shortcut entry are sorted for optimal performance


Uber H3 findings:
replacing the polygon data with hexagon key mappings failed,
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
import functools
import itertools
import json
from dataclasses import dataclass
from os.path import abspath, join
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Set, Tuple, Union

import h3.api.numpy_int as h3
import numpy as np

from scripts.configs import (
    DEBUG,
    DEBUG_POLY_STOP,
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_PATH,
    MAX_LAT,
    MAX_LNG,
    HexIdSet,
    PolyIdSet,
    ZoneIdSet,
)
from scripts.utils import (
    print_shortcut_statistics,
    time_execution,
    to_numpy_polygon,
    write_binary,
    write_boundary_data,
    write_coordinate_data,
    write_json,
)
from timezonefinder.configs import (
    DTYPE_FORMAT_H,
    DTYPE_FORMAT_I,
    HOLE_ADR2DATA,
    HOLE_COORD_AMOUNT,
    HOLE_DATA,
    HOLE_REGISTRY_FILE,
    NR_BYTES_I,
    POLY_ADR2DATA,
    POLY_COORD_AMOUNT,
    POLY_DATA,
    POLY_MAX_VALUES,
    POLY_NR2ZONE_ID,
    POLY_ZONE_IDS,
    SHORTCUT_FILE,
    SHORTCUT_H3_RES,
    THRES_DTYPE_H,
    THRES_DTYPE_I,
    TIMEZONE_NAMES_FILE,
)
from timezonefinder.hex_helpers import export_shortcuts_binary, lies_in_h3_cell
from timezonefinder.utils import (
    any_pt_in_poly,
    coord2int,
    fully_contained_in_hole,
    int2coord,
)

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
poly_nr2zone_id = []


def _holes_in_poly(poly_nr):
    for i, nr in enumerate(polynrs_of_holes):
        if nr == poly_nr:
            yield holes[i]


def parse_polygons_from_json(input_path: Path) -> int:
    global nr_of_holes, nr_of_polygons, nr_of_zones, poly_zone_ids
    global polygons, polygon_lengths, poly_zone_ids, poly_boundaries

    print(f"parsing input file: {input_path}\n...\n")
    with open(input_path) as json_file:
        tz_list = json.loads(json_file.read()).get("features")

    poly_id = 0
    zone_id = 0
    print("extracting data.\nfound holes:")
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

            if DEBUG and poly_id > DEBUG_POLY_STOP:
                break
            # the first entry is the outer polygon
            # NOTE: starting from here, only coordinates converted into int32 will be considered!
            # this allows using the JIT util function already here
            poly = to_numpy_polygon(poly_with_hole.pop(0))
            polygons.append(poly)
            x_coords = poly[0]
            y_coords = poly[1]
            polygon_lengths.append(len(x_coords))
            bounds = Boundaries(
                np.max(x_coords), np.min(x_coords), np.max(y_coords), np.min(y_coords)
            )
            poly_boundaries.append(bounds)
            poly_zone_ids.append(zone_id)

            # everything else is interpreted as a hole!
            for hole_nr, hole in enumerate(poly_with_hole):
                print(f"#{nr_of_holes}: polygon #{poly_id}({hole_nr}) zone: {tz_name}")
                nr_of_holes += 1  # keep track of how many holes there are
                polynrs_of_holes.append(poly_id)
                hole_poly = to_numpy_polygon(hole)
                holes.append(hole_poly)
                nr_coords = hole_poly.shape[1]
                assert nr_coords >= 3
                all_hole_lengths.append(nr_coords)

            poly_id += 1

    nr_of_polygons = len(polygon_lengths)
    nr_of_zones = len(all_tz_names)
    assert nr_of_polygons >= 0
    assert nr_of_polygons >= nr_of_zones
    assert zone_id == nr_of_zones - 1
    assert (
        poly_id == nr_of_polygons
    ), f"polygon counter {poly_id} and entry amount in all_length {nr_of_polygons} are different."

    if 0 in polygon_lengths:
        raise ValueError()

    # binary file value range tests:
    assert (
        nr_of_polygons < THRES_DTYPE_H
    ), f"address overflow: #{nr_of_polygons} polygon ids cannot be encoded as {DTYPE_FORMAT_H}!"
    assert (
        nr_of_zones < THRES_DTYPE_H
    ), f"address overflow: #{nr_of_zones} zone ids cannot be encoded as {DTYPE_FORMAT_H}!"
    max_poly_length = max(polygon_lengths)
    assert (
        max_poly_length < THRES_DTYPE_I
    ), f"address overflow: the maximal amount of coords {max_poly_length} cannot be represented by {DTYPE_FORMAT_I}"
    max_hole_poly_length = max(all_hole_lengths)
    assert max_hole_poly_length < THRES_DTYPE_H, (
        f"address overflow: the maximal amount of coords in hole polygons "
        f"{max_hole_poly_length} cannot be represented by {DTYPE_FORMAT_I}"
    )

    print("... parsing done. found:")
    print(f"{nr_of_polygons:,} polygons from")
    print(f"{nr_of_zones:,} timezones with")
    print(f"{nr_of_holes:,} holes")
    print(f"{max_poly_length:,} maximal amount of coordinates in one polygon")
    print(f"{max_hole_poly_length:,} maximal amount of coordinates in a hole polygon")
    # there are two floats per coordinate (lng, lat)
    nr_of_floats = 2 * sum(polygon_lengths)
    print(f"{nr_of_floats:,} floats in all the polygons (2 per point)")
    polygon_space = nr_of_floats * NR_BYTES_I
    return polygon_space


def update_zone_names(output_path):
    # update all the zone names and set the right ids to be written in the poly_zone_ids.bin
    global poly_zone_ids
    global list_of_pointers
    global poly_boundaries
    global polygons
    global polygon_lengths
    global polynrs_of_holes
    global nr_of_zones
    global nr_of_polygons
    file_path = abspath(join(output_path, TIMEZONE_NAMES_FILE))
    print(f"updating the zone names in {file_path} now.")
    # pickle the zone names (python array)
    write_json(all_tz_names, file_path)
    print("...Done.\n\nComputing where zones start and end...")
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
        res = h3.h3_get_resolution(id)
        coord_pairs = h3.h3_to_geo_boundary(id)
        # ATTENTION: (lat, lng)! pairs
        coords = to_numpy_polygon(coord_pairs, flipped=True)
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
        # TODO test once again
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
        return set(h3.h3_to_children(self.id))

    @property
    def outer_children(self) -> Set[int]:
        child_set = self.children
        center_child = h3.h3_to_center_child(self.id)
        child_set.remove(center_child)
        return child_set

    @property
    def neighbours(self) -> HexIdSet:
        return set(h3.k_ring(self.id, k=1))

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
        coord_pairs = h3.h3_to_geo_boundary(self.id)
        return {h3.geo_to_h3(pt[0], pt[1], lower_res) for pt in coord_pairs}


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
    mapping: ShortcutMapping = {}
    total_candidates = len(candidates)

    def report_progress():
        nr_candidates = len(candidates)
        processed = total_candidates - nr_candidates
        print(
            f"\r{processed:,} processed\t{nr_candidates:,} remaining\t",
            end="",
        )

    while candidates:
        hex_id = candidates.pop()
        cell = get_hex(hex_id)
        polys = list(cell.polys_in_cell)
        mapping[hex_id] = optimise_shortcut_ordering(polys)
        report_progress()

    return mapping


def all_res_candidates(res: int) -> HexIdSet:
    print(f"compiling hex candidates for resolution {res}.")
    if res == 0:
        return set(h3.get_res0_indexes())
    parent_res_candidates = all_res_candidates(res - 1)
    child_iter = (h3.h3_to_children(h) for h in parent_res_candidates)
    return set(itertools.chain.from_iterable(child_iter))


@time_execution
def compile_shortcut_mapping(output_path: Path) -> int:
    """compiles h3 hexagon shortcut mapping

    returns: mapping from hexagon id to list of polygon ids

    cf. https://eng.uber.com/h3/
    """
    candidates = all_res_candidates(SHORTCUT_H3_RES)
    print(
        f"reached desired resolution {SHORTCUT_H3_RES}.\n"
        "storing mapping to timezone polygons for every hexagon candidate at this resolution (-> 'full coverage')"
    )
    path2shortcut_file = Path(output_path) / SHORTCUT_FILE
    shortcuts = compile_h3_map(candidates=candidates)
    print_shortcut_statistics(shortcuts, poly_zone_ids)
    shortcut_space = export_shortcuts_binary(shortcuts, path2shortcut_file)
    validate_shortcut_mapping(shortcuts)
    return shortcut_space


def geo_to_h3(lng: float, lat: float) -> int:
    return h3.geo_to_h3(lat, lng, SHORTCUT_H3_RES)


def validate_shortcut_completeness(mapping: ShortcutMapping):
    print("validating shortcut completeness...")

    error = False
    for poly_id, poly in enumerate(polygons):
        print(f"validating polygon {poly_id}")
        for i, pt in enumerate(poly.T):
            # ATTENTION: int to coord conversion required!
            lng = int2coord(pt[0])
            lat = int2coord(pt[1])
            hex_id = geo_to_h3(lng, lat)
            try:
                shortcut_entries = mapping[hex_id]
            except KeyError:
                raise ValueError(
                    f"shortcut mapping is incomplete at point ({lng}, {lat}) "
                    f"(hexagon cell id {hex_id} missing in mapping)"
                )
            if poly_id not in shortcut_entries:
                print(
                    f"ERR: point #{i} ({lng}, {lat}) of polygon {poly_id} "
                    f"does not appear in shortcut entries {shortcut_entries} of cell {hex_id}"
                )
                error = True

    assert not error


def validate_shortcut_resolution(mapping: ShortcutMapping):
    for hex_id in mapping.keys():
        assert h3.h3_get_resolution(hex_id) == SHORTCUT_H3_RES


@time_execution
def validate_shortcut_mapping(mapping: ShortcutMapping):
    print("validating shortcut mapping")
    validate_shortcut_resolution(mapping)
    validate_shortcut_completeness(mapping)


@time_execution
def compile_polygon_binaries(output_path):
    global nr_of_polygons

    def compile_addresses(
        length_list: List[int], multiplier: int, byte_amount_per_entry: int
    ):
        adr = 0
        addresses = [adr]
        for length in length_list:
            adr += multiplier * byte_amount_per_entry * length
            addresses.append(adr)
        return addresses

    # NOTE: last entry is nr_of_polygons -> allow +1
    write_binary(
        output_path,
        POLY_NR2ZONE_ID,
        poly_nr2zone_id,
        upper_value_limit=nr_of_polygons + 1,
    )
    write_binary(
        output_path, POLY_ZONE_IDS, poly_zone_ids, upper_value_limit=nr_of_zones
    )
    write_boundary_data(output_path, POLY_MAX_VALUES, poly_boundaries)
    write_coordinate_data(output_path, POLY_DATA, polygons)
    write_binary(
        output_path,
        POLY_COORD_AMOUNT,
        polygon_lengths,
        data_format=DTYPE_FORMAT_I,
        upper_value_limit=THRES_DTYPE_I,
    )

    # 2 entries per coordinate
    poly_addresses = compile_addresses(
        polygon_lengths, multiplier=2, byte_amount_per_entry=NR_BYTES_I
    )
    write_binary(
        output_path,
        POLY_ADR2DATA,
        poly_addresses,
        data_format=DTYPE_FORMAT_I,
        upper_value_limit=THRES_DTYPE_I,
    )

    # [HOLE AREA, Y = number of holes (very few: around 22)]
    hole_space = 0

    # store for which polygons (how many) holes exits and the id of the first of those holes
    # since there are very few it is feasible to keep them in memory
    # -> export and import as json
    hole_registry = {}
    # read the polygon ids for all the holes
    for i, poly_id in enumerate(polynrs_of_holes):
        try:
            amount_of_holes, hole_id = hole_registry[poly_id]
            hole_registry.update(
                {
                    poly_id: (amount_of_holes + 1, hole_id),
                }
            )
        except KeyError:
            hole_registry.update(
                {
                    poly_id: (1, i),
                }
            )

    with open(join(output_path, HOLE_REGISTRY_FILE), "w") as json_file:
        json.dump(hole_registry, json_file, indent=4)

    # '<H'  Y times [H unsigned short: nr of values (coordinate PAIRS! x,y in int32 int32) in this hole]
    assert len(all_hole_lengths) == nr_of_holes
    used_space = write_binary(output_path, HOLE_COORD_AMOUNT, all_hole_lengths)
    hole_space += used_space

    # '<I' Y times [ I unsigned int: absolute address of the byte where the data of that hole starts]
    write_binary(
        output_path,
        POLY_ADR2DATA,
        poly_addresses,
        data_format=DTYPE_FORMAT_I,
        upper_value_limit=THRES_DTYPE_I,
    )

    # 2 entries per coordinate
    hole_adr2data = compile_addresses(
        all_hole_lengths, multiplier=2, byte_amount_per_entry=NR_BYTES_I
    )
    used_space = write_binary(
        output_path,
        HOLE_ADR2DATA,
        hole_adr2data,
        data_format=DTYPE_FORMAT_I,
        upper_value_limit=THRES_DTYPE_I,
    )
    hole_space += used_space

    # Y times [ 2x i signed ints for every hole: x coords, y coords ]
    used_space = write_coordinate_data(output_path, HOLE_DATA, holes)
    hole_space += used_space
    return hole_space


@time_execution
def parse_data(
    input_path: Union[Path, str] = DEFAULT_INPUT_PATH,
    output_path: Union[Path, str] = DEFAULT_OUTPUT_PATH,
):
    polygon_space = parse_polygons_from_json(input_path)
    update_zone_names(output_path)
    hole_space = compile_polygon_binaries(output_path)

    shortcut_space = compile_shortcut_mapping(output_path)

    total_space = polygon_space + hole_space + shortcut_space
    print(f"the polygon data makes up {polygon_space / total_space:.2%} of the data")
    print(f"the shortcuts make up {shortcut_space / total_space:.2%} of the data")
    print(f"holes make up {hole_space / total_space:.2%}  of the data")
    print(f"\n\nfinished parsing timezonefinder data to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="parse data directories")
    parser.add_argument(
        "-inp", help="path to input JSON file", default=DEFAULT_INPUT_PATH
    )
    parser.add_argument(
        "-out",
        help="path to output folder for storing the parsed data files",
        default=DEFAULT_OUTPUT_PATH,
    )
    parsed_args = parser.parse_args()  # takes input from sys.argv
    parse_data(input_path=parsed_args.inp, output_path=parsed_args.out)
