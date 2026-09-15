#!/usr/bin/env python3

"""Find the batch size at which the batched lookup starts paying, and stops improving.

Why this is not a ``benchmarks/`` suite
---------------------------------------

``benchmarks/test_timezone_finding.py`` measures the batch API at one fixed size
(``BATCH_SIZE``, 2,500) so that two commits can be compared, and its node ids are the
trend chart's join key. The question here is the *shape* of the curve that measurement
takes a single point on, and a sweep would add a node id per rung - fourteen metrics
that are not comparable to each other and that no chart should carry.

It is also the other kind of measurement: two candidates in one working tree rather than
one implementation across commits. That is what ``benchmarks/candidate_comparison.py``
exists for, and what ``docs/benchmarking_methodology.rst`` records three wrong designs
for, so every rung below is one call into that harness rather than a timing loop.

What it measures
----------------

Per rung ``N``, a scalar loop over ``N`` points against one batched call on the same
``N`` points:

* baseline    ``[tf.timezone_at(lng=..., lat=...) for ...]``
* challenger  ``tf.timezone_names_at(lngs=..., lats=...)``

``timezone_names_at`` rather than ``timezone_ids_at`` because there is no public scalar
*id* method: pairing a name-producing loop against an id-producing batch would credit
the batch with skipping the per-point string lookup the baseline paid. ``--api ids``
sweeps the id form as its own run, and the two are never put in one table.

Both candidates are handed the same :class:`PreparedBatch`, whose two representations
are built before the clock starts - a conversion inside either callable would charge one
side for marshalling, and the charge scales with ``N``, which tilts the whole curve.

The crossing is read off the **ratio** within a rung, never off absolute times across
rungs. The two candidates in a rung are measured in one alternating loop against one
shared draw, so drift over the ladder cancels inside each rung instead of bending it.
Saturation is the exception and is read off the batched call's absolute per-point time,
because it asks about that side alone - :func:`saturation` says why, and
:func:`control_spread` is what bounds the drift that choice is exposed to.

Only the acceleration path this environment bound is measured, and it is stamped into
the report rather than asserted - a downstream user's report names their own path.
``make batch-break-even`` asserts ``clang`` on top of that, so the committed page cannot
end up beside its siblings describing a different configuration.

Reporting only, like every other measurement here: nothing in this module fails a build.

Usage::

    uv run python -m scripts.measure_batch_break_even --output tmp/batch-break-even.json
    uv run python -m scripts.measure_batch_break_even --points my.csv --output tmp/mine.json
"""

import argparse
import csv
import json
import random
import statistics
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Final, Literal, NamedTuple, Sequence

import numpy as np

from benchmarks.candidate_comparison import (
    DEFAULT_ROUNDS,
    DEFAULT_THRESHOLD,
    CandidateComparison,
    compare_candidates,
)
from scripts.assert_acceleration_path import active_acceleration_path
from scripts.benchmark_utils import cpu_info, get_system_status
from scripts.configs import DEBUG
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    benchmark_fixture_provenance,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder
from timezonefinder.configs import MAX_LAT_VAL, MAX_LNG_VAL
from timezonefinder.zone_names import NAMES_GATHER_MIN_BATCH

#: The committed point fixtures a sweep can run over, by the name the page uses.
POINT_CLASSES: Final[dict[str, str]] = {
    "random": RANDOM_POINTS_FIXTURE,
    "unique_shortcut": UNIQUE_SHORTCUT_POINTS_FIXTURE,
    "ambiguous_shortcut": AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    "on_land": ON_LAND_POINTS_FIXTURE,
}

#: How a point class is named to a reader. Defined beside the classes themselves so the
#: page and the chart cannot label the same series differently.
POINT_CLASS_LABELS: Final[dict[str, str]] = {
    "random": "uniformly random points",
    "unique_shortcut": "unique-shortcut points",
    "ambiguous_shortcut": "ambiguous-shortcut points",
    "on_land": "on-land points",
}


def point_class_label(point_class: str) -> str:
    """The reader-facing name of a point class, or a tidied form of a custom one."""
    return POINT_CLASS_LABELS.get(point_class, point_class.replace("_", " "))


#: Swept by default. ``random`` is the headline - the only globally representative mix.
#: ``unique_shortcut`` is the ceiling, the stratum where the batch path has the most to
#: amortise and where the measured baseline puts the ~1.6x. ``ambiguous_shortcut`` is
#: deliberately absent: it is where the batch path degenerates to a per-point geometry
#: loop, so it is simultaneously the least informative curve and the slowest to measure.
DEFAULT_POINT_CLASSES: Final[tuple[str, ...]] = ("random", "unique_shortcut")

#: The rungs. Log-spaced, because the interesting region spans four decades and an
#: integer step would spend the whole run where nothing changes.
#:
#: The two rungs around ``NAMES_GATHER_MIN_BATCH`` are the exception, and they are
#: imported rather than written as 127/128: ``ZoneNames.names_of`` switches from a
#: Python loop to a numpy gather exactly there, so a plain 1-2-5 ladder steps over a
#: real discontinuity inside the measured path and renders it as noise between 100 and
#: 200. It is also the most actionable thing this page can show a caller sizing batches.
DEFAULT_LADDER: Final[tuple[int, ...]] = (
    1,
    2,
    5,
    10,
    20,
    50,
    100,
    NAMES_GATHER_MIN_BATCH - 1,
    NAMES_GATHER_MIN_BATCH,
    200,
    500,
    1000,
    2000,
    5000,
)

#: Points each round asks both candidates to answer, held constant across rungs so the
#: curve compares like with like. A round is then tens of milliseconds at every rung -
#: far above timer resolution at ``N = 1``, and short enough that the machine's state is
#: unlikely to change inside one, which is the reasoning behind the harness's own
#: ``DEFAULT_BATCH_SIZE``.
DEFAULT_POINTS_PER_ROUND: Final[int] = 25_000

#: Batched calls a round must contain. Below this the ``min`` over rounds stops being
#: "the least perturbed round" and becomes "the luckiest single call".
MIN_CALLS_PER_ROUND: Final[int] = 4

#: Distinct prepared batches a rung draws from, expressed as a point budget so small
#: rungs get many batches and large ones get a few, and so the pool stays too large to
#: sit in cache. Floored, so even the top rung is not one batch measured 61 times.
POOL_POINT_BUDGET: Final[int] = 100_000
MIN_POOL_BATCHES: Final[int] = 8

#: How close to the asymptote counts as saturated. Above the harness's own
#: ``DEFAULT_THRESHOLD`` on purpose: below that floor a difference is not demonstrable
#: on this workload, so "within tolerance of the asymptote" would be a claim the
#: instrument cannot support. :func:`saturation` rejects anything at or under it.
DEFAULT_SATURATION_TOLERANCE: Final[float] = 0.05

#: How far the scalar baseline's per-point time may spread across rungs before the page
#: says the ladder measured more than one thing. Published, never a gate - the same
#: stance ``render_acceleration_paths`` takes with its shared clang baseline.
#:
#: Much wider than that page's 3 % on purpose. This is the *range* over a dozen separate
#: comparisons, where that is a ratio between two; a single machine's own jitter on this
#: workload is 3-9 % per comparison (``DEFAULT_THRESHOLD``), and the maximum-over-minimum
#: of a dozen such samples reaches into the teens with nothing wrong at all. A measured
#: ladder read 13.1 % with a textbook curve. So this catches gross contamination - a
#: drifting clock, a competing process, a ladder that warmed into a different regime -
#: and nothing finer, which is what a range statistic can honestly do.
CONTROL_SPREAD_THRESHOLD: Final[float] = 0.15

#: Rungs below this are excluded from the control statistic, because the baseline's
#: per-point figure there is structurally inflated rather than noisy.
#:
#: ``compare_candidates`` times a pass over its input items, so every timed item costs a
#: callable dispatch and an answer list beside the lookups. That is a cost per *batch*,
#: which the per-point normalisation spreads as ``h/N`` - measured here at h = 0.209 us
#: per item, i.e. 16.5 % of the scalar baseline at N=1, 1.7 % at N=10, and 0.3-0.8 %
#: across the rungs where break-even actually falls. It therefore does not move the
#: answer, but it does put a real 1/N ramp into the smallest rungs of a curve that is
#: supposed to be flat, and a control that flagged it every run would train its reader to
#: ignore it. Ten is where the term drops under 2 %.
CONTROL_MIN_BATCH_SIZE: Final[int] = 10

BatchApi = Literal["names", "ids"]


class PreparedBatch(NamedTuple):
    """One batch of points, in both candidates' native input forms.

    Built once, at pool time. The scalar loop wants tuples and the batch call wants one
    contiguous ``float64`` array per axis (its documented zero-copy form,
    ``utils.coordinate_arrays``); building either inside a timed callable would charge
    that candidate for marshalling rather than for lookups, and the charge grows with
    ``N``, so it would tilt the curve rather than merely offset it.

    Both candidates receive the *same* object, which is what preserves the harness's
    "one shared draw" property across two candidates needing different shapes.
    """

    points: list[tuple[float, float]]
    lngs: np.ndarray
    lats: np.ndarray


@dataclass(frozen=True)
class BreakEven:
    """Where the batched form starts winning, as far as a discrete ladder can say."""

    #: ``below_ladder`` - already faster at the smallest rung measured.
    #: ``bracketed`` - the crossing lies in ``(lower, upper]``.
    #: ``not_reached`` - no rung is demonstrably faster.
    #: ``no_terminal_run`` - some rungs are faster but the top of the ladder is not, so
    #: nothing is established. Kept distinct from ``not_reached`` because one noisy top
    #: rung is enough to produce it, and calling that "never faster" would contradict a
    #: table full of ``faster`` rows.
    status: Literal["below_ladder", "bracketed", "not_reached", "no_terminal_run"]
    lower: int | None = None
    upper: int | None = None
    #: rungs that read ``faster`` below the terminal run - the signal to re-measure
    #: rather than to read the bracket
    non_monotone: tuple[int, ...] = ()

    @property
    def bracket(self) -> tuple[int, int] | None:
        """The two rungs the crossing lies between, or ``None`` if it is not bracketed.

        The accessor exists so a caller narrows both endpoints in one test instead of
        pairing a ``status`` check with two ``is not None`` checks a type checker cannot
        connect to it.
        """
        if self.lower is None or self.upper is None:
            return None
        return self.lower, self.upper

    def describe(self) -> str:
        if self.status == "below_ladder":
            return f"already faster at the smallest rung measured (N={self.upper})"
        if self.status == "not_reached":
            return "not demonstrably faster at any rung measured"
        if self.status == "no_terminal_run":
            won = ", ".join(f"N={size}" for size in self.non_monotone)
            return f"not established: faster at {won}, but not at the top of the ladder"
        return f"between N={self.lower} and N={self.upper}"


@dataclass(frozen=True)
class Saturation:
    """Where a bigger batch stops buying anything."""

    status: Literal["saturated", "not_reached"]
    tolerance: float
    #: seconds per point the top of the ladder settles at
    reference_seconds: float
    batch_size: int | None = None
    speedup: float | None = None
    verdict: str | None = None

    def describe(self) -> str:
        if self.status == "not_reached":
            return "not reached within the ladder"
        return f"N={self.batch_size} ({self.speedup:.2f}x, {self.verdict})"


@dataclass(frozen=True)
class ControlSpread:
    """How flat the scalar baseline stayed across the ladder.

    The baseline answers the same points with the same method at every rung, so this
    should be flat. Where it is not, the ladder measured something besides the batching
    and a smooth speed-up curve is smooth for the wrong reason. Published, never a gate
    and never a divisor - the rungs are separate experiments and nothing here divides one
    into another.
    """

    fastest: float
    slowest: float
    spread: float
    within_threshold: bool
    threshold: float
    #: rungs below :data:`CONTROL_MIN_BATCH_SIZE` are excluded; see that constant
    min_batch_size: int
    rungs_used: int


# --- reading one stored rung -------------------------------------------------------
#
# These take the stored dict rather than a live object so the renderer can call them on
# a committed JSON run without re-measuring. Note that ``rung["batch_size"]`` (points
# per batched call - this page's subject) and ``rung["comparison"]["batch_size"]``
# (calls per round - what the harness names ``batch_size``) are different numbers: never
# reach for the latter, or every figure comes out off by a factor of N.


def comparison_of(rung: dict[str, Any]) -> CandidateComparison:
    """Rebuild the harness's dataclass, so a page cannot disagree with it on a verdict."""
    return CandidateComparison(**rung["comparison"])


def speedup(rung: dict[str, Any]) -> float:
    """Scalar loop over batched, from the two best rounds. Above 1.0 the batch wins."""
    comparison = comparison_of(rung)
    return comparison.best_baseline / comparison.best_challenger


def per_point_seconds(rung: dict[str, Any], side: str) -> float:
    """Seconds per point for one candidate.

    Normalised by the rung's *actual* ``points_per_round``, never by the target: a rung
    whose size does not divide the target does slightly less work than asked for, and
    dividing by the nominal figure puts a sawtooth into a curve read at a 5 % tolerance.
    """
    return getattr(comparison_of(rung), side) / rung["points_per_round"]


def load_points_csv(path: Path) -> list[tuple[float, float]]:
    """A caller's own coordinates, two columns of ``lng,lat``, an optional header row.

    The point of accepting these: break-even is a property of the workload as much as of
    the machine, because the batch path answers every point of an H3 cell from one
    lookup. A clustered stream - a delivery round, a city - breaks even sooner than the
    uniformly random fixture, and only the caller's own points can say where.
    """
    points: list[tuple[float, float]] = []
    seen_a_row = False
    with open(path, newline="", encoding="utf-8") as handle:
        for line_number, row in enumerate(csv.reader(handle), start=1):
            if not row or row[0].lstrip().startswith("#"):
                continue
            first_row, seen_a_row = not seen_a_row, True
            try:
                point = (float(row[0]), float(row[1]))
            except (IndexError, ValueError):
                # a header is allowed on the first row that is not blank or a comment,
                # rather than on line 1: a file that opens with a comment still has one
                if first_row:
                    continue
                raise ValueError(
                    f"{path}:{line_number}: expected two numeric columns "
                    f"'lng,lat', got {row!r}"
                ) from None
            points.append(point)

    if not points:
        raise ValueError(f"{path} holds no coordinates")
    for index, (lng, lat) in enumerate(points):
        if not (
            -MAX_LNG_VAL <= lng <= MAX_LNG_VAL and -MAX_LAT_VAL <= lat <= MAX_LAT_VAL
        ):
            raise ValueError(
                f"{path}: coordinate {index} is out of range (lng={lng}, lat={lat}). "
                f"Longitude must be in [-{MAX_LNG_VAL}, {MAX_LNG_VAL}] and latitude in "
                f"[-{MAX_LAT_VAL}, {MAX_LAT_VAL}]. Columns are lng first, then lat - a "
                "swapped pair is a valid coordinate over most of the populated world, "
                "so this check is the only thing that can catch it."
            )
    return points


def ladder_for(sizes: Sequence[int], pool_size: int) -> list[int]:
    """The rungs actually measurable against a pool of ``pool_size`` points.

    Capped at half the pool because a batch is drawn *without replacement*: at
    ``N == pool_size`` exactly one batch exists, so the harness would draw the same
    object every round on a fully warm cache - and that rung is what sets the saturation
    reference. Sorted and de-duplicated so a retuned ``NAMES_GATHER_MIN_BATCH`` collapses
    into its neighbour rather than producing a repeated rung.
    """
    cap = pool_size // 2
    rungs = sorted({int(size) for size in sizes if 0 < int(size) <= cap})
    if not rungs:
        raise ValueError(
            f"no requested batch size fits a pool of {pool_size:,} points (the largest "
            f"measurable rung is {cap:,}, half the pool - a batch is drawn without "
            "replacement, and one possible batch is not a sample). Lower --sizes, or "
            "supply more points."
        )
    return rungs


def prepare_pool(
    points: Sequence[tuple[float, float]], batch_size: int, rng: random.Random
) -> list[PreparedBatch]:
    """Distinct batches of ``batch_size`` points each, for one rung.

    ``rng.sample`` - so no point appears twice *inside* a batch. With replacement, the
    points sharing an H3 cell would be resolved once for the whole batch and the saving
    would grow with ``N``: it would fake exactly the curve being measured. Batches
    overlap each other freely, which costs nothing and is what lets the top rungs have
    more than one batch at all.
    """
    nr_batches = max(
        MIN_POOL_BATCHES, min(POOL_POINT_BUDGET // batch_size, len(points))
    )
    pool = []
    for _ in range(nr_batches):
        sample = rng.sample(points, batch_size)
        lngs = np.ascontiguousarray([lng for lng, _ in sample], dtype=np.float64)
        lats = np.ascontiguousarray([lat for _, lat in sample], dtype=np.float64)
        pool.append(PreparedBatch(sample, lngs, lats))
    return pool


def _batch_caller(
    finder: TimezoneFinder, api: BatchApi
) -> Callable[[PreparedBatch], object]:
    if api == "ids":
        return lambda batch: finder.timezone_ids_at(lngs=batch.lngs, lats=batch.lats)
    return lambda batch: finder.timezone_names_at(lngs=batch.lngs, lats=batch.lats)


def _scalar_caller(finder: TimezoneFinder) -> Callable[[PreparedBatch], object]:
    # A list comprehension rather than a bare loop, deliberately: the challenger
    # materialises one answer per point, so a baseline that threw each result away would
    # be charged less allocation than the challenger for the same job.
    timezone_at = finder.timezone_at
    return lambda batch: [timezone_at(lng=lng, lat=lat) for lng, lat in batch.points]


def measure_rung(
    finder: TimezoneFinder,
    points: Sequence[tuple[float, float]],
    batch_size: int,
    api: BatchApi,
    rounds: int,
    points_per_round_target: int,
    seed: int,
) -> dict[str, Any]:
    """One paired comparison at one batch size."""
    calls_per_round = points_per_round_target // batch_size
    if calls_per_round < MIN_CALLS_PER_ROUND:
        raise ValueError(
            f"batch size {batch_size:,} leaves only {calls_per_round} batched call(s) "
            f"per round at --points-per-round {points_per_round_target:,}, below the "
            f"{MIN_CALLS_PER_ROUND} this harness requires: with fewer, the minimum over "
            "rounds stops being the least perturbed round and becomes the luckiest "
            f"single call. Raise --points-per-round to at least "
            f"{batch_size * MIN_CALLS_PER_ROUND:,}, or drop this rung from --sizes."
        )

    pool = prepare_pool(points, batch_size, random.Random(seed + batch_size))
    comparison = compare_candidates(
        ("scalar loop", _scalar_caller(finder)),
        (
            "timezone_ids_at" if api == "ids" else "timezone_names_at",
            _batch_caller(finder, api),
        ),
        pool,
        rounds=rounds,
        batch_size=calls_per_round,
        seed=seed,
    )
    return {
        # points per batched call - the subject of this whole measurement
        "batch_size": batch_size,
        # what the harness calls `batch_size`; kept under its own name so nothing
        # downstream reaches for the dataclass field and reports it as a batch size
        "calls_per_round": calls_per_round,
        # the normaliser: what a round actually answered, not what it was asked for
        "points_per_round": calls_per_round * batch_size,
        "pool_batches": len(pool),
        "comparison": asdict(comparison),
    }


def break_even(rungs: Sequence[dict[str, Any]]) -> BreakEven:
    """Where the batched form starts winning and keeps winning.

    The answer is the *terminal run* of ``faster`` rungs, not the first ``faster`` rung:
    a single lucky crossing that falls back at the next rung must not fix the bracket.

    It is deliberately an interval rather than a number. A discrete ladder plus a
    threshold verdict cannot locate a crossing point, and interpolating one would invent
    precision the instrument does not have. Rungs *inside* the bracket typically read
    ``no difference`` or ``unresolved``; that is what a bracket is, not a broken run.
    """
    verdicts = [comparison_of(rung).verdict for rung in rungs]
    terminal = len(verdicts)
    while terminal > 0 and verdicts[terminal - 1] == "faster":
        terminal -= 1

    won_below = tuple(
        rungs[index]["batch_size"]
        for index in range(terminal)
        if verdicts[index] == "faster"
    )
    if terminal == len(verdicts):
        # The terminal run is empty: the ladder does not end in a win. Which of the two
        # answers that is depends on whether anything won at all - a ladder where the
        # top rung alone came out unresolved has plenty of faster rungs, and reporting
        # it as "never faster" would contradict its own table.
        if won_below:
            return BreakEven("no_terminal_run", non_monotone=won_below)
        return BreakEven("not_reached")
    if terminal == 0:
        return BreakEven("below_ladder", upper=rungs[0]["batch_size"])
    return BreakEven(
        "bracketed",
        lower=rungs[terminal - 1]["batch_size"],
        upper=rungs[terminal]["batch_size"],
        non_monotone=won_below,
    )


def saturation(
    rungs: Sequence[dict[str, Any]],
    tolerance: float = DEFAULT_SATURATION_TOLERANCE,
) -> Saturation:
    """The smallest rung already at the ladder's asymptote, and staying there.

    Two steps, and the first one is not optional. **Establish that the ladder reached an
    asymptote at all** before naming where: the top two rungs differ in size by a factor
    of several, so if they still disagree the curve is falling off the end of the ladder
    and there is nothing to be the smallest rung *of*. Reported as ``not_reached``,
    which is the honest answer and is not the same as "saturates at the top rung".

    Only then is a reference taken, as the *median* of the top three per-point times
    rather than the minimum over the ladder: a minimum over a dozen noisy samples is
    biased low, which would push the answer later or off the ladder entirely.

    Every larger rung must also be inside the tolerance, so one lucky dip at a small
    rung cannot qualify it.

    Read off the batched call's **absolute** per-point time rather than off the speed-up
    ratio, unlike :func:`break_even`. Saturation asks whether a bigger batch still buys
    anything, which is a property of the batched side alone; the ratio would mix in the
    scalar baseline's own noise. A measured run showed why: between N=1,000 and N=2,000
    on the unique-shortcut stratum the ratio moved 2.9 % while the batched per-point time
    moved 0.2 % - the whole difference was the scalar loop. The cost of using an absolute
    quantity is exposure to drift across rungs, which is exactly what
    :func:`control_spread` is published to bound.
    """
    if tolerance <= DEFAULT_THRESHOLD:
        raise ValueError(
            f"saturation tolerance {tolerance} is at or under the candidate harness's "
            f"own threshold ({DEFAULT_THRESHOLD}), below which a difference on this "
            "workload is not demonstrable at all - so 'within tolerance of the "
            "asymptote' would be a claim the instrument cannot support."
        )
    if len(rungs) < 3:
        raise ValueError(
            f"saturation needs at least 3 rungs to take a reference from, got "
            f"{len(rungs)}"
        )

    per_point = [per_point_seconds(rung, "best_challenger") for rung in rungs]
    reference = statistics.median(per_point[-3:])

    # Has the curve stopped moving at all? The top two rungs differ in size by a factor
    # of several, so if the per-point time still falls between them the asymptote is
    # past the end of the ladder. Without this check the answer is never `not_reached`:
    # on any decreasing curve the median of the top three *is* the second-from-last
    # value, so that rung would always trivially qualify and the function would report
    # saturation for a run that plainly had not saturated.
    top, second = max(per_point[-2:]), min(per_point[-2:])
    if top / second - 1.0 > tolerance:
        return Saturation(
            status="not_reached", tolerance=tolerance, reference_seconds=reference
        )

    ceiling = reference * (1.0 + tolerance)

    for index in range(len(per_point)):
        if all(later <= ceiling for later in per_point[index:]):
            rung = rungs[index]
            comparison = comparison_of(rung)
            return Saturation(
                status="saturated",
                tolerance=tolerance,
                reference_seconds=reference,
                batch_size=rung["batch_size"],
                speedup=speedup(rung),
                verdict=comparison.verdict,
            )
    return Saturation(
        status="not_reached", tolerance=tolerance, reference_seconds=reference
    )


def control_spread(
    rungs: Sequence[dict[str, Any]],
    threshold: float = CONTROL_SPREAD_THRESHOLD,
    min_batch_size: int = CONTROL_MIN_BATCH_SIZE,
) -> ControlSpread:
    """How far the scalar baseline's per-point time moved across the ladder.

    Rungs under ``min_batch_size`` are left out: their baseline carries the harness's
    per-item cost divided by a very small N, which is a known structural term rather
    than evidence of anything (:data:`CONTROL_MIN_BATCH_SIZE`).
    """
    per_point = [
        per_point_seconds(rung, "best_baseline")
        for rung in rungs
        if rung["batch_size"] >= min_batch_size
    ]
    if not per_point:
        raise ValueError(
            f"no rung at or above N={min_batch_size} to take a control reading from; "
            f"the ladder tops out at {max(r['batch_size'] for r in rungs)}"
        )
    fastest, slowest = min(per_point), max(per_point)
    spread = slowest / fastest - 1.0
    return ControlSpread(
        fastest,
        slowest,
        spread,
        spread <= threshold,
        threshold,
        min_batch_size,
        len(per_point),
    )


def measure_sweep(
    finder: TimezoneFinder,
    point_class: str,
    points: Sequence[tuple[float, float]],
    points_source: str,
    sizes: Sequence[int],
    api: BatchApi,
    rounds: int,
    points_per_round_target: int,
    seed: int,
) -> dict[str, Any]:
    """Every rung of one point class."""
    rungs_requested = ladder_for(sizes, len(points))
    print(
        f"  {point_class}: {len(points):,} points, "
        f"{len(rungs_requested)} rungs up to N={rungs_requested[-1]:,}",
        file=sys.stderr,
    )
    rungs = []
    for batch_size in rungs_requested:
        print(f"    N={batch_size:<6,}", end="", file=sys.stderr, flush=True)
        rung = measure_rung(
            finder,
            points,
            batch_size,
            api,
            rounds,
            points_per_round_target,
            seed,
        )
        print(f" {speedup(rung):.3f}x  {comparison_of(rung).verdict}", file=sys.stderr)
        rungs.append(rung)
    return {
        "point_class": point_class,
        "points_source": points_source,
        "pool_size": len(points),
        "ladder_cap": len(points) // 2,
        "rungs": rungs,
    }


def build_report(
    sweeps: list[dict[str, Any]],
    api: BatchApi,
    in_memory: bool,
    rounds: int,
    points_per_round_target: int,
    seed: int,
    custom_points: bool,
) -> dict[str, Any]:
    """Assemble the JSON the renderer draws and tabulates.

    Each comparison is stored as the fields :class:`CandidateComparison` is built from
    rather than as a rendered verdict, exactly as ``scripts.measure_acceleration_paths``
    does, so the renderer reconstructs the dataclass and reuses its agreement rule. The
    derived answers - break-even, saturation, the control spread - are *not* stored
    either: the renderer imports the functions above, so the page and this script's
    stdout cannot drift apart.
    """
    timezonefinder_info: dict[str, Any] = {
        **get_system_status(),
        "acceleration_path": active_acceleration_path(),
        "in_memory": in_memory,
        "scalar_api": "timezone_at",
        "batch_api": "timezone_ids_at" if api == "ids" else "timezone_names_at",
        "points_per_round_target": points_per_round_target,
        "rounds": rounds,
        "seed": seed,
        "names_gather_min_batch": NAMES_GATHER_MIN_BATCH,
        "saturation_tolerance": DEFAULT_SATURATION_TOLERANCE,
        "control_spread_threshold": CONTROL_SPREAD_THRESHOLD,
        "control_spread_min_batch_size": CONTROL_MIN_BATCH_SIZE,
    }
    if not custom_points:
        # only meaningful for the committed fixtures; a caller's own CSV has no
        # fixture version, and stamping a stale one would be worse than stamping none
        timezonefinder_info.update(benchmark_fixture_provenance())
    return {
        "machine_info": {"cpu": cpu_info(), "timezonefinder": timezonefinder_info},
        "sweeps": sweeps,
    }


def print_summary(report: dict[str, Any]) -> None:
    """The stdout block.

    Written out rather than delegated to ``CandidateComparison.render()``: that method
    prints its ``batch_size`` as "inputs", which on this measurement are *batches*, and
    the one number a reader of this script wants is points per call.
    """
    info = report["machine_info"]["timezonefinder"]
    print(
        f"\n{info['batch_api']} against a {info['scalar_api']} loop "
        f"({info['acceleration_path']}, "
        f"{'in memory' if info['in_memory'] else 'memory mapped'}, "
        f"{info['rounds']} rounds x ~{info['points_per_round_target']:,} points)\n"
    )
    for sweep in report["sweeps"]:
        rungs = sweep["rungs"]
        control = control_spread(rungs)
        print(f"  --- {sweep['point_class']} ({sweep['points_source']}) ---")
        print(
            f"  {'N':>6} {'scalar':>10} {'batched':>10} {'speed-up':>9} {'verdict':>14}"
        )
        for rung in rungs:
            comparison = comparison_of(rung)
            print(
                f"  {rung['batch_size']:>6,} "
                f"{per_point_seconds(rung, 'best_baseline') * 1e6:>8.3f}us "
                f"{per_point_seconds(rung, 'best_challenger') * 1e6:>8.3f}us "
                f"{speedup(rung):>8.3f}x {comparison.verdict:>14}"
            )
        print(f"  break-even : {break_even(rungs).describe()}")
        print(f"  saturation : {saturation(rungs).describe()}")
        print(
            f"  control    : scalar loop spread {control.spread * 100:.1f} % across "
            f"{control.rungs_used} rungs at or above N={control.min_batch_size} "
            f"({'ok' if control.within_threshold else 'ABOVE THRESHOLD'})\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Sweep the batched lookup against a scalar loop over a ladder of batch "
            "sizes, to find where batching starts paying and where it stops improving."
        )
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Path to write the JSON report to"
    )
    parser.add_argument(
        "--points",
        type=Path,
        help=(
            "CSV of your own coordinates, two columns 'lng,lat'. Break-even depends on "
            "how clustered the input is, so this is how to get the number for your own "
            "workload. Default: the committed point fixtures."
        ),
    )
    parser.add_argument(
        "--point-classes",
        default=",".join(DEFAULT_POINT_CLASSES),
        help=(
            f"committed fixtures to sweep, comma-separated, one of "
            f"{', '.join(POINT_CLASSES)} (default: {','.join(DEFAULT_POINT_CLASSES)}). "
            "Ignored with --points."
        ),
    )
    parser.add_argument(
        "--sizes",
        default=",".join(str(size) for size in DEFAULT_LADDER),
        help="comma-separated batch sizes to measure (default: the log-spaced ladder)",
    )
    parser.add_argument(
        "--api",
        choices=("names", "ids"),
        default="names",
        help=(
            "which batch method to sweep. 'names' (default) is the like-for-like pair "
            "against a timezone_at loop; 'ids' skips the per-point string lookup the "
            "scalar loop still pays, so read it as a bound rather than as a pair."
        ),
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=DEFAULT_ROUNDS,
        help=f"paired rounds per rung (default: {DEFAULT_ROUNDS})",
    )
    parser.add_argument(
        "--points-per-round",
        type=int,
        default=DEFAULT_POINTS_PER_ROUND,
        help=(
            "points each round answers, held constant across rungs so the curve "
            f"compares like with like (default: {DEFAULT_POINTS_PER_ROUND:,})"
        ),
    )
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help=(
            "load the coordinate data into memory instead of mapping it. Default is "
            "the mapped mode, which is what a plain install runs."
        ),
    )
    parser.add_argument("--seed", type=int, default=0, help="RNG seed (default: 0)")
    args = parser.parse_args()

    if DEBUG:
        # the same guard benchmarks/conftest.py and measure_query_latency.py apply
        raise RuntimeError(
            "scripts.configs.DEBUG is True, which overrides SHORTCUT_H3_RES to a much "
            "coarser resolution. That changes how many points reach the geometry at "
            "all - which is simultaneously this measurement's asymptote and its "
            "crossing point - so a sweep taken under DEBUG must never be published."
        )

    sizes = [int(size) for size in args.sizes.split(",") if size.strip()]
    if args.points:
        sources = [(args.points.name, str(args.points), load_points_csv(args.points))]
    else:
        names = [name.strip() for name in args.point_classes.split(",") if name.strip()]
        unknown = [name for name in names if name not in POINT_CLASSES]
        if unknown:
            parser.error(
                f"unknown point class(es) {', '.join(unknown)}. "
                f"Choose from: {', '.join(POINT_CLASSES)}"
            )
        sources = [
            (name, POINT_CLASSES[name], load_benchmark_points(POINT_CLASSES[name]))
            for name in names
        ]

    finder = TimezoneFinder(in_memory=args.in_memory)
    try:
        # One finder for the whole run, warmed with a call at or above
        # NAMES_GATHER_MIN_BATCH: ZoneNames builds its gather lookup array lazily on the
        # first such call, so whichever rung triggered it would otherwise pay a one-off
        # array build that every rung below it never pays.
        warmup = sources[0][2][:NAMES_GATHER_MIN_BATCH]
        finder.timezone_names_at(
            lngs=np.ascontiguousarray([lng for lng, _ in warmup], dtype=np.float64),
            lats=np.ascontiguousarray([lat for _, lat in warmup], dtype=np.float64),
        )

        sweeps = [
            measure_sweep(
                finder,
                point_class,
                points,
                points_source,
                sizes,
                args.api,
                args.rounds,
                args.points_per_round,
                args.seed,
            )
            for point_class, points_source, points in sources
        ]
    finally:
        finder.cleanup()

    report = build_report(
        sweeps,
        args.api,
        args.in_memory,
        args.rounds,
        args.points_per_round,
        args.seed,
        custom_points=bool(args.points),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print_summary(report)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
