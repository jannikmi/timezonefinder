import json
import pickle
import struct
from os.path import abspath, join
from time import time
from typing import Dict, List

import numpy as np

from timezonefinder import configs
from timezonefinder.utils import coord2int


def load_json(path):
    print("loading json from ", path)
    with open(path, "r") as fp:
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


def to_numpy_polygon(coord_pairs, flipped: bool = False) -> np.ndarray:
    if flipped:
        y_coords1, x_coords1 = zip(*coord_pairs)
    else:
        x_coords1, y_coords1 = zip(*coord_pairs)
    x_coords = list(map(coord2int, x_coords1))
    y_coords = list(map(coord2int, y_coords1))
    if x_coords[0] == x_coords[-1] and y_coords[0] == y_coords[-1]:
        # IMPORTANT: polygon are represented without point repetition at the end
        # -> do not use the last coordinate (only if equal to the first)!
        x_coords.pop(-1)
        y_coords.pop(-1)
    assert len(x_coords) == len(y_coords)
    assert len(x_coords) >= 3
    poly = np.array((x_coords, y_coords), dtype=configs.DTYPE_FORMAT_SIGNED_I_NUMPY)
    return poly


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


def export_mapping(file_name: str, obj: Dict, res: int):
    write_pickle(obj, f"{file_name}_res{res}.pickle")
    # uint key type can't be JSON serialised
    json_mapping = {str(k): v for k, v in obj.items()}
    write_json(json_mapping, f"{file_name}_res{res}.json")


def write_value(output_file, value, data_format, lower_value_limit, upper_value_limit):
    assert (
        value > lower_value_limit
    ), f"trying to write value {value} subceeding lower limit {lower_value_limit} (data type {data_format})"
    assert (
        value < upper_value_limit
    ), f"trying to write value {value} exceeding upper limit {upper_value_limit} (data type {data_format})"
    output_file.write(struct.pack(data_format, value))


def write_coordinate_value(output_file, coord_as_int):
    # NOTE: float coordinates are assumed to have been converted into int32 already
    write_value(
        output_file,
        coord_as_int,
        data_format=configs.DTYPE_FORMAT_SIGNED_I,
        lower_value_limit=configs.THRES_DTYPE_SIGNED_I_LOWER,
        upper_value_limit=configs.THRES_DTYPE_SIGNED_I_UPPER,
    )


def write_regular(output_file, data, *args, **kwargs):
    for value in data:
        write_value(output_file, value, *args, **kwargs)


def write_coordinates(output_file, data, *args, **kwargs):
    for x_coords, y_coords in data:
        for x in x_coords:
            write_coordinate_value(output_file, x)

        for y in y_coords:
            write_coordinate_value(output_file, y)


def write_boundaries(output_file, boundaries: List, *args, **kwargs):
    for boundary in boundaries:
        write_coordinate_value(output_file, boundary.xmax)
        write_coordinate_value(output_file, boundary.xmin)
        write_coordinate_value(output_file, boundary.ymax)
        write_coordinate_value(output_file, boundary.ymin)


def write_binary(
    output_path,
    bin_file_name,
    data,
    data_format=configs.DTYPE_FORMAT_H,
    lower_value_limit=-1,
    upper_value_limit=configs.THRES_DTYPE_H,
    writing_fct=write_regular,
):
    path = abspath(join(output_path, bin_file_name + configs.BINARY_FILE_ENDING))
    print(f"writing {path}")
    with open(path, "wb") as output_file:
        writing_fct(
            output_file, data, data_format, lower_value_limit, upper_value_limit
        )
        file_length = output_file.tell()
    return file_length


def write_coordinate_data(output_path, bin_file_name, data):
    return write_binary(output_path, bin_file_name, data, writing_fct=write_coordinates)


def write_boundary_data(output_path, bin_file_name, data):
    return write_binary(output_path, bin_file_name, data, writing_fct=write_boundaries)
