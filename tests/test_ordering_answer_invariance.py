"""What a regenerated shortcut index may and may not change about an answer.

Reordering a cell's candidates must not move a ``TimezoneFinder`` answer, while a
``TimezoneFinderL`` suggestion *is* that order. Neither is a property of the lookup,
which reads the order twice over - it returns the first candidate containing the
point, and past the stop index returns the final zone with no test at all - so both
rest on what ``scripts/shortcut_ordering.py`` is willing to emit.

Asserted here against the real lookup rather than a model of it, because the
converter-side guards in ``tests/test_shortcut_ordering.py`` cover the orders the
converter produces and not what the query does with one:
``test_fixed_zone_precedence_preserves_every_hit_pattern`` compares two orders
through a hit-pattern helper written in the test, so the untested-tail shortcut
could change meaning without failing it.
"""

import random

import h3.api.numpy_int as h3
import numpy as np
import pytest

from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinderL, utils
from timezonefinder.configs import SHORTCUT_H3_RES
from timezonefinder.shortcut_index import ABSENT, get_last_change_idx

pytestmark = pytest.mark.unit

# One seed, so a failure names a reproducible permutation rather than a lucky draw.
PERMUTATION_SEED = 20260913

# Per cell, for the unconditional invariant: enough to catch an order dependence,
# few enough that the point-in-polygon work stays a unit test.
PERMUTATIONS_PER_CELL = 8


@pytest.fixture(scope="module")
def ambiguous_cells(tf) -> list[tuple[float, float, int]]:
    """The committed ambiguous-cell points, with the shortcut entry each one hits.

    Points rather than cells, because the guarantee is about answers: a cell whose
    candidates were reordered is only interesting where some query reads them.
    """
    cells = []
    for lng, lat in load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE):
        entry = tf.shortcuts.entry_of(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES))
        if entry < 0 and entry != ABSENT:
            cells.append((lng, lat, entry))
    assert cells, "the ambiguous-point fixture reached no multi-zone cell"
    return cells


def zone_blocks(tf, candidates: np.ndarray) -> list[list[int]]:
    """The candidate list split into its runs of one zone, in stored order."""
    blocks: list[list[int]] = []
    for boundary_id in candidates.tolist():
        zone_id = tf._zone_id_of(boundary_id)
        if blocks and tf._zone_id_of(blocks[-1][0]) == zone_id:
            blocks[-1].append(boundary_id)
        else:
            blocks.append([boundary_id])
    return blocks


def within_zone_permutation(
    tf, candidates: np.ndarray, rng: random.Random
) -> np.ndarray:
    """Shuffle each zone's polygons, leaving the sequence of zones untouched."""
    shuffled: list[int] = []
    for block in zone_blocks(tf, candidates):
        block = block.copy()
        rng.shuffle(block)
        shuffled.extend(block)
    return np.array(shuffled, dtype=candidates.dtype)


def answer(tf, candidates: np.ndarray, lng: float, lat: float) -> int:
    """The zone the real lookup returns for this candidate order.

    The stop index is recomputed from the order rather than read from the index,
    because a permutation is exactly what invalidates the stored one.
    """
    zone_ids = np.array([tf._zone_id_of(pid) for pid in candidates.tolist()])
    return tf._zone_id_among(candidates, get_last_change_idx(zone_ids), lng, lat)


def test_shuffling_a_zones_own_polygons_cannot_move_the_answer(tf, ambiguous_cells):
    """The structural half of the guarantee, through the query itself.

    Holds without consulting any geometry: the zone sequence is what decides, and a
    within-zone shuffle leaves it alone. This is the reordering the converter permits
    for every cell its geometric gate refuses, so it carries the guarantee for the
    cells where the certified argument is unavailable.
    """
    rng = random.Random(PERMUTATION_SEED)
    moved = 0
    for lng, lat, entry in ambiguous_cells:
        candidates = tf.shortcuts.candidates_of(entry)
        permuted = within_zone_permutation(tf, candidates, rng)
        moved += not np.array_equal(permuted, candidates)
        assert answer(tf, permuted, lng, lat) == answer(tf, candidates, lng, lat), (
            f"({lng}, {lat}): {permuted.tolist()} answers differently from "
            f"{candidates.tolist()}"
        )
    assert moved, (
        "no cell in the fixture has a zone holding two candidates, so this asserted "
        "nothing about shuffling - the guarantee needs a multi-polygon zone to be real"
    )


def test_promoting_another_zone_to_the_tail_does_move_answers(tf, ambiguous_cells):
    """The guarantee is not vacuous: order does decide, absent the converter's care.

    Rotating the zone blocks hands the untested tail to a different zone. Without a
    case that changes an answer, the test above would pass on a lookup that had
    stopped reading the order at all, and the documented promise would be describing
    nothing.
    """
    changed = 0
    for lng, lat, entry in ambiguous_cells:
        candidates = tf.shortcuts.candidates_of(entry)
        blocks = zone_blocks(tf, candidates)
        if len(blocks) < 2:
            continue
        rotated = np.array(
            [pid for block in blocks[1:] + blocks[:1] for pid in block],
            dtype=candidates.dtype,
        )
        changed += answer(tf, rotated, lng, lat) != answer(tf, candidates, lng, lat)
    assert changed, (
        "no cross-zone rotation changed any answer, so these points cannot witness "
        "the order-sensitivity the converter's gate exists to contain"
    )


def test_the_lightweight_finder_answers_the_final_candidates_zone(tf, ambiguous_cells):
    """``TimezoneFinderL`` *is* the stored order, which is why a rebuild can move it.

    Pinned because its answer is documented as stable only for a fixed dataset, and
    that is only true while the answer comes from the order rather than the geometry.
    """
    finder = TimezoneFinderL()
    for lng, lat, entry in ambiguous_cells:
        last = tf.shortcuts.candidates_of(entry)[-1]
        expected = tf.zone_names.name_of(tf._zone_id_of(last))
        assert finder.timezone_at(lng=lng, lat=lat) == expected


def test_a_point_inside_a_single_zone_survives_any_permutation(tf, ambiguous_cells):
    """The invariant that survives every reordering, unconditionally.

    Where the candidates containing a point all belong to one zone, that zone is what
    the geometry decides, so *any* permutation returns it - including the cross-zone
    rotations the test above shows can otherwise move an answer, and whether the loop
    tests the containing polygon or reaches its zone as the untested tail. This is the
    invariant that holds even for a cell the converter's geometric gate refuses.
    """
    rng = random.Random(PERMUTATION_SEED)
    checked = 0
    for lng, lat, entry in ambiguous_cells:
        candidates = tf.shortcuts.candidates_of(entry)
        x, y = utils.coord2int(lng), utils.coord2int(lat)
        containing = {
            tf._zone_id_of(pid)
            for pid in candidates.tolist()
            if tf.inside_of_polygon(pid, x, y)
        }
        if len(containing) != 1:
            continue
        checked += 1
        expected = containing.pop()
        for _ in range(PERMUTATIONS_PER_CELL):
            shuffled = candidates.tolist()
            rng.shuffle(shuffled)
            permuted = np.array(shuffled, dtype=candidates.dtype)
            assert answer(tf, permuted, lng, lat) == expected, (
                f"({lng}, {lat}): {permuted.tolist()} moved an answer the geometry "
                "decides on its own"
            )
    assert checked, (
        "no fixture point was contained by a single zone's candidates, so the "
        "unconditional invariant went unexercised"
    )
