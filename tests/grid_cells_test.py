"""The converter's candidate rule, against the point-in-polygon kernel itself.

``scripts/grid_cells.py`` decides which polygons a lookup in a cell will test, so a
polygon wrongly left out is a silently wrong timezone for every point of that cell the
polygon covers - and nothing downstream can notice, because the compiled index is then
internally consistent. ``scripts/audit_shortcut_candidates.py`` is the exhaustive check,
but it inspects a *compiled directory*: it catches a bad artifact on the next data
update, not a bad rule on the next commit. This file is the rule's own unit tests, and
the oracle is the real kernel over every integer point of the cell rather than a second
statement of the rule.

**The candidate rule needs its own unit tests, and the whole-suite pass rate does not
supply them.** Without this file both of these mutations of ``owned_pairs``'s ``outer``
box passed every other test in the repository. Both are checked rather than asserted -
the failures below are what they actually produce:

* ``box(x0 - 0.5, y0 - 0.5, x1, y1)`` -> ``box(x0, y0, x1, y1)``, dropping the half-unit
  shift that matches the kernel's edge convention. That **introduces omissions**, and
  ``test_the_rule_never_omits_a_polygon_that_owns_a_point_of_the_cell`` and
  ``test_a_one_column_polygon_is_a_candidate_in_exactly_one_column`` both fail on it.
* the same box grown to ``x1 + 0.5, y1 + 0.5``, which makes the rule touch-inclusive and
  gives up the selectivity the whole index change is for.
  ``test_a_one_column_polygon_is_a_candidate_in_exactly_one_column`` fails on it, because
  it is the one that probes a cell on the *east* side of a polygon.

That one test catches both, which is why it checks every expectation against the kernel
in the same breath rather than hard-coding a verdict: it is load-bearing, so it must not
be able to encode the rule it tests.
"""

import numpy as np
import pytest
import shapely
from shapely import Polygon, box

from scripts.grid_cells import grouped, owned_pairs
from timezonefinder import utils

pytestmark = pytest.mark.unit


def prepared(*polygons) -> np.ndarray:
    array = np.asarray(list(polygons), dtype=object)
    shapely.prepare(array)
    return array


def ring_of(polygon: Polygon) -> np.ndarray:
    """The polygon's exterior as the kernel takes it.

    ``int32`` and C-contiguous per axis, which is what ``PolygonArray.coords_of`` hands
    the kernel and what the C extension reinterprets its buffer as - a ``float64`` ring
    is read as garbage rather than rejected, so the dtype is part of calling it, not a
    detail. The vertices here are integers by construction.
    """
    return np.ascontiguousarray(np.asarray(polygon.exterior.coords).T.astype(np.int32))


def candidates_in(polygons: np.ndarray, bounds: tuple[int, int, int, int]) -> set[int]:
    x0, y0, x1, y1 = bounds
    _, poly_idx = owned_pairs(
        polygons,
        np.array([x0], dtype=np.int64),
        np.array([y0], dtype=np.int64),
        np.array([x1], dtype=np.int64),
        np.array([y1], dtype=np.int64),
    )
    return {int(p) for p in poly_idx}


def owns_a_point_of(polygon: Polygon, bounds: tuple[int, int, int, int]) -> bool:
    """The oracle: does the real kernel place any of the cell's integer points inside?"""
    x0, y0, x1, y1 = bounds
    ring = ring_of(polygon)
    return any(
        utils.inside_polygon(x, y, ring)
        for x in range(x0, x1 + 1)
        for y in range(y0, y1 + 1)
    )


# A cell small enough that its integer points can be enumerated, placed away from the
# coordinate limits so that the shifted boxes stay in range.
CELL = (100, 200, 104, 204)


# --- the direction that matters: never an omission ---------------------------------


def test_the_rule_never_omits_a_polygon_that_owns_a_point_of_the_cell():
    """Randomised, with the kernel as the oracle. This is the one that cannot be allowed
    to fail: an omission is a wrong answer nothing downstream can see.

    Triangles with integer vertices, drawn to straddle the cell's edges and corners,
    which is where the half-unit shift decides the outcome.
    """
    rng = np.random.default_rng(20261013)
    x0, y0, x1, y1 = CELL
    omissions = []
    admitted_without_owning = 0
    checked = 0
    for _ in range(4000):
        pts = np.column_stack(
            (
                rng.integers(x0 - 3, x1 + 4, 3),
                rng.integers(y0 - 3, y1 + 4, 3),
            )
        ).astype(float)
        polygon = Polygon(pts)
        if not polygon.is_valid or polygon.area == 0:
            continue
        checked += 1
        offered = bool(candidates_in(prepared(polygon), CELL))
        owns = owns_a_point_of(polygon, CELL)
        if owns and not offered:
            omissions.append(pts.tolist())
        if offered and not owns:
            admitted_without_owning += 1

    assert checked > 2000, f"only {checked} valid polygons were generated"
    assert not omissions, (
        f"{len(omissions)} polygons own a point of the cell and are not offered in it, "
        f"e.g. {omissions[:3]}"
    )
    # the other direction is the documented over-inclusion, and it has to be *present*
    # or this test is measuring a touch-inclusive rule by accident
    assert admitted_without_owning > 0, (
        "no polygon was admitted without owning a point of the cell, so the rule under "
        "test is not the tight one this file describes"
    )


def test_the_half_unit_shift_admits_a_polygon_owning_only_the_cells_west_column():
    """The witness the shift exists for, stated as the rule rather than as a mutation.

    A polygon whose *east* edge falls exactly on the cell's first column owns that
    column: the kernel gives a point on an east boundary to the polygon. Its interior
    lies entirely west of the cell, so only a box reaching west of ``x0`` finds it -
    which is what the half-unit shift is.
    """
    x0, y0, x1, y1 = CELL
    polygon = Polygon([(x0 - 4, y0 - 1), (x0, y0 - 1), (x0, y1 + 1), (x0 - 4, y1 + 1)])
    assert owns_a_point_of(polygon, CELL), "the kernel must own the x0 column here"
    assert candidates_in(prepared(polygon), CELL) == {0}


def test_the_half_unit_shift_admits_a_polygon_owning_only_the_cells_south_row():
    """The same on the other axis: a north edge exactly on the cell's first row."""
    x0, y0, x1, y1 = CELL
    polygon = Polygon([(x0 - 1, y0 - 4), (x1 + 1, y0 - 4), (x1 + 1, y0), (x0 - 1, y0)])
    assert owns_a_point_of(polygon, CELL)
    assert candidates_in(prepared(polygon), CELL) == {0}


def test_a_polygon_that_only_touches_the_cell_is_not_a_candidate():
    """What the touch-inclusive mutation kills, and the whole selectivity result.

    A polygon whose east edge is one unit *west* of the cell's first column owns none of
    the cell's points - the kernel gives its own boundary away to the west, and the cell
    starts east of that. It touches the cell's closed box, so a rule built on plain
    ``intersects`` would list it in every cell along the border it runs down.
    """
    x0, y0, x1, y1 = CELL
    polygon = Polygon(
        [(x0 - 5, y0 - 1), (x0 - 1, y0 - 1), (x0 - 1, y1 + 1), (x0 - 5, y1 + 1)]
    )
    assert not owns_a_point_of(polygon, CELL)
    assert candidates_in(prepared(polygon), CELL) == set()

    # and the same immediately south
    south = Polygon(
        [(x0 - 1, y0 - 5), (x1 + 1, y0 - 5), (x1 + 1, y0 - 1), (x0 - 1, y0 - 1)]
    )
    assert not owns_a_point_of(south, CELL)
    assert candidates_in(prepared(south), CELL) == set()


def test_a_polygon_covering_the_whole_cell_is_a_candidate():
    """The trivial case, so that a rule refusing everything cannot pass this file."""
    x0, y0, x1, y1 = CELL
    polygon = Polygon(
        [(x0 - 9, y0 - 9), (x1 + 9, y0 - 9), (x1 + 9, y1 + 9), (x0 - 9, y1 + 9)]
    )
    assert owns_a_point_of(polygon, CELL)
    assert candidates_in(prepared(polygon), CELL) == {0}


def test_a_polygon_well_clear_of_the_cell_is_not_a_candidate():
    polygon = box(0, 0, 10, 10)
    assert candidates_in(prepared(polygon), CELL) == set()


# --- the cell's own edges, from both sides -----------------------------------------


def test_a_one_column_polygon_is_a_candidate_in_exactly_one_column():
    """The property the whole index rests on, stated where it is tightest.

    A polygon spanning ``[column - 1, column]`` owns the integer points at ``column``
    (its east edge) and none at ``column - 1`` (its west edge, which the kernel gives
    away). So of the three single-column cells around it, exactly one lists it - and
    neither neighbour does, which is what "a zone across an aligned border is not a
    candidate" means. Each expectation is checked against the kernel in the same breath,
    so the test cannot encode the rule it is testing.
    """
    x0, y0, x1, y1 = CELL
    column = x0 + 2
    polygon = Polygon([(column - 1, y0), (column, y0), (column, y1), (column - 1, y1)])
    array = prepared(polygon)
    for label, cell in {
        "the column west": (column - 1, y0, column - 1, y1),
        "its own column": (column, y0, column, y1),
        "the column east": (column + 1, y0, column + 1, y1),
    }.items():
        owns = owns_a_point_of(polygon, cell)
        offered = candidates_in(array, cell) == {0}
        assert owns == offered, f"{label}: kernel owns={owns}, rule offers={offered}"
    assert owns_a_point_of(polygon, (column, y0, column, y1)), (
        "the polygon must own its own column, or every expectation above is vacuous"
    )
    assert not owns_a_point_of(polygon, (column - 1, y0, column - 1, y1))
    assert not owns_a_point_of(polygon, (column + 1, y0, column + 1, y1))


# --- holes --------------------------------------------------------------------------


def test_a_hole_covering_the_cell_removes_the_polygon_from_it():
    """Holes are subtracted before the predicate, because the kernel subtracts them too.

    A cell entirely inside a hole is not covered by the polygon, and listing it there
    would offer a candidate that can never match.
    """
    x0, y0, x1, y1 = CELL
    outer = [(x0 - 9, y0 - 9), (x1 + 9, y0 - 9), (x1 + 9, y1 + 9), (x0 - 9, y1 + 9)]
    hole = [(x0 - 4, y0 - 4), (x1 + 4, y0 - 4), (x1 + 4, y1 + 4), (x0 - 4, y1 + 4)]
    assert candidates_in(prepared(Polygon(outer)), CELL) == {0}
    assert candidates_in(prepared(Polygon(outer, [hole])), CELL) == set()


def test_a_hole_clipping_part_of_the_cell_keeps_the_polygon():
    """The other half, and the case a corner-only rule used to get wrong: a hole running
    *through* the cell leaves the rest of it covered."""
    x0, y0, x1, y1 = CELL
    outer = [(x0 - 9, y0 - 9), (x1 + 9, y0 - 9), (x1 + 9, y1 + 9), (x0 - 9, y1 + 9)]
    hole = [(x0 - 4, y0 - 4), (x0 + 1, y0 - 4), (x0 + 1, y1 + 4), (x0 - 4, y1 + 4)]
    polygon = Polygon(outer, [hole])
    assert owns_a_point_of(polygon, CELL)
    assert candidates_in(prepared(polygon), CELL) == {0}


# --- grouping -----------------------------------------------------------------------


def test_grouped_reports_one_zone_only_when_every_candidate_shares_it():
    """``single >= 0`` is what decides whether a cell answers outright or refines, so a
    cell with two zones reported as one would answer one of them without testing."""
    zone_ids = np.array([7, 7, 9], dtype=np.int64)
    cells = np.array([0, 0, 1, 1, 1])
    polys = np.array([0, 1, 0, 1, 2])

    result = {
        cell: (list(p), single) for cell, p, single in grouped(cells, polys, zone_ids)
    }
    assert result[0][1] == 7, "both candidates are zone 7"
    assert result[1][1] == -1, "zone 9 joins them, so the cell is ambiguous"
    assert sorted(result[1][0]) == [0, 1, 2]


def test_grouped_is_empty_for_no_pairs():
    empty = np.empty(0, dtype=np.int64)
    assert grouped(empty, empty, np.array([0], dtype=np.int64)) == []
