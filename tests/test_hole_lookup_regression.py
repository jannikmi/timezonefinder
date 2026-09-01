"""The lookup answers hole interiors from the geometry, not from the candidate order.

A hole says "this area is *not* the surrounding zone", and the only points where that
statement can change an answer are the points inside one. This gate walks interior points
of **every** packaged hole and requires the lookup to agree with the geometry itself -
ground truth derived by testing every boundary polygon whose bounding box admits the
point, with holes applied, and without consulting the shortcut index at all.

It is the test that would have caught the mistake behind GH-513: dropping holes was
expected to be answer-preserving because every hole is covered by another zone, and
covered is not reached-first. Removing the hole subsystem moves 1,404 of these points, so
this fails loudly rather than silently returning a neighbour's timezone. See
``contributing/improvements/items/lookup-geometry-and-data-format/gh-513-drop-hole-polygons-entirely.md``.
"""

import numpy as np
import pytest

from timezonefinder import TimezoneFinder, utils

PROBES_PER_HOLE = 8
MAX_REJECTION_TRIES = 8_000
SEED = 17


def _sample_hole_interiors(
    finder: TimezoneFinder, rng: np.random.Generator
) -> list[tuple[int, int, int]]:
    """``(x, y, hole_id)`` interior points of every hole, by rejection sampling."""
    probes: list[tuple[int, int, int]] = []
    for hole_id in range(len(finder.holes)):
        ring = finder.holes.coords_of(hole_id)
        xmin, xmax = int(finder.holes.xmin[hole_id]), int(finder.holes.xmax[hole_id])
        ymin, ymax = int(finder.holes.ymin[hole_id]), int(finder.holes.ymax[hole_id])
        found = 0
        for _ in range(MAX_REJECTION_TRIES):
            if found >= PROBES_PER_HOLE:
                break
            x = int(rng.integers(xmin, xmax + 1))
            y = int(rng.integers(ymin, ymax + 1))
            if utils.inside_polygon(x, y, ring):
                probes.append((x, y, hole_id))
                found += 1
    return probes


def _zone_from_geometry(finder: TimezoneFinder, x: int, y: int) -> set[int]:
    """Every zone containing the point, found by exhaustive search over the polygons.

    The shortcut index is deliberately not used: it is what the assertion is checking, so
    deriving the expected answer from it would compare the lookup against itself.
    """
    candidates = np.nonzero(
        (finder.boundaries.xmin <= x)
        & (x <= finder.boundaries.xmax)
        & (finder.boundaries.ymin <= y)
        & (y <= finder.boundaries.ymax)
    )[0]
    return {
        int(finder.zone_ids[boundary_id])
        for boundary_id in candidates.tolist()
        if finder.inside_of_polygon(boundary_id, x, y)
    }


@pytest.mark.integration
def test_every_hole_interior_is_answered_from_the_geometry():
    finder = TimezoneFinder(in_memory=True)
    probes = _sample_hole_interiors(finder, np.random.default_rng(SEED))
    assert {hole_id for _, _, hole_id in probes} == set(range(len(finder.holes))), (
        "rejection sampling missed a hole entirely - every hole has to be exercised"
    )

    names = finder.timezone_names
    mismatches = []
    for x, y, hole_id in probes:
        expected = _zone_from_geometry(finder, x, y)
        got = finder.timezone_at(lng=utils.int2coord(x), lat=utils.int2coord(y))
        if got is None or names.index(got) not in expected:
            mismatches.append(
                f"hole {hole_id} at lng={utils.int2coord(x)} lat={utils.int2coord(y)}: "
                f"lookup says {got}, the geometry says "
                f"{sorted(names[z] for z in expected)}"
            )
    assert not mismatches, (
        f"{len(mismatches)} of {len(probes)} hole interior points are answered with a "
        f"zone whose geometry does not contain them:\n" + "\n".join(mismatches[:20])
    )
