"""utility functions"""

import io
import mmap
from pathlib import Path
import re
from typing import Callable, Tuple, Union

import numpy as np

from timezonefinder.configs import (
    DEFAULT_DATA_DIR,
    OCEAN_TIMEZONE_PREFIX,
)
from timezonefinder import utils_numba, utils_clang


# make numba functions available via utils
using_numba = utils_numba.using_numba
clang_extension_loaded = utils_clang.clang_extension_loaded
is_valid_lat = utils_numba.is_valid_lat
is_valid_lng = utils_numba.is_valid_lng
coord2int = utils_numba.coord2int
int2coord = utils_numba.int2coord
convert2coords = utils_numba.convert2coords
convert2coord_pairs = utils_numba.convert2coord_pairs
get_last_change_idx = utils_numba.get_last_change_idx


inside_polygon: Callable[[int, int, np.ndarray], bool]
# at import time fix which "point-in-polygon" implementation will be used
if clang_extension_loaded and not using_numba:
    # use the C implementation only if Numba is not present
    inside_polygon = utils_clang.pt_in_poly_clang
else:
    # use the (JIT compiled) python function if Numba is present or the C extension cannot be loaded
    inside_polygon = utils_numba.pt_in_poly_python


def validate_lat(lat):
    if not is_valid_lat(lat):
        raise ValueError(f"The given latitude {lat} is out of bounds")


def validate_lng(lng: float) -> None:
    if not is_valid_lng(lng):
        raise ValueError(f"The given longitude {lng} is out of bounds")


def validate_coordinates(lng: float, lat: float) -> Tuple[float, float]:
    lng, lat = float(lng), float(lat)
    validate_lng(lng)
    validate_lat(lat)
    return lng, lat


def load_buffer(
    file: Path, in_memory: bool = True
) -> Tuple[Union[io.BufferedReader, None], Union[mmap.mmap, bytes]]:
    """Load a binary file into memory or as a memory-mapped file."""
    buf: Union[mmap.mmap, bytes]
    if in_memory:
        # Read entire file into memory
        with open(file, "rb") as f:
            buf = f.read()
    else:
        # Use memory-mapped file for on-demand reading
        file_obj = open(file, "rb")
        # Create memory map
        buf = mmap.mmap(file_obj.fileno(), 0, access=mmap.ACCESS_READ)
    return None, buf


def _safe_close(obj):
    try:
        obj.close()
    except Exception:
        pass


def close_ressources(file: io.BufferedReader, buf: mmap.mmap) -> None:
    """Close the file and buffer resources."""
    _safe_close(file)
    _safe_close(buf)


def is_ocean_timezone(timezone_name: str) -> bool:
    if re.match(OCEAN_TIMEZONE_PREFIX, timezone_name) is None:
        return False
    return True


def get_boundaries_dir(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the boundaries directory."""
    return data_dir / "boundaries"


def get_holes_dir(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the holes directory."""
    return data_dir / "holes"


def get_hole_registry_path(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the path to the hole registry file."""
    return data_dir / "hole_registry.json"
