"""Attribute a ``timezone_at`` query to its individual stages, per backend.

Several proposed optimisations are each justified by an assumption about which stage of
a lookup dominates - the batch API (#499) by per-call overhead, the native candidate
loop (#364) by per-polygon FFI marshalling, shortcut ordering (#301) by the polygon
loop. This script measures the breakdown so those assumptions stop being assumptions.
See issue #497.

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


FINDINGS (2026-08-21, `b331eee`, Apple arm64, Python 3.14, data 2026c, fixture set v2)

Re-measured wholesale after the coordinate accessors stopped re-walking the
FlatBuffers vtable per candidate (finding 5, now closed). Every figure below comes
from the same four runs, so they are comparable with each other and with nothing
else - do not diff an individual stage against the previous block, which was taken
on a different interpreter and a different day, and where a stage that did not
change still moves by the machine's own 3-9%.

These are one machine's, and the three kinds of figure below do not travel equally.
A *hit count* is a property of the code rather than the hardware and survives any
move - 1.13 candidates per ambiguous query, one FFI crossing per candidate on clang
- so state what a change removes as a count first. A *share* travels as an order of
magnitude only: the stages are bound by different resources (memory latency for the
mapped fetch, interpreter dispatch for the Python prologue, FP throughput for the
kernel), so another machine re-weights them against each other. Absolute
*nanoseconds* travel nowhere, and are not comparable with CI's or with a report
page's. Two further corrections before comparing anything: read the clang /
``in_memory=False`` column, which is what a plain install in a constrained container
runs and what CI tracks for that reason, and convert a stratum share into a workload
share - uniformly random points are ~25% ambiguous and an ambiguous query costs ~11x
a unique one, so ambiguous work is ~80% of a mixed wall clock. Both are in
docs/benchmarking_methodology.rst.

All figures are nanoseconds per query. Ladder figures are the min over 15 passes of
2,000 fixture points; the ``real`` row is ``tf.timezone_at(lng=, lat=)`` itself, and the
gap above it is the bound-method call the ladder does not pay.

Counts x sampled share, over the real function with nothing attached to it - blocks, so
that the sampler's one-line skid stays inside a block:

    block             ambiguous            unique
                    numba    clang    numba    clang
    prologue        1,184    1,166      919      798
    bookkeeping     1,462    1,623        -        -
    candidate loop  7,332    7,691        -        -
    zone name         192      220      132      160
    -----------------------------------------------
    total          10,236   10,814    1,094    1,013

  `zone name` on the unique stratum is not just ``zone_name_from_id`` (the ladder puts
  that at 45-54 ns): a frame's teardown is attributed to the line it returns from, so
  that block absorbs the ~155-175 ns of call overhead the ladder measures separately.

  The number this construction gives that neither other instrument does is **cost per
  candidate polygon tested**, since the candidate loop is one line and its hit count is
  exact: **6,488 ns (numba) / 6,806 ns (clang)** per candidate on the ambiguous stratum,
  8,850 / 9,182 ns on `on_land`, at 1.13 candidates per ambiguous query.

Unique-shortcut stratum - the common case, and the one with no geometry in it at all:

    stage                       numba      clang
    validate_coordinates          362        305
    h3.latlng_to_cell             414        401
    shortcut_mapping.get          105         88
    zone_name_from_id              45         54
    ------------------------------------------------
    ladder total                  944        833
    real timezone_at()          1,099      1,007   (+155 / +174 call overhead)

Ambiguous-shortcut stratum, default ``in_memory=False`` (the same run with
``--in-memory`` in brackets):

    stage                       numba              clang
    validate + h3 + get           888    (845)       784    (784)
    zone_ids_of                   577    (601)       569    (609)
    get_last_change_idx           120    (131)       310    (313)
    coord2int x2                  225    (200)       191    (122)
    bbox rejection                863    (966)       757    (797)
    hole checks                 1,335  (1,116)     1,257  (1,209)
    boundary PIP                5,783  (5,309)     6,708  (5,366)
    --------------------------------------------------------------
    ladder total                9,798  (9,200)    10,608  (9,233)
    real timezone_at()         10,050  (9,303)    10,718  (9,296)

One point-in-polygon test, per call, by polygon size stratum:

    stratum   vertices    coords_of  coords_of   ffi.from_buffer   kernel    kernel
                            mapped   in-memory      (clang only)    numba     clang
    small          114         834          62               651      301       254
    medium       3,039         826          62               649    1,615     1,579
    large       47,196         829          60               650   22,430    22,027

  ``coords_of`` on the mapped path is flat in polygon size, as it was before the offset
  table - it never copied. What changed is its height: ~4.9 us to ~0.83 us.

CONCLUSIONS, in the order #497 asks them:

1. **The batch API (#499) amortises real overhead, not noise.** A unique-zone query is
   ~1.0-1.1 us of which *no stage is geometry*: ~830-940 ns of four fixed-cost calls plus
   ~155-175 ns for the bound-method call itself. The two largest, h3 cell computation
   (~400 ns) and coordinate validation (305-362 ns), are exactly the two that vectorise
   over an array of points - over half the query, addressable before any lookup logic is
   touched. This conclusion is untouched by the offset table, which does not run here.

2. **#477's flat-array layout must keep a scalar path.** ``shortcut_mapping.get`` is
   88 ns, ~9% of a real unique-zone query - so #477's ``searchsorted`` variant (+355 ns)
   costs ~35% of the whole query, and its direct-index variant (+57 ns) ~6%. #477's
   verdict is unchanged and its ranking of the two variants is confirmed from the query
   side rather than the microbenchmark side.

3. **Per-polygon FFI marshalling is now comparable to the fetch it used to be dwarfed
   by, and that is what re-opens #364.** ``ffi.from_buffer`` over both axes is ~650 ns
   per PIP call and flat in polygon size. It used to sit next to a 4.9 us fetch, ~10x
   its size; the fetch is now ~830 ns, so the two are the same order and together are
   ~1.5 us of a small-polygon candidate against a 254 ns kernel. A native candidate loop
   removes both - but see 5 for how little of a *workload* that is.

   Also measured, and contrary to what the backend split suggests: **the two PIP kernels
   are within 15% of each other and numba is not reliably ahead** (small 301 vs 254 ns,
   large 22.4 vs 22.0 us - clang faster in both). numba's advantage on an ambiguous query
   is the marshalling it does not do, not a faster kernel; and on the unique-zone path
   numba is slower, because ``validate_coordinates`` calls two njit'd scalar functions
   whose dispatch costs more than the pure-Python comparison it replaces (362 vs 305 ns).

4. **Better shortcut ordering (#301) has a ceiling of the boundary-PIP row**: 59-63% of
   an ambiguous query mapped, 58% in memory. With the fetch down to ~830 ns the balance
   inside a candidate has moved: the clang kernel runs at ~0.45 ns/vertex, so fetch plus
   marshalling stops dominating at roughly 1,400 vertices rather than around ten thousand.
   The medium stratum is now kernel-bound. Ordering still wins by reducing *how many*
   candidates are opened rather than by opening cheaper ones first, and #301 was rejected
   on a count, which no timing here disturbs.

5. **Finding 5 of the previous block is closed, and this is what it was worth.** The
   mapped path paid **4.9 us per candidate** to hand out coordinates, against 57 ns for
   ``in_memory=True`` - 86x for the same bytes - because the accessor was rebuilt from
   scratch per candidate. Addressing polygons by a precomputed ``(offset, length)`` table
   brings it to **~830 ns against ~60 ns**, and an ambiguous clang query from 14.0 us to
   10.7 us. The mapped mode now costs ~15% more than in-memory on an ambiguous query,
   where it cost ~46%.

6. **``zone_ids_of`` + ``get_last_change_idx`` cost 0.70-0.88 us**, ~7-8% of an ambiguous
   query - more than validation, h3 and the shortcut lookup put together, and now a
   larger share than before because the denominator shrank. Both are numpy calls over a
   candidate list of a handful of elements, where the per-call overhead dominates
   whatever they compute, and neither appears in any open issue.

7. **What is left of the mapped-vs-in-memory gap is one buffer acquisition per fetch.**
   ~830 ns against ~60 ns is still 14x, and it is not I/O: ``np.frombuffer`` re-acquires
   the ``mmap`` object's buffer on every call. Slicing a single whole-file ``int32`` view
   instead measures 415 ns against 788 ns per fetch in isolation - but that view is a
   live export held for the accessor's lifetime, which is the mapping-pinning trade the
   offset table was chosen to avoid and which ``BufferError`` on ``cleanup()`` made real
   once already. Recorded in ``potential-improvements.md`` rather than taken here.

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
from timezonefinder import TimezoneFinder, utils, utils_clang
from timezonefinder.configs import SHORTCUT_H3_RES

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
    shortcuts = tf.shortcut_mapping
    zone_name_from_id = tf.zone_name_from_id
    zone_ids_of = tf.zone_ids_of
    last_change_idx = utils.get_last_change_idx
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
            shortcut_value = shortcuts.get(hex_id)
            n += 1
        return n

    def s4_zone_name(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            shortcut_value = shortcuts.get(hex_id)
            if isinstance(shortcut_value, int):
                zone_name_from_id(shortcut_value)
            n += 1
        return n

    def s5_zone_ids(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            shortcut_value = shortcuts.get(hex_id)
            if isinstance(shortcut_value, int):
                zone_name_from_id(shortcut_value)
                continue
            zone_ids = zone_ids_of(shortcut_value)
            n += 1
        return n

    def s6_last_change(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            shortcut_value = shortcuts.get(hex_id)
            if isinstance(shortcut_value, int):
                zone_name_from_id(shortcut_value)
                continue
            zone_ids = zone_ids_of(shortcut_value)
            last = last_change_idx(zone_ids)
            n += 1
        return n

    def s7_coord2int(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            shortcut_value = shortcuts.get(hex_id)
            if isinstance(shortcut_value, int):
                zone_name_from_id(shortcut_value)
                continue
            zone_ids = zone_ids_of(shortcut_value)
            last = last_change_idx(zone_ids)
            x = coord2int(lng)
            y = coord2int(lat)
            n += 1
        return n

    def s8_bbox(points: Points) -> int:
        n = 0
        for lng, lat in points:
            lng, lat = validate(lng, lat)
            hex_id = latlng_to_cell(lat, lng, res)
            shortcut_value = shortcuts.get(hex_id)
            if isinstance(shortcut_value, int):
                zone_name_from_id(shortcut_value)
                continue
            zone_ids = zone_ids_of(shortcut_value)
            last = last_change_idx(zone_ids)
            x = coord2int(lng)
            y = coord2int(lat)
            for i, boundary_id in enumerate(shortcut_value):
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
            shortcut_value = shortcuts.get(hex_id)
            if isinstance(shortcut_value, int):
                zone_name_from_id(shortcut_value)
                continue
            zone_ids = zone_ids_of(shortcut_value)
            last = last_change_idx(zone_ids)
            x = coord2int(lng)
            y = coord2int(lat)
            for i, boundary_id in enumerate(shortcut_value):
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
            shortcut_value = shortcuts.get(hex_id)
            if isinstance(shortcut_value, int):
                zone_name_from_id(shortcut_value)
                continue
            zone_ids = zone_ids_of(shortcut_value)
            last = last_change_idx(zone_ids)
            x = coord2int(lng)
            y = coord2int(lat)
            matched = False
            for i, boundary_id in enumerate(shortcut_value):
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
        ("shortcut_mapping.get", s3_shortcut),
        ("zone_name_from_id", s4_zone_name),
        ("zone_ids_of", s5_zone_ids),
        ("get_last_change_idx", s6_last_change),
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

    Keeps the polygon *id* rather than a pre-resolved coordinate array, so
    ``coords_of`` is measured as the lookup performs it - through the memory map,
    unless ``--in-memory`` was passed.
    """
    strata = load_pip_strata()
    grouped: dict[str, list[tuple[int, int, int]]] = {name: [] for name in PIP_STRATA}
    for (x, y, poly_id), stratum in zip(load_pip_inputs(), strata):
        bucket = grouped[stratum]
        if len(bucket) < PIP_BATCH_SIZE:
            bucket.append((x, y, poly_id))

    inside_polygon = utils.inside_polygon
    coords_of = tf.boundaries.coords_of
    ffi = utils_clang.ffi
    # marshalling is a property of the *active* path: the C extension is importable
    # either way, but a numba lookup never crosses into it.
    measure_marshalling = backend == "clang" and ffi is not None

    print(f"\n### point-in-polygon, per call ({PIP_BATCH_SIZE} per stratum)\n")
    print(
        "| polygon stratum | vertices (mean) | coords_of | ffi.from_buffer | kernel | total |"
    )
    print("|---|---:|---:|---:|---:|---:|")
    for stratum, entries in grouped.items():
        n = len(entries)
        vertices = np.mean([coords_of(poly_id).shape[1] for _, _, poly_id in entries])

        def do_loop(entries=entries) -> int:
            n = 0
            for x, y, poly_id in entries:
                n += 1
            return n

        def do_coords_of(entries=entries) -> int:
            n = 0
            for x, y, poly_id in entries:
                coords_of(poly_id)
                n += 1
            return n

        def do_marshal(entries=entries) -> int:
            n = 0
            for x, y, poly_id in entries:
                coords = coords_of(poly_id)
                ffi.from_buffer(utils_clang.INT_LIST_REP, coords[0])
                ffi.from_buffer(utils_clang.INT_LIST_REP, coords[1])
                n += 1
            return n

        def do_pip(entries=entries) -> int:
            n = 0
            for x, y, poly_id in entries:
                inside_polygon(x, y, coords_of(poly_id))
                n += 1
            return n

        t_base = measure(do_loop)
        t_coords = measure(do_coords_of)
        t_pip = measure(do_pip)
        t_marshal = measure(do_marshal) if measure_marshalling else t_coords

        per_call = 1e9 / n
        marshal_ns = (
            f"{(t_marshal - t_coords) * per_call:,.0f}"
            if measure_marshalling
            else "n/a"
        )
        print(
            f"| {stratum} | {vertices:,.0f} | {(t_coords - t_base) * per_call:,.0f} | "
            f"{marshal_ns} | {(t_pip - t_marshal) * per_call:,.0f} | "
            f"{(t_pip - t_base) * per_call:,.0f} |"
        )
    if not measure_marshalling:
        print(
            f"\n(the {backend} backend crosses no FFI boundary at all - the "
            "marshalling cost that motivates the native candidate loop only exists "
            "on the clang path, and the kernel column absorbs it there)"
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
    ("shortcut_mapping.get", "prologue"),
    ("shortcut_value is None", "prologue"),
    ("match shortcut_value", "prologue"),
    ("case int(zone_id)", "prologue"),
    ("zone_name_from_id", "zone name"),
    ("possible_boundaries = shortcut_value", "bookkeeping"),
    ("nr_possible_polygons", "bookkeeping"),
    ("zone_ids_of", "bookkeeping"),
    ("get_last_change_idx", "bookkeeping"),
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
