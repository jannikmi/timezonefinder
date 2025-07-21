import json
import pickle
from contextlib import redirect_stdout
from os.path import abspath
from time import time
from typing import Dict, List, Callable

import numpy as np

from scripts.configs import (
    DATA_REPORT_FILE,
    DEBUG,
    DTYPE_FORMAT_F_NUMPY,
    DTYPE_FORMAT_SIGNED_I_NUMPY,
)
from scripts.utils_numba import is_valid_lat_vec, is_valid_lng_vec
from timezonefinder import configs
from timezonefinder.utils_numba import coord2int


def load_json(path):
    with open(path) as fp:
        return json.load(fp)


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


# DECORATORS


def time_execution(func: Callable) -> Callable:
    """decorator showing the execution time of a function"""

    def wrap_func(*args, **kwargs):
        t1 = time()
        result = func(*args, **kwargs)
        t2 = time()
        print(f"\nfunction {func.__name__}(...) executed in {(t2 - t1):.1f}s")
        return result

    return wrap_func


# decorator to reroute the output of a function to a file
def redirect_output_to_file(file_path: str) -> Callable:
    """Decorator to redirect the output of a function to a file."""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # NOTE: append to the file, do not overwrite it
            with open(file_path, "a") as f:
                with redirect_stdout(f):
                    return func(*args, **kwargs)

        return wrapper

    return decorator


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


def rst_title(title: str, level: int = 0) -> str:
    """Return a title in restructured text format"""
    separators = ["=", "-", "~", "^", "`"]
    level = min(level, len(separators) - 1)
    sep = separators[level]
    return f"\n\n{title}\n{sep * len(title)}\n"


def print_rst_table(headers: List[str], rows: List[List[str]]):
    """
    Print a table in restructured text (.rst) format using list-table directive

    :param headers: List of column headers
    :param rows: List of rows, each row is a list of values
    """
    # Calculate appropriate column widths based on content
    col_count = len(headers)
    default_width = 100 // col_count
    widths = [default_width] * col_count

    # Start the list-table directive
    print("\n.. list-table::")
    print("   :header-rows: 1")
    print(f"   :widths: {' '.join(str(w) for w in widths)}")
    print("")

    # Print headers
    print("   * - " + "\n     - ".join(str(h) for h in headers))

    # Print rows
    for row in rows:
        # Convert all cells to strings
        str_cells = [str(cell) for cell in row]
        print("   * - " + "\n     - ".join(str_cells))

    print("")


def print_frequencies(counts: List[int], amount_of_shortcuts: int):
    max_val = max(*counts)
    frequencies = [counts.count(i) for i in range(max_val + 1)]
    nr_empty_shortcuts = frequencies[0]

    # Summary information
    summary_headers = ["Metric", "Value"]
    summary_rows = [
        ["Highest amount in one shortcut", str(max_val)],
        [
            "Empty shortcuts percentage",
            f"{percent(nr_empty_shortcuts, amount_of_shortcuts)}%",
        ],
    ]

    print(rst_title("Summary Statistics", level=2))
    print_rst_table(summary_headers, summary_rows)

    # Frequency table
    freq_headers = ["Amount", "Frequency"]
    freq_rows = [[i, amount] for i, amount in enumerate(frequencies)]

    print(rst_title("Frequencies of Entry Amounts", level=2))
    print_rst_table(freq_headers, freq_rows)

    # Accumulated frequency table
    acc = accumulated_frequency(frequencies)
    acc_inverse = [round(100 - x, 2) for x in acc]

    acc_headers = ["Amount", "Accumulated %", "Missing %"]
    acc_rows = [[i, acc[i], acc_inverse[i]] for i in range(len(acc))]
    print(rst_title("Accumulated Frequencies", level=2))
    print_rst_table(acc_headers, acc_rows)


@redirect_output_to_file(DATA_REPORT_FILE)
def print_shortcut_statistics(mapping: Dict[int, List[int]], poly_zone_ids: List[int]):
    print(rst_title("Shortcut Mapping Statistics", level=1))

    amount_of_shortcuts = len(mapping)
    nr_of_entries_in_shortcut = [len(v) for v in mapping.values()]

    print("\nAmount of timezone polygons per shortcut:\n")
    print_frequencies(nr_of_entries_in_shortcut, amount_of_shortcuts)

    amount_of_different_zones = []
    for polygon_ids in mapping.values():
        # TODO count and evaluate the appearance of the different zones
        zone_ids = [poly_zone_ids[i] for i in polygon_ids]
        distinct_zones = set(zone_ids)
        amount_of_distinct_zones = len(distinct_zones)
        amount_of_different_zones.append(amount_of_distinct_zones)

    print("\nAmount of different timezones per shortcut:\n")
    print_frequencies(amount_of_different_zones, amount_of_shortcuts)


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
    # TODO further check the ordering of the polygons
