from ast import List
from collections.abc import Iterable
import fnmatch
import os
from pathlib import Path
import random
from re import Pattern
import re
import shutil
import subprocess
import timeit
from math import log10
from typing import Callable, Iterator, Tuple, Union

import numpy as np

from scripts.utils import validate_coord_array_shape
from tests.locations import REDUCED_TIMEZONE_MAPPING
from timezonefinder import utils
from timezonefinder.configs import (
    MAX_LAT_VAL,
    MAX_LAT_VAL_INT,
    MAX_LNG_VAL,
    MAX_LNG_VAL_INT,
    PACKAGE_DIR,
)
from timezonefinder.polygon_array import PolygonArray
from timezonefinder.utils_numba import convert2coords


#######################
# PATH CONSTANTS
#######################

PROJECT_ROOT = PACKAGE_DIR.parent
DIST_DIR = PROJECT_ROOT / "dist"


# Command constants
BUILD_SDIST_CMD = ["uv", "build", "-v", "--sdist"]
BUILD_WHEEL_CMD = ["uv", "build", "-v", "--wheel"]


# for reading coordinates
boundaries_dir = utils.get_boundaries_dir()
boundaries = PolygonArray(data_location=boundaries_dir, in_memory=True)

#######################
# UTILITY FUNCTIONS
#######################


def run_command(
    cmd: list, capture_output: bool = False, cwd: Path = PROJECT_ROOT
) -> subprocess.CompletedProcess:
    """Run a command and handle errors appropriately."""
    print(f"Running command: {' '.join(cmd)}")
    try:
        return subprocess.run(
            cmd,
            check=True,
            capture_output=capture_output,
            text=capture_output,
            cwd=str(cwd),
        )
    except subprocess.CalledProcessError as e:
        # Include the stdout/stderr in the error message if available
        error_msg = str(e)
        if capture_output and e.stdout:
            error_msg += f"\nStdout: {e.stdout}"
        if capture_output and e.stderr:
            error_msg += f"\nStderr: {e.stderr}"
        raise subprocess.CalledProcessError(
            e.returncode, e.cmd, e.output, e.stderr
        ) from None


def build_wheel(clean_dist: bool = True) -> Path:
    """Build wheel distribution and return its path."""
    # TODO reuse with DistributionFilesFixture (found in test_package_contents.py)
    if clean_dist and DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    run_command(BUILD_WHEEL_CMD, cwd=str(PROJECT_ROOT))

    wheels = list(DIST_DIR.glob("*.whl"))
    assert wheels, "No wheel file found in dist/"
    return wheels[0]


def build_sdist(clean_dist: bool = True) -> Path:
    """Build the distribution using the configured build command and return the path to the archive."""
    if clean_dist and DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    run_command(BUILD_SDIST_CMD, cwd=str(PROJECT_ROOT))

    dist_files = file_path_iterator(DIST_DIR, relative=False)
    sdist_files = list(filter_paths(dist_files, "*.tar.gz"))
    assert len(sdist_files) == 1, "Expected exactly one .tar.gz distribution file"
    sdist = sdist_files[0]
    print(f"Found distribution file: {sdist}")
    return sdist


def file_path_iterator(
    path: Path = PROJECT_ROOT, relative: bool = False
) -> Iterator[Path]:
    """
    Recursively iterate over all files in the given path.

    Args:
        path: The root path to start the iteration from (default: PROJECT_ROOT)

    Yields:
        Path objects for each file found
    """
    assert isinstance(path, Path), "path must be a Path object"
    # assert path.is_dir(), f"path must be a directory, got {path}"

    # recursively walk through the directory
    for root, _, files in os.walk(path):
        for file in files:
            # yield the full path to the file
            # using Path to ensure compatibility with different OS path formats
            file_path = Path(root) / file
            if relative:
                # yield relative to the project root
                file_path = file_path.relative_to(path)
            yield file_path


def matches_pattern(path: Path, pattern: Union[str, Pattern, None]) -> bool:
    r"""
    Check if a path matches a given pattern.

    Args:
        path: The path to check
        pattern: A glob pattern string or compiled regex pattern to match against
                 If None, always returns True (matches everything)
                 you can use:
                   - Simple filename patterns: '*.py' matches any Python file
                   - Directory patterns: 'tests/*.py' matches Python files in tests directory
                   - Path patterns: '*/data/*.json' matches JSON files in any data directory

    Returns:
        bool: True if the path matches the pattern, False otherwise

    Examples:
        # Check if file matches a glob pattern (filename only)
        is_python_file = matches_pattern(Path('script.py'), '*.py')  # True

        # Match against full path including directories
        in_tests_dir = matches_pattern(Path('tests/test_data.py'), 'tests/*.py')  # True

        # Match files in any data directory
        data_file = matches_pattern(Path('src/data/config.json'), '*/data/*.json')  # True

        # Check with regex pattern against full path
        import re
        is_test_file = matches_pattern(
            Path('tests/unit/test_utils.py'),
            re.compile(r'tests/.*\.py$')
        )  # True

        # Always matches when pattern is None
        matches_all = matches_pattern(Path('any_file.txt'), None)  # True
    """
    if pattern is None:
        return True
    assert isinstance(path, Path), "path must be a Path object"
    # Remove assert for is_file() to allow matching directories too
    assert isinstance(pattern, (str, re.Pattern)), (
        "pattern must be a string or a compiled regex pattern"
    )

    # Get the relative path as string for matching
    path_str = str(path)
    if isinstance(pattern, str):
        if pattern.endswith("/"):
            # pattern points to a directory
            # all content should be matched
            pattern = pattern + "*"

        # For string patterns, check against both the full path
        # Try matching against the full path first
        return fnmatch.fnmatch(path_str, pattern)
    elif isinstance(pattern, re.Pattern):
        # For regex patterns, always match against the full path
        return bool(pattern.search(path_str))


def filter_paths(
    paths: Iterator[Path],
    pattern: Union[str, Pattern, None] = None,
    include_matches: bool = True,
) -> Iterator[Path]:
    """
    Filter paths based on a pattern, either keeping matches or non-matches.

    Args:
        paths: An iterator of Path objects to filter (can be files or directories)
        pattern: A glob pattern string or compiled regex pattern to filter by
                 If None, behavior depends on include_matches
                 Patterns can include directory parts, e.g. 'tests/*.py'
        include_matches: If True, yield paths that match the pattern
                         If False, yield paths that don't match the pattern

    Yields:
        Path objects that match (or don't match) the pattern based on include_matches
    """
    for path in paths:
        is_match = matches_pattern(path, pattern)
        if (
            is_match == include_matches
        ):  # Yield when match status matches desired include status
            yield path


def any_filter_paths(
    paths: Iterator[Path], patterns: Iterable[str], include_matches: bool = True
) -> Iterator[Path]:
    """Filter paths by multiple patterns, yielding paths that match any of the patterns."""
    for path in paths:
        is_match = any(matches_pattern(path, pattern) for pattern in patterns)
        if is_match == include_matches:
            yield path


def ocean2land(test_locations):
    for lat, lng, description, expected in test_locations:
        if utils.is_ocean_timezone(expected):
            expected = None
        yield lat, lng, description, expected


def check_geometry(geometry_obj: List):
    coords = geometry_obj[0][0]
    assert len(coords) == 2, (
        "the polygon does not consist of two latitude longitude lists"
    )
    x_coords, y_coords = coords
    nr_x_coords = len(x_coords)
    nr_y_coords = len(y_coords)
    assert nr_x_coords > 2, "a polygon must consist of more than 2 coordinates"
    assert nr_x_coords == nr_y_coords, (
        "the amount of x and y coordinates (lng, lat) must be equal"
    )


def check_pairwise_geometry(geometry_obj: List):
    # list of all coord pairs of the first polygon
    cord_pairs = geometry_obj[0][0]
    assert len(cord_pairs) > 2, "a polygon must consist of more than 2 coordinates"
    first_coord_pair = cord_pairs[0]
    assert len(first_coord_pair) == 2, (
        "the polygon does not consist of coordinate pairs as expected."
    )


def is_valid_lng_int(x: int) -> bool:
    return -MAX_LNG_VAL_INT <= x <= MAX_LNG_VAL_INT


def is_valid_lat_int(y: int) -> bool:
    return -MAX_LAT_VAL_INT <= y <= MAX_LAT_VAL_INT


def is_valid_lng_int_vec(arr) -> bool:
    return np.all((-MAX_LNG_VAL_INT <= arr) & (arr <= MAX_LNG_VAL_INT))


def is_valid_lat_int_vec(arr) -> bool:
    return np.all((-MAX_LAT_VAL_INT <= arr) & (arr <= MAX_LAT_VAL_INT))


def validate_polygon_coordinates(coords: np.ndarray):
    """Helper function to validate polygon coordinates format and values."""
    validate_coord_array_shape(coords)

    # test whether the coordinates are within valid ranges
    x_coords, y_coords = coords
    # apply to every coordinate

    assert is_valid_lng_int_vec(x_coords)
    assert is_valid_lat_int_vec(y_coords)


def timefunc(function: Callable, *args):
    def wrap():
        function(*args)

    timer = timeit.Timer(wrap)
    nr_runs = 1
    t_in_sec = timer.timeit(nr_runs)
    return t_in_sec


def proto_test_case(data, fct):
    for input, expected_output in data:
        # print(input, expected_output, fct(input))
        actual_output = fct(input)
        if actual_output != expected_output:
            print(
                "input: {} expected: {} got: {}".format(
                    input, expected_output, actual_output
                )
            )
        assert actual_output == expected_output


def time_preprocess(time):
    valid_digits = 4
    zero_digits = abs(min(0, int(log10(time))))
    digits_to_print = zero_digits + valid_digits
    return str(round(time, digits_to_print)) + "s"


def get_rnd_query_pt() -> Tuple[float, float]:
    lng = random.uniform(-MAX_LNG_VAL, MAX_LNG_VAL)
    lat = random.uniform(-MAX_LAT_VAL, MAX_LAT_VAL)
    return lng, lat


def get_rnd_poly_int() -> np.ndarray:
    max_poly_id = len(boundaries) - 1
    poly_id = random.randint(0, max_poly_id)
    poly = boundaries.coords_of(poly_id)
    return poly


def get_rnd_poly() -> np.ndarray:
    poly = get_rnd_poly_int()
    coords = convert2coords(poly)
    return np.array(coords)


def convert_inside_polygon_input(lng: float, lat: float):
    x, y = utils.coord2int(lng), utils.coord2int(lat)
    return x, y


def get_pip_test_input() -> Tuple[int, int, np.ndarray]:
    # one test polygon + one query point
    lng, lat = get_rnd_query_pt()
    x, y = convert_inside_polygon_input(lng, lat)
    poly_int = get_rnd_poly_int()
    return x, y, poly_int


def convert_to_reduced_timezone(timezone: str) -> str:
    """
    Convert a timezone to its reduced version using the provided mapping.

    NOTE: unused, but kept for future reference

    Args:
        timezone: The original timezone string.
        mapping: A dictionary mapping original timezones to their reduced versions.

    Returns:
        The reduced timezone if found in the mapping, otherwise the original timezone.
    """
    return REDUCED_TIMEZONE_MAPPING.get(timezone, timezone)


def single_location_test(func, lat, lng, description, expected_orig):
    result = func(lng=lng, lat=lat)
    func_name = func.__name__
    # expected = convert_to_reduced_timezone(expected_orig)
    assert result == expected_orig, (
        f"{func_name}({lng}, {lat}) [{description}] should return {expected_orig}, got {result}"
    )
