from collections.abc import Iterable
from contextlib import contextmanager
import fnmatch
import json
import os
from pathlib import Path
import random
from re import Pattern
import re
import shutil
import subprocess
import sys
import warnings
from math import asin, degrees, log10
from typing import Any, Iterator

import numpy as np
import pytest

from scripts.configs import DEBUG, read_data_version
from scripts.utils import validate_coord_array_shape
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
# this repository's root distribution; the data one is named by
# scripts.configs.DATA_DISTRIBUTION_NAME, which also owns the path to it
ROOT_DISTRIBUTION_NAME = "timezonefinder"
# where GitHub looks for workflows and for local `uses: ./...` actions - the
# layout is GitHub's, not ours, so the tests that read those files share one
# declaration of it rather than each spelling out the same directories
GITHUB_DIR = PROJECT_ROOT / ".github"
WORKFLOW_DIR = GITHUB_DIR / "workflows"
ACTION_DIR = GITHUB_DIR / "actions"
BENCHMARK_FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "benchmarks"
BENCHMARK_FIXTURES_METADATA_PATH = BENCHMARK_FIXTURES_DIR / "metadata.json"

# benchmark fixture names: shared as both the ``.npy`` file stem under
# BENCHMARK_FIXTURES_DIR and the matching key in metadata.json's "counts".
# Reused by the generator (scripts/generate_benchmark_fixtures.py) and the
# loader below so the two can't silently drift apart.
RANDOM_POINTS_FIXTURE = "random_points"
ON_LAND_POINTS_FIXTURE = "on_land_points"
UNIQUE_SHORTCUT_POINTS_FIXTURE = "unique_shortcut_points"
AMBIGUOUS_SHORTCUT_POINTS_FIXTURE = "ambiguous_shortcut_points"
PIP_INPUTS_FIXTURE = "pip_inputs"
PIP_STRATA_FIXTURE = "pip_strata"

# The polygon-size strata every ``pip_inputs`` fixture is split into. Order
# matters: the index is the integer code stored in ``pip_strata.npy``, and the
# names are written into metadata.json for ``load_pip_strata`` to decode with.
# Lives here rather than in the generator for the same reason FIXTURE_VERSION
# does, and so that ``group_pip_inputs_by_stratum`` can state which strata a
# fixture must contain rather than only inspecting the ones it found.
PIP_STRATA = ("small", "medium", "large")

# Bump whenever the *generation logic* changes in a way that makes previously
# committed fixtures mean something different: the point sampler, the ``N_*``
# counts, or the order in which the generators consume the shared seeded
# ``rng``. The loader below refuses fixtures carrying a different version, so
# a checkout with new generator code and stale ``.npy`` files fails loudly
# instead of silently benchmarking a workload nobody described.
# NOTE: this deliberately lives here rather than in the generator - the
# generator imports from this module, so the loader could not validate a
# constant owned by the generator without an import cycle.
FIXTURE_VERSION = 2


# Command constants.
#
# ``--python sys.executable`` pins the build to the interpreter running the tests.
# Without it uv picks the newest interpreter it can find, which need not be the one
# under test: a 3.12 ``.venv`` on a machine that also has 3.14 installed yields a
# ``cp314`` wheel, and pip in the 3.12 venv that tests/test_integration.py installs
# it into rejects it as "not a supported wheel on this platform". CI never saw this
# because a tox env offers a single interpreter, so the two agreed by accident.
# Keep the pin on the sdist build too: it costs nothing and stops the two artefacts
# in ``dist/`` from being built by different interpreters.
#
# ``-o dist/`` is explicit rather than left to the default: inside a uv workspace,
# where a build target is selected with ``--package``, the output directory is not
# obviously the one a caller then globs.
BUILD_CMD = ["uv", "build", "-v", "--python", sys.executable, "-o", "dist/"]
BUILD_SDIST_CMD = [*BUILD_CMD, "--sdist"]
BUILD_WHEEL_CMD = [*BUILD_CMD, "--wheel"]


# for reading coordinates
boundaries_dir = utils.get_boundaries_dir()
boundaries = PolygonArray(data_location=boundaries_dir, in_memory=True)

#######################
# UTILITY FUNCTIONS
#######################


@contextmanager
def strict_numpy_errors() -> Iterator[None]:
    """Turn numpy overflow/invalid-value warnings into errors, then restore.

    Both `np.seterr` and the warning filters are process-global, so code that
    sets them without restoring them decides the error state of everything that
    runs afterwards - which turns an unrelated later failure into one that
    depends on collection order.
    """
    original_state = np.seterr(all="warn")
    with warnings.catch_warnings():
        warnings.filterwarnings("error")
        try:
            yield
        finally:
            np.seterr(**original_state)


@pytest.fixture
def strict_numpy_warnings() -> Iterator[None]:
    """`strict_numpy_errors` scoped to a single test.

    Per-test (not module scope, unlike the old
    `scripts/check_speed_inside_polygon.py`) so it cannot leak into other
    modules collected in the same session. Shared by `tests/` and
    `benchmarks/` through the conftest of each.
    """
    with strict_numpy_errors():
        yield


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
        # ``CalledProcessError.__str__`` reports the exit code and nothing else, and
        # with capture_output the child's streams never reached the terminal either.
        # Echo them before re-raising, otherwise a packaging failure under
        # ``make testint`` says only that the build exited non-zero.
        if capture_output:
            for stream_name, stream in (("Stdout", e.stdout), ("Stderr", e.stderr)):
                if stream:
                    print(f"{stream_name} of failed command:\n{stream}")
        raise


def build_wheel(
    clean_dist: bool = True,
    package: str | None = None,
    source_root: Path = PROJECT_ROOT,
) -> Path:
    """Build a wheel distribution and return its path.

    ``package`` names a workspace member to build instead of the root distribution
    (``timezonefinder-data``), and ``source_root`` is where that member lives. Both
    wheels land in the same ``dist/``, so the glob names the distribution rather than
    taking whatever wheel is there - and a caller building both must pass
    ``clean_dist=False`` for the second, or it deletes the first.

    ``<source_root>/build`` is removed first. setuptools copies package data into
    ``build/lib`` and never prunes it, so a file that has since been renamed stays
    there and is zipped into every later wheel - which is how a 63 MB
    ``coordinates.fbs`` kept shipping next to the ``coordinates.bin`` that replaced it,
    doubling the data wheel. CI never sees this because it builds from a fresh
    checkout; that is exactly why the local build has to match it, or these tests
    inspect an artefact nobody will ever publish.
    """
    # TODO reuse with DistributionFilesFixture (found in test_package_contents.py)
    if clean_dist and DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    shutil.rmtree(source_root / "build", ignore_errors=True)

    cmd = (
        BUILD_WHEEL_CMD if package is None else [*BUILD_WHEEL_CMD, "--package", package]
    )
    run_command(cmd, cwd=PROJECT_ROOT)

    # a distribution name is normalised to underscores in the wheel filename
    dist_name = (package or ROOT_DISTRIBUTION_NAME).replace("-", "_")
    wheels = list(DIST_DIR.glob(f"{dist_name}-*.whl"))
    assert wheels, f"No {dist_name} wheel found in dist/"
    assert len(wheels) == 1, f"Expected exactly one {dist_name} wheel, got {wheels}"
    return wheels[0]


def build_sdist(clean_dist: bool = True) -> Path:
    """Build the distribution using the configured build command and return the path to the archive."""
    if clean_dist and DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    run_command(BUILD_SDIST_CMD, cwd=PROJECT_ROOT)

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


def matches_pattern(path: Path, pattern: str | Pattern | None) -> bool:
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
    pattern: str | Pattern | None = None,
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


def check_geometry(geometry_obj: list):
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


def check_pairwise_geometry(geometry_obj: list):
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


def is_valid_lng_int_vec(arr: np.ndarray) -> bool:
    return bool(np.all((-MAX_LNG_VAL_INT <= arr) & (arr <= MAX_LNG_VAL_INT)))


def is_valid_lat_int_vec(arr: np.ndarray) -> bool:
    return bool(np.all((-MAX_LAT_VAL_INT <= arr) & (arr <= MAX_LAT_VAL_INT)))


def validate_polygon_coordinates(coords: np.ndarray):
    """Helper function to validate polygon coordinates format and values."""
    validate_coord_array_shape(coords)

    # test whether the coordinates are within valid ranges
    x_coords, y_coords = coords
    # apply to every coordinate

    assert is_valid_lng_int_vec(x_coords)
    assert is_valid_lat_int_vec(y_coords)


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


def get_rnd_query_pt(rng: random.Random | None = None) -> tuple[float, float]:
    """Draw a random (lng, lat) point uniform in the lat/lng *rectangle*.

    Pass a seeded ``random.Random`` for reproducible sequences (fixture
    generation, benchmarks). Leaving ``rng`` as ``None`` keeps drawing from
    the global, unseeded ``random`` module, which is what the regular test
    suite (including hypothesis-adjacent code) relies on.

    Uniform in latitude, therefore **not** uniform per unit of surface area:
    it oversamples the poles roughly 2.5x. That is a feature for correctness
    and fuzz testing - polar coordinates are edge cases, and hitting more of
    them per draw is exactly what those tests want. It is wrong for benchmark
    inputs; see :func:`get_rnd_query_pt_area_weighted`.
    """
    _rng = rng if rng is not None else random
    lng = _rng.uniform(-MAX_LNG_VAL, MAX_LNG_VAL)
    lat = _rng.uniform(-MAX_LAT_VAL, MAX_LAT_VAL)
    return lng, lat


def get_rnd_query_pt_area_weighted(
    rng: random.Random | None = None,
) -> tuple[float, float]:
    """Draw a random (lng, lat) point uniform per unit of *surface area*.

    ``lat = degrees(asin(U(-1, 1)))`` gives each equal-area patch of the globe
    an equal chance, where :func:`get_rnd_query_pt`'s ``lat ~ U(-90, 90)``
    crowds draws toward the poles: 33.3% of points from the naive sampler land
    above |60| latitude, against 13.4% for this one.

    That distortion is not cosmetic for benchmarking. Under the naive sampler
    30.5% of query points fall in an ambiguous H3 shortcut cell (the expensive
    full point-in-polygon path); the area-correct share is 25.5%, matching the
    shortcut index's own ``unique surface fraction`` of 0.745 in
    ``docs/data_report.rst``. A benchmark's job is to represent real query
    load, so a pole-biased mix misstates what a unique-shortcut optimisation
    is worth.

    Used by ``scripts/generate_benchmark_fixtures.py`` for every committed
    benchmark fixture. Swapping the two samplers silently invalidates all of
    them, which is what ``FIXTURE_VERSION`` and the ``point_sampler`` entry in
    ``metadata.json`` exist to catch.

    See :func:`get_rnd_query_pt` for the ``rng`` seeding convention. Draws from
    the same ``random.Random`` stream, so the generator stays reproducible from
    a single seed.
    """
    _rng = rng if rng is not None else random
    lng = _rng.uniform(-MAX_LNG_VAL, MAX_LNG_VAL)
    lat = degrees(asin(_rng.uniform(-1.0, 1.0)))
    return lng, lat


def get_rnd_poly_int(rng: random.Random | None = None) -> np.ndarray:
    """Pick the coordinates of a uniformly random polygon.

    See :func:`get_rnd_query_pt` for the ``rng`` seeding convention.
    """
    _rng = rng if rng is not None else random
    max_poly_id = len(boundaries) - 1
    poly_id = _rng.randint(0, max_poly_id)
    poly = boundaries.coords_of(poly_id)
    return poly


def get_rnd_poly() -> np.ndarray:
    poly = get_rnd_poly_int()
    coords = convert2coords(poly)
    return np.array(coords)


def convert_inside_polygon_input(lng: float, lat: float):
    x, y = utils.coord2int(lng), utils.coord2int(lat)
    return x, y


def get_pip_test_input(
    rng: random.Random | None = None,
) -> tuple[int, int, np.ndarray]:
    """One test polygon + one query point.

    See :func:`get_rnd_query_pt` for the ``rng`` seeding convention.
    """
    lng, lat = get_rnd_query_pt(rng)
    x, y = convert_inside_polygon_input(lng, lat)
    poly_int = get_rnd_poly_int(rng)
    return x, y, poly_int


#######################
# BENCHMARK FIXTURE LOADING
#######################


class BenchmarkFixtureError(RuntimeError):
    """Raised when committed benchmark fixtures are missing or stale."""


def _load_benchmark_fixture_metadata() -> dict:
    if not BENCHMARK_FIXTURES_METADATA_PATH.exists():
        raise BenchmarkFixtureError(
            "Benchmark fixtures are missing "
            f"(expected metadata at {BENCHMARK_FIXTURES_METADATA_PATH}). "
            "Generate them with `make benchmark-fixtures`."
        )
    with open(BENCHMARK_FIXTURES_METADATA_PATH) as f:
        metadata = json.load(f)
    fixture_debug = metadata.get("debug")
    if fixture_debug != DEBUG:
        raise BenchmarkFixtureError(
            f"Benchmark fixtures were generated with scripts.configs.DEBUG={fixture_debug}, "
            f"but the current scripts.configs.DEBUG={DEBUG}. "
            "Regenerate the fixtures with `make benchmark-fixtures`."
        )
    current_data_version = read_data_version()
    fixture_data_version = metadata.get("data_version")
    if fixture_data_version != current_data_version:
        raise BenchmarkFixtureError(
            f"Benchmark fixtures were generated against timezone data version "
            f"{fixture_data_version!r}, but the current DATA_VERSION is "
            f"{current_data_version!r} (on_land/shortcut classification and pip_inputs "
            "polygon ids are tied to the boundary data). "
            "Regenerate the fixtures with `make benchmark-fixtures`."
        )
    # NOTE: the two checks below must stay *after* the DEBUG and data_version
    # checks above - tests/test_benchmark_fixtures.py asserts on those two
    # error messages using deliberately minimal metadata dicts, which would
    # trip an earlier check instead.
    fixture_version = metadata.get("fixture_version")
    if fixture_version != FIXTURE_VERSION:
        raise BenchmarkFixtureError(
            f"Benchmark fixtures were generated by fixture logic version "
            f"{fixture_version!r}, but this checkout expects "
            f"{FIXTURE_VERSION!r}. The generator's sampling, counts or "
            "ordering changed, so the committed fixtures no longer describe "
            "the workload the code assumes. "
            "Regenerate the fixtures with `make benchmark-fixtures`."
        )
    fixture_sampler = metadata.get("point_sampler")
    expected_sampler = get_rnd_query_pt_area_weighted.__name__
    if fixture_sampler != expected_sampler:
        raise BenchmarkFixtureError(
            f"Benchmark fixtures were generated with the {fixture_sampler!r} "
            f"point sampler, but this checkout generates them with "
            f"{expected_sampler!r}. The two draw different distributions over "
            "the globe, so their benchmark timings are not comparable. "
            "Regenerate the fixtures with `make benchmark-fixtures`."
        )
    return metadata


def _load_benchmark_fixture_array(name: str) -> np.ndarray:
    path = BENCHMARK_FIXTURES_DIR / f"{name}.npy"
    if not path.exists():
        raise BenchmarkFixtureError(
            f"Benchmark fixture '{name}' not found at {path}. "
            "Generate it with `make benchmark-fixtures`."
        )
    _load_benchmark_fixture_metadata()  # validates fixture/runtime consistency
    return np.load(path)


def load_benchmark_points(name: str) -> list[tuple[float, float]]:
    """Load a committed (lng, lat) point fixture by name.

    ``name`` is one of :data:`RANDOM_POINTS_FIXTURE`, :data:`ON_LAND_POINTS_FIXTURE`,
    :data:`UNIQUE_SHORTCUT_POINTS_FIXTURE`, :data:`AMBIGUOUS_SHORTCUT_POINTS_FIXTURE`.
    """
    arr = _load_benchmark_fixture_array(name)
    return [(float(lng), float(lat)) for lng, lat in arr]


def benchmark_fixture_provenance() -> dict[str, Any]:
    """Which fixture generation and boundary data the benchmark inputs came from.

    Recorded into the benchmark JSON by ``benchmarks/conftest.py`` so the
    rendered ``docs/benchmark_results_*.rst`` state the workload their numbers
    describe. Without that stamp, regenerated fixtures or updated boundary data
    leave the committed reports silently describing a workload that no longer
    exists - the numbers stay plausible, so nothing flags them as stale.

    Read through :func:`_load_benchmark_fixture_metadata` rather than off the
    file directly, so the values are the *validated* ones: a fixture set out of
    sync with this checkout raises here instead of being stamped into a report.
    """
    metadata = _load_benchmark_fixture_metadata()
    return {
        "fixture_version": metadata["fixture_version"],
        "data_version": metadata["data_version"],
    }


def load_pip_inputs() -> list[tuple[int, int, int]]:
    """Load the committed point-in-polygon benchmark inputs.

    Returns ``(x, y, polygon_id)`` triples of already ``coord2int``-scaled
    query coordinates. Use :func:`load_pip_strata` for the matching
    small/medium/large size classification of ``polygon_id``.
    """
    arr = _load_benchmark_fixture_array(PIP_INPUTS_FIXTURE)
    poly_ids = arr[:, 2]
    max_poly_id = len(boundaries) - 1
    out_of_range = poly_ids[(poly_ids < 0) | (poly_ids > max_poly_id)]
    if len(out_of_range) > 0:
        # belt-and-suspenders on top of the data_version check in
        # _load_benchmark_fixture_metadata(): catch a mismatch between the
        # fixture's polygon ids and the currently loaded boundary data
        # directly, in case the recorded data_version is somehow stale
        # without having been bumped (e.g. hand-edited data).
        raise BenchmarkFixtureError(
            f"Benchmark fixture {PIP_INPUTS_FIXTURE!r} references polygon id "
            f"{int(out_of_range[0])}, outside the valid range (0-{max_poly_id}) "
            "for the currently loaded boundary data. The fixtures were likely "
            "generated against a different timezone data version. "
            "Regenerate them with `make benchmark-fixtures`."
        )
    return [(int(x), int(y), int(poly_id)) for x, y, poly_id in arr]


def load_pip_strata() -> list[str]:
    """Load the polygon-size stratum ("small"/"medium"/"large") for each
    entry returned by :func:`load_pip_inputs`, in the same order."""
    arr = _load_benchmark_fixture_array(PIP_STRATA_FIXTURE)
    metadata = _load_benchmark_fixture_metadata()
    stratum_names = metadata["pip_strata"]
    return [stratum_names[code] for code in arr]


def group_pip_inputs_by_stratum(
    inputs: list[tuple[int, int, int]],
    strata: list[str],
    batch_size: int,
) -> dict[str, list[tuple[int, int, np.ndarray]]]:
    """Pair PIP inputs with their labels and take ``batch_size`` of each stratum.

    Returns ``(x, y, polygon_coords)`` triples keyed by :data:`PIP_STRATA`, with
    the polygon ids of :func:`load_pip_inputs` already resolved against the
    loaded boundary data.

    Every way the two fixture files can disagree - different lengths, an
    unexpected label, a stratum that is short or missing altogether - raises
    here, naming the fixture and the fix. Left to the caller, each of them
    instead produces a full-looking result that mislabels its points, or a bare
    ``KeyError`` from the benchmark that consumes it.
    """
    if len(inputs) != len(strata):
        raise ValueError(
            f"benchmark fixtures {PIP_INPUTS_FIXTURE!r} ({len(inputs)} points) and "
            f"{PIP_STRATA_FIXTURE!r} ({len(strata)} labels) disagree in length; "
            "they must be generated together. Regenerate the fixtures via "
            "`make benchmark-fixtures`."
        )
    unknown = sorted(set(strata) - set(PIP_STRATA))
    if unknown:
        raise ValueError(
            f"benchmark fixture {PIP_STRATA_FIXTURE!r} labels points with unknown "
            f"strata {unknown}; expected only {list(PIP_STRATA)}. Regenerate the "
            "fixtures via `make benchmark-fixtures`."
        )
    # seeded with every expected stratum rather than with whatever the fixture
    # turns out to contain, so a stratum missing from it entirely reaches the
    # count check below instead of never becoming a key
    grouped: dict[str, list[tuple[int, int, np.ndarray]]] = {
        stratum: [] for stratum in PIP_STRATA
    }
    for (x, y, poly_id), stratum in zip(inputs, strata, strict=True):
        bucket = grouped[stratum]
        if len(bucket) < batch_size:
            bucket.append((x, y, boundaries.coords_of(poly_id)))
    for stratum, bucket in grouped.items():
        if len(bucket) < batch_size:
            raise ValueError(
                f"benchmark fixture {PIP_INPUTS_FIXTURE!r} has only {len(bucket)} "
                f"'{stratum}' entries, but the benchmark suite needs at least "
                f"{batch_size} per stratum. Regenerate the fixtures with a larger "
                "count via `make benchmark-fixtures`."
            )
    return grouped


def single_location_test(func, lat, lng, description, expected_orig):
    result = func(lng=lng, lat=lat)
    func_name = func.__name__
    assert result == expected_orig, (
        f"{func_name}({lng}, {lat}) [{description}] should return {expected_orig}, got {result}"
    )
