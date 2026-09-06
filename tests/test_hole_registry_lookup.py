"""What a boundary polygon's hole ids cost to look up.

``_hole_ids_of`` answers for every candidate polygon that survives the bounding-box
test, and 1,225 of the 1,322 packaged boundary polygons own no hole at all - so the
shape of the *empty* answer is what the lookup path actually pays for. These tests pin
that shape, because it is invisible to the answer-level tests: a generator that raises
and catches a ``KeyError`` and an empty ``range`` are indistinguishable to every caller
except the profiler.
"""

import numpy as np
import pytest

from timezonefinder import TimezoneFinder


@pytest.fixture(scope="module")
def finder() -> TimezoneFinder:
    return TimezoneFinder()


@pytest.fixture(scope="module")
def with_holes(finder: TimezoneFinder) -> int:
    boundary_id = next(iter(sorted(finder.hole_registry)), None)
    assert boundary_id is not None, (
        "the packaged data has no boundary polygon with holes"
    )
    return boundary_id


@pytest.mark.unit
def test_a_polygon_without_holes_answers_an_empty_range(finder: TimezoneFinder) -> None:
    """The majority path, and the one that used to raise and catch a ``KeyError``."""
    without = next(
        i for i in range(finder.nr_of_polygons) if i not in finder.hole_registry
    )
    hole_ids = finder._hole_ids_of(without)
    assert hole_ids == range(0)
    assert not hole_ids, "the emptiness test in inside_of_polygon relies on this"
    assert list(hole_ids) == []


@pytest.mark.unit
def test_a_polygon_with_holes_answers_its_registry_entry(
    finder: TimezoneFinder, with_holes: int
) -> None:
    amount_of_holes, first_hole_id = finder.hole_registry[with_holes]
    hole_ids = finder._hole_ids_of(with_holes)
    assert list(hole_ids) == list(range(first_hole_id, first_hole_id + amount_of_holes))
    assert hole_ids, "a polygon that owns holes must not read as empty"


@pytest.mark.unit
def test_a_numpy_boundary_id_reads_the_same_entry(
    finder: TimezoneFinder, with_holes: int
) -> None:
    """Candidate ids arrive from the shortcut payload as numpy integers."""
    assert finder._hole_ids_of(np.uint16(with_holes)) == finder._hole_ids_of(with_holes)


@pytest.mark.unit
def test_every_registered_polygon_owns_the_holes_it_names(
    finder: TimezoneFinder,
) -> None:
    """The ids stay in range and stay disjoint, which is what the registry means."""
    owned: set[int] = set()
    for boundary_id in finder.hole_registry:
        hole_ids = set(finder._hole_ids_of(boundary_id))
        assert hole_ids, boundary_id
        assert not (hole_ids & owned), (
            f"hole shared with another polygon: {boundary_id}"
        )
        assert max(hole_ids) < finder.nr_of_holes
        owned |= hole_ids
    assert len(owned) == finder.nr_of_holes


@pytest.mark.unit
def test_a_point_inside_a_hole_is_still_excluded(
    finder: TimezoneFinder, with_holes: int
) -> None:
    """The guard must not skip a hole check that has something to check.

    Takes a vertex of an actual hole, nudged inwards, and asserts the owning boundary
    polygon rejects it - which is the answer the empty-range fast path would break.
    """
    for boundary_id in sorted(finder.hole_registry):
        for hole_id in finder._hole_ids_of(boundary_id):
            hole = finder.holes.coords_of(hole_id)
            x, y = int(np.mean(hole[0])), int(np.mean(hole[1]))
            # a hole need not contain its own centroid; the first one that does is
            # enough, and the packaged data offers many
            if finder.holes.pip_with_bbox_check(hole_id, x, y):
                assert not finder.inside_of_polygon(boundary_id, x, y)
                return
    pytest.fail("no packaged hole contains its own centroid")
