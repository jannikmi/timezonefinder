"""
test the actually stored shortcut binary file
"""

import numpy as np
import pytest


from scripts.shortcuts import check_shortcut_sorting
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder.configs import COORD2INT_FACTOR, DEFAULT_DATA_DIR
from timezonefinder.shortcut_index import (
    ABSENT,
    ROOT_CELLS,
    ROOT_COLUMNS,
    cell_bounds,
    child_cells_of,
    is_root_cell,
)
from timezonefinder.utils import coord2int, int2coord, query2int

# Tests now work directly with hybrid_shortcuts format

VERBOSE_TESTING = True


def cell_centre(cell_id: int) -> tuple[float, float]:
    """A coordinate inside one cell, which for a rectangle is exactly its middle."""
    x0, y0, x1, y1 = cell_bounds(cell_id)
    return ((x0 + x1) // 2) / COORD2INT_FACTOR, ((y0 + y1) // 2) / COORD2INT_FACTOR


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
def test_every_vertex_a_polygon_owns_is_offered_in_its_cell(tf, shortcut_index):
    """Walk every stored boundary vertex: if the kernel puts it inside its own polygon,
    the cell a lookup there reads must offer that polygon.

    **The condition is the point of this test.** A vertex is on a boundary, and the
    kernel gives a point on a polygon's south or west boundary to the *other* polygon -
    so a polygon frequently does not contain its own vertex. The candidate rule is exact
    rather than conservative: a polygon that only touches a cell owns none of its points
    and is correctly left out of it. Asserting that every vertex's cell lists its polygon
    would therefore assert the old H3 rule's over-inclusion. It fails on 326 vertices of
    the ~8.0 million this loop visits (4.1 million of them distinct) - all 326 of them
    vertices the kernel places *outside* their own polygon, including 32 on the -180
    meridian, which a lookup reads as +180 and answers from the far side by design.

    What matters, and what this asserts, is that no polygon *containing* the queried
    point is missing from the candidates. ``scripts/audit_shortcut_candidates.py`` is the
    exhaustive form of that over three probe streams; this is the cheap vertex-driven
    half of it, kept because it needs no separate run.
    """
    errors = []
    for poly_id in range(tf.nr_of_polygons):
        poly = tf.boundaries.coords_of(poly_id)
        if VERBOSE_TESTING and poly_id % 100 == 0:
            print(f"\rvalidating polygon {poly_id}", end="", flush=True)
        zone = tf.zone_id_of(poly_id)
        for i, pt in enumerate(poly.T):
            lng, lat = int2coord(pt[0]), int2coord(pt[1])
            x, y = query2int(lng, lat)
            if not tf.inside_of_polygon(poly_id, x, y):
                # the kernel does not place this vertex inside its own polygon, so the
                # cell owes it nothing - see the docstring
                continue
            cell = shortcut_index.cell_at(lng, lat)
            value = shortcut_index.value_of(cell)
            offered = (
                value == zone
                if isinstance(value, int)
                else value is not None and poly_id in value
            )
            if not offered:
                errors.append(
                    f"vertex #{i} ({lng}, {lat}) of polygon {poly_id} (zone {zone}) is "
                    f"inside that polygon, but cell {cell} offers {value}"
                )

    assert not errors, f"Shortcut completeness errors: {errors[:5]}"


@pytest.mark.slow
def test_a_vertex_outside_its_own_polygon_is_still_answered(tf):
    """The other half, and what keeps the test above from being satisfied by exclusion.

    A rule that dropped *every* polygon from *every* cell would pass the test above
    vacuously on the vertices it skips. So: at a vertex the kernel places outside its own
    polygon, a lookup must still answer, and no polygon that *does* contain the point may
    be missing. A sample rather than all 4.1 million, because establishing "no containing
    polygon is missing" means a bounding-box sweep per point.
    """
    rng = np.random.default_rng(20261013)
    checked = outside = 0
    errors = []
    for poly_id in rng.integers(0, tf.nr_of_polygons, 150).tolist():
        poly = tf.boundaries.coords_of(poly_id)
        for i in rng.integers(0, poly.shape[1], 20).tolist():
            lng, lat = int2coord(poly[0, i]), int2coord(poly[1, i])
            x, y = query2int(lng, lat)
            checked += 1
            if tf.inside_of_polygon(poly_id, x, y):
                continue
            outside += 1
            bounds = tf.boundaries
            eligible = np.flatnonzero(
                (bounds.xmin <= x)
                & (bounds.xmax >= x)
                & (bounds.ymin <= y)
                & (bounds.ymax >= y)
            )
            candidates = set(tf._iter_boundaries_in_shortcut(lng=lng, lat=lat))
            missing = [
                int(p)
                for p in eligible
                if p not in candidates and tf.inside_of_polygon(int(p), x, y)
            ]
            if missing:
                errors.append(f"({lng}, {lat}) does not offer containing {missing}")
            if tf.timezone_at(lng=lng, lat=lat) is None:
                errors.append(f"({lng}, {lat}) is unanswered")

    assert outside > 100, (
        f"only {outside} of {checked} sampled vertices fall outside their own polygon - "
        "the assertion below would be close to vacuous"
    )
    assert not errors, f"{len(errors)} failures, e.g. {errors[:5]}"


@pytest.mark.unit
def test_every_stored_cell_is_a_leaf_of_the_tree(shortcut_index, hybrid_shortcuts):
    """The stored cells are exactly the tree's leaves - no more and no fewer.

    This is what the H3 resolution check became. There a stale cell id was one built for
    another resolution; here it is one on the wrong level: a root cell that also refines
    has two answers and the lookup reads one of them, and a finest-level cell whose root
    does not refine has no stored value at all. Both are invisible in the file.
    """
    expected = set(np.flatnonzero(shortcut_index.table >= 0).tolist())
    for parent in np.flatnonzero(shortcut_index.table < ABSENT).tolist():
        expected.update(int(child) for child in child_cells_of(parent))
    stored = set(hybrid_shortcuts)
    # the packaged ocean zones cover every cell, so the two sets are equal; a dataset
    # leaving cells uncovered stores a subset, never a cell outside the tree
    assert stored <= expected, (
        f"{len(stored - expected)} stored cells are not leaves of the tree, e.g. "
        f"{sorted(stored - expected)[:5]}"
    )
    assert not expected - stored, (
        f"{len(expected - stored)} leaves of the tree are not stored, e.g. "
        f"{sorted(expected - stored)[:5]}"
    )
    assert all(0 <= cell < ROOT_CELLS for cell in stored if is_root_cell(cell))


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
            empty_shortcuts.append(f"cell {hex_id} at {cell_centre(hex_id)}")

    assert not empty_shortcuts, f"Found empty shortcut entries: {empty_shortcuts[:5]}"


def test_the_rows_along_both_poles_are_covered(tf, shortcut_index):
    """What replaces "exactly one cell surrounds each pole", which was H3 topology.

    An aligned grid reaches a pole as a whole row of cells rather than as one cell, so
    there is no cell to be unique. What still has to hold is that the rows are *there*
    and answered: they are the hardest row for a candidate rule to get right - every
    polygon reaching them is clipped by the row's own edge - and a gap in either would
    be a band of unanswered coordinates around a pole.

    It says nothing about different spellings of a pole agreeing. They do not, and did
    not under H3 either: the Arctic and Antarctic ocean zones are longitude strips, so
    the kernel gives (0, 90) and (170, 90) to different ones whatever the index offers.
    """
    rows = {
        "southernmost": range(ROOT_COLUMNS),
        "northernmost": range(ROOT_CELLS - ROOT_COLUMNS, ROOT_CELLS),
    }
    for name, roots in rows.items():
        # the *leaves*, not the roots: a refined root cell is not an answer, so checking
        # it would pass even if all sixteen of its children were uncovered - which is
        # exactly the band of unanswered coordinates this exists to refuse
        leaves = []
        for root in roots:
            entry = shortcut_index.entry_of(root)
            if entry < ABSENT:
                leaves.extend(int(c) for c in child_cells_of(root))
            else:
                leaves.append(root)
        uncovered = [c for c in leaves if shortcut_index.entry_of(c) == ABSENT]
        assert not uncovered, (
            f"{len(uncovered)} of the {len(leaves)} cells along the {name} row are "
            f"uncovered, e.g. {uncovered[:5]}"
        )
        # and the index being covered is not the same as the lookup answering, which is
        # the claim a reader of this test cares about. One probe per cell of the row,
        # at the pole itself.
        pole = 90.0 if name == "northernmost" else -90.0
        unanswered = [
            cell
            for cell in leaves
            if tf.timezone_at(lng=cell_centre(cell)[0], lat=pole) is None
        ]
        assert not unanswered, (
            f"{len(unanswered)} longitudes answer nothing at latitude {pole}"
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
            # a point in this cell: its centre, which a rectangle states exactly - where
            # a hexagon's first boundary vertex could fall in a neighbouring cell
            lng, lat = cell_centre(hex_id)

            # Check using TimezoneFinder's timezone_at method
            found_timezone = tf.timezone_at(lng=lng, lat=lat)
            if found_timezone is not None:
                # Convert timezone name to zone ID to compare
                expected_zone_id = tf.timezone_names.index(found_timezone)
                assert expected_zone_id == zone_id, (
                    f"Hybrid shortcut has zone {zone_id} for hex {hex_id}, "
                    f"but TimezoneFinder returns timezone '{found_timezone}' (zone {expected_zone_id})"
                )


def test_shortcut_sorting(tf, hybrid_shortcuts):
    """Test that shortcuts are ordered with a whole final zone suffix."""
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


# Coordinates whose H3 cell had all six corners inside a hole of the polygon that covers
# the coordinate itself - an ocean zone's cut-out around an island, or one country's
# enclave inside another. Compiling the index by corner alone dropped that polygon from
# the cell, and every coordinate in the part of the cell outside the hole was answered
# with the zone that happens to be left. The grid tree subtracts holes from the ring it
# intersects cells with, so it has no corner rule to be fooled; these stay as the
# cheapest statement of the invariant at the hardest coordinates anyone has found.
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


# Coordinates in the three H3 cells north of latitude 88.5 whose stored ring jumped the
# +-180 degree cut. Judged as a planar ring that was not a hexagon at all but a
# self-intersecting shape spanning most of the globe, so the overlap tests answered about
# that shape and the ocean strip on the far side of the cut was left out of all three. No
# cell of an aligned grid crosses the cut, so the failure mode is gone with the hexagons;
# the invariant is pinned here all the same.
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
def test_a_cell_at_the_antimeridian_keeps_the_polygon_covering_it(tf, lng, lat):
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
    ``scripts/audit_shortcut_candidates.py``, which ``update_data.sh`` runs over every
    cell corner, every stored ring vertex and both seams on each compiled dataset and
    enumerates the defective cells outright instead of sampling for them - that is what
    ``ANTIMERIDIAN_CELL_COORDS`` and ``HOLE_CLIPPED_CELL_COORDS`` were found with, under
    the H3 index. This test stays because it is a cheap interior sweep on every gate.
    """
    n = 100_000
    rng = np.random.default_rng(20260825)
    # area weighted, so the sample is a workload rather than a pole-heavy one
    lats = np.degrees(np.arcsin(rng.uniform(-1.0, 1.0, n)))
    lngs = rng.uniform(-180.0, 180.0, n)

    uncovered = [
        (float(lng), float(lat))
        for lng, lat in zip(lngs, lats, strict=True)
        if tf.certain_timezone_at(lng=float(lng), lat=float(lat)) is None
    ]

    assert not uncovered, (
        "the shortcut index does not list the polygon covering "
        f"{len(uncovered)} of {n} sampled coordinates, e.g. {uncovered[:5]}"
    )


@pytest.mark.unit
def test_the_candidate_loop_answers_what_the_narrowed_array_answered(tf):
    """``_zone_id_among`` agrees with the form that narrowed the whole list up front.

    It now reads the zone id of the *one* candidate that answers, where it used to index
    an array built from the same candidate list by position. The loop's ``i`` is what
    tied those two together, so the failure mode is a pairing that has slipped: a
    neighbouring zone returned for a fraction of ambiguous points, with no exception and
    no empty answer.

    The reference below is that earlier form, so this compares the two implementations
    rather than comparing numpy indexing to itself - which is what an assertion over the
    candidate lists alone would do, and it cannot fail. Injecting
    ``possible_boundaries[(i + 1) % len(possible_boundaries)]`` into the real loop turns
    1,003 of these 2,000 points red.
    """

    def reference(possible_boundaries, last_zone_change_idx, lng, lat):
        """The pre-change body: narrow every candidate's zone id before testing a point."""
        zone_ids = tf.zone_ids[possible_boundaries]
        x, y = coord2int(lng), coord2int(lat)
        for i, boundary_id in enumerate(possible_boundaries):
            if i >= last_zone_change_idx:
                break
            if tf.inside_of_polygon(boundary_id, x, y):
                return int(zone_ids[i])
        return int(zone_ids[-1])

    points = load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)[:2000]
    for lng, lat in points:
        entry = tf.shortcuts.entry_at(lng, lat)
        if entry >= 0:
            # a unique-zone cell is answered by the table and reaches no candidate loop
            continue
        candidates = tf.shortcuts.candidates_of(entry)
        last = tf.shortcuts.stop_index_of(entry)
        assert tf._zone_id_among(candidates, last, lng, lat) == reference(
            candidates, last, lng, lat
        ), f"({lng}, {lat}) in cell entry {entry} over candidates {candidates.tolist()}"
