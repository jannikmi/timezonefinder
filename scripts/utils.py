import json
from pathlib import Path
from os.path import abspath
from time import time
from typing import Callable

import numpy as np

from scripts.configs import DEBUG, DTYPE_FORMAT_F_NUMPY, DTYPE_FORMAT_SIGNED_I_NUMPY
from scripts.utils_numba import is_valid_lat_vec, is_valid_lng_vec
from timezonefinder import configs
from timezonefinder.utils_numba import coord2int


def write_json(obj, path: Path):
    print(
        f"writing json to {repr(path)}",
    )
    # Emit exactly what the pretty-format-json pre-commit hook would impose, so a
    # re-parse is byte-comparable against the committed file instead of showing a
    # spurious diff of reordered keys.
    #
    # The keys must be stringified *before* sorting: json already coerces them on
    # write, but sort_keys would otherwise order int keys numerically (16, 26, 1165)
    # while the hook re-reads the file - where keys are strings - and orders them
    # lexicographically ("1165", "16", "26").
    if isinstance(obj, dict):
        obj = {str(key): value for key, value in obj.items()}
    with open(abspath(path), "w") as json_file:
        json.dump(obj, json_file, indent=2, sort_keys=True)
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
    # NOTE: jit compiled functions expect C ordered arrays (CoordType). signatures must match
    poly = np.array((x_ints, y_ints), dtype=DTYPE_FORMAT_SIGNED_I_NUMPY, order="C")
    return poly


def canonical_ring_key(ring: np.ndarray) -> bytes:
    """Byte key identifying a closed ring regardless of where it starts and how it winds.

    Two rings tracing the same closed path produce the same key even when stored with a
    different first vertex or in the opposite direction, and different keys whenever any
    vertex differs. Used to recognise a hole that is a verbatim copy of some zone's
    boundary polygon, which is how the upstream builder emits enclaves.

    The comparison is exact - it orders the integer coordinates themselves, never a
    derived floating point quantity such as the signed area, so there is no tolerance to
    tune and a near-degenerate ring cannot be misjudged. Winding is normalised by
    generating the key for both directions and keeping the smaller, which is cheaper to
    trust than a shoelace sum (whose intermediate products overflow int64 for a polygon
    with many vertices at full coordinate scale).

    :param ring: Ring coordinates with shape (2, N), without a repeated closing vertex
    :return: A key that compares equal exactly for rings describing the same path
    """
    x, y = ring[0], ring[1]
    best: bytes | None = None
    for xs, ys in ((x, y), (x[::-1], y[::-1])):
        # rotate the ring to begin at its lexicographically smallest vertex
        on_xmin = np.flatnonzero(xs == xs.min())
        starts = on_xmin[ys[on_xmin] == ys[on_xmin].min()]
        # normally a single vertex; a ring that visits its extreme point more than once
        # has several equally valid rotations, so all of them are tried
        for start in starts:
            candidate = np.concatenate(
                (np.roll(xs, -start), np.roll(ys, -start))
            ).tobytes()
            if best is None or candidate < best:
                best = candidate
    if best is None:
        raise ValueError("cannot compute a canonical key for an empty ring")
    return best


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
