"""The per-polygon union of hole bounding boxes, and the predicate that reads it.

``in_any_polygon`` cannot answer "the point is in none of these holes" without
visiting every one of them, and that is the answer on essentially every point that
reaches a hole-owning polygon - so the polygon owning 95 holes used to pay 95 bounding
box tests to establish nothing. ``HoleArray._build_union_bounds`` gives each boundary
polygon one box enclosing all of its holes, so a single test answers for the whole
set, and ``HoleArray.any_contains`` is the whole question in one call.

The risk the union introduces is a *false negative*: a box too small skips a hole that
does contain the point, and the polygon then claims a point it should have excluded.
So these tests check the bounds are exactly the union rather than merely a superset,
and check the predicate itself against the pre-union formulation.
"""

import numpy as np
import pytest

from timezonefinder import TimezoneFinder
from timezonefinder.polygon_array import NEVER_INSIDE
from timezonefinder import utils

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def finder() -> TimezoneFinder:
    return TimezoneFinder(in_memory=True)


def without_union(finder: TimezoneFinder, pid: int, x: int, y: int) -> bool:
    """``inside_of_polygon`` as it read before the union bbox, as the oracle."""
    if finder.boundaries.outside_bbox(pid, x, y):
        return False
    hole_ids = finder._hole_ids_of(pid)
    if hole_ids and finder.holes.in_any_polygon(hole_ids, x, y):
        return False
    return finder.boundaries.pip(pid, x, y)


def test_bounds_are_exactly_the_union_of_the_member_holes(finder):
    assert finder.hole_registry, "the packaged data has no boundary polygon with holes"
    for pid, (amount, first) in finder.hole_registry.items():
        ids = range(first, first + amount)
        # exact, not merely enclosing: a box larger than the union only costs a
        # pointless descent into the loop, but a smaller one loses a hole
        assert finder.holes._union_x0_ints[pid] == min(
            finder.holes.xmin[h] for h in ids
        )
        assert finder.holes._union_x1_ints[pid] == max(
            finder.holes.xmax[h] for h in ids
        )
        assert finder.holes._union_y0_ints[pid] == min(
            finder.holes.ymin[h] for h in ids
        )
        assert finder.holes._union_y1_ints[pid] == max(
            finder.holes.ymax[h] for h in ids
        )


def test_a_hole_less_polygon_carries_a_box_no_query_can_enter(finder):
    holeless = [
        pid for pid in range(len(finder.boundaries)) if pid not in finder.hole_registry
    ]
    assert holeless, "the packaged data has no hole-less boundary polygon"
    # the empty box is what lets the union test stand in for the `dict.get` and the
    # `range` on the majority path, rather than sit in front of them
    for pid in holeless:
        assert finder.holes._union_x0_ints[pid] == NEVER_INSIDE
    assert NEVER_INSIDE > utils.coord2int(180.0)
    assert NEVER_INSIDE <= np.iinfo(np.int32).max


def test_every_hole_is_inside_the_union_of_its_polygon(finder):
    for pid, (amount, first) in finder.hole_registry.items():
        for h in range(first, first + amount):
            assert finder.holes._union_x0_ints[pid] <= finder.holes.xmin[h]
            assert finder.holes._union_x1_ints[pid] >= finder.holes.xmax[h]
            assert finder.holes._union_y0_ints[pid] <= finder.holes.ymin[h]
            assert finder.holes._union_y1_ints[pid] >= finder.holes.ymax[h]


def test_predicate_matches_the_pre_union_formulation_around_every_hole(finder):
    """Dense random coverage of each hole-owning polygon's own bounding box.

    Points are drawn inside the boundary bbox rather than globally: outside it the
    outer test answers first and the hole path is never reached, so a global sample
    would spend itself on the case that cannot regress.
    """
    rng = np.random.default_rng(20260908)
    boundaries = finder.boundaries
    checked = 0
    for pid in finder.hole_registry:
        xs = rng.integers(
            boundaries._xmin_ints[pid], boundaries._xmax_ints[pid] + 1, 250
        )
        ys = rng.integers(
            boundaries._ymin_ints[pid], boundaries._ymax_ints[pid] + 1, 250
        )
        for x, y in zip(xs.tolist(), ys.tolist(), strict=True):
            checked += 1
            assert finder.inside_of_polygon(pid, x, y) == without_union(
                finder, pid, x, y
            ), f"polygon {pid} disagrees at ({x}, {y})"
    assert checked >= 20_000


def test_points_inside_a_hole_are_still_excluded(finder):
    """The union must not let a real hole hit slip through.

    Drawn from inside each hole's own bounding box, which is where a hit can happen at
    all, so this samples the case the union could break rather than the common miss.
    """
    rng = np.random.default_rng(7)
    holes = finder.holes
    excluded = 0
    for pid, (amount, first) in finder.hole_registry.items():
        for h in range(first, first + amount):
            xs = rng.integers(holes._xmin_ints[h], holes._xmax_ints[h] + 1, 40)
            ys = rng.integers(holes._ymin_ints[h], holes._ymax_ints[h] + 1, 40)
            for x, y in zip(xs.tolist(), ys.tolist(), strict=True):
                if holes.pip(h, x, y):
                    assert not finder.inside_of_polygon(pid, x, y), (
                        f"point ({x}, {y}) is in hole {h} of polygon {pid}"
                    )
                    excluded += 1
    assert excluded > 0, "no sampled point landed in a hole; the test proved nothing"


def test_cleanup_releases_the_views(finder_factory=TimezoneFinder):
    tf = finder_factory(in_memory=True)
    holes = tf.holes
    assert holes._union_x0_ints is not None
    tf.cleanup()
    for attr in ("_union_x0_ints", "_union_y1_ints", "union_bounds", "hole_registry"):
        assert not hasattr(holes, attr)
    tf.cleanup()  # idempotent


def test_any_contains_matches_the_unguarded_loop(finder):
    """``any_contains`` must equal the union-free question it replaces."""
    rng = np.random.default_rng(11)
    holes, boundaries = finder.holes, finder.boundaries
    for pid in finder.hole_registry:
        xs = rng.integers(
            boundaries._xmin_ints[pid], boundaries._xmax_ints[pid] + 1, 60
        )
        ys = rng.integers(
            boundaries._ymin_ints[pid], boundaries._ymax_ints[pid] + 1, 60
        )
        for x, y in zip(xs.tolist(), ys.tolist(), strict=True):
            assert holes.any_contains(pid, x, y) == holes.in_any_polygon(
                holes.ids_of(pid), x, y
            )


def test_an_array_without_a_registry_refuses_to_guess(finder):
    """The integrity checks build one to *establish* the registry, so it has none."""
    from timezonefinder.polygon_array import HoleArray

    bare = HoleArray(data_location=finder.holes_dir, boundaries=finder.boundaries)
    with pytest.raises(AttributeError, match="without a hole registry"):
        bare.ids_of(0)
    bare.cleanup()
