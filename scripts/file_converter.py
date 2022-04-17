"""
USAGE:

- download the latest timezones.geojson.zip file from github.com/evansiroky/timezone-boundary-builder/releases
- unzip and place the combined.json inside this timezonefinder folder
- run this file_converter.py as a script until the compilation of the binary files is completed.


IMPORTANT: all coordinates (floats) are being converted to int32 (multiplied by 10^7). This makes computations faster
and it takes lot less space, without loosing too much accuracy (min accuracy (=at the equator) is still 1cm !)

B = unsigned char (1byte = 8bit Integer)
H = unsigned short (2 byte integer)
I = unsigned 4byte integer
i = signed 4byte integer


Binaries being written:

[POLYGONS:] there are approx. 1k Polygons (evansiroky/timezone-boundary-builder 2017a)
poly_zone_ids: the related zone_id for every polygon ('<H')
poly_coord_amount: the amount of coordinates in every polygon ('<I')
poly_adr2data: address in poly_data.bin where data for every polygon starts ('<I')
poly_max_values: boundaries for every polygon ('<iiii': xmax, xmin, ymax, ymin)
poly_data: coordinates for every polygon (multiple times '<i') (for every polygon first all x then all y values!)
poly_nr2zone_id: the polygon number of the first polygon from every zone('<H')

[HOLES:] number of holes (162 evansiroky/timezone-boundary-builder 2018d)
hole_poly_ids: the related polygon_nr (=id) for every hole ('<H')
hole_coord_amount: the amount of coordinates in every hole ('<H')
hole_adr2data: address in hole_data.bin where data for every hole starts ('<I')
hole_data: coordinates for every hole (multiple times '<i')

[SHORTCUTS:] the surface of the world is split up into a grid of shortcut rectangles.
-> there are a total of 360 * NR_SHORTCUTS_PER_LNG * 180 * NR_SHORTCUTS_PER_LAT shortcuts
shortcut here means storing for every cell in a grid of the world map which polygons are located in that cell
they can therefore be used to drastically reduce the amount of polygons which need to be checked in order to
decide which timezone a point is located in.

the list of polygon ids in each shortcut is sorted after freq. of appearance of their zone id
the polygons of the least frequent zone come first
this is critical for ruling out zones faster (as soon as just polygons of one zone are left this zone can be returned)

shortcuts_entry_amount: the amount of polygons for every shortcut ('<H')
shortcuts_adr2data: address in shortcut_data.bin where data for every shortcut starts ('<I')
shortcuts_data: polygon numbers (ids) for every shortcut (multiple times '<H')
shortcuts_direct_id: the id of the most common zone in that shortcut,
                     a high number (with no corresponding zone) if no zone is present ('<H').
                     the majority of zones either have no polygons at all (sea) or just one zone.
                     this zone then can be instantly returned without actually testing polygons.
shortcuts_unique_id: the zone id if only polygons from one zone are present,
                     a high number (with no corresponding zone) if not ('<H').
                     this zone then can be instantly returned without actually testing polygons.
                    the majority of shortcuts either have no polygons at all (sea) or just one zone
                    (cf. statistics below)



statistics:
DATA WITH OCEANS (2020d):

... parsing done. found:
1,403 polygons from
451 timezones with
805 holes
151,050 maximal amount of coordinates in one polygon
21,495 maximal amount of coordinates in a hole polygon

calculating the shortcuts took: 0:01:21.594385

shortcut statistics:
highest entry amount is 49
frequencies of entry amounts (from 0 to max entries):
[0, 109402, 18113, 1828, 187, 35, 14, 6, 5, 3, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
relative accumulated frequencies [%]:
[0.0, 84.42, 98.39, 99.8, 99.95, 99.97, 99.98, 99.99, 99.99, 99.99, 100.0, ...
         100.0]
[100.0, 15.58, 1.61, 0.2, 0.05, 0.03, 0.02, 0.01, 0.01, 0.01, 0.0, ... 0.0]
0.0 % of all shortcuts are empty

highest amount of different zones in one shortcut is 7
frequencies of entry amounts (from 0 to max):
[0, 109403, 18489, 1572, 120, 13, 1, 2]
relative accumulated frequencies [%]:
[0.0, 84.42, 98.68, 99.9, 99.99, 100.0, 100.0, 100.0]
[100.0, 15.58, 1.32, 0.1, 0.01, 0.0, 0.0, 0.0]
--------------------------------

The number of filled shortcut zones are:  129600 (= 100.0 % of all shortcuts)
number of polygons: 1403
number of floats in all the polygons: 12,644,038 (2 per point)

the polygon data makes up 94.67 % of the data
the shortcuts make up 2.03 % of the data
holes make up 3.31 % of the data
"""
import functools
import itertools
import json
from dataclasses import dataclass
from os import path
from os.path import abspath, join
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Tuple, Union

import h3.api.numpy_int as h3
import numpy as np

from scripts.configs import (
    DEBUG,
    DEBUG_POLY_STOP,
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_PATH,
    MAX_LAT,
    MAX_LNG,
    POLY_DTYPE,
    HexIdSet,
    PolyIdSet,
    ZoneIdSet,
)
from scripts.numba_utils import any_pt_in_poly, fully_contained_in_hole
from scripts.utils import extract_coords, write_json, write_pickle
from timezonefinder.configs import (
    DTYPE_FORMAT_H,
    DTYPE_FORMAT_I,
    MAX_RES,
    SHORTCUT_FILE,
    THRES_DTYPE_H,
    THRES_DTYPE_I,
    TIMEZONE_NAMES_FILE,
)
from timezonefinder.hex_helpers import export_shortcuts_binary, read_shortcuts_binary

nr_of_polygons = -1
nr_of_zones = -1
all_tz_names = []
poly_zone_ids = []
poly_boundaries = []
polygons = []
polygon_lengths = []
nr_of_holes = 0
polynrs_of_holes = []
holes = []
all_hole_lengths = []
list_of_pointers = []
poly_nr2zone_id = []


# id2hex: Dict[int, Hex] = {}


def most_common_zone_id(polys: Iterable[int]) -> int:
    zones = list(map(lambda p: poly_zone_ids[p], polys))
    zones_unique, counts = np.unique(zones, return_counts=True)
    most_common = zones_unique[np.argmax(counts)]
    return most_common


def _holes_in_poly(poly_nr):
    for i, nr in enumerate(polynrs_of_holes):
        if nr == poly_nr:
            yield holes[i]


def coords2polygon(x_coords, y_coords) -> np.ndarray:
    return np.array((x_coords, y_coords), dtype=POLY_DTYPE)


def parse_polygons_from_json(input_path):
    global nr_of_holes, nr_of_polygons, nr_of_zones, poly_zone_ids

    print(f"parsing input file: {input_path}\n...\n")
    with open(input_path) as json_file:
        tz_list = json.loads(json_file.read()).get("features")

    polygon_counter = 0  # this counter just counts polygons, not holes!
    current_zone_id = 0
    print("extracting data.\nfound holes:")
    for tz_dict in tz_list:
        if DEBUG and polygon_counter > DEBUG_POLY_STOP:
            break

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
            # the first entry is polygon
            x_coords, y_coords = extract_coords(poly_with_hole.pop(0))
            poly = coords2polygon(x_coords, y_coords)
            polygons.append(poly)
            polygon_lengths.append(len(x_coords))
            bounds = Boundaries(
                max(x_coords), min(x_coords), max(y_coords), min(y_coords)
            )
            poly_boundaries.append(bounds)
            poly_zone_ids.append(current_zone_id)

            # everything else is interpreted as a hole!
            for hole_nr, hole in enumerate(poly_with_hole):
                print(
                    f"#{nr_of_holes}: polygon #{polygon_counter}({hole_nr}) zone: {tz_name}"
                )
                nr_of_holes += 1  # keep track of how many holes there are
                polynrs_of_holes.append(polygon_counter)
                x_coords, y_coords = extract_coords(hole)
                holes.append(coords2polygon(x_coords, y_coords))
                all_hole_lengths.append(len(x_coords))

            polygon_counter += 1

        current_zone_id += 1

    nr_of_polygons = len(polygon_lengths)
    assert polygon_counter == nr_of_polygons
    nr_of_zones = len(all_tz_names)
    assert current_zone_id == nr_of_zones
    assert nr_of_polygons >= nr_of_zones

    assert (
        polygon_counter == nr_of_polygons
    ), f"polygon counter {polygon_counter} and entry amount in all_length {nr_of_polygons} are different."

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
    print("\n")


def update_zone_names(output_path):
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
    for poly_nr, zone_id in enumerate(poly_zone_ids):
        if zone_id != last_id:
            poly_nr2zone_id.append(poly_nr)
            assert zone_id >= last_id
            last_id = zone_id
    assert (
        zone_id == nr_of_zones - 1
    ), f"not pointing to the last zone with id {nr_of_zones - 1}"
    assert nr_of_polygons == len(poly_zone_ids)
    assert (
        poly_nr == nr_of_polygons - 1
    ), f"not pointing to the last polygon with id {nr_of_polygons - 1}"
    # ATTENTION: add one more entry for knowing where the last zone ends!
    # ATTENTION: the last entry is one higher than the last polygon id (to be consistant with the
    poly_nr2zone_id.append(nr_of_polygons)
    assert len(poly_nr2zone_id) == nr_of_zones + 1
    print("...Done.\n")


def lies_in_h3_cell(h, lng, lat):
    res = h3.h3_get_resolution(h)
    return h3.geo_to_h3(lat, lng, res) == h


def any_pt_in_cell(h: int, poly_nr: int) -> bool:
    def pt_in_cell(pt):
        return lies_in_h3_cell(h, pt[0], pt[1])

    poly = polygons[poly_nr]
    return any(map(pt_in_cell, poly.T))


def pts_not_in_cell(h: int, coords: np.ndarray) -> Iterable[np.ndarray]:
    def not_in_cell(pt):
        return not lies_in_h3_cell(h, pt[0], pt[1])

    return filter(not_in_cell, coords.T)


def get_corrected_hex_boundaries(
    x_coords, y_coords, surr_n_pole, surr_s_pole
) -> Tuple["Boundaries", bool]:
    # ATTENTION: a h3 polygon may cross the boundaries of the lat/lng coordinate plane (only in lng=x direction)
    # -> cannot use usual geometry assumptions (polygon algorithm, min max boundary check etc.)
    # -> rectify boundaries
    xmax0, xmin0, ymax0, ymin0 = (
        max(x_coords),
        min(x_coords),
        max(y_coords),
        min(y_coords),
    )
    if surr_n_pole:
        # clip to max lat
        ymax0 = MAX_LAT
    elif surr_s_pole:
        # clip to min lat
        ymin0 = -MAX_LAT

    # Observation: a h3 hexagon can only span a fraction of the globe (<< 360 degree)
    # use this property to clip the correct bounding boxes
    x_overflow = abs(xmax0 - xmin0) > 150.0
    if x_overflow:
        # high longitude difference observed. could indicate crossing the 180 deg lng boundary
        # -> search all lngs, to be save
        xmin0 = -MAX_LNG
        xmax0 = MAX_LNG

    return Boundaries(xmax0, xmin0, ymax0, ymin0), x_overflow


class Boundaries(NamedTuple):
    xmax: float
    xmin: float
    ymax: float
    ymin: float


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
    def from_id(cls, id):
        res = h3.h3_get_resolution(id)
        # ATTENTION: (lat, lng)! pairs
        coord_pairs = h3.h3_to_geo_boundary(id)
        y_coords, x_coords = extract_coords(coord_pairs)
        coords = coords2polygon(x_coords, y_coords)
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
        if self._poly_candidates is not None:
            # avoid overwriting initialised values
            # NOTE: this allows setting the candidates with some custom set
            #   as it is required when completing the cell coverage!
            return
        if self.res == 0:
            # at the highest level all polygons have to be tested
            self._poly_candidates = set(range(nr_of_polygons))
            return

        # at lower levels only consider the actual detected zones of parent
        # -> narrow down choice to speed computation up
        # (previously computed and cached, not just candidates):
        parent_id = h3.h3_to_parent(self.id)
        parent = get_hex(parent_id)
        self._poly_candidates = parent.polys_in_cell

    def is_poly_candidate(self, poly_id: int) -> bool:
        cell_bounds = self.bounds
        poly_bound = poly_boundaries[poly_id]
        if poly_bound.xmin > cell_bounds.xmax:
            return False
        if poly_bound.xmax < cell_bounds.xmin:
            return False
        if poly_bound.ymin > cell_bounds.ymax:
            return False
        if poly_bound.ymax < cell_bounds.ymin:
            return False
        return True

    @property
    def poly_candidates(self) -> Set[int]:
        self._init_candidates()
        self._poly_candidates = set(
            filter(self.is_poly_candidate, self._poly_candidates)
        )
        return self._poly_candidates

    def lies_in_cell(self, poly_nr: int) -> bool:
        hex_coords = self.coords
        poly_coords = polygons[poly_nr]
        overlap = any_pt_in_poly(hex_coords, poly_coords)
        if not overlap:
            # also test the inverse: if any point of the polygon lies inside the hex cell
            if self.is_special:
                # ATTENTION: special hex cells cannot be used as polygons in regular point in polygon algorithm!
                overlap = any_pt_in_cell(self.id, poly_nr)
            else:
                overlap = any_pt_in_poly(poly_coords, hex_coords)

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
    def neighbours(self) -> PolyIdSet:
        return set(h3.k_ring(self.id, k=1))


@functools.lru_cache(maxsize=int(1e6))
def get_hex(hex_id: int) -> Hex:
    # NOTE: do not evaluate constructor when value has been stored already!
    # return id2hex.get(hex_id) or id2hex.setdefault(hex_id, Hex.from_id(hex_id))
    return Hex.from_id(hex_id)


def check_child_coverage(
    parent_id: int, child_id: int, next_res_candidates: HexIdSet, neighbours: HexIdSet
):
    child_cell = get_hex(child_id)
    # check if the child has a vertex that lies outside the parent but within one of the selected neighbours
    # NOTE: this does not always return a unique point as expected (numerical errors)
    #   however this is not critical, since in the worst case only
    #   some superfluous mapping entries will be added
    pts = pts_not_in_cell(parent_id, child_cell.coords)
    for pt, neighbour in itertools.product(pts, neighbours):
        if lies_in_h3_cell(neighbour, pt[0], pt[1]):
            next_res_candidates.add(child_id)
            # ATTENTION: usually the polygons of the parent cell are assumed candidates for the child node,
            # initialise with the candidates of the neighbour instead!
            neighbour_cell = get_hex(neighbour)
            child_cell._poly_candidates = neighbour_cell.polys_in_cell
            break


def complete_coverage(mapping, next_res_candidates):
    """
    observation: some small region of children protrudes the parent cell and
      is not covered by the children of the neighbouring parent cell!
    but "complete coverage" required: for every point on earth there is a zone match (mapping to None)
    account for these protrusions as well: also add a mapping for these children if necessary
    all zones with a unique zone found
    -> "block view": regularly none of their children would be added
    """
    nr_candidates_before = len(next_res_candidates)
    print(f"{nr_candidates_before} candidates for next resolution level")
    print("completing coverage...")

    blocking_cells = {k for k, v in mapping.items() if v is not None}
    nr_cells2check = len(blocking_cells)
    for i, p1 in enumerate(blocking_cells):
        print(
            f"\r{i:,} / {nr_cells2check:,} cells processed\t"
            f"{len(next_res_candidates) - nr_candidates_before:,} candidates added",
            end="",
        )
        cell = get_hex(p1)
        # find the "non-blocking" neighbours: zones where only their children add coverage (=without a mapping stored)
        neighbours = {n for n in cell.neighbours if n not in mapping.keys()}
        if len(neighbours) == 0:
            continue

        # NOTE: their parents could be blocking as well (no mapping stored in this case)
        # -> additionally check if a mapping would have been created (more than one zones detected)
        neighbour_cells = iter(get_hex(n) for n in neighbours)
        neighbour_cells = filter(lambda n: len(n.zones_in_cell) > 1, neighbour_cells)
        neighbours = {n.id for n in neighbour_cells}

        if len(neighbours) == 0:
            continue

        for c1_i in cell.outer_children:
            check_child_coverage(p1, c1_i, next_res_candidates, neighbours)

    print("\n... done.")
    nr_candidates_after = len(next_res_candidates)
    nr_candidates_added = nr_candidates_after - nr_candidates_before
    if nr_candidates_before == 0:
        ratio = 0.0
    else:
        ratio = nr_candidates_added / nr_candidates_before
    print(f"{nr_candidates_after:,} candidates in total ({ratio :.2%} new)")


def export_mapping(file_name: str, obj: Dict, res: int):
    write_pickle(obj, f"{file_name}_res{res}.pickle")
    # uint key type can't be JSON serialised
    json_mapping = {str(k): v for k, v in obj.items()}
    write_json(json_mapping, f"{file_name}_res{res}.json")


def compile_main_coverage(candidates: HexIdSet, max_res_reached: bool):
    def report_progress():
        nr_candidates = len(candidates)
        processed = total_candidates - nr_candidates
        found = len(mapping)
        nr_new_candidates = len(next_res_candidates)
        print(
            f"\r{found :,} found\t{nr_candidates:,} remaining\t"
            f"{processed:,} processed\t{nr_new_candidates :,} new candidates",
            end="",
        )

    print("compiling mapping...")
    mapping: Dict[int, Optional[int]] = {}
    if max_res_reached:
        print(
            "highest possible resolution reached.\n"
            "SPECIAL CASE: storing mapping for every candidate to ensure full coverage"
        )

    next_res_candidates = set()
    total_candidates = len(candidates)
    while candidates:

        hex_id = candidates.pop()
        cell = get_hex(hex_id)
        zones = list(cell.zones_in_cell)
        nr_zones = len(zones)

        if nr_zones <= 1 or max_res_reached:
            # special case: only 0 or 1 zone = valid "shortcut"
            # special case: highest resolution -> always choose one!
            # TODO shortcuts
            # polys = list(cell.polys_in_cell)
            # mapping[hex_id] = polys

            polys = cell.polys_in_cell
            if len(polys) == 0:
                mapping[hex_id] = None
            most_common = most_common_zone_id(polys)
            mapping[hex_id] = most_common
            report_progress()
            # NOTE: do not search the child nodes!
            continue

        # recurse children
        children = cell.children
        next_res_candidates.update(children)
        report_progress()

    report_progress()
    print("\n... done.")

    if max_res_reached:
        assert (
            len(next_res_candidates) == 0
        ), "expected no more candidates for the next level"

    return mapping, next_res_candidates


def compile_h3_map(res: int, candidates: Set) -> Tuple[Set, Dict[int, Optional[int]]]:
    """

    operate on one hex resolution at a time
    also store results separately to divide the output data files
    """
    print(f"\nresolution: {res}")
    max_res_reached = res >= MAX_RES
    mapping, next_res_candidates = compile_main_coverage(candidates, max_res_reached)
    if not max_res_reached:
        # ATTENTION: at every level!
        # NOTE: not on the last resolution level (all candidates will be added -> full coverage)
        complete_coverage(mapping, next_res_candidates)

    export_mapping("mapping", mapping, res)
    write_json([int(c) for c in next_res_candidates], f"next_candidates_res{res}.json")
    return next_res_candidates, mapping


def compile_h3_maps() -> Dict[int, List[int]]:
    """
    property (assumption): the 7 children of a hex are almost fully contained in the parent
    cf. https://eng.uber.com/h3/
    TODO describe approach

    TODO types

    TODO use `uint64`
    TODO create all different binaries and upload them
    """
    # start with the lowest resolution 0 cells
    candidates: Set = set(h3.get_res0_indexes())
    global_mapping = {}
    for res in range(MAX_RES + 1):
        candidates, res_mapping = compile_h3_map(res, candidates)
        global_mapping.update(res_mapping)

        # free_up_memory(res)

    return global_mapping


# def free_up_memory(res):
#     prev = len(id2hex)
#     print(f"{prev :,} stored.")
#     # NOTE: remember to free up memory of the parent
#     # keep the parents, but remove all lower resolution hex cells
#     res_limit = res - 2
#     if res_limit < 0:
#         pass
#     print(f"removing all cells of resolution {res_limit}...")
#     cells2remove = [cell for cell in id2hex.values() if cell.res <= res_limit]
#     for cell in cells2remove:
#         id2hex.pop(cell.id)
#         del cell
#     print(f"... done.\nremoved {prev - len(id2hex):,} cells.")
#


def parse_data(
    input_path: Union[Path, str] = DEFAULT_INPUT_PATH,
    output_path: Union[Path, str] = DEFAULT_OUTPUT_PATH,
):
    # # parsing the data from the .json into RAM
    # TODO re-arra
    parse_polygons_from_json(input_path)
    # # update all the zone names and set the right ids to be written in the poly_zone_ids.bin
    # # sort data according to zone_id
    update_zone_names(output_path)

    # lng, lat = 35.295953, -89.662186
    # res = 0
    # hex_id = h3.geo_to_h3(lat, lng, res)
    # h = get_hex(hex_id)
    # x = h.is_poly_candidate(84)
    # polys = h.polys_in_cell
    # x = 1
    # TODO
    # IMPORTANT: import the newly compiled timezone_names pickle!
    # the compilation process needs the new version of the timezone names
    # with open(path2timezone_names, 'r') as f:
    #     timezone_names = json.loads(f.read())

    # compute shortcuts and write everything into the binaries
    # with open("log.txt", "w") as f:
    #     with contextlib.redirect_stdout(f):
    #         compile_h3_maps(output_path)

    global_mapping = compile_h3_maps()
    path2shortcut_file = Path(output_path) / SHORTCUT_FILE
    export_shortcuts_binary(global_mapping, path2shortcut_file)


if __name__ == "__main__":
    import argparse

    # TODO document
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
