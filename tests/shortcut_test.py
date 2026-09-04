"""
test the actually stored shortcut binary file
"""

import h3.api.numpy_int as h3
import numpy as np
import pytest


from scripts.hex_utils import surrounds_north_pole, surrounds_south_pole
from scripts.shortcuts import check_shortcut_sorting, has_coherent_sequences
from timezonefinder.configs import DEFAULT_DATA_DIR, SHORTCUT_H3_RES
from timezonefinder.utils_numba import int2coord

# Tests now work directly with hybrid_shortcuts format

VERBOSE_TESTING = True


def latlng_to_cell(lng: float, lat: float) -> int:
    return h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)


def test_single_shortcut_binary_exists(shortcut_file_path):
    """Exactly one shortcut binary ships, and it is the one the reader opens.

    A data directory left over from an older format keeps its binary under a different
    name, and nothing about a stale second file announces itself - the finder simply
    never reads it.
    """
    shortcut_files = list(DEFAULT_DATA_DIR.glob("*shortcut*.bin"))
    assert shortcut_files == [shortcut_file_path], (
        f"expected {shortcut_file_path.name} alone in {DEFAULT_DATA_DIR}, found "
        f"{[f.name for f in shortcut_files]}"
    )


@pytest.mark.slow
def test_shortcut_completeness(tf, hybrid_shortcuts):
    """Test that all points of each polygon are included in the proper shortcuts."""
    # Get access to the timezone polygons
    polygons = [tf.boundaries.coords_of(i) for i in range(tf.nr_of_polygons)]

    errors = []
    for poly_id, poly in enumerate(polygons):
        if VERBOSE_TESTING and poly_id % 100 == 0:
            print(f"\rvalidating polygon {poly_id}", end="", flush=True)

        for i, pt in enumerate(poly.T):
            # ATTENTION: int to coord conversion required!
            lng = int2coord(pt[0])
            lat = int2coord(pt[1])
            hex_id = latlng_to_cell(lng, lat)
            try:
                hybrid_value = hybrid_shortcuts[hex_id]
            except KeyError:
                errors.append(
                    f"shortcut mapping is incomplete at point ({lng}, {lat}) "
                    f"(hexagon cell id {hex_id} missing in mapping)"
                )
                continue

            # For hybrid shortcuts, check if polygon is covered
            polygon_covered = False
            if isinstance(hybrid_value, int):
                # Zone ID - check if polygon belongs to this zone
                polygon_zone = tf.zone_id_of(poly_id)
                polygon_covered = polygon_zone == hybrid_value
            else:
                # Polygon array - check if polygon is in the list
                polygon_covered = poly_id in hybrid_value

            if not polygon_covered:
                errors.append(
                    f"point #{i} ({lng}, {lat}) of polygon {poly_id} (zone {tf.zone_id_of(poly_id)}) "
                    f"is not covered by hybrid shortcut entry {hybrid_value} of cell {hex_id}"
                )

    assert not errors, f"Shortcut completeness errors: {errors[:5]}"


def test_shortcut_resolution(hybrid_shortcuts):
    """Test that all shortcuts have the correct H3 resolution."""
    invalid_resolutions = []
    for hex_id in hybrid_shortcuts.keys():
        res = h3.get_resolution(hex_id)
        if res != SHORTCUT_H3_RES:
            invalid_resolutions.append(
                f"Hexagon {hex_id} has resolution {res}, expected {SHORTCUT_H3_RES}"
            )

    assert not invalid_resolutions, f"Resolution errors: {invalid_resolutions[:5]}"


@pytest.mark.slow
def test_unused_polygons(tf, hybrid_shortcuts):
    """Test that all polygons are used in at least one shortcut."""
    # Get the total number of polygons
    nr_of_polygons = tf.nr_of_polygons

    # check if all polygons are used in the shortcuts (hybrid format)
    used_polygons = set()
    for hybrid_value in hybrid_shortcuts.values():
        if isinstance(hybrid_value, int):
            # Zone ID - find all polygons belonging to this zone
            for poly_id in range(nr_of_polygons):
                if tf.zone_id_of(poly_id) == hybrid_value:
                    used_polygons.add(poly_id)
        else:
            # Polygon array
            used_polygons.update(hybrid_value)

    all_polygon_ids = set(range(nr_of_polygons))
    unused_poly_ids = all_polygon_ids - used_polygons

    assert len(unused_poly_ids) == 0, (
        f"There are {len(unused_poly_ids)} unused polygons: {unused_poly_ids}"
    )


def test_empty_shortcut(hybrid_shortcuts):
    """Test that no shortcut entries are empty (all should have polygons or zones)."""
    # since using timezone data with ocean coverage all the cells should have polygons or zones in them
    empty_shortcuts = []
    for hex_id, hybrid_value in hybrid_shortcuts.items():
        is_empty = False
        if isinstance(hybrid_value, int):
            # Zone ID - not empty
            is_empty = False
        else:
            # Polygon array - check if empty
            is_empty = len(hybrid_value) == 0

        if is_empty:
            boundary = h3.cell_to_boundary(hex_id)[0]
            empty_shortcuts.append(f"Hexagon {hex_id} at {boundary}")

    assert not empty_shortcuts, f"Found empty shortcut entries: {empty_shortcuts[:5]}"


def test_unique_pole_cells(hybrid_shortcuts):
    """Test that exactly one cell surrounds each pole."""
    s_pole_cells = []
    n_pole_cells = []

    for hex_id in hybrid_shortcuts.keys():
        # Check if this hex cell surrounds the poles using extracted functions
        if surrounds_south_pole(hex_id):
            s_pole_cells.append(hex_id)
        if surrounds_north_pole(hex_id):
            n_pole_cells.append(hex_id)

    assert len(s_pole_cells) == 1, (
        f"{len(s_pole_cells)} cells surround the south pole: {s_pole_cells}"
    )
    assert len(n_pole_cells) == 1, (
        f"{len(n_pole_cells)} cells surround the north pole: {n_pole_cells}"
    )


def test_shortcut_uniqueness(hybrid_shortcuts):
    """Test that shortcuts are unique (no duplicates in polygon IDs)."""
    duplicates = []
    for hex_id, hybrid_value in hybrid_shortcuts.items():
        if isinstance(hybrid_value, int):
            # Zone ID - no duplicates by definition
            continue
        else:
            # Polygon array - check for duplicates
            polygon_ids = hybrid_value
            if len(np.unique(polygon_ids)) != len(polygon_ids):
                duplicates.append(
                    f"Shortcut {hex_id} contains duplicate polygon IDs: {polygon_ids}"
                )

    assert not duplicates, f"Shortcut uniqueness errors: {duplicates[:5]}"


@pytest.mark.slow
def test_unique_shortcut_consistency(tf, hybrid_shortcuts):
    """Ensure the unique shortcut entries are consistent with zone assignments."""

    # Count unique shortcuts (zone IDs in hybrid format)
    unique_shortcut_count = sum(
        1 for value in hybrid_shortcuts.values() if isinstance(value, int)
    )
    assert unique_shortcut_count > 0

    for hex_id, hybrid_value in hybrid_shortcuts.items():
        if isinstance(hybrid_value, int):
            # This is a zone ID - verify it's consistent with timezone_at
            zone_id = hybrid_value
            # Get a point in this hex cell to test
            boundary = h3.cell_to_boundary(hex_id)
            lat, lng = boundary[0]  # Get first boundary point

            # Check using TimezoneFinder's timezone_at method
            found_timezone = tf.timezone_at(lng=lng, lat=lat)
            if found_timezone is not None:
                # Convert timezone name to zone ID to compare
                expected_zone_id = tf.timezone_names.index(found_timezone)
                assert expected_zone_id == zone_id, (
                    f"Hybrid shortcut has zone {zone_id} for hex {hex_id}, "
                    f"but TimezoneFinder returns timezone '{found_timezone}' (zone {expected_zone_id})"
                )


@pytest.mark.parametrize(
    "lst,expected",
    [
        ([], True),
        ([1], True),
        ([1, 1], True),
        ([2, 3], True),
        ([2, 3, 3, 0, 0, 4], True),
        ([2, 3, 2], False),
        ([2, 3, 2, 3], False),
    ],
)
def test_has_coherent_check_fct(lst, expected):
    assert has_coherent_sequences(lst) == expected


def test_shortcut_sorting(tf, hybrid_shortcuts):
    """Test that shortcuts are correctly sorted by zone ID and polygon size."""
    invalid_sortings = []
    for hex_id, hybrid_value in hybrid_shortcuts.items():
        if isinstance(hybrid_value, int):
            # Zone ID - no sorting to check
            continue
        else:
            # Polygon array - check sorting
            polygon_ids = hybrid_value
            try:
                check_shortcut_sorting(polygon_ids, tf.zone_ids)
            except AssertionError as e:
                invalid_sortings.append(
                    f"Invalid sorting for hexagon {hex_id}: {str(e)}"
                )

    assert not invalid_sortings, f"Shortcut sorting errors: {invalid_sortings[:5]}"


# Coordinates whose H3 cell has all six corners inside a hole of the polygon that covers
# the coordinate itself - an ocean zone's cut-out around an island, or one country's
# enclave inside another. Compiling the index by corner alone dropped that polygon from
# the cell, and every coordinate in the part of the cell outside the hole was answered
# with the zone that happens to be left.
HOLE_CLIPPED_CELL_COORDS = [
    # in South Africa, in a cell whose corners are all inside Lesotho
    (27.52307, -29.24473),
    # Tuamotus: ocean around an atoll, in a cell whose corners are all on the Tahiti side
    (-145.65772, -15.78144),
    # near Adak, and near San Andrés
    (178.89059, 51.84103),
    (-81.57602, 12.19784),
]


@pytest.mark.unit
@pytest.mark.parametrize("lng,lat", HOLE_CLIPPED_CELL_COORDS)
def test_a_hole_clipping_a_cell_leaves_the_covering_polygon_in_it(tf, lng, lat):
    """``timezone_at`` must answer what the polygons actually say, at these coordinates.

    The two methods differ only in what they do when no candidate contains the point:
    ``certain_timezone_at`` says so, ``timezone_at`` answers with the last zone in the
    cell without testing it. So they disagree exactly when the index has left out the
    polygon that covers the point, which is what these coordinates used to demonstrate.

    Pinned as an invariant rather than as expected zone names, since the names are the
    packaged dataset's answer and a data update is free to move a border.
    """
    certain = tf.certain_timezone_at(lng=lng, lat=lat)

    assert certain is not None
    assert tf.timezone_at(lng=lng, lat=lat) == certain


# Coordinates in the three cells north of latitude 88.5 whose stored ring jumps the
# +-180 degree cut. Judged as a planar ring it is not a hexagon at all but a
# self-intersecting shape spanning most of the globe, so the overlap tests answered about
# that shape and the ocean strip on the far side of the cut was left out of all three.
ANTIMERIDIAN_CELL_COORDS = [
    (-179.42048, 89.60654),
    (-175.13121, 89.44923),
    (177.58690, 88.76167),
    (179.61929, 88.60653),
    (174.97945, 88.91468),
    (172.97725, 88.64155),
    (178.31014, 89.18498),
    (174.21060, 89.33760),
]


@pytest.mark.unit
@pytest.mark.parametrize("lng,lat", ANTIMERIDIAN_CELL_COORDS)
def test_a_cell_crossing_the_antimeridian_keeps_the_polygon_covering_it(tf, lng, lat):
    """Same invariant as above, on the other way a cell used to lose its polygon."""
    certain = tf.certain_timezone_at(lng=lng, lat=lat)

    assert certain is not None
    assert tf.timezone_at(lng=lng, lat=lat) == certain


@pytest.mark.slow
def test_the_index_lists_the_polygon_covering_each_sampled_coordinate(tf):
    """Sweep cell interiors, which the vertex-driven tests above never visit.

    ``test_shortcut_completeness`` walks the polygon vertices, so it sees a cell only
    where a boundary passes through it. A cell can still lose a polygon that covers its
    interior, and this is what notices.

    Sampled by area rather than uniformly in latitude, so it is a workload and not a
    pole-heavy one - which also means it visits the cells at the antimeridian and the
    poles far too rarely to stand in for an exhaustive check. The exhaustive form is
    this same assertion over the seven resolution-5 child centres of every cell
    (``h3.cell_to_children(cell, SHORTCUT_H3_RES + 1)`` over ``all_res_candidates``),
    which enumerates the defective cells outright instead of sampling for them - that
    is what ``ANTIMERIDIAN_CELL_COORDS`` and ``HOLE_CLIPPED_CELL_COORDS`` were found
    with. At ~2 million lookups it costs ~8 minutes against this test's ~15 seconds,
    so run it by hand after changing the shortcut compiler rather than on every gate.
    """
    n = 100_000
    rng = np.random.default_rng(20260825)
    # area weighted, so the sample is a workload rather than a pole-heavy one
    lats = np.degrees(np.arcsin(rng.uniform(-1.0, 1.0, n)))
    lngs = rng.uniform(-180.0, 180.0, n)

    uncovered = [
        (float(lng), float(lat))
        for lng, lat in zip(lngs, lats)
        if tf.certain_timezone_at(lng=float(lng), lat=float(lat)) is None
    ]

    assert not uncovered, (
        "the shortcut index does not list the polygon covering "
        f"{len(uncovered)} of {n} sampled coordinates, e.g. {uncovered[:5]}"
    )


@pytest.mark.unit
def test_a_candidate_s_zone_id_read_one_at_a_time_matches_the_narrowed_array(
    tf, hybrid_shortcuts
):
    """Every ambiguous cell's candidates answer the same read one at a time as in bulk.

    ``_zone_id_among`` reads the zone id of the *one* candidate that answers, where it
    used to narrow the whole candidate list with ``zone_ids[candidates]`` before any
    point was tested. The two are the same lookup at two arities, and the loop's index
    ``i`` is what tied them together - a candidate's position in the list, used to index
    an array built from that same list. Nothing about a wrong pairing is visible in a
    lookup's answer unless the mismatched zones differ, so a silent off-by-one here
    would return a neighbouring zone for a fraction of ambiguous points and fail no
    existing test.
    """
    for hex_id, hybrid_value in hybrid_shortcuts.items():
        if isinstance(hybrid_value, int):
            # a unique-zone cell holds no candidate list to narrow
            continue
        candidates = np.asarray(hybrid_value)
        narrowed = tf.zone_ids[candidates]
        one_at_a_time = [tf._zone_id_of(candidate) for candidate in candidates]
        assert one_at_a_time == narrowed.tolist(), (
            f"cell {hex_id}: per-candidate zone ids {one_at_a_time} disagree with the "
            f"narrowed array {narrowed.tolist()}"
        )
