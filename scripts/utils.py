import json
import pickle
from os.path import abspath
from time import time
from typing import Dict, List

import numpy as np

from scripts.configs import DEBUG, DTYPE_FORMAT_F_NUMPY, DTYPE_FORMAT_SIGNED_I_NUMPY
from scripts.utils_numba import is_valid_lat_vec, is_valid_lng_vec
from timezonefinder import configs
from timezonefinder.utils_numba import coord2int


def load_json(path):
    print("loading json from ", path)
    with open(path) as fp:
        obj = json.load(fp)
    return obj


def load_pickle(path):
    print("loading pickle from ", path)
    with open(path, "rb") as fp:
        obj = pickle.load(fp)
    return obj


def write_pickle(obj, path):
    print("writing pickle to ", path)
    with open(path, "wb") as fp:
        pickle.dump(obj, fp)


def write_json(obj, path):
    print("writing json to ", path)
    with open(abspath(path), "w") as json_file:
        json.dump(obj, json_file, indent=2)
        # write a newline at the end of the file
        json_file.write("\n")


def time_execution(func):
    """decorator showing the execution time of a function"""

    def wrap_func(*args, **kwargs):
        t1 = time()
        result = func(*args, **kwargs)
        t2 = time()
        print(f"\nfunction {func.__name__}(...) executed in {(t2 - t1):.1f}s")
        return result

    return wrap_func


def percent(numerator, denominator):
    return round((numerator / denominator) * 100, 2)


def validate_coord_array_shape(coords: np.ndarray):
    assert isinstance(coords, np.ndarray)
    assert coords.ndim == 2, "coords must be a 2D array"
    assert coords.shape[0] == 2, "coords must have two columns (lng, lat)"
    # all polygons must have at least 3 coordinates
    assert coords.shape[1] >= 3, (
        f"a polygon must consist of at least 3 coordinates, but has {coords.shape[1]} coordinates"
    )


# NOTE: no JIT compilation. slows down the execution
def convert2ints(coordinates: configs.CoordLists) -> configs.IntLists:
    # return a tuple of coordinate lists
    return [
        [coord2int(x) for x in coordinates[0]],
        [coord2int(y) for y in coordinates[1]],
    ]


def convert_polygon(coords, validate: bool = True) -> np.ndarray:
    coord_array = np.array(coords, dtype=DTYPE_FORMAT_F_NUMPY)
    validate_coord_array_shape(coord_array)
    x_coords, y_coords = coord_array
    if validate:
        assert len(x_coords) >= 3, "Polygon must have at least 3 coordinates"
        assert is_valid_lng_vec(x_coords), "encountered invalid longitude values."
        assert is_valid_lat_vec(y_coords), "encountered invalid latitude values."
    x_ints, y_ints = convert2ints(coords)
    # NOTE: jit compiled functions expect fortran ordered arrays. signatures must match
    poly = np.array((x_ints, y_ints), dtype=DTYPE_FORMAT_SIGNED_I_NUMPY, order="F")
    return poly


def to_numpy_polygon_repr(coord_pairs, flipped: bool = False) -> np.ndarray:
    if flipped:
        # support the (lat, lng) format used by h3
        y_coords, x_coords = zip(*coord_pairs)
    else:
        x_coords, y_coords = zip(*coord_pairs)
    # Remove last coordinate if it repeats the first
    if y_coords[0] == y_coords[-1] and x_coords[0] == x_coords[-1]:
        x_coords = x_coords[:-1]
        y_coords = y_coords[:-1]
    # NOTE: skip expensive validation
    return convert_polygon((x_coords, y_coords), validate=DEBUG)


def accumulated_frequency(int_list):
    out = []
    total = sum(int_list)
    acc = 0
    for e in int_list:
        acc += e
        out.append(percent(acc, total))

    return out


def print_shortcut_statistics(mapping: Dict[int, List[int]], poly_zone_ids: List[int]):
    print("\n\nshortcut statistics:")
    amount_of_shortcuts = len(mapping)
    nr_of_entries_in_shortcut = [len(v) for v in mapping.values()]
    print("\namount of timezone polygons per shortcut")
    print_frequencies(nr_of_entries_in_shortcut, amount_of_shortcuts)

    amount_of_different_zones = []
    for polygon_ids in mapping.values():
        # TODO count and evaluate the appearance of the different zones
        zone_ids = [poly_zone_ids[i] for i in polygon_ids]
        distinct_zones = set(zone_ids)
        amount_of_distinct_zones = len(distinct_zones)
        amount_of_different_zones.append(amount_of_distinct_zones)

    print("amount of different timezones per shortcut")
    print_frequencies(amount_of_different_zones, amount_of_shortcuts)


def print_frequencies(counts: List[int], amount_of_shortcuts: int):
    max_val = max(*counts)
    print("highest amount in one shortcut is", max_val)
    frequencies = [counts.count(i) for i in range(max_val + 1)]
    nr_empty_shortcuts = frequencies[0]
    print(
        percent(nr_empty_shortcuts, amount_of_shortcuts),
        "% of all shortcuts are empty",
    )
    # show the proper amount of shortcuts with 0 zones (=nr of empty shortcuts)
    # frequencies.append(nr_empty_shortcuts)
    print("frequencies of entry amounts:")
    for i, amount in enumerate(frequencies):
        print(f"{i}: {amount}")
    print("relative accumulated frequencies [%]:")
    acc = accumulated_frequency(frequencies)
    print(acc)
    print("missing relative accumulated frequencies [%]:")
    acc_inverse = [round(100 - x, 2) for x in acc]
    print(acc_inverse)
    print("--------------------------------\n")


def has_coherent_sequences(lst: List[int]) -> bool:
    """
    :return: True if equal entries in the list are not separated by entries of other values
    """
    if len(lst) <= 1:
        return True
    encountered = set()
    # at least 2 entries
    lst_iter = iter(lst)
    prev = next(lst_iter)
    for e in lst:
        if e in encountered:
            # the entry appeared earlier already
            return False
        if e != prev:
            encountered.add(prev)
            prev = e

    return True


def check_shortcut_sorting(polygon_ids: np.ndarray, all_zone_ids: np.ndarray):
    # the polygons in the shortcuts are sorted by their zone id (and the size of their polygons)
    if len(polygon_ids) == 1:
        # single polygon in the shortcut, no need to check
        return
    zone_ids = all_zone_ids[polygon_ids]
    assert has_coherent_sequences(zone_ids), (
        f"shortcut polygon ids {polygon_ids} do not have coherent sequences of zone ids: {zone_ids}"
    )
    # TODO check that the size of the polygons of that zones are descending
