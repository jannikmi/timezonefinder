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


def test_single_shortcut_binary_exists(zone_id_dtype, hybrid_shortcut_file_path):
    """Test that only a single .fbs binary file for the shortcut index exists in the data folder."""
    data_dir = DEFAULT_DATA_DIR

    # Find all .fbs files that could be shortcut-related
    fbs_files = list(data_dir.glob("*shortcut*.fbs"))

    # We expect exactly one shortcut .fbs file (hybrid_shortcuts_uint8.fbs or hybrid_shortcuts_uint16.fbs)
    assert len(fbs_files) == 1, (
        f"Expected exactly 1 shortcut .fbs file in {data_dir}, "
        f"but found {len(fbs_files)}: {[f.name for f in fbs_files]}"
    )

    # Verify it's the correct hybrid shortcuts file
    shortcut_file = fbs_files[0]
    assert shortcut_file.name.startswith("hybrid_shortcuts_"), (
        f"Expected hybrid shortcuts file, but found {shortcut_file.name}"
    )

    # Verify it matches the expected file based on zone_id_dtype
    assert shortcut_file == hybrid_shortcut_file_path, (
        f"Found shortcut file {shortcut_file.name} doesn't match expected {hybrid_shortcut_file_path.name}"
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
