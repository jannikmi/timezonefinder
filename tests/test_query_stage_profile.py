"""Keep the stage ladder faithful to the lookup it copies.

`prototypes/query_stage_profile.py` is the only per-stage attribution this repository
has, so every performance item's rank is read off it. It is a *hand-written copy* of
`TimezoneFinder.timezone_at`, and a copy drifts in ways no number reveals: a rung that
binds the wrong accessor, or opens more candidates than the lookup does, still produces
a plausible table. Both have happened - see finding 10 in that module - which is why the
two invariants are asserted here rather than left to the next reader of the numbers.

The exploratory code around them is deliberately untested; these two properties are not
exploratory, because contributor memory quotes the shares they decide.
"""

import inspect

import pytest

from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import SHORTCUT_H3_RES
from timezonefinder.shortcut_index import ABSENT

pytest.importorskip("line_profiler", reason="prototypes/ needs the `proto` group")

from prototypes.query_stage_profile import (  # noqa: E402
    BATCH_SIZE,
    QUERY_STRATA,
    examined_candidates,
    make_ladder,
)
from tests.auxiliaries import load_benchmark_points  # noqa: E402

# The profiler's own batch, not a sample of it. A correct and a run-to-the-end count
# differ on very few points - 40 of 2,000 on the ambiguous stratum, 10 on ``on_land``,
# 3 on ``random``, 0 on ``unique`` - so a 300-point sample left ``random`` with a single
# differing point and ``on_land`` with none, and two of the four parametrizations could
# not fail on a defective helper at all. The whole file still runs in ~0.1 s.
SAMPLE = BATCH_SIZE


@pytest.fixture(scope="module")
def tf() -> TimezoneFinder:
    return TimezoneFinder()


@pytest.mark.unit
def test_ladder_binds_no_public_timezonefinder_method(tf: TimezoneFinder) -> None:
    """No rung may reach for a *checked public* accessor of ``TimezoneFinder``.

    ``timezone_at`` calls the unchecked internals (``self._zone_id_of``) and the
    collaborators (``self.zone_names.name_of``, ``self.shortcuts.entry_of``) directly.
    The public wrappers in front of those add id validation that the query path does not
    pay, so a rung binding one prices a call the lookup never makes: the
    ``zone_name_from_id`` rung read 58-64 ns for a call costing 37-38. The
    public/private split on this class exists *because* the two differ in cost, which
    makes the ladder the one caller for which the public name is a bug. The deleted
    ``zone_ids_of`` rung carried the same mistake, which is why this is asserted rather
    than remembered.

    Asserted structurally, over what ``make_ladder`` actually closes over, and over
    *every* rung rather than the last one: a rung's ``co_freevars`` lists only the names
    that rung references, so a mis-bound accessor used by one new rung is invisible from
    any other.
    """
    offenders = {}
    for name, rung in make_ladder(tf):
        for var, bound in inspect.getclosurevars(rung).nonlocals.items():
            if (
                inspect.ismethod(bound)
                and bound.__self__ is tf
                and not bound.__func__.__name__.startswith("_")
            ):
                offenders[f"{name}:{var}"] = bound.__func__.__name__
    assert not offenders, (
        f"stage-ladder rungs bind public TimezoneFinder methods {offenders}; "
        "bind the internal accessor or the collaborator that timezone_at calls"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "stratum,fixture", QUERY_STRATA, ids=[s for s, _ in QUERY_STRATA]
)
def test_examined_candidates_matches_the_lookup(
    tf: TimezoneFinder, stratum: str, fixture: str
) -> None:
    """The count handed to the geometry rungs is the lookup's own loop trip count.

    ``s8_bbox`` and ``s9_holes`` run no point-in-polygon test, so they cannot discover
    the ``break`` that ends the real loop on a match; left to run to ``stop_index_of``
    they open ~2 % more candidates than the lookup does, overstating themselves and
    understating ``boundary PIP``, which is the difference above them. This pins the
    count they are given to the two facts it has to sit between: never zero where the
    lookup opens a candidate, and never past the candidate slice.
    """
    from h3.api import numpy_int as h3

    points = load_benchmark_points(fixture)[:SAMPLE]
    counts = examined_candidates(tf, points)
    assert len(counts) == len(points)

    for (lng, lat), opened in zip(points, counts, strict=True):
        lng, lat = utils.validate_coordinates(lng, lat)
        entry = tf.shortcuts.entry_of(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES))
        if entry >= 0 or entry == ABSENT:
            assert opened == 0, "these two entries answer without opening a candidate"
            continue
        slice_length = min(
            tf.shortcuts.stop_index_of(entry), len(tf.shortcuts.candidates_of(entry))
        )
        assert 1 <= opened <= slice_length
        candidates = tf.shortcuts.candidates_of(entry)
        x, y = utils.coord2int(lng), utils.coord2int(lat)
        # ``inside_of_polygon`` is what the lookup's own loop calls, so this asserts the
        # loop and not a re-derivation of the predicate inside it
        contains = tf.inside_of_polygon

        # Pinned from both sides, so neither a missing nor a premature ``break``
        # survives: the lookup stops at the first candidate containing the point, so
        # none before the last one opened may contain it, and the last one either
        # contains it or is the end of the slice.
        assert not any(contains(int(b), x, y) for b in candidates[: opened - 1])
        assert contains(int(candidates[opened - 1]), x, y) or opened == slice_length
