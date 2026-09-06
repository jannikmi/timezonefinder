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

pytest.importorskip("line_profiler", reason="prototypes/ needs the `proto` group")

from prototypes.query_stage_profile import (  # noqa: E402
    QUERY_STRATA,
    examined_candidates,
    make_ladder,
)
from tests.auxiliaries import load_benchmark_points  # noqa: E402

# a few hundred points per stratum is enough to reach every branch; the profiler's own
# batch is 2,000 and this is a correctness check, not a measurement
SAMPLE = 300


@pytest.fixture(scope="module")
def tf() -> TimezoneFinder:
    return TimezoneFinder()


@pytest.mark.unit
def test_ladder_binds_no_public_timezonefinder_method(tf: TimezoneFinder) -> None:
    """No rung may reach for a *checked public* accessor of ``TimezoneFinder``.

    ``timezone_at`` calls the unchecked internals (``self._zone_id_of``) and the
    collaborators (``self.zone_names.name_of``, ``self.shortcuts.entry_of``) directly.
    The public wrappers in front of those add id validation that the query path does not
    pay, so a rung binding one prices a call the lookup never makes: ``zone_ids_of`` read
    ~1,685 ns against ~564, and ``zone_name_from_id`` 58-64 ns against 37-38. The
    public/private split on this class exists *because* the two differ in cost, which
    makes the ladder the one caller for which the public name is a bug.

    Asserted structurally, over what ``make_ladder`` actually closes over, so a rung
    added later is covered without anyone remembering this rule.
    """
    closure = inspect.getclosurevars(make_ladder(tf)[-1][1]).nonlocals
    offenders = {
        name: bound.__func__.__name__
        for name, bound in closure.items()
        if inspect.ismethod(bound)
        and bound.__self__ is tf
        and not bound.__func__.__name__.startswith("_")
    }
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
        if entry >= 0:
            assert opened == 0, "a unique-zone cell reaches no candidate list"
            continue
        slice_length = min(
            tf.shortcuts.stop_index_of(entry), len(tf.shortcuts.candidates_of(entry))
        )
        assert 1 <= opened <= slice_length
        candidates = tf.shortcuts.candidates_of(entry)
        x, y = utils.coord2int(lng), utils.coord2int(lat)

        def contains(boundary_id: int, x: int = x, y: int = y) -> bool:
            hole_ids = tf._hole_ids_of(boundary_id)
            return bool(
                not tf.boundaries.outside_bbox(boundary_id, x, y)
                and not (hole_ids and tf.holes.in_any_polygon(hole_ids, x, y))
                and tf.boundaries.pip(boundary_id, x, y)
            )

        # Pinned from both sides, so neither a missing nor a premature ``break``
        # survives: the lookup stops at the first candidate containing the point, so
        # none before the last one opened may contain it, and the last one either
        # contains it or is the end of the slice.
        assert not any(contains(int(b)) for b in candidates[: opened - 1])
        assert contains(int(candidates[opened - 1])) or opened == slice_length
