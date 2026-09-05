"""Attribute a ``timezone_at`` query to its individual stages, per backend.

Several proposed optimisations are each justified by an assumption about which stage of
a lookup dominates - a batch API by per-call overhead, a native candidate loop by
per-polygon FFI marshalling, better shortcut ordering by the polygon loop. This script
measures the breakdown so those assumptions stop being assumptions.

No instrument is unbiased here, so there are three, chosen to fail differently, and
the report leads with the one that measures the *real* function untouched.

* **Exact counts x sampled share** (primary). Hit counts come from ``line_profiler``,
  whose timings are unusable (below) but whose *counts* are exact and invariant under
  that perturbation - deoptimising the interpreter does not change how many times a line
  runs. The time share comes from an ``ITIMER_REAL`` signal sampler, which installs no
  tracing hooks. Neither half carries the other's bias::

      ns per query = sampled share x untouched wall clock / queries
      ns per hit   = ns per query / exact hits per query

  Wall clock rather than ``ITIMER_PROF`` on purpose: CPU-time sampling hides memory
  stalls, and the mapped coordinate accessor (finding 5) is one. Attribution is to
  *blocks* of lines, because a signal is delivered at the next bytecode boundary, so a
  long call's time can land on the following line - a skid that cancels inside a block
  and does not across one. Measured overhead: 0.3-3.7%, printed per stratum rather than
  claimed, against an unsampled *mean* over the same loop. (Against the unsampled *min*
  it reads 8-16%, which charges the sampler for the machine's own 3-9% jitter; the
  reconciliation line prints both so the comparison cannot be made wrongly.)
* **Stage ladder** (for splits inside a block, and for the ~1 us strata where no
  profiler resolves anything). A series of prefixes of ``TimezoneFinder.timezone_at``,
  each executing the real code up to stage k and stopping. The cost of stage k is
  ``T_k - T_(k-1)``. Nothing is instrumented, so nothing is distorted; the prices are
  that the ladder is a *copy* of the lookup - which the ``timezone_at`` row at the
  bottom of every table cross-checks against the real thing - and that a stage measured
  as the difference of two large numbers is noise (see the ``ffi.from_buffer`` note).
* **line_profiler** (``--line-profile``, corroboration only). Its cost is not a per-line
  probe that could be subtracted off: enabling it deoptimises the whole interpreter, so
  code that never calls the profiled function slows down too. Measured here, with only
  ``timezone_at`` registered, ``validate_coordinates`` goes 284 -> 2,251 ns and
  ``h3.latlng_to_cell`` 390 -> 1,090 ns in loops that call neither, and both revert when
  it is switched off. The inflation is therefore non-uniform by stage type - ~8x for a
  pure-Python stage, ~2.8x for a C-extension one, ~1x for time spent inside numba or the
  C extension, which the interpreter never sees - so it shifts attribution away from
  geometry and towards the Python prologue. That is the exact ratio this script exists to
  settle, which is why it is not the primary instrument. Read the *ordering* of its
  lines; never a share-of-total.

Both backends must be measured. ``timezonefinder/utils.py`` binds the point-in-polygon
implementation at *import* time and numba wins whenever it is importable, so::

    # numba (what a dev checkout runs)
    PYTHONPATH=. uv run python prototypes/query_stage_profile.py

    # clang (what a plain `pip install timezonefinder` runs, and what CI tracks)
    PYTHONPATH=. uv run --isolated --no-group numba --group proto --group test \
        python prototypes/query_stage_profile.py

``--in-memory`` repeats either of those against ``TimezoneFinder(in_memory=True)``,
which is worth running: the two coordinate access modes differ by more than the
backends do (see finding 5).

Inputs are the committed fixtures in ``tests/fixtures/benchmarks/``, so two runs of the
same commit execute the same workload.


FINDINGS (2026-09-05, Apple arm64, Python 3.14.2, data 2026c, fixture set v3)

Re-taken when the candidate loop stopped reading its bounding-box columns and vertex
counts through numpy indexing, which moves three of the rungs below. The ladder and
block tables are **two** runs of this script on one machine on one day - both backends,
``in_memory=False``, the tracked configuration - so the in-memory columns that used to
sit beside them are gone rather than carried forward from an older tree; the two modes
last read within ~2 % of each other on every stratum. Every figure is comparable with
the others here and with nothing else. Where a *before* is quoted it is the
same script run against `origin/master` on the same machine, the same day and **the same
interpreter**, which is the part that is easy to get wrong: see the interpreter note at
the end.

These are one machine's, and the three kinds of figure below do not travel equally.
A *hit count* is a property of the code rather than the hardware and survives any
move - 1.05 candidates per ambiguous query, one FFI crossing per candidate on clang
- so state what a change removes as a count first. A *share* travels as an order of
magnitude only: the stages are bound by different resources (memory latency for the
mapped fetch, interpreter dispatch for the Python prologue, FP throughput for the
kernel), so another machine re-weights them against each other. Absolute
*nanoseconds* travel nowhere, and are not comparable with CI's or with a report
page's. One further correction before comparing anything: read the clang /
``in_memory=False`` column, which is what a plain install in a constrained container
runs and what CI tracks for that reason. The ``random`` stratum is the
workload-representative one and is measured here directly, so rank on it rather than
converting an ambiguous-stratum share by hand.

All figures are nanoseconds per query. Ladder figures are the min over 15 passes of
2,000 fixture points; the ``real`` row is ``tf.timezone_at(lng=, lat=)`` itself, and the
gap above it is the bound-method call the ladder does not pay.

Counts x sampled share, over the real function with nothing attached to it. The sampler
attributes to *blocks* of lines so that its one-line skid stays inside a block; since the
candidate loop became shared code, ``timezone_at`` itself holds only the prologue and one
call, so the breakdown is two blocks rather than five:

    stratum      in_memory=False
                 numba    clang
    unique         868      799
    ambiguous    4,598    4,020
    random       1,252    1,142
    on_land      1,642    1,444

  Paired against the same tree with the four buffer views rebound to numpy indexing,
  25 rounds a side alternated round by round, answers asserted equal every round:
  ambiguous **-11.3 % clang / -11.0 % numba**, on_land -5.6 / -5.9 %, random -4.8 /
  -4.7 %, unique -0.2 / +1.0 % (13/25 and 11/25 rounds - the unique path never enters
  the candidate loop, so that column is the internal control). The shape a change to
  the candidate loop has to have: it can only remove work from queries that reach one.

  The `prologue` block - coordinate validation plus the H3 cell computation, before any
  lookup logic - is 86.9 % of a unique query (clang), 60.6 % of a random one, 47.7 % of
  `on_land` and 20.5 % of an ambiguous one. Its *absolute* cost is flat across strata at
  ~690-830 ns, which is the useful way to read it: what changes between strata is
  everything else, and every stratum that reads geometry has now got cheaper around
  it twice.

Unique-shortcut stratum - the common case, and the one with no geometry in it at all
(``in_memory=False``):

    stage                       numba      clang
    validate_coordinates          270        212
    h3.latlng_to_cell             372        366
    shortcut table read           112        110
    zone_name_from_id              63         64
    ------------------------------------------------
    ladder total                  805        740
    real timezone_at()            873        791   (+68 / +51 call overhead)

Ambiguous-shortcut stratum, ``in_memory=False``:

    stage                       numba      clang
    validate + h3 + table         749        640
    candidate list slice          259        256
    zone_ids_of                 1,792      1,793
    last_change read              127        136
    coord2int x2                  229        104
    bbox rejection                499        584
    hole checks                   834        817
    boundary PIP                1,368        931
    ------------------------------------------------
    ladder total                5,864      5,312
    real timezone_at()          4,595      4,015

  The three rungs this change moved, clang: ``bbox rejection`` 937 -> 584,
  ``hole checks`` 1,268 -> 817 (the hole loop bbox-tests every hole through the same
  method) and ``boundary PIP`` 3,074 -> 931 - though the last is measured against a
  tree two format changes back and is not attributable to this change alone.

  **The ladder still overshoots the real function by ~28-30 % on this stratum, and that
  is a property of the instrument rather than of any change.** Two rungs bind the
  *checked public* accessors where ``timezone_at`` calls the unchecked internal ones,
  which is most of it; ``PROF-1`` in the improvement register carries the measurement
  and owns the repair. Read this table for *ordering* and for the rows that moved by
  more than the overshoot; the block breakdown above is the one to quote a share from.

One point-in-polygon test, per call, by polygon size stratum. Nothing precedes the
kernel any more: since polygon layout 3 a collection binds its backend and wraps its
buffers once, and ``PolygonArray.pip`` is a single call that finds the ring by where its
blocks start. ``decode`` is ``coords_of``, which no lookup performs - it is what
``get_geometry()`` costs, and what testing a block in its own frame avoids.

    stratum   vertices    clang     numba     decode
                         mapped     mapped   (coords_of)
    small          112      429        740       44,246
    medium       3,486      463        791      126,020
    large       46,823      645      1,157    1,051,947

  Each ``pip`` column is ~45-50 ns cheaper per call than before the buffer views,
  on every size stratum and on both backends: that is the vertex count reaching the
  kernel as a Python ``int`` rather than as a ``numpy.uint32`` unboxed through
  ``__index__``, and it is flat in ring size because it is paid once per call.

  and the same call under polygon layout 2, which is what it replaced - there the total
  was a coordinate fetch plus, on clang, three ``ffi.from_buffer`` calls, plus the
  kernel:

    stratum   vertices   clang mapped   clang in-mem   numba mapped   numba in-mem
    small          112          2,199          1,449          1,274            524
    medium       3,486          2,217          1,491          1,337            611
    large       46,823          2,516          1,735          1,568            787

CONCLUSIONS

1. **The block index moved the point-in-polygon kernel from linear in polygon size to
   almost flat, and the packed payload then removed everything in front of it.** A whole
   candidate now costs 429-645 ns on clang against 2,199-2,516 ns under layout 2 and
   ~23,000 ns on the largest stratum before the index - and it is flat in polygon size
   to within 50 %, where it was once proportional. A ray only crosses a few blocks of any
   ring, so what the kernel scans is "a few hundred edges" whatever the polygon; what
   layout 3 added is that reaching those edges costs nothing per call.

2. **The mapped mode's per-candidate penalty is gone, not reduced.** Measured when
   layout 3 landed, ``pip`` read 528/566/746 ns mapped against 532/572/746 in memory -
   the same number three times over. Under layout 2 the mapped fetch was ~950-990 ns
   against ~210 in memory, which was the entire difference between the two memory modes
   on the geometry path; now neither mode fetches anything, because the kernel addresses
   the collection's payload directly. The batch suite read the same way:
   ``timezone_at_land`` over the on-land fixture was 5.29 ms both ways, against 6.70 vs
   6.09 ms before. This re-take measured only ``in_memory=False``, so the mapped column
   above has moved since and the in-memory one has not been re-taken; nothing in this
   conclusion depends on which, since the claim is that they are equal.

3. **A batch API would amortise real overhead, not noise.** A unique-zone query is
   ~0.80-0.87 us of which *no stage is geometry*: ~740-805 ns of four fixed-cost calls
   plus ~51-68 ns for the bound-method call. The two largest, h3 cell computation
   (~366-372 ns) and coordinate validation (~212-270 ns), are exactly the two that
   vectorise over an array of points - over two thirds of the query, addressable before
   any lookup logic is touched. At resolution 4 ~89 % of uniformly random points are
   answered from that path, so the prologue is ~54-64 % of a random-workload query, and
   it has grown as a share every time the geometry got cheaper.

4. **The shortcut lookup is a slot-addressed table read, and it is not where a query's
   time goes.** Reading it costs ~110-112 ns: ~14 % of a unique-zone query, ~2.5 % of
   an ambiguous one, and well under a tenth of the workload-representative random
   stratum.
   That is the *ceiling* on what any further work on this structure could return.

5. **Per-polygon FFI marshalling is gone, and with it the largest single cost a
   candidate used to carry on the clang path.** ``ffi.from_buffer`` over the two axes and
   the block ranges was 925-967 ns per PIP call and flat in polygon size - more than the
   kernel on every stratum but the largest. Layout 3 removed it by giving the kernel the
   *collection's* arrays and a block offset, so the five buffer handles are built once
   when the collection is loaded. **That is most of what this format change bought**, and
   it is worth separating from the encoding: the same hoisting was available to layout 2
   and was not taken, while the bit-packed decode on its own costs ~+34 % of a hoisted
   kernel on clang and ~+88 % on numba (measured over 279 real query pairs, 41 paired
   order-alternated rounds). What remains of the case for a native candidate loop is the
   kernel itself, not the crossing.

6. **Better shortcut ordering has a much lower ceiling than it had.** The boundary-PIP
   rung is ~18-23 % of the ambiguous ladder, against 59-66 % before the index - and a correspondingly small share of a random one, which is the workload.
   Ordering still wins by reducing *how many* candidates are opened rather than by
   opening cheaper ones first, and it was rejected on a count, which no timing here
   disturbs. What changed is that opening a *large* candidate is no longer expensive, so
   the case for ordering by size is weaker than it was.

7. **What layout 3 costs is ``get_geometry()``, and it is the only thing it costs.**
   ``coords_of`` rebuilds absolute coordinates from residuals, which is ~40 us of fixed
   numpy overhead plus ~24 ns per vertex - 41.5 us for a 112-vertex ring and 1.15 ms for
   a 46,823-vertex one, against a zero-copy view before. Nothing on the lookup path
   reaches it; ``get_polygon`` / ``get_geometry`` and the integrity checks are the whole
   population. It is worth knowing that the obvious implementation is far worse: decoding
   block by block, which is how the frames are stored, cost 5.4 ms on that same ring
   because a block is only ~129 values and numpy call overhead dominates. One gather over
   the whole ring is what makes it 5x cheaper.

8. **``zone_ids_of`` reads ~1.79 us on this ladder and that is not a finding about
   ``zone_ids_of``.** The rung binds ``tf.zone_ids_of``, the *checked public* accessor,
   where ``timezone_at`` calls the unchecked ``_zone_ids_of`` - 1,685 ns against 564 ns
   measured directly - and the ``zone_name_from_id`` rung binds the public accessor the
   same way. That is most of the ~28-30 % by which this ladder overshoots the real
   function on the ambiguous stratum. ``PROF-1`` in the improvement register carries the
   measurement and the repair; until it lands, use the block breakdown for shares rather
   than a rung.

9. **Two checkouts do not compare unless they name the same interpreter.** uv picks a
   Python per invocation, and two worktrees *inside* this repository, on one machine and
   one ``.python-version``, resolved a free-threaded CPython and the regular one - so
   where the worktree sits is not what decides it. Pure-Python call chains differ by
   ~50 % between those builds: ``validate_coordinates`` reads 199 ns on one and 294 ns on
   the other with *identical* code, which presents as a 17 % regression on the unique
   stratum, a stratum the change under test does not touch. Pass ``--python`` explicitly
   when profiling a second checkout, and prefer an A/B inside one process where the
   question allows it. The contributor memory carries the rule; this is where it was
   measured.

"""

import argparse
import collections
import inspect
import signal
import time
from collections.abc import Callable, Sequence

import numpy as np
from h3.api import numpy_int as h3
from line_profiler import LineProfiler

from scripts.assert_acceleration_path import active_acceleration_path
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    PIP_STRATA,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
    load_pip_inputs,
    load_pip_strata,
)
from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import SHORTCUT_H3_RES
from timezonefinder.shortcut_index import slot_of

# one pass over this many points is a round; the reported value is the min over
# ``REPEATS`` rounds, the estimator the benchmark suite tracks (see
# scripts/benchmark_utils.py on why min is the least noise-sensitive one here).
BATCH_SIZE = 2_000
REPEATS = 15
# the PIP-level table needs its own, smaller batch: a large-polygon test is ~40 us
# on the clang backend, so 2,000 of them per round would make a run take minutes.
PIP_BATCH_SIZE = 300

QUERY_STRATA = (
    ("unique", UNIQUE_SHORTCUT_POINTS_FIXTURE),
    ("ambiguous", AMBIGUOUS_SHORTCUT_POINTS_FIXTURE),
    ("random", RANDOM_POINTS_FIXTURE),
    ("on_land", ON_LAND_POINTS_FIXTURE),
)

Points = Sequence[tuple[float, float]]


def measure(fn: Callable[[], object], repeats: int = REPEATS) -> float:
    """Seconds for one call of ``fn``, taken as the min over ``repeats``."""
    fn()  # warm up: JIT compilation, page faults on the mapped coordinate file
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - start)
    return best


# ---------------------------------------------------------------------------
# the stage ladder: prefixes of TimezoneFinder.timezone_at
#
# Each function is a verbatim copy of the real lookup up to one more stage. They are
# written out rather than parametrised on purpose - a `if depth >= k` inside the loop
# would add a branch per stage to the very thing being measured.
# ---------------------------------------------------------------------------


def make_ladder(tf: TimezoneFinder) -> list[tuple[str, Callable[[Points], int]]]:
    validate = utils.validate_coordinates
    latlng_to_cell = h3.latlng_to_cell
    res = SHORTCUT_H3_RES
    shortcuts = tf.shortcuts
    zone_name_from_id = tf.zone_name_from_id
    zone_ids_of = tf.zone_ids_of
    coord2int = utils.coord2int
    outside_bbox = tf.boundaries.outside_bbox
    holes_in_any = tf.holes.in_any_polygon
    hole_ids_of = tf._iter_hole_ids_of
    boundary_pip = tf.boundaries.pip

    def s0_loop(points: Points) -> int:
        n = 0
        for lng, lat in points:
            n += 1
        return n

    def s1_validate(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            n += 1
        return n

    def s2_h3(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            n += 1
        return n

    def s3_shortcut(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            entry = shortcuts.entry_of(hex_id)
            n += 1
        return n

    def s4_zone_name(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            entry = shortcuts.entry_of(hex_id)
            if entry >= 0:
                zone_name_from_id(entry)
            n += 1
        return n

    def s4b_candidates(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            entry = shortcuts.entry_of(hex_id)
            if entry >= 0:
                zone_name_from_id(entry)
                continue
            candidates = shortcuts.candidates_of(entry)
            n += 1
        return n

    def s5_zone_ids(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            entry = shortcuts.entry_of(hex_id)
            if entry >= 0:
                zone_name_from_id(entry)
                continue
            candidates = shortcuts.candidates_of(entry)
            zone_ids = zone_ids_of(candidates)
            n += 1
        return n

    def s6_last_change(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            entry = shortcuts.entry_of(hex_id)
            if entry >= 0:
                zone_name_from_id(entry)
                continue
            candidates = shortcuts.candidates_of(entry)
            zone_ids = zone_ids_of(candidates)
            last = shortcuts.stop_index_of(entry)
            n += 1
        return n

    def s7_coord2int(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            entry = shortcuts.entry_of(hex_id)
            if entry >= 0:
                zone_name_from_id(entry)
                continue
            candidates = shortcuts.candidates_of(entry)
            zone_ids = zone_ids_of(candidates)
            last = shortcuts.stop_index_of(entry)
            x = coord2int(lng)
            y = coord2int(lat)
            n += 1
        return n

    def s8_bbox(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            entry = shortcuts.entry_of(hex_id)
            if entry >= 0:
                zone_name_from_id(entry)
                continue
            candidates = shortcuts.candidates_of(entry)
            zone_ids = zone_ids_of(candidates)
            last = shortcuts.stop_index_of(entry)
            x = coord2int(lng)
            y = coord2int(lat)
            for i, boundary_id in enumerate(candidates):
                if i >= last:
                    break
                outside_bbox(boundary_id, x, y)
            zone_name_from_id(int(zone_ids[-1]))
            n += 1
        return n

    def s9_holes(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            entry = shortcuts.entry_of(hex_id)
            if entry >= 0:
                zone_name_from_id(entry)
                continue
            candidates = shortcuts.candidates_of(entry)
            zone_ids = zone_ids_of(candidates)
            last = shortcuts.stop_index_of(entry)
            x = coord2int(lng)
            y = coord2int(lat)
            for i, boundary_id in enumerate(candidates):
                if i >= last:
                    break
                if outside_bbox(boundary_id, x, y):
                    continue
                holes_in_any(hole_ids_of(boundary_id), x, y)
            zone_name_from_id(int(zone_ids[-1]))
            n += 1
        return n

    def s10_full(points: Points) -> int:
        """The whole lookup, inlined - compare against ``tf.timezone_at`` below."""
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            entry = shortcuts.entry_of(hex_id)
            if entry >= 0:
                zone_name_from_id(entry)
                continue
            candidates = shortcuts.candidates_of(entry)
            zone_ids = zone_ids_of(candidates)
            last = shortcuts.stop_index_of(entry)
            x = coord2int(lng)
            y = coord2int(lat)
            matched = False
            for i, boundary_id in enumerate(candidates):
                if i >= last:
                    break
                if outside_bbox(boundary_id, x, y):
                    continue
                if holes_in_any(hole_ids_of(boundary_id), x, y):
                    continue
                if boundary_pip(boundary_id, x, y):
                    zone_name_from_id(int(zone_ids[i]))
                    matched = True
                    break
            if not matched:
                zone_name_from_id(int(zone_ids[-1]))
            n += 1
        return n

    return [
        ("loop overhead", s0_loop),
        ("validate_coordinates", s1_validate),
        ("h3.latlng_to_cell", s2_h3),
        ("shortcut table read", s3_shortcut),
        ("zone_name_from_id", s4_zone_name),
        ("candidate list slice", s4b_candidates),
        ("zone_ids_of", s5_zone_ids),
        ("last_change read", s6_last_change),
        ("coord2int x2", s7_coord2int),
        ("bbox rejection", s8_bbox),
        ("hole checks", s9_holes),
        ("boundary PIP", s10_full),
    ]


def profile_query_stages(tf: TimezoneFinder) -> None:
    ladder = make_ladder(tf)

    def timezone_at_batch(points: Points) -> int:
        n = 0
        for lng, lat in points:
            tf.timezone_at(lng=lng, lat=lat)
            n += 1
        return n

    for stratum, fixture in QUERY_STRATA:
        points = load_benchmark_points(fixture)[:BATCH_SIZE]
        n = len(points)
        totals = [measure(lambda fn=fn, points=points: fn(points)) for _, fn in ladder]
        real = measure(lambda points=points: timezone_at_batch(points))

        ladder_total = totals[-1] - totals[0]
        print(f"\n### {stratum} ({n} points, min of {REPEATS} rounds)\n")
        print(
            "_a stage a stratum never reaches - every unique-cell point skips "
            "everything below `zone_name_from_id` - measures as noise around zero._\n"
        )
        print("| stage | ns/query | % of ladder total |")
        print("|---|---:|---:|")
        for (name, _), prev, cur in zip(ladder[1:], totals, totals[1:]):
            delta = (cur - prev) / n
            share = 100 * (cur - prev) / ladder_total if ladder_total else 0.0
            print(f"| {name} | {delta * 1e9:,.0f} | {share:.1f} |")
        print(f"| **ladder total** | **{ladder_total / n * 1e9:,.0f}** | 100.0 |")
        print(
            f"| `timezone_at()`, real | {real / n * 1e9:,.0f} | "
            f"(+{(real - totals[-1] + totals[0]) / n * 1e9:,.0f} call overhead) |"
        )


# ---------------------------------------------------------------------------
# the PIP-level breakdown: where one point-in-polygon test goes
# ---------------------------------------------------------------------------


def profile_pip_stages(tf: TimezoneFinder, backend: str) -> None:
    """Ladder again, one level down: what one candidate polygon costs.

    Keeps the polygon *id* rather than a pre-resolved ring, so this measures what the
    lookup performs - which since polygon layout 3 is the whole of it. There is no fetch
    stage left to separate out and, on clang, no per-call marshalling: the kernel is
    handed the collection's arrays once when the collection is loaded and finds a ring by
    where its blocks start, so ``PolygonArray.pip`` is one call with nothing in front of
    it.

    ``decode`` is the cost of *not* doing it that way, and it is here for scale rather
    than because a lookup pays it: ``coords_of`` rebuilds a whole ring's absolute
    coordinates, which is what ``get_geometry()`` costs and what a kernel reading
    residuals in the block's own frame avoids.
    """
    strata = load_pip_strata()
    grouped: dict[str, list[tuple[int, int, int]]] = {name: [] for name in PIP_STRATA}
    for (x, y, poly_id), stratum in zip(load_pip_inputs(), strata):
        bucket = grouped[stratum]
        if len(bucket) < PIP_BATCH_SIZE:
            bucket.append((x, y, poly_id))

    pip = tf.boundaries.pip
    coords_of = tf.boundaries.coords_of

    print(f"\n### point-in-polygon, per call ({PIP_BATCH_SIZE} per stratum)\n")
    print("| polygon stratum | vertices (mean) | pip | decode (`coords_of`) |")
    print("|---|---:|---:|---:|")
    for stratum, entries in grouped.items():
        n = len(entries)
        vertices = np.mean([int(tf.boundaries.nr_vertices[p]) for _, _, p in entries])

        def do_loop(entries=entries) -> int:
            n = 0
            for x, y, poly_id in entries:
                n += 1
            return n

        def do_pip(entries=entries) -> int:
            n = 0
            for x, y, poly_id in entries:
                pip(poly_id, x, y)
                n += 1
            return n

        def do_decode(entries=entries) -> int:
            n = 0
            for x, y, poly_id in entries:
                coords_of(poly_id)
                n += 1
            return n

        t_base = measure(do_loop)
        t_pip = measure(do_pip)
        t_decode = measure(do_decode)

        per_call = 1e9 / n
        print(
            f"| {stratum} | {vertices:,.0f} | {(t_pip - t_base) * per_call:,.0f} | "
            f"{(t_decode - t_base) * per_call:,.0f} |"
        )
    print(
        f"\n(the {backend} backend is bound when the collection is loaded, so neither "
        "column crosses an FFI boundary per call any more; on clang that removed three "
        "`ffi.from_buffer` calls at ~0.30 us each from every test)"
    )


# ---------------------------------------------------------------------------
# the unbiased construction: exact counts x sampled time share
#
# Neither half carries the other's bias. Hit counts come from ``line_profiler``,
# whose *timings* are unusable here (enabling it deoptimises the interpreter,
# non-uniformly by stage type - see the module docstring) but whose *counts* are
# exact and invariant under that perturbation: slowing the interpreter down does
# not change how many times a line runs. The time share comes from a signal
# sampler, which installs no tracing hooks at all. The untouched wall clock of
# the same workload is the third input, and the reconciliation line below is what
# proves the profile describes the program that actually ran:
#
#     ns per query = sampled_share x untouched_total / queries
#     ns per hit   = ns per query / exact hits per query
#
# ITIMER_REAL, not ITIMER_PROF: CPU-time sampling hides memory stalls, and the
# mapped coordinate accessor (finding 5) is exactly such a stall. Attribution is
# to *blocks* of lines rather than to single lines, because a signal is delivered
# at the next bytecode boundary and a long call's time can land on the following
# line - within a block that skid cancels, across one it does not, and there are
# three block boundaries here instead of ten line boundaries. Splits *inside* a
# block are the ladder's job.
# ---------------------------------------------------------------------------

SAMPLE_SECONDS = 6.0
# 1 kHz, tuned against the overhead line the report prints rather than guessed:
# 5 kHz cost 11-17% of the workload, which is a large enough perturbation to be
# worth avoiding even though it is roughly uniform in time. At 1 kHz it is ~3%
# and a 6 s window still yields ~6,000 samples, so a 10% block is resolved to
# about +/-4% relative.
SAMPLE_INTERVAL_S = 0.001
# window for the unsampled mean the overhead line is measured against
OVERHEAD_REFERENCE_SECONDS = 2.0

# Which block each line of ``timezone_at`` belongs to, matched on what the line
# *says* rather than on its number, so the mapping survives edits to
# timezonefinder.py. A line matching nothing is reported as "other", which is the
# signal that this table needs a new marker.
BLOCK_MARKERS: tuple[tuple[str, str], ...] = (
    ("validate_coordinates", "prologue"),
    ("latlng_to_cell", "prologue"),
    ("entry = int(", "prologue"),
    ("shortcuts.entry_of", "prologue"),
    ("SLOT_BASE_CELL_SHIFT", "prologue"),
    ("SLOT_DIGITS_SHIFT", "prologue"),
    ("if entry >= 0", "prologue"),
    ("if entry == ABSENT", "prologue"),
    ("zone_name_from_id", "zone name"),
    ("i = -(entry + 2)", "bookkeeping"),
    ("shortcuts.candidates_of", "bookkeeping"),
    ("zone_ids_of", "bookkeeping"),
    ("shortcuts.stop_index_of", "bookkeeping"),
    ("coord2int", "bookkeeping"),
    ("for i, boundary_id", "bookkeeping"),
    ("i >= last_zone_change_idx", "bookkeeping"),
    ("break", "bookkeeping"),
    ("zone_id = zone_ids", "bookkeeping"),
    ("inside_of_polygon", "candidate loop"),
)
BLOCK_ORDER = ("prologue", "bookkeeping", "candidate loop", "zone name", "other")


def line_blocks(func: Callable) -> dict[int, str]:
    """Map every line number of ``func`` to its block, by source text."""
    lines, first = inspect.getsourcelines(func)
    blocks = {}
    for offset, text in enumerate(lines):
        block = next(
            (name for marker, name in BLOCK_MARKERS if marker in text), "other"
        )
        blocks[first + offset] = block
    return blocks


def mean_ns_per_query(tf: TimezoneFinder, points: Points, seconds: float) -> float:
    """Mean ns per query over a fixed window, the estimator the overhead line needs.

    Deliberately not :func:`measure`, which reports a min: comparing a sampled
    *mean* against an unsampled *min* charges the sampler for the machine's own
    jitter as well, which is how a 4% perturbation reads as 16%.
    """
    queries = 0
    start = time.perf_counter()
    while time.perf_counter() - start < seconds:
        for lng, lat in points:
            tf.timezone_at(lng=lng, lat=lat)
        queries += len(points)
    return (time.perf_counter() - start) / queries * 1e9


def sample_blocks(
    tf: TimezoneFinder, points: Points, blocks: dict[int, str]
) -> tuple[collections.Counter, int, float]:
    """Sample ``timezone_at`` by wall clock for ``SAMPLE_SECONDS``.

    Returns the per-block sample counts, the number of queries executed, and the
    elapsed time - the latter two so the caller can state the sampler's own
    overhead against an unsampled run of the same loop.
    """
    target = TimezoneFinder.timezone_at.__code__
    samples: collections.Counter = collections.Counter()

    def handler(signum, frame):
        f = frame
        while f is not None:
            if f.f_code is target:
                samples[blocks.get(f.f_lineno, "other")] += 1
                return
            f = f.f_back

    previous = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, SAMPLE_INTERVAL_S, SAMPLE_INTERVAL_S)
    queries = 0
    start = time.perf_counter()
    try:
        while time.perf_counter() - start < SAMPLE_SECONDS:
            for lng, lat in points:
                tf.timezone_at(lng=lng, lat=lat)
            queries += len(points)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    return samples, queries, time.perf_counter() - start


def exact_hits_per_query(
    tf: TimezoneFinder, points: Points, blocks: dict[int, str]
) -> dict[str, float]:
    """Exact per-block execution counts per query, from ``line_profiler``.

    Its timings are discarded. Counts are what survives the perturbation, and
    they are the half a sampler cannot supply.
    """
    profiler = LineProfiler()
    profiler.add_function(TimezoneFinder.timezone_at)
    profiler.enable_by_count()
    try:
        for lng, lat in points:
            tf.timezone_at(lng=lng, lat=lat)
    finally:
        profiler.disable_by_count()

    hits: dict[str, float] = collections.defaultdict(float)
    for (_, _, _), entries in profiler.get_stats().timings.items():
        for lineno, nr_hits, _time in entries:
            hits[blocks.get(lineno, "other")] += nr_hits
    return {block: count / len(points) for block, count in hits.items()}


def profile_combined(tf: TimezoneFinder) -> None:
    blocks = line_blocks(TimezoneFinder.timezone_at)

    def timezone_at_batch(points: Points) -> int:
        n = 0
        for lng, lat in points:
            tf.timezone_at(lng=lng, lat=lat)
            n += 1
        return n

    for stratum, fixture in QUERY_STRATA:
        points = load_benchmark_points(fixture)[:BATCH_SIZE]
        untouched = measure(lambda points=points: timezone_at_batch(points))
        per_query_ns = untouched / len(points) * 1e9
        unsampled_mean_ns = mean_ns_per_query(tf, points, OVERHEAD_REFERENCE_SECONDS)
        samples, queries, elapsed = sample_blocks(tf, points, blocks)
        hits = exact_hits_per_query(tf, points, blocks)
        total_samples = sum(samples.values())
        sampled_per_query_ns = elapsed / queries * 1e9

        print(f"\n### {stratum} — counts x sampled share\n")
        print("| block | share | line hits/query | ns/query | ns/hit |")
        print("|---|---:|---:|---:|---:|")
        for block in BLOCK_ORDER:
            if not samples.get(block):
                continue
            share = samples[block] / total_samples
            ns_query = share * per_query_ns
            per_hit = f"{ns_query / hits[block]:,.0f}" if hits.get(block) else "—"
            print(
                f"| {block} | {100 * share:.1f}% | {hits.get(block, 0):.2f} | "
                f"{ns_query:,.0f} | {per_hit} |"
            )
        print(f"| **total** | 100.0% | | **{per_query_ns:,.0f}** | |")
        print(
            f"\nreconciliation: {total_samples:,} samples over {queries:,} queries; "
            f"shares scaled by the untouched min, {per_query_ns:,.0f} ns/query. "
            f"Sampler overhead {100 * (sampled_per_query_ns / unsampled_mean_ns - 1):+.1f}% "
            f"(mean vs mean: {sampled_per_query_ns:,.0f} vs {unsampled_mean_ns:,.0f} ns), "
            f"machine jitter {100 * (unsampled_mean_ns / per_query_ns - 1):+.1f}% "
            f"(unsampled mean vs min)"
        )


# ---------------------------------------------------------------------------
# line_profiler corroboration - ambiguous stratum only, see the module docstring
# ---------------------------------------------------------------------------


def line_profile(tf: TimezoneFinder) -> None:
    points = load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)[:500]
    profiler = LineProfiler()
    profiler.add_function(TimezoneFinder.timezone_at)
    profiler.add_function(TimezoneFinder.inside_of_polygon)
    profiler.enable_by_count()
    for lng, lat in points:
        tf.timezone_at(lng=lng, lat=lat)
    profiler.disable_by_count()
    print(
        "\nline_profiler over the ambiguous stratum. The per-line probe costs the "
        "same order as the stages it measures, so read the *ordering* of the lines, "
        "never their share of the total.\n"
    )
    profiler.print_stats()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--line-profile",
        action="store_true",
        help="additionally dump a line_profiler table (corroboration only)",
    )
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help="read the coordinate data into memory instead of mapping it",
    )
    args = parser.parse_args()

    backend = active_acceleration_path()
    tf = TimezoneFinder(in_memory=args.in_memory)
    print(
        f"backend: {backend} | in_memory={args.in_memory} | "
        f"data {tf.data_version} | batch {BATCH_SIZE}"
    )

    profile_combined(tf)
    profile_query_stages(tf)
    profile_pip_stages(tf, backend)
    if args.line_profile:
        line_profile(tf)


if __name__ == "__main__":
    main()
