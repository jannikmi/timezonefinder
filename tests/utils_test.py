import json
from collections import Counter
from typing import Callable

import h3.api.numpy_int as h3
import numpy as np
import pytest

from scripts import reporting
from scripts.configs import ZONE_ID_DTYPE, BinaryData, ShortcutIndexStats
from scripts.utils import convert2ints, convert_polygon, write_json
from tests.auxiliaries import (
    convert_inside_polygon_input,
    get_rnd_poly,
    get_rnd_poly_int,
    get_rnd_query_pt,
    strict_numpy_errors,
)
from tests.locations import OUT_OF_RANGE_COORDINATES
from timezonefinder import utils_clang, utils_numba, utils
from timezonefinder.configs import DEFAULT_DATA_DIR

POINT_IN_POLYGON_TESTCASES = [
    # (polygon, list of test points, expected results)
    (
        # square
        ([0.5, 0.5, -0.5, -0.5, 0.5], [0.0, 0.5, 0.5, -0.5, -0.5]),
        [
            # (x,y),
            # inside
            (0.0, 0.000),
            # outside
            (-1.0, 1.0),
            (0.0, 1.0),
            (1.0, 1.0),
            (-1.0, 0.0),
            (1.0, 0.0),
            (-1.0, -1.0),
            (0.0, -1.0),
            (1.0, -1.0),
            # on the line test cases
            # inclusion is not defined if point lies on the line
            # (0.0, -0.5),
            # (0, 0.5),
            # (-0.5, 0),
            # (0.5, 0),
        ],
        [True, False, False, False, False, False, False, False, False],
    ),
    (
        # more complex polygon with sloped edges
        ([1, 5, 7, 8, 7, 6, 1, 1, 5, 1], [1, 4, 1, 3, 3, 6, 6, 2, 5, 1]),
        [
            # (x,y),
            # inside (14 cases)
            (7, 1.0001),
            (7, 1.1),
            (7, 1.5),
            (7, 2.9),
            (7, 2.999),
            (1.1, 3),
            (3.1, 3),
            (6, 3),
            (2, 4),
            (3, 4),
            (4.5, 4),
            (6, 4),
            (6.5, 4),
            (2, 5.5),
            # outside (21 cases)
            (0.0, 0.0),
            (5.0, 0.0),
            (9.0, 0.0),
            (7, 0.9),
            (7, 0.9999),
            (0.0, 1.0),
            (5.0, 1.0),
            (8.0, 1.0),
            (0.9, 3),
            (2.5, 3),
            (4, 3),
            (5, 3),
            (8.1, 3),
            (7, 3.00001),
            (7, 3.1),
            (0, 4),
            (7, 4),
            (0, 6),
            (7, 6),
            (0, 7),
            (7, 7),
            # on the line test cases
            # inclusion is not defined if point lies on the line
        ],
        [True] * 14 + [False] * 21,
    ),
    (
        # test for overflow, use maximum valid domain (of the coordinates)
        # ATTENTION: only values \in [-180, 180] allowed!
        # delta_y_max * delta_x_max = 180x10^7 * 360x10^7
        [[-180.0, 180.0, -180.0], [-90.0, 90.0, 90.0]],
        [
            # choose query points so (x-x_i) and (y-y_i) get big!
            # inside
            (
                -179.9999999,
                -89.9999998,
            ),
            (-179.9999, -89.9998),
            (-179.9999, 89.9999),
            # TODO uncertain case:
            # (179.9998, 89.9999),
        ],
        [True] * 3,
    ),
]


def test_dtype_conversion():
    # coordinates (float) to int
    lng, lat = get_rnd_query_pt()
    x_int = utils.coord2int(lng)
    y_int = utils.coord2int(lat)
    lng2 = utils.int2coord(x_int)
    lat2 = utils.int2coord(y_int)
    np.testing.assert_almost_equal(lng, lng2)
    np.testing.assert_almost_equal(lat, lat2)


def test_convert2coord_pairs():
    x_ints, y_ints = get_rnd_poly_int()
    polygon_int = np.array((x_ints, y_ints))
    pairs = utils.convert2coord_pairs(polygon_int)
    assert isinstance(pairs, list)
    for pair in pairs:
        assert isinstance(pair, tuple)
        assert len(pair) == 2
        lng, lat = pair
        assert isinstance(lng, float)
        assert isinstance(lat, float)
        utils.validate_coordinates(lng, lat)

    coords_converted = np.array(pairs).T
    longitudes = [utils.int2coord(x) for x in x_ints]
    latitudes = [utils.int2coord(y) for y in y_ints]
    coords_true = np.array((longitudes, latitudes))
    np.testing.assert_almost_equal(coords_converted, coords_true)


def test_convert2coords():
    x_ints, y_ints = get_rnd_poly_int()
    polygon_int = np.array((x_ints, y_ints))
    coord_lists = utils.convert2coords(polygon_int)
    assert isinstance(coord_lists, list)
    assert len(coord_lists) == 2
    x_coords, y_coords = coord_lists
    assert len(x_coords) == len(y_coords)
    for lng, lat in zip(x_coords, y_coords):
        assert isinstance(lng, float)
        assert isinstance(lat, float)
        utils.validate_coordinates(lng, lat)

    coords_converted = np.array(coord_lists)
    longitudes = [utils.int2coord(x) for x in x_ints]
    latitudes = [utils.int2coord(y) for y in y_ints]
    coords_true = np.array((longitudes, latitudes))
    np.testing.assert_almost_equal(coords_converted, coords_true)


def test_convert2ints():
    coords_true = get_rnd_poly()
    poly_int = convert2ints(coords_true)
    assert isinstance(poly_int, list)
    assert len(poly_int) == 2
    x_coords, y_coords = poly_int
    assert len(x_coords) == len(y_coords)

    ints_converted = np.array(poly_int)
    longitudes, latitudes = coords_true
    x_ints = [utils.coord2int(x) for x in longitudes]
    y_ints = [utils.coord2int(y) for y in latitudes]
    ints_true = np.array((x_ints, y_ints))
    np.testing.assert_almost_equal(ints_converted, ints_true)


def test_clang_extension_loaded():
    # testing the Clang version of the Point in Polygon algorithm requires the C extension to be loaded
    assert utils.clang_extension_loaded, "the clang extension not loaded, "


# `strict_numpy_errors` (tests/auxiliaries.py) is what keeps the overflow tests below
# and in tests/main_test.py from deciding the numpy error state of every test collected
# after them. Both properties it promises are asserted here, because a version that
# silently stopped restoring the state would only surface as an unrelated failure in
# whichever module pytest happened to collect next.
def test_strict_numpy_errors_promotes_overflow_to_an_exception():
    with strict_numpy_errors(), pytest.raises(RuntimeWarning):
        np.int16(32767) + np.int16(1)


def test_strict_numpy_errors_restores_the_global_state_after_raising():
    # a state distinct from the one the context manager installs, so this cannot pass
    # by coincidence when a previous test has already leaked `all="warn"`
    original = np.seterr(over="ignore", under="ignore")
    try:
        with pytest.raises(RuntimeWarning), strict_numpy_errors():
            np.int16(32767) + np.int16(1)
        assert np.geterr()["over"] == "ignore"
        assert np.geterr()["under"] == "ignore"
    finally:
        np.seterr(**original)


# NOTE: these call the kernels directly, on hand-built arrays. That the two agree on
# the *real* data, reached through the real coordinate accessors, is covered by
# tests/test_acceleration_paths.py - which also explains why only one of them is ever
# the bound `utils.inside_polygon` locally.
@pytest.mark.parametrize(
    "inside_poly_func",
    [
        utils_numba.pt_in_poly_python,
        utils_clang.pt_in_poly_clang,
    ],
)
@pytest.mark.parametrize(
    "test_case",
    POINT_IN_POLYGON_TESTCASES,
)
@pytest.mark.usefixtures("strict_numpy_warnings")
def test_inside_polygon(inside_poly_func: Callable, test_case: tuple):
    # print(f"\ntesting function {inside_poly_func.__name__}")

    # the fixture promotes numpy overflow warnings to errors for this test
    nr_mistakes = 0
    template = "{:12s} | {:10s} | {:10s} | {:2s}"
    print()
    print(template.format("#test point", "EXPECTED", "COMPUTED", "  "))
    # print("=" * 50)
    coords, query_points, expected_results = test_case
    coords_int = convert_polygon(coords)
    for i, ((lng, lat), expected_result) in enumerate(
        zip(query_points, expected_results)
    ):
        utils.validate_coordinates(lng, lat)  # check the range of lng, lat
        x, y = convert_inside_polygon_input(lng, lat)
        actual_result = inside_poly_func(x, y, coords_int)
        if actual_result == expected_result:
            ok = "OK"
        else:
            print((lng, lat), "-->", (x, y))
            print(coords)
            ok = "XX"
            nr_mistakes += 1
        print(template.format(str(i), str(expected_result), str(actual_result), ok))

    print(f"{nr_mistakes} mistakes made")
    assert nr_mistakes == 0


@pytest.mark.unit
def test_pt_in_poly_clang_rejects_strided_rows():
    """The C extension must refuse a strided row instead of quietly copying it.

    ``ascontiguousarray`` used to sit here and made a strided producer look correct
    while allocating a full polygon copy on every point in polygon test - a regression
    no result-based test could observe. The loud failure is the point.
    """
    coords_int = convert_polygon(POINT_IN_POLYGON_TESTCASES[0][0])
    strided = np.asfortranarray(coords_int)
    assert not strided[0].flags["C_CONTIGUOUS"]

    with pytest.raises(ValueError, match="not C-contiguous"):
        utils_clang.pt_in_poly_clang(0, 0, strided)


@pytest.mark.unit
def test_convert_polygon_is_c_contiguous():
    """The build-time producer must match the kernels' C-ordered signature.

    A mismatch here surfaces only as a Numba ``TypeError`` deep inside ``make parse``.
    """
    coords_int = convert_polygon(POINT_IN_POLYGON_TESTCASES[0][0])
    assert coords_int.flags["C_CONTIGUOUS"]
    assert coords_int[0].flags["C_CONTIGUOUS"]
    assert coords_int[1].flags["C_CONTIGUOUS"]


@pytest.mark.parametrize("lng, lat", OUT_OF_RANGE_COORDINATES)
def test_validate_coordinates_rejects_out_of_range(lng, lat):
    with pytest.raises(ValueError):
        utils.validate_coordinates(lng=lng, lat=lat)


@pytest.mark.parametrize(
    "lng, lat",
    [
        # NaN in longitude
        (float("nan"), 0.0),
        (float("nan"), 45.0),
        (float("nan"), 90.0),
        (float("nan"), -90.0),
        # NaN in latitude
        (0.0, float("nan")),
        (45.0, float("nan")),
        (180.0, float("nan")),
        (-180.0, float("nan")),
        # NaN in both
        (float("nan"), float("nan")),
        # Positive infinity in longitude
        (float("inf"), 0.0),
        (float("inf"), 45.0),
        (float("inf"), -45.0),
        # Negative infinity in longitude
        (float("-inf"), 0.0),
        (float("-inf"), -90.0),
        # Positive infinity in latitude
        (0.0, float("inf")),
        (45.0, float("inf")),
        (-180.0, float("inf")),
        # Negative infinity in latitude
        (0.0, float("-inf")),
        (90.0, float("-inf")),
        (180.0, float("-inf")),
        # Infinity in both
        (float("inf"), float("inf")),
        (float("-inf"), float("-inf")),
        (float("inf"), float("-inf")),
        # Edge case: values that convert to infinity
        (1e308 * 10, 0.0),  # Too large, overflows to infinity
        (0.0, 1e308 * 10),  # Too large, overflows to infinity
    ],
)
def test_validate_coordinates_rejects_nan_and_inf(lng, lat):
    """Test that validate_coordinates rejects NaN and infinity values."""
    with pytest.raises(ValueError):
        utils.validate_coordinates(lng=lng, lat=lat)


@pytest.mark.parametrize(
    "lng, lat",
    [
        # Valid edge cases (boundaries)
        (0.0, 0.0),
        (180.0, 90.0),
        (-180.0, -90.0),
        (180.0, -90.0),
        (-180.0, 90.0),
        # Valid regular cases
        (45.5, 22.5),
        (-45.5, -22.5),
        (165.123456, 75.987654),
        (-165.123456, -75.987654),
        # Very small numbers (near-zero, but finite)
        (1e-10, 1e-10),
        (-1e-10, -1e-10),
        (1e-20, -1e-20),
    ],
)
def test_validate_coordinates_accepts_finite_values(lng, lat):
    """Test that validate_coordinates accepts all valid finite coordinates."""
    result = utils.validate_coordinates(lng=lng, lat=lat)
    assert result == (lng, lat)
    assert isinstance(result[0], float)
    assert isinstance(result[1], float)


@pytest.mark.parametrize(
    "entry_list, expected",
    [
        ([], 0),
        ([1], 0),
        ([2], 0),
        ([1, 1], 0),
        ([1, 2], 1),
        ([1, 3], 1),
        ([1, 3, 3], 1),
        ([1, 3, 3, 0], 3),
        ([1, 3, 3, 0, 0, 0, 0], 3),
    ],
)
def test_get_last_change_idx(entry_list, expected):
    array = np.array(entry_list, dtype=ZONE_ID_DTYPE)
    assert utils.get_last_change_idx(array) == expected


@pytest.mark.unit
def test_write_json_output_is_pre_commit_clean(tmp_path):
    """Generated JSON must already be what pretty-format-json would produce.

    Otherwise a re-parse shows a spurious diff of reordered keys against the
    committed file, which looks like converter drift. The subtle part is that the
    registry keys are ints in memory: sorting those directly gives numeric order,
    while the hook re-reads the file - where keys are strings - and sorts
    lexicographically.
    """
    path = tmp_path / "registry.json"
    write_json({1165: [1, 2], 16: [3, 4], 26: [5, 6], 1184: [7, 8]}, path)

    written = path.read_text()
    reparsed = json.loads(written)
    normalized = json.dumps(reparsed, indent=2, sort_keys=True) + "\n"

    assert written == normalized, "output is not what pretty-format-json would emit"
    assert list(reparsed) == ["1165", "1184", "16", "26"], "keys not sorted as strings"


@pytest.mark.unit
@pytest.mark.parametrize(
    "cells, expected",
    [
        (["a", "b"], "   * - a\n     - b"),
        (["", ""], "   * -\n     -"),  # spacer row: no trailing whitespace
        (["only"], "   * - only"),
    ],
)
def test_format_table_row_has_no_trailing_whitespace(cells, expected):
    """Spacer rows used to emit '   * - ' with a dangling space.

    The trailing-whitespace hook stripped it, so a freshly generated
    docs/data_report.rst never matched the committed one until the hook had run.
    """
    assert reporting._format_table_row(cells) == expected


@pytest.mark.unit
def test_print_frequencies_labels_the_zero_bucket(capsys):
    """A zero bucket can mean something other than "zero of them".

    In the shortcut distribution it counts H3 cells needing no
    point-in-polygon test at all, which the bare "0" reported as cells holding
    no polygons - impossible for data whose ocean zones cover the globe.
    """
    reporting.print_frequencies([0, 0, 2, 3], "Polygons to test", "none (unique zone)")

    table = capsys.readouterr().out
    assert "- none (unique zone)" in table
    assert "\n   * - 0\n" not in table
    # only the zero row is relabelled
    assert "- 2" in table and "- 3" in table


@pytest.mark.unit
def test_print_frequencies_keeps_the_bare_zero_without_a_label(capsys):
    reporting.print_frequencies([0, 2], "Polygons to test")

    assert "   * - 0\n" in capsys.readouterr().out


@pytest.mark.unit
@pytest.mark.parametrize("resolution", [0, 3, 5])
def test_shortcut_index_stats_takes_the_cell_count_from_h3(monkeypatch, resolution):
    """``possible_cells`` is the denominator of every coverage figure.

    It used to come from a ladder of literals covering resolutions 0-4 only,
    with everything else falling through to the number of cells actually
    stored - which makes ``coverage_ratio`` exactly 1.0 and reports complete H3
    coverage for a resolution nobody tabulated. Resolution 5 is in this
    parametrization because it is the first one past the end of that ladder:
    the two tabulated resolutions agree with h3 and so cannot show the
    difference.
    """
    monkeypatch.setattr(reporting, "SHORTCUT_H3_RES", resolution)
    mapping = {0: 1, 1: np.array([0, 1]), 2: np.array([], dtype=int)}

    stats = reporting.calculate_shortcut_index_stats(mapping, [7, 7])

    assert stats["h3_resolution"] == resolution
    assert stats["possible_cells"] == h3.get_num_cells(resolution)
    # the fallback this replaces reported stored == possible, hence full coverage
    assert stats["stored_cells"] == len(mapping)
    assert stats["coverage_ratio"] < 1.0


@pytest.mark.unit
def test_shortcut_index_stats_classifies_each_entry_kind():
    """One direct zone id, one polygon list, one empty list."""
    mapping = {0: 1, 1: np.array([0, 1]), 2: np.array([], dtype=int)}

    stats = reporting.calculate_shortcut_index_stats(mapping, [7, 8])

    assert stats["zone_entries"] == 1
    assert stats["polygon_entries"] == 1
    assert stats["empty_entries"] == 1
    assert stats["polygon_id_count"] == 2
    # the polygon entry spans two distinct zones; the direct one spans a single
    # zone, and the empty one none
    assert stats["zones_per_shortcut"] == [1, 2, 0]
    assert stats["polygons_per_shortcut"] == [0, 2, 0]


@pytest.mark.unit
def test_polygon_distribution_table_pairs_each_count_with_an_example(capsys):
    """The polygon count labels a row and keys the example lookup.

    It used to be formatted into the label and parsed back out of it, so the
    two could only agree by the label's wording staying parseable.
    """
    # zone 0 has one polygon, zones 1 and 2 have two each
    polygons_per_timezone = Counter({0: 1, 1: 2, 2: 2})

    reporting.print_polygon_distribution_table(
        polygons_per_timezone, ["Europe/Berlin", "Etc/GMT", "Etc/GMT+1"]
    )

    table = capsys.readouterr().out

    # whole rows, so label, count, percentage and example are pinned together
    # rather than merely all being present somewhere in the table
    assert "   * - 1 polygon\n     - 1\n     - 33.33%\n     - Europe/Berlin\n" in table
    assert "   * - 2 polygons\n     - 2\n     - 66.67%\n     - Etc/GMT\n" in table
    # zone 1 is the first zone with two polygons, so zone 2 never exemplifies it
    assert "Etc/GMT+1" not in table


# The two TypedDicts below describe dicts assembled by hand in scripts/reporting.py.
# The pre-commit mypy hook excludes scripts/, so nothing in CI compares the
# declaration against the literal - a key added to one and not the other would
# only surface as a KeyError part-way through writing a report.


@pytest.mark.unit
def test_shortcut_index_stats_matches_its_typed_dict():
    stats = reporting.calculate_shortcut_index_stats({0: 1}, [7])

    assert set(stats) == set(ShortcutIndexStats.__annotations__)


@pytest.mark.integration
def test_load_binary_data_matches_its_typed_dict():
    data = reporting.load_binary_data(DEFAULT_DATA_DIR)

    assert set(data) == set(BinaryData.__annotations__)


if __name__ == "__main__":
    pytest.main([__file__])
