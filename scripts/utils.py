import json
import pickle
from os.path import abspath
from typing import List, Tuple


def load_json(path):
    with open(path, "r") as fp:
        obj = json.load(fp)
    return obj


def load_pickle(path):
    with open(path, "rb") as fp:
        obj = pickle.load(fp)
    return obj


def write_pickle(obj, path):
    with open(path, "wb") as fp:
        pickle.dump(obj, fp)


def percent(numerator, denominator):
    return round((numerator / denominator) * 100, 2)


def extract_coords(coord_pairs) -> Tuple[List, List]:
    x_coords, y_coords = zip(*coord_pairs)
    x_coords = list(x_coords)
    y_coords = list(y_coords)
    if x_coords[0] == x_coords[-1] and y_coords[0] == y_coords[-1]:
        # IMPORTANT: polygon are represented without point repetition at the end
        # -> do not use the last coordinate (only if equal to the first)!
        x_coords.pop(-1)
        y_coords.pop(-1)
    assert len(x_coords) == len(y_coords)
    assert len(x_coords) >= 3
    return x_coords, y_coords


def write_json(obj, path):
    with open(abspath(path), "w") as json_file:
        json.dump(obj, json_file, indent=2)
