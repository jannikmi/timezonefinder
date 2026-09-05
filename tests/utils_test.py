import json
import math
from collections import Counter
from pathlib import Path
from typing import Callable

import h3.api.numpy_int as h3
import numpy as np
import pytest

from scripts import reporting
from scripts.configs import (
    DATA_REPORT_FILE,
    SOURCE_DATA_DIR,
    BinaryData,
    ShortcutIndexStats,
)
from scripts.utils import (
    convert2ints,
    convert_polygon,
    source_coord2int,
    write_json,
)
from tests.auxiliaries import (
    convert_inside_polygon_input,
    get_rnd_poly,
    get_rnd_poly_int,
    get_rnd_query_pt,
    strict_numpy_errors,
)
from tests.locations import OUT_OF_RANGE_COORDINATES
from timezonefinder import utils_clang, utils_numba, utils
from timezonefinder.configs import (
    DEFAULT_DATA_DIR,
    MAX_LAT_VAL,
    MAX_LNG_VAL,
    MIN_LAT_VAL,
    MIN_LNG_VAL,
)

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


def test_the_conversion_refuses_a_seventh_decimal():
    """The guard that lets the packaged data be stored on the source's own grid.

    Rounding a coordinate onto that grid is lossless only while the source stays on it,
    and timezone-boundary-builder has published at most six decimals in every release so
    far. An upstream that started publishing a seventh would have real information
    rounded away, silently, and every downstream check would still pass because the file
    would be internally consistent. So the converter stops instead.
    """
    assert source_coord2int(13.358) == 133580000
    assert source_coord2int(-13.358) == -133580000
    assert source_coord2int(0.1) == 1000000

    with pytest.raises(ValueError, match="more than six decimal places"):
        source_coord2int(13.3580001)

    # ... and a value finer than a storage step, which is the case a check applied
    # *after* the rounding cannot see: this one rounds onto the grid and would pass
    with pytest.raises(ValueError, match="more than six decimal places"):
        source_coord2int(13.35800004)


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


def test_convert2ints_from_source_rounds_onto_the_source_grid():
    """The default conversion is for transient geometry; stored rings ask for the grid.

    Both exist because both are needed: an H3 cell's boundary is computed here and has
    as many decimals as a float carries, while a *stored* boundary coordinate has to sit
    on the grid the packed payload counts residuals in. Converting the first the second
    way raises - which is how this got the wrong way round once, and what
    `scripts/hex_utils.py` would hit again.
    """
    coords = ([13.358, -0.5], [52.5186, 0.25])
    assert convert2ints(coords, from_source=True) == [
        [133580000, -5000000],
        [525186000, 2500000],
    ]
    from timezonefinder.configs import SOURCE_COORD_STEP

    for axis in convert2ints(coords, from_source=True):
        assert all(v % SOURCE_COORD_STEP == 0 for v in axis)


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
    "name, minimum, maximum, coordinates_at",
    [
        (
            "latitude",
            MIN_LAT_VAL,
            MAX_LAT_VAL,
            lambda value: {"lng": 0.0, "lat": value},
        ),
        (
            "longitude",
            MIN_LNG_VAL,
            MAX_LNG_VAL,
            lambda value: {"lng": value, "lat": 0.0},
        ),
    ],
)
def test_the_rejection_message_states_the_bounds_the_validator_enforces(
    name, minimum, maximum, coordinates_at
):
    """The bound that is checked and the bound that is reported are one statement.

    They used to be two: the validator held its own literals and the message was built
    from a second pair passed at the call site, compared against nothing. Either could
    have moved without the other, and the resulting error would have named a range the
    code does not enforce.
    """
    for accepted in (minimum, maximum):
        utils.validate_coordinates(**coordinates_at(accepted))

    for rejected in (
        math.nextafter(minimum, -math.inf),
        math.nextafter(maximum, math.inf),
    ):
        with pytest.raises(
            ValueError,
            match=rf"Invalid {name} .*: must be in range \[{minimum}, {maximum}\]",
        ):
            utils.validate_coordinates(**coordinates_at(rejected))


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
def test_render_frequencies_labels_the_zero_bucket():
    """A zero bucket can mean something other than "zero of them".

    In the shortcut distribution it counts H3 cells needing no
    point-in-polygon test at all, which the bare "0" reported as cells holding
    no polygons - impossible for data whose ocean zones cover the globe.
    """
    table = reporting.render_frequencies(
        [0, 0, 2, 3], "Polygons to test", "none (unique zone)"
    )

    assert "- none (unique zone)" in table
    assert "\n   * - 0\n" not in table
    # only the zero row is relabelled
    assert "- 2" in table and "- 3" in table


@pytest.mark.unit
def test_render_frequencies_keeps_the_bare_zero_without_a_label():
    assert "   * - 0\n" in reporting.render_frequencies([0, 2], "Polygons to test")


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
def test_shortcut_efficiency_metrics_read_the_counts_they_are_given():
    """The four ratios, each against a denominator only this seam chooses.

    They used to be computed inline beside the counts, so a wrong denominator
    was invisible: every figure was derived from locals in the same scope, and
    the report states them as percentages nobody recomputes.
    """
    counts = reporting.ShortcutEntryCounts(
        total_entries=4,
        zone_entries=1,
        polygon_entries=2,
        empty_entries=1,
        polygon_id_count=6,
        polygons_per_shortcut=[0, 2, 4, 0],
        zones_per_shortcut=[1, 2, 3, 0],
    )

    metrics = reporting.shortcut_efficiency_metrics(counts, possible_cells=8)

    # one of four cells answers outright, of eight cells the grid could hold
    assert metrics["unique_entry_fraction"] == 0.25
    assert metrics["unique_surface_fraction"] == 0.125
    # the two cells spanning at most one zone, over every cell - including the
    # empty one, which spans none
    assert metrics["zone_distribution_efficiency"] == 0.5
    # six polygon ids over the two entries listing polygons, never over all four
    assert metrics["avg_polygons_per_entry"] == 3.0


@pytest.mark.unit
def test_shortcut_efficiency_metrics_answer_zero_on_an_empty_index():
    counts = reporting.ShortcutEntryCounts(0, 0, 0, 0, 0, [], [])

    metrics = reporting.shortcut_efficiency_metrics(counts, possible_cells=0)

    assert set(metrics.values()) == {0.0}


@pytest.mark.unit
def test_shortcut_storage_metrics_price_each_entry_kind_by_what_it_stores():
    """A direct-zone cell stores a key and a zone id; a polygon cell, ids."""
    counts = reporting.ShortcutEntryCounts(
        total_entries=3,
        zone_entries=1,
        polygon_entries=2,
        empty_entries=0,
        polygon_id_count=5,
        polygons_per_shortcut=[0, 2, 3],
        zones_per_shortcut=[1, 2, 2],
    )

    metrics = reporting.shortcut_storage_metrics(counts)

    assert metrics["zone_storage_bytes"] == 1 * (8 + 1)
    assert metrics["polygon_storage_bytes"] == 2 * 8 + 5 * 2
    assert metrics["total_storage_bytes"] == 9 + 26
    # naive storage gives every cell a key plus the average id payload
    assert metrics["compression_ratio"] == pytest.approx((3 * (8 + 5 * 2 / 3)) / 35)


@pytest.mark.unit
def test_shortcut_storage_metrics_answer_a_ratio_of_one_on_an_empty_index():
    metrics = reporting.shortcut_storage_metrics(
        reporting.ShortcutEntryCounts(0, 0, 0, 0, 0, [], [])
    )

    assert metrics["total_storage_bytes"] == 0
    assert metrics["compression_ratio"] == 1.0


@pytest.mark.unit
def test_polygon_distribution_table_pairs_each_count_with_an_example():
    """The polygon count labels a row and keys the example lookup.

    It used to be formatted into the label and parsed back out of it, so the
    two could only agree by the label's wording staying parseable.
    """
    # zone 0 has one polygon, zones 1 and 2 have two each
    polygons_per_timezone = Counter({0: 1, 1: 2, 2: 2})

    table = reporting.render_polygon_distribution_table(
        polygons_per_timezone, ["Europe/Berlin", "Etc/GMT", "Etc/GMT+1"]
    )

    # whole rows, so label, count, percentage and example are pinned together
    # rather than merely all being present somewhere in the table
    assert "   * - 1 polygon\n     - 1\n     - 33.33%\n     - Europe/Berlin\n" in table
    assert "   * - 2 polygons\n     - 2\n     - 66.67%\n     - Etc/GMT\n" in table
    # zone 1 is the first zone with two polygons, so zone 2 never exemplifies it
    assert "Etc/GMT+1" not in table


@pytest.mark.unit
@pytest.mark.parametrize(
    "render, args",
    [
        (reporting.render_rst_table, (["H"], [["v"]])),
        (reporting.render_frequencies, ([0, 2], "Polygons to test")),
        (reporting.render_polygon_statistics_table, ("Hole", 0, [])),
        (reporting.render_polygon_distribution_table, (Counter({0: 1}), ["Etc/GMT"])),
        (reporting.render_shortcut_statistics, ({0: 1, 1: np.array([0, 1])}, [7, 8])),
    ],
)
def test_renderers_return_their_page_and_print_nothing(render, args, capsys):
    """Report text is a return value, never something written to stdout.

    Using stdout as the return channel is what forced every caller to redirect
    it, and a redirected destination is bound where the redirection is set up -
    which is why ``docs/data_report.rst`` was rewritten by parses that were
    given another output directory entirely. A renderer that starts printing
    again puts that back, so assert the absence of output rather than only the
    presence of the return value.
    """
    rendered = render(*args)

    assert rendered.endswith("\n")
    assert capsys.readouterr().out == ""


@pytest.mark.unit
@pytest.mark.parametrize("data_dir", [SOURCE_DATA_DIR, DEFAULT_DATA_DIR])
def test_report_path_for_keeps_the_committed_page_for_the_packaged_data(data_dir):
    """``make reports`` and ``make parse`` must still write the committed page.

    ``SOURCE_DATA_DIR`` is where the generators write and ``DEFAULT_DATA_DIR``
    where the installed data package sits - the same directory under an
    editable install, different ones otherwise, and both the packaged data.
    """
    assert reporting.report_path_for(Path(data_dir)) == DATA_REPORT_FILE


@pytest.mark.unit
def test_report_path_for_puts_another_parse_beside_its_own_binaries(tmp_path):
    """The defect: the destination used to be fixed, so every parse of another
    directory - ``make testparse``, or a user compiling custom data - rewrote
    the checkout's committed report to describe their input, silently.
    """
    assert reporting.report_path_for(tmp_path) == tmp_path / DATA_REPORT_FILE.name


@pytest.mark.integration
def test_write_data_report_writes_only_the_path_it_was_given(tmp_path):
    report_path = tmp_path / "data_report.rst"
    before = DATA_REPORT_FILE.read_bytes()

    reporting.write_data_report_from_binary(DEFAULT_DATA_DIR, report_path)

    assert report_path.read_text(encoding="utf-8").startswith(".. _data_report:")
    assert DATA_REPORT_FILE.read_bytes() == before


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


# The prefix comparison that replaced ``re.match(OCEAN_TIMEZONE_PREFIX, name)``. The
# constant holds no regex metacharacters and ``re.match`` anchors at the start, so the
# two are exactly equivalent - which is a claim about the *constant*, and therefore
# worth pinning where a future prefix could quietly break it.
OCEAN_NAME_CASES = [
    ("Etc/GMT", True),
    ("Etc/GMT+5", True),
    ("Etc/GMT-14", True),
    ("Europe/Berlin", False),
    ("America/Etc/GMT", False),
    ("", False),
    ("Etc/GM", False),
]


@pytest.mark.unit
@pytest.mark.parametrize("name, expected", OCEAN_NAME_CASES)
def test_is_ocean_timezone_matches_the_anchored_pattern(name: str, expected: bool):
    import re

    from timezonefinder.configs import OCEAN_TIMEZONE_PREFIX

    assert utils.is_ocean_timezone(name) is expected
    # the pattern this replaced, evaluated here rather than trusted
    assert (re.match(OCEAN_TIMEZONE_PREFIX, name) is not None) is expected


@pytest.mark.unit
def test_is_ocean_timezone_still_rejects_a_non_string():
    with pytest.raises(TypeError):
        utils.is_ocean_timezone(None)  # type: ignore[arg-type]
