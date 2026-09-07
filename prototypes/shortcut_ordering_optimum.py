"""Construct and price the per-cell candidate ordering that minimises expected query compute.

A shortcut cell that is not answered by a single zone id stores an ordered list of candidate
boundary polygons. ``TimezoneFinder._zone_id_among`` walks it, stops at the first hit, and never
tests the final zone's run - so the order is free to choose and somebody will keep proposing a
better one. Issue #301 proposed ordering by the area each candidate overlaps the cell. This script
is what settles that family: it builds real shortcut binaries under each candidate ordering,
counts what each removes, constructs the provable optimum, and times all of them inside the whole
public call.

Nothing here ships. It exists so the refusal is re-checkable against a new dataset, a new H3
resolution or a new kernel, none of which it hard-codes.


THE MODEL

Write ``S`` for the index at which the final zone's run begins (``last_zone_change_idx``, stored
per distinct candidate list), ``c_t`` for the expected compute of testing the candidate at
position ``t``, and ``p_t`` for the probability a query point lands inside it. The loop tests
positions ``0 .. S-1``, stopping early on a hit, and returns the final zone untested. So

    E = sum_{t < S} c_t * (1 - sum_{u < t} p_u)                                            (1)

Everything below is a way of choosing an order that makes (1) small, or of checking one.


THE COST COEFFICIENT c_i

Not the vertex count. ``inside_polygon_packed_int`` walks *every* latitude block of a ring,
skips any whose stored ``[min, max]`` latitude excludes the query latitude, and scans the edges
of the survivors. Blocks hold ``POLYGON_BLOCK_SIZE`` vertices and their ranges are built by
``timezonefinder._block_index.block_latitude_ranges``. So

    c_i = alpha + beta * B_i + gamma * V_i                                                 (2)

with ``B_i`` the ring's block count, and ``V_i`` the expected edges scanned:

    V_i = sum_b n_b * P[y in [lo_b, hi_b]]                                                 (3)

``alpha`` absorbs the call, the bbox rejection and the hole path; ``beta`` is the per-block range
check paid whether or not the block survives; ``gamma`` is one edge of the scan. ``B_i`` and
``V_i`` are exact and computable at build time; only the three machine constants need measuring,
which ``calibrate`` does by regressing measured ``PolygonArray.pip`` times on ``[1, B, V]``.

The probability measure (3) puts on the query latitude is A6 below.


THE HIT PROBABILITY p_i

``p_i = area(polygon_i ∩ cell) / area(cell)``, planar, in the scaled integer coordinates the
package works in, computed with ``shapely`` over the ring minus its holes - the region the tested
predicate actually returns True on, rather than the ring. See A12 to A16.

**Polygon overlap is measured but not modelled, and it is the load-bearing approximation.** (1)
uses ``1 - sum p_u`` for
the survival probability, which is the probability of no hit only if the candidates' hit regions
are *disjoint within the cell*. They are not always. Upstream ships genuinely overlapping zones -
``Asia/Urumqi`` lies inside ``Asia/Shanghai`` - so some points are inside two candidates at once.
``areas`` measures exactly this and prints it: the summed candidate area above the *union* area is
the doubly-covered area, per cell. Where that is non-zero, (1) understates survival, and, far more
importantly, **the ordering decides which zone is returned rather than only how long it takes** -
a point inside two candidates is answered by whichever is tested first.

Modelling it properly is not a small correction. The survival after a prefix becomes the area of
the prefix's *union*, which depends on the set already tested rather than on each candidate alone,
so the ratio rule stops being a sort key at all: the exchange argument in step 1 below assumes
``p_i`` is independent of position, and with correlated predicates the sequencing problem is the
correlated pipelined-filter ordering problem, which is hard in general. This script therefore does
the honest thing rather than the elegant one - it takes the disjoint model, and then *measures*
every ordering it produces, with ``count`` reporting per strategy how many committed fixture
answers move. An ordering that wins on (1) and moves 158 answers has not been shown to be better;
it has been shown to be different. Finding 7 is that report.

Measured over 2026c: candidates overlap in **1,090 of 31,368 cells (3.47%)**, and where they do,
the doubly-covered area is 2.7% of the cell on average and 100% of it in the worst case - a fully
nested pair, which is what ``Asia/Urumqi`` inside ``Asia/Shanghai`` is.


THE CONSTRUCTION

Zone contiguity is a constraint, not a choice: ``last_zone_change_idx`` is only well defined when
the final zone's polygons form a suffix, and ``scripts.shortcuts.check_shortcut_sorting`` asserts
coherent runs for all of them. Under it:

1. **Within a zone, order by ``c/p`` ascending.** Exchanging adjacent ``i, j`` moves (1) by
   ``c_j*p_i - c_i*p_j``, so ``i`` precedes ``j`` iff ``c_i/p_i <= c_j/p_j``.

2. **Across zones, order by ``C/P`` ascending**, with ``C = sum c``, ``P = sum p``. A zone entered
   at survival ``R`` contributes ``R*C - K`` where ``K = sum_i c_i * sum_{u<i} p_u`` is internal
   to the block, so exchanging adjacent zone blocks moves (1) by ``C_A*P_B - C_B*P_A``: the ``K``
   terms cancel and a zone behaves *exactly* as one job of summed cost and summed probability.
   This is an equality, not an approximation.

3. **Enumerate the free final slot.** It does not reduce to a sort key, because designating zone
   ``m`` last both saves its own contribution and removes its probability from shielding the
   zones after it:

       E(m) = E_all - (R_m*C_m - K_m) + P_m * sum_{j>m} C_j                                (4)

   With ``k`` zones per cell - at most 25, and 2 in 94% of ambiguous cells - evaluate all ``k``.

``enumerate`` checks this against exhaustive enumeration of every contiguity-respecting ordering
on the cells small enough to brute-force, which is where a plausible-looking derivation would be
caught.

**The relaxation.** Only the *final* zone must be contiguous; the loop returns the zone of
whichever polygon hits, so the tested prefix could interleave zones freely and the ratio rule
would then apply per polygon. That variant is built (``optimal-relaxed``) and brute-forced too.
It would require relaxing ``has_coherent_sequences`` and ``check_shortcut_sorting``.


ASSUMPTIONS AND APPROXIMATIONS

All of them, so a later reader can attack the list rather than rediscover it. "Measured" means this
script prints the size of the error; "unmeasured" means it does not, and says so.

*What is being optimised*

A1  The objective is the **expected** compute over a uniformly random query point in the cell - the
    premise issue #301 itself argues from. Not the tail: an ordering halving the mean and doubling
    p99 scores better under (1). ``ab`` reports whole-query minima and round wins, so a tail
    regression would surface there rather than in the model.
A2  A population-weighted query distribution is not modelled. Real traffic is not uniform over a
    cell, and a candidate covering an inhabited sliver would deserve more weight than its area.
A3  Each ambiguous cell is weighted **equally** in ``enumerate``'s totals, though real traffic hits
    cells at wildly different rates. ``count`` and ``ab`` instead weight by the committed fixtures,
    which sample geographically - so the two stages answer different questions on purpose, and
    where they disagree the fixture-weighted one is the one about a workload.
A4  Unique cells are ignored. Exact: they reach no candidate loop.
A5  Build-time cost is ignored. Every ordering here is free at query time and paid in the converter.

*The cost model (2)*

A6  The query latitude is uniform on the cell's **latitude extent**. The point is uniform over the
    cell's *area*, so its latitude density follows the cell's width - a trapezoidal weighting this
    ignores. Unmeasured; it biases every candidate in a cell the same way, and only the ordering
    *within* a cell is being decided.
A7  Cost is **affine** in (1, blocks, in-band edges). Cache behaviour, branch prediction, and the
    x-residual reads that happen only on latitude-straddling edges are not terms; they are absorbed
    into the constants as averages. Measured: R² = 0.9886 bounds what is left over.
A8  ``alpha``, ``beta``, ``gamma`` are **global**, identical for every polygon, though ``alpha``
    varies with hole count (1,225 of 1,322 packaged polygons own no hole) and ``gamma`` with how
    many edges straddle the query latitude. Unmeasured per polygon.
A9  The **bbox rejection is not a separate branch**. A candidate whose bbox misses costs only that
    test, where (2) charges the full ``alpha + beta*B + gamma*V``. Cheap misses are over-charged,
    which *inflates* the modelled headroom of any reordering - conservative for a refusal.
A10 ``calibrate`` times ``PolygonArray.pip``, not ``inside_of_polygon``, so the fitted ``alpha``
    **excludes** the Python-level bbox and hole dispatch above it. 437.5 ns is a lower bound on the
    real per-candidate overhead, making the loop's 14.7% share an under-estimate and finding 4's
    ceiling generous. It also samples latitudes inside each ring's own span, so it under-samples
    the bbox-miss case by construction.
A11 One machine, one interpreter, one backend per run; the constants are not portable. Counts
    (``count``) are, and are the instrument to prefer when moving.

*The probability model*

A12 ``p_i`` is **planar** area in scaled integers, not spherical. Unmeasured, and a real
    approximation away from the equator.
A13 Cells enclosing a pole, and cells torn by the antimeridian whose candidates cannot all be
    rotated into one frame, are **excluded** and keep the shipped ordering. Measured: 26 of 31,394
    on 2026c.
A14 **Polygon overlap is measured, not modelled** - the section above. (1)'s survival is exact only
    for disjoint hit regions; 3.47% of cells violate that. Its consequence for *answers* rather
    than for cost is what ``count`` reports per strategy.
A15 ``p_i`` is normalised over the **candidate set**, not the cell: it divides by the summed
    candidate area, not the cell's. Where candidates do not cover the cell this scales every
    ``p_i`` by one common factor, so survival reaches exactly 0 at the end of the prefix where it
    should stay positive. Orderings are unchanged - a common factor cancels in every ratio and
    every exchange - but (1) understates absolute cost. Unmeasured.
A16 Invalid rings are repaired with ``shapely.validation.make_valid``, which can move their area
    slightly. Unmeasured; it affects a handful of rings.

*The construction*

A17 The exchange arguments need ``p_i`` **independent of position**, which A14 breaks wherever
    candidates overlap. The construction is optimal *under the disjoint model* and only
    approximately so on the real data. With correlated predicates the problem is the correlated
    pipelined-filter ordering problem, which is hard in general.
A18 Zone contiguity is a hard constraint. ``optimal-relaxed`` prices dropping it for all but the
    final zone and is not loadable without relaxing ``has_coherent_sequences`` and
    ``check_shortcut_sorting``.
A19 The brute force covers cells with at most ``--brute-max`` candidates (5 by default, 99.9% of
    them) and validates the **construction against the model**, never the model against reality.
    That is what ``ab`` is for.
A20 Ties in any sort key fall to the input order. This script sorts candidate ids to make that
    deterministic; the shipped generator does not (finding 9).

*The measurements*

A21 ``ab`` claims a direction only when both estimators agree, and carries the ``unique`` stratum
    as a control no ordering can reach. A moving control means the run measured the machine.
A22 ``count`` wraps ``inside_of_polygon`` in Python, which slows the run. The counts are exact and
    unaffected, and no timing is taken from that stage.
A23 The ``ambiguous`` and ``unique`` fixture strata are classifications **by the shortcut index**,
    so they are not comparable across an H3 resolution change; ``random`` and ``on_land`` are.
A24 The workload-share conversion uses ``AMBIGUOUS_QUERY_NS`` and the stratum mix from the
    contributor-memory measurement baseline, taken at a different anchor commit. Re-read them there
    before quoting a share - they move with the query path.


HOW TO RUN

Needs the ``proto`` group, ``shapely``, and the upstream GeoJSON the packaged data was built from
(``update_data.sh`` leaves it in ``tmp/``; any release works, and the cells are recompiled for
whatever it holds).

    PYTHONPATH=. uv run --group proto --with shapely \\
        python prototypes/shortcut_ordering_optimum.py all --geojson tmp/combined-with-oceans-2026c.json

Stages are separate subcommands and cache to ``--work`` (default ``tmp/ordering``), so an
experiment that only changes a *strategy* re-runs in seconds:

    cells      compile hex id -> candidate polygon ids from the GeoJSON   (minutes, cached)
    areas      per (cell, candidate) overlap area, via shapely            (~1 min, cached)
    costs      per (cell, candidate) block count and expected edges       (seconds, cached)
    calibrate  fit alpha, beta, gamma against measured pip times
    enumerate  score every strategy under the model; brute-force the constructions
    build      write a shortcuts.bin per strategy into a mirrored data dir
    count      exact point-in-polygon test counts and moved answers, over the committed fixtures
    ab         paired order-alternated whole-query A/B against the shipped ordering

**To add an ordering**, write one function taking ``(ctx, hex_id, poly_ids)`` and returning the
ordered ids, and register it in ``STRATEGIES``. Everything else - counts, binaries, timings,
brute-force check - picks it up.

The A/B must be run on the tracked configuration as well as on a dev checkout, since the backend
is bound at import (``timezonefinder/utils.py``):

    PYTHONPATH=. uv run --isolated --group test --with shapely \\
        python prototypes/shortcut_ordering_optimum.py ab


FINDINGS (2026-09-07, Apple arm64, CPython 3.14.2 free-threading build, data 2026c, H3
resolution 4, fixture set v3, taken against ``c27b452``)

1. **Every candidate ordering is slower than the one that ships, and the optimum is neutral.**
   Paired, order-alternated, 61 rounds x 2,500 points, one process holding both indices, on the
   C extension (the tracked configuration) and repeated on numba. Ranking zones by
   ``vertices / area**w`` costs +4.2% of an ambiguous query at w=0.25, +5.5% at w=0.5, +9.7% at
   w=1 and +24.8% at w=inf (pure area) - monotone in the area weight, with no turning point, so
   the family's optimum is w=0, the shipped key. **The provable optimum measures as no difference
   on every stratum**, both estimators agreeing: +0.1% on ambiguous with 30 of 61 rounds won,
   +1.7% random, +0.3% on-land, and the ``unique`` control - which no ordering can reach - equally
   still at 30 of 61. ``true-cost`` is likewise flat (+0.4%, 33 of 61). Earlier runs against an
   index built from *guessed* cost constants read ``unresolved`` and swung +3.8 / -6.3 / +0.2%;
   calibrating (2) is what made the comparison quiet, which is itself a reason to run
   ``calibrate`` before believing an ordering.

2. **A count of tests removed is not a share of compute here.** The area ordering removes 2.8% of
   the point-in-polygon tests on the ambiguous stratum and 3.6% on the random one - exactly, by
   instrumenting ``inside_of_polygon`` - and is 24.8% slower. The zone with the largest overlap is
   usually the zone with the most vertices, so a probability-led key buys fewer tests by making
   the first test the expensive one. Weighting by (3), it doubles the expected edges scanned.

3. **The shipped cost proxy is stale, and it does not matter.** Model (2) calibrates to
   ``437.5 ns + 0.511*B + 1.133*V``, R^2 = 0.9886, against **R^2 = 0.524 for the total vertex
   count** the shipped key sorts on. A polygon of >=512 vertices scans a median 2.2% of its ring,
   and the two keys disagree about which of two candidates is cheaper in 31.6% of candidate pairs.
   Ordering on the *true* cost still measures as no difference (finding 4 says why).

4. **The loop is overhead-bound, which is the durable result.** With the calibrated model the
   expected candidate-loop compute per ambiguous query is 758.5 ns shipped, 735.8 ns on a pure
   true-cost key and 723.8 ns at the optimum (-4.57%). But 437.5 ns of that is fixed per candidate
   and only ~1.05 candidates are tested, so the loop is **14.7% of a ~5,150 ns ambiguous query**:
   the optimum saves 34.7 ns, **0.67% of an ambiguous query and 0.27% of a mixed workload**,
   against a 3-9% noise floor. An *oracle* that knows the answer and pays only the cheapest
   candidate saves 80% of the loop - 4.7% of a mixed workload, and that is the ceiling on
   candidate ordering as a subject. Future work on this loop should attack the per-call overhead.

5. **The construction is optimal, checked rather than argued.** Exhaustive enumeration of every
   contiguity-respecting ordering, on all 31,344 ambiguous cells holding at most 5 candidates:
   the construction attains the minimum in 31,344 of 31,344. The relaxed variant likewise, on
   31,354 cells.

6. **Dropping contiguity for all but the final zone is correct and buys nothing.** 0.04 ns per
   ambiguous query, -0.005%. It *could* bind on 2,020 of 31,368 cells and actually costs something
   on **16**, worth -5.77% on those alone and 226 ns on the worst.

7. **Reordering moves answers with no data change** - up to 158 of 5,000 ambiguous fixture points
   depending on the key. Every moved point lies inside *two* zones' polygons where the upstream
   boundaries genuinely overlap (A14), mostly ``Asia/Urumqi`` inside ``Asia/Shanghai``. Candidates
   overlap in **1,090 of 31,368 cells (3.47%)**; where they do, the doubly-covered area is 2.7% of
   the cell on average and 100% of the worst, which is a fully nested pair. That is the population
   an ordering change can silently re-answer, and it is why the disjointness (1) assumes is the
   model's load-bearing approximation rather than a technicality.
   The area-led keys move the most (158 ambiguous, 97 on-land); ``true-cost`` and ``optimal`` move
   0-4, and ``tiebreak`` and ``w0.25`` move none at all. How many an ordering moves is a property
   of that ordering, so ``count`` reports it per strategy rather than once. Nothing runs the
   data-update guard for an index reordering, so a future key owes that diff by hand.

8. **Resolution 4 shrank the prize.** 29,372 of 31,394 ambiguous cells hold exactly two polygons
   of two zones, where the free final slot makes every order cost exactly one test. At resolution
   3 the equivalent count was 9,046 of 10,511. Re-run ``enumerate`` after any resolution change:
   the bound moves with it.

10. **Some ambiguous cells need no geometry at all, which is worth more than any ordering.** 826 of
   31,368 (2.63%) are covered *entirely* by a single zone, so no query point in them can fall
   outside it and the index could store them as unique-zone cells. That is ~109 ns, **2.12% of an
   ambiguous query** - about three times the provably optimal ordering, because it removes the loop
   instead of reordering it. It is not free: in 824 of the 826 another zone genuinely overlaps, so
   converting changes which zone answers there (only 2 are answer-preserving). Recorded as PERF-7
   with the precedence question that blocks it; do not implement it from here.

9. **The shipped ordering is not reproducible from the data alone.** Rebuilding it here reproduces
   the packaged ``shortcuts.bin`` to 29 bytes over ~6 cells - every one a tie in the sort key,
   broken by ``polys_in_cell``'s set iteration order. Recorded separately; a polygon-id tie-break
   fixes it and needs nothing from this script.
"""

import argparse
import pickle
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from itertools import permutations
from pathlib import Path

import h3.api.numpy_int as h3
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from timezonefinder import TimezoneFinder  # noqa: E402
from timezonefinder.configs import POLYGON_BLOCK_SIZE, SHORTCUT_H3_RES  # noqa: E402
from timezonefinder.shortcut_index import (  # noqa: E402
    build_shortcut_index,
    write_shortcuts_binary,
)
from timezonefinder.utils import coord2int  # noqa: E402

# Calibrated by `calibrate`; see finding 3. Kept here so `enumerate` has a cost model without a
# machine, and re-fit rather than trusted when the kernel or the machine changes.
ALPHA_NS = 437.5  # call, bbox rejection, hole path
BETA_NS = (
    0.511  # latitude-range check, per block, paid whether or not the block survives
)
GAMMA_NS = 1.1326  # one edge of the scan, inside a surviving block

# Denominators for turning a saving in the loop into a share of a workload. From
# contributing/improvements/query-performance-measurement-baseline.md; re-read them there rather
# than trusting these copies, and update both together.
AMBIGUOUS_QUERY_NS = 5150.0
RANDOM_AMBIGUOUS_SHARE = 0.11
AMBIGUOUS_COST_RATIO = 5.3


@dataclass
class Context:
    """Everything a strategy may consult, all of it available at build time."""

    mapping: dict[int, list[int]]  # hex id -> candidate polygon ids
    zone_ids: np.ndarray  # zone id per boundary polygon
    lengths: list[int]  # vertex count per boundary polygon
    areas: dict[int, dict[int, float]]  # hex id -> polygon id -> overlap area
    costs: dict[
        int, dict[int, tuple[float, int]]
    ]  # hex id -> polygon id -> (edges, blocks)

    def zone_of(self, poly_id: int) -> int:
        return int(self.zone_ids[poly_id])

    def group(self, poly_ids) -> dict[int, list[int]]:
        buckets: dict[int, list[int]] = defaultdict(list)
        for pid in poly_ids:
            buckets[self.zone_of(pid)].append(pid)
        return buckets

    def cost(self, hex_id: int, poly_ids) -> dict[int, float]:
        """Model (2), in nanoseconds."""
        per = self.costs[hex_id]
        return {
            p: ALPHA_NS + BETA_NS * per[p][1] + GAMMA_NS * per[p][0] for p in poly_ids
        }

    def prob(self, hex_id: int, poly_ids) -> dict[int, float] | None:
        """Normalised overlap areas, or None where no planar area could be taken (P2)."""
        area = self.areas.get(hex_id)
        if area is None:
            return None
        total = sum(area.get(p, 0.0) for p in poly_ids)
        if total <= 0:
            return None
        return {p: area.get(p, 0.0) / total for p in poly_ids}


def expected_compute(order, ctx: Context, c, p) -> float:
    """Equation (1) for one ordering: the final zone's run is never tested."""
    zones = [ctx.zone_of(i) for i in order]
    stop, last = len(order), zones[-1]
    while stop > 0 and zones[stop - 1] == last:
        stop -= 1
    total, survived = 0.0, 1.0
    for t in range(stop):
        total += c[order[t]] * survived
        survived -= p[order[t]]
    return total


# --------------------------------------------------------------------------------------------
# Orderings. Each takes (ctx, hex_id, poly_ids) and returns the ordered ids. Add one here and
# every stage below picks it up.
# --------------------------------------------------------------------------------------------


def order_shipped(ctx, hex_id, poly_ids):
    """What `scripts.shortcuts.optimise_shortcut_ordering` does: vertex counts, ascending."""
    b = ctx.group(poly_ids)
    sizes = {z: sum(ctx.lengths[i] for i in ps) for z, ps in b.items()}
    get = ctx.lengths.__getitem__
    return [i for z in sorted(b, key=sizes.__getitem__) for i in sorted(b[z], key=get)]


def _weighted(ctx, hex_id, poly_ids, w):
    """Zones by (vertices in this cell) / (area covered) ** w; w=0 is the shipped key."""
    p = ctx.prob(hex_id, poly_ids)
    if p is None or any(v <= 0 for v in p.values()):
        return order_shipped(ctx, hex_id, poly_ids)
    b = ctx.group(poly_ids)
    zkey = lambda z: sum(ctx.lengths[i] for i in b[z]) / sum(p[i] for i in b[z]) ** w  # noqa: E731
    pkey = lambda i: ctx.lengths[i] / p[i] ** w  # noqa: E731
    return [i for z in sorted(b, key=zkey) for i in sorted(b[z], key=pkey)]


def order_area_desc(ctx, hex_id, poly_ids):
    """Pure probability: the likeliest zone tested first."""
    p = ctx.prob(hex_id, poly_ids)
    if p is None:
        return order_shipped(ctx, hex_id, poly_ids)
    b = ctx.group(poly_ids)
    za = {z: sum(p[i] for i in ps) for z, ps in b.items()}
    return [
        i
        for z in sorted(b, key=lambda z: -za[z])
        for i in sorted(b[z], key=lambda i: -p[i])
    ]


def order_area_asc(ctx, hex_id, poly_ids):
    """The likeliest zone kept in the free final slot - the shipped shape, area for size."""
    p = ctx.prob(hex_id, poly_ids)
    if p is None:
        return order_shipped(ctx, hex_id, poly_ids)
    b = ctx.group(poly_ids)
    za = {z: sum(p[i] for i in ps) for z, ps in b.items()}
    return [
        i
        for z in sorted(b, key=lambda z: za[z])
        for i in sorted(b[z], key=lambda i: -p[i])
    ]


def order_true_cost(ctx, hex_id, poly_ids):
    """The shipped structure exactly, with model (2) replacing the vertex count. No areas."""
    c = ctx.cost(hex_id, poly_ids)
    b = ctx.group(poly_ids)
    tot = {z: sum(c[i] for i in ps) for z, ps in b.items()}
    return [
        i
        for z in sorted(b, key=tot.__getitem__)
        for i in sorted(b[z], key=c.__getitem__)
    ]


def order_tiebreak(ctx, hex_id, poly_ids):
    """The shipped key with area breaking its ties, instead of set iteration order (finding 9)."""
    p = ctx.prob(hex_id, poly_ids)
    if p is None:
        return order_shipped(ctx, hex_id, poly_ids)
    b = ctx.group(poly_ids)
    sizes = {z: sum(ctx.lengths[i] for i in ps) for z, ps in b.items()}
    za = {z: sum(p[i] for i in ps) for z, ps in b.items()}
    return [
        i
        for z in sorted(b, key=lambda z: (sizes[z], -za[z]))
        for i in sorted(b[z], key=lambda i: (ctx.lengths[i], -p[i]))
    ]


def _blocks(ctx, hex_id, poly_ids, c, p):
    """Each zone as one composite job: its internally optimal run, its C and its P (step 2)."""
    ratio = lambda i: float("inf") if p[i] <= 0 else c[i] / p[i]  # noqa: E731
    out = {}
    for z, arr in ctx.group(poly_ids).items():
        arr = sorted(arr, key=ratio)
        out[z] = (arr, sum(c[i] for i in arr), sum(p[i] for i in arr))
    return out


def order_optimal(ctx, hex_id, poly_ids):
    """The construction: c/p within a zone, C/P across zones, final slot enumerated (4)."""
    p = ctx.prob(hex_id, poly_ids)
    if p is None:
        return order_true_cost(ctx, hex_id, poly_ids)
    c = ctx.cost(hex_id, poly_ids)
    blocks = _blocks(ctx, hex_id, poly_ids, c, p)
    zr = lambda z: float("inf") if blocks[z][2] <= 0 else blocks[z][1] / blocks[z][2]  # noqa: E731
    ordered = sorted(blocks, key=zr)
    best, best_e = None, float("inf")
    for m in ordered:
        cand = [i for z in ordered if z != m for i in blocks[z][0]] + blocks[m][0]
        e = expected_compute(cand, ctx, c, p)
        if e < best_e:
            best, best_e = cand, e
    return best


def order_optimal_relaxed(ctx, hex_id, poly_ids):
    """Contiguity for the final zone only: the prefix interleaves freely, ratio rule per polygon.

    NOT loadable by the shipped reader as it stands - `check_shortcut_sorting` and
    `has_coherent_sequences` would have to be relaxed first. Kept for the price (finding 6).
    """
    p = ctx.prob(hex_id, poly_ids)
    if p is None:
        return order_true_cost(ctx, hex_id, poly_ids)
    c = ctx.cost(hex_id, poly_ids)
    ratio = lambda i: float("inf") if p[i] <= 0 else c[i] / p[i]  # noqa: E731
    b = ctx.group(poly_ids)
    best, best_e = None, float("inf")
    for m in b:
        prefix = sorted([i for z, arr in b.items() if z != m for i in arr], key=ratio)
        cand = prefix + b[m]
        e = expected_compute(cand, ctx, c, p)
        if e < best_e:
            best, best_e = cand, e
    return best


STRATEGIES = {
    "shipped": order_shipped,
    "tiebreak": order_tiebreak,
    "w0.25": lambda ctx, h, ids: _weighted(ctx, h, ids, 0.25),
    "w0.5": lambda ctx, h, ids: _weighted(ctx, h, ids, 0.5),
    "w1": lambda ctx, h, ids: _weighted(ctx, h, ids, 1.0),
    "area-desc": order_area_desc,
    "area-asc": order_area_asc,
    "true-cost": order_true_cost,
    "optimal": order_optimal,
    "optimal-relaxed": order_optimal_relaxed,
}

#: Orderings the shipped reader cannot load, so `build`/`count`/`ab` skip them.
NOT_LOADABLE = {"optimal-relaxed"}


# --------------------------------------------------------------------------------------------
# Stages
# --------------------------------------------------------------------------------------------


def stage_cells(args):
    """hex id -> candidate polygon ids, order-independent, from the upstream GeoJSON."""
    from scripts.configs import SHORTCUT_H3_RES as GEN_RES
    from scripts.shortcuts import all_res_candidates
    from scripts.timezone_data import TimezoneData

    out = args.work / "cells.pkl"
    if out.exists() and not args.force:
        print(f"{out} exists; --force to recompile")
        return
    data = TimezoneData.from_path(args.geojson)
    print(f"{data.nr_of_polygons} polygons, {data.nr_of_zones} zones", flush=True)
    candidates = all_res_candidates(GEN_RES)
    print(f"resolution {GEN_RES}: {len(candidates):,} cells", flush=True)
    mapping, t0 = {}, time.time()
    for i, hex_id in enumerate(candidates, start=1):
        # sorted, not the set's own order: this script must be reproducible where the shipped
        # generator is not (finding 9)
        mapping[int(hex_id)] = sorted(
            int(p) for p in data.get_hex(hex_id).polys_in_cell
        )
        if i % 25_000 == 0:
            print(f"  {i:,} / {len(candidates):,}  {time.time() - t0:.0f}s", flush=True)
    _dump(
        out,
        {
            "mapping": mapping,
            "zone_ids": data.poly_zone_ids,
            "lengths": list(data.polygon_lengths),
            "resolution": GEN_RES,
        },
    )


def stage_areas(args):
    """Per (cell, candidate) planar overlap area, for the ambiguous cells (P2)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    from shapely.validation import make_valid

    from scripts.hex_utils import is_torn_by_cut, rotate_half_turn
    from scripts.timezone_data import TimezoneData

    out = args.work / "areas.pkl"
    if out.exists() and not args.force:
        print(f"{out} exists; --force to recompute")
        return
    cached = _load(args.work / "cells.pkl")
    zone_ids, mapping = cached["zone_ids"], cached["mapping"]
    ambiguous = {
        h: ids for h, ids in mapping.items() if len({int(zone_ids[i]) for i in ids}) > 1
    }
    print(f"{len(ambiguous):,} ambiguous cells of {len(mapping):,}", flush=True)
    data = TimezoneData.from_path(args.geojson)

    cache: dict[tuple[int, bool], Polygon] = {}

    def poly_of(pid, rot):
        key = (pid, rot)
        if key in cache:
            return cache[key]
        shell = data.polygons[pid]
        holes = list(data.holes_in_poly(pid))
        if rot:
            shell = rotate_half_turn(shell)
            holes = [rotate_half_turn(h) for h in holes]
        poly = Polygon(
            np.ascontiguousarray(shell.T),
            [np.ascontiguousarray(h.T) for h in holes],
        )
        if not poly.is_valid:
            poly = make_valid(poly)
        cache[key] = poly
        return poly

    areas, overlap, covered, skipped, t0 = {}, {}, {}, set(), time.time()
    for n, (hex_id, poly_ids) in enumerate(ambiguous.items(), start=1):
        cell = data.get_hex(hex_id)
        if cell.surr_n_pole or cell.surr_s_pole:
            skipped.add(hex_id)
            continue
        rot = False
        if cell.crosses_antimeridian:
            rot = all(
                not is_torn_by_cut(rotate_half_turn(data.polygons[pid]))
                for pid in poly_ids
            )
            if not rot:
                skipped.add(hex_id)
                continue
        ring = Polygon(
            np.ascontiguousarray((cell.rotated_coords if rot else cell.coords).T)
        )
        try:
            clipped = {pid: ring.intersection(poly_of(pid, rot)) for pid in poly_ids}
            areas[hex_id] = {pid: g.area for pid, g in clipped.items()}
            # Assumption P1, measured rather than asserted: the survival probability in (1) is
            # `1 - sum p_u` only where the hit regions are disjoint. Summed area above union area
            # is exactly the area counted twice, i.e. the area on which two candidates both answer
            # and the ordering therefore decides *which* zone is returned.
            summed = sum(g.area for g in clipped.values())
            united = unary_union(list(clipped.values())).area
            if summed > united * (1 + 1e-9):
                overlap[hex_id] = (summed - united, ring.area)
            # How much of the cell each *zone* covers, as the union of its own candidates. A zone
            # reaching the whole cell means no point in the cell can fall outside it, so the cell
            # could be answered without any geometry at all - see `coverage`.
            by_zone: dict[int, list] = defaultdict(list)
            for pid, geom in clipped.items():
                by_zone[int(zone_ids[pid])].append(geom)
            best = max(unary_union(g).area for g in by_zone.values())
            covered[hex_id] = (best, ring.area)
        except Exception as exc:  # noqa: BLE001 - a bad ring must not lose the whole run
            print(f"\n  cell {hex_id}: {exc}", flush=True)
            skipped.add(hex_id)
        if n % 5_000 == 0:
            print(f"  {n:,} / {len(ambiguous):,}  {time.time() - t0:.0f}s", flush=True)
    print(
        f"{len(areas):,} cells measured, {len(skipped):,} left to the shipped ordering (P2)"
    )
    if areas:
        share = sum(d / c for d, c in overlap.values()) / len(areas)
        worst = max(overlap.values(), key=lambda v: v[0] / v[1], default=(0.0, 1.0))
        print(
            f"P1: candidates overlap in {len(overlap):,} of {len(areas):,} cells "
            f"({len(overlap) / len(areas) * 100:.2f} %); doubly-covered area is "
            f"{share * 100:.3f} % of an average cell and {worst[0] / worst[1] * 100:.1f} % of the "
            f"worst. Where it is non-zero the ordering decides the answer, not only the cost."
        )
    if covered:
        full = [h for h, (b, c) in covered.items() if b >= c * (1 - 1e-9)]
        near = [h for h, (b, c) in covered.items() if b >= c * 0.9999]
        print(
            f"single-zone coverage: {len(full):,} of {len(covered):,} ambiguous cells are covered "
            f"entirely by one zone ({len(full) / len(covered) * 100:.2f} %), {len(near):,} to "
            f"within 1e-4. Those cells need no geometry at all - see the note in `coverage`."
        )
    _dump(
        out,
        {
            "areas": areas,
            "skipped": sorted(skipped),
            "overlap": overlap,
            "covered": covered,
        },
    )


def stage_costs(args):
    """Per (cell, candidate) expected scanned edges (3) and block count, from the shipped index."""
    out = args.work / "costs.pkl"
    if out.exists() and not args.force:
        print(f"{out} exists; --force to recompute")
        return
    cached = _load(args.work / "cells.pkl")
    zone_ids, mapping = cached["zone_ids"], cached["mapping"]
    tf = TimezoneFinder(in_memory=True)
    ranges = np.asarray(tf.boundaries.block_ranges)
    offsets = list(tf.boundaries.block_offsets)
    nr_vertices = np.asarray(tf.boundaries.nr_vertices)
    print(
        f"{len(offsets) - 1:,} polygons, {ranges.shape[0]:,} latitude blocks",
        flush=True,
    )

    def edges_per_block(pid):
        n, nb = int(nr_vertices[pid]), offsets[pid + 1] - offsets[pid]
        counts = np.full(nb, POLYGON_BLOCK_SIZE, dtype=np.int64)
        counts[-1] = n - (nb - 1) * POLYGON_BLOCK_SIZE
        return counts

    def expected(pid, ylo, yhi):
        s, e = offsets[pid], offsets[pid + 1]
        lo = ranges[s:e, 0].astype(np.int64)
        hi = ranges[s:e, 1].astype(np.int64)
        covered = np.clip(np.minimum(hi, yhi) - np.maximum(lo, ylo), 0, None)
        return float((edges_per_block(pid) * covered / max(yhi - ylo, 1)).sum()), int(
            e - s
        )

    ambiguous = {
        h: ids for h, ids in mapping.items() if len({int(zone_ids[i]) for i in ids}) > 1
    }
    costs = {}
    for hex_id, poly_ids in ambiguous.items():
        lats = [pt[0] for pt in h3.cell_to_boundary(hex_id)]
        ylo, yhi = coord2int(min(lats)), coord2int(max(lats))
        costs[hex_id] = {pid: expected(pid, ylo, yhi) for pid in poly_ids}
    _dump(out, costs)

    lengths = cached["lengths"]
    shares = [
        c[0] / lengths[pid]
        for per in costs.values()
        for pid, c in per.items()
        if lengths[pid] >= 512
    ]
    shares.sort()
    print(
        f"rings of >=512 vertices: expected scanned share median "
        f"{shares[len(shares) // 2]:.4f}, min {shares[0]:.5f}, max {shares[-1]:.4f}"
    )
    disagree = same = 0
    for hex_id, per in costs.items():
        ids = list(per)
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                i, j = ids[a], ids[b]
                if (lengths[i] < lengths[j]) != (per[i][0] < per[j][0]):
                    disagree += 1
                else:
                    same += 1
    print(
        f"candidate pairs where the vertex count and model (2) disagree on the cheaper one: "
        f"{disagree:,} of {disagree + same:,} ({disagree / max(disagree + same, 1) * 100:.1f} %)"
    )


def stage_calibrate(args):
    """Fit alpha, beta, gamma of (2) against measured pip times; report R^2 against the proxy."""
    import random

    tf = TimezoneFinder(in_memory=True)
    ba = tf.boundaries
    ranges = np.asarray(ba.block_ranges)
    offsets = list(ba.block_offsets)
    nr_vertices = np.asarray(ba.nr_vertices)
    print(
        f"clang={TimezoneFinder.using_clang_pip()} numba={TimezoneFinder.using_numba()} "
        f"- the backend is bound at import, so run this on both"
    )
    rng = random.Random(args.seed)

    samples = []
    for pid in range(len(offsets) - 1):
        s, e = offsets[pid], offsets[pid + 1]
        ylo, yhi = int(ranges[s:e, 0].min()), int(ranges[s:e, 1].max())
        if yhi <= ylo:
            continue
        n, nb = int(nr_vertices[pid]), e - s
        counts = np.full(nb, POLYGON_BLOCK_SIZE, dtype=np.int64)
        counts[-1] = n - (nb - 1) * POLYGON_BLOCK_SIZE
        for _ in range(3):
            # inside the ring's own latitude span, so the bbox rejection does not dominate
            y = rng.randint(ylo, yhi)
            alive = (y >= ranges[s:e, 0].astype(np.int64)) & (
                y <= ranges[s:e, 1].astype(np.int64)
            )
            samples.append((pid, y, nb, int(counts[alive].sum())))
    rng.shuffle(samples)
    samples = samples[: args.samples]
    print(
        f"{len(samples):,} (polygon, latitude) samples, {args.reps} reps x 5 rounds each"
    )

    pip = ba.pip
    rows, times = [], []
    for pid, y, nb, edges in samples:
        pip(pid, 0, y)  # warm
        # the minimum over rounds, not the mean: the machine's own jitter is one-sided
        best = float("inf")
        for _ in range(5):
            t0 = time.perf_counter()
            for _ in range(args.reps):
                pip(pid, 0, y)
            best = min(best, (time.perf_counter() - t0) / args.reps)
        rows.append([1.0, nb, edges])
        times.append(best * 1e9)

    A, b = np.array(rows), np.array(times)
    coef, *_ = np.linalg.lstsq(A, b, rcond=None)
    ss_tot = float(((b - b.mean()) ** 2).sum())
    r2 = 1 - float(((b - A @ coef) ** 2).sum()) / ss_tot
    print(
        f"\n  time_ns = {coef[0]:.1f} + {coef[1]:.3f} * blocks + {coef[2]:.4f} * in_band_edges"
    )
    print(f"  R^2 = {r2:.4f}")
    proxy = np.array([[1.0, float(nr_vertices[pid])] for pid, _, _, _ in samples])
    pc, *_ = np.linalg.lstsq(proxy, b, rcond=None)
    print(
        f"  total vertex count alone: R^2 = {1 - float(((b - proxy @ pc) ** 2).sum()) / ss_tot:.4f}"
    )
    print(
        f"\nupdate ALPHA_NS / BETA_NS / GAMMA_NS with these before re-running `enumerate`"
    )


def stage_enumerate(args):
    """Score every strategy under the model, brute-force the constructions, price the ceiling."""
    ctx = _context(args)
    totals = {name: 0.0 for name in STRATEGIES}
    oracle = 0.0
    n = brute_checked = 0
    mismatches = defaultdict(int)
    binds_possible = binds_real = 0

    for hex_id, poly_ids in ctx.mapping.items():
        p = ctx.prob(hex_id, poly_ids)
        if p is None or len({ctx.zone_of(i) for i in poly_ids}) < 2:
            continue
        c = ctx.cost(hex_id, poly_ids)
        n += 1
        for name, fn in STRATEGIES.items():
            totals[name] += expected_compute(fn(ctx, hex_id, poly_ids), ctx, c, p)
        # an oracle pays the cheapest candidate once, and nothing when the answer is the zone it
        # would have put last
        b = ctx.group(poly_ids)
        oracle += min(c.values()) * (
            1 - max(sum(p[i] for i in ps) for ps in b.values())
        )

        if len(b) >= 3 or (len(b) >= 2 and any(len(ps) >= 2 for ps in b.values())):
            binds_possible += 1
            if expected_compute(
                order_optimal_relaxed(ctx, hex_id, poly_ids), ctx, c, p
            ) < (
                expected_compute(order_optimal(ctx, hex_id, poly_ids), ctx, c, p) - 1e-9
            ):
                binds_real += 1

        if len(poly_ids) <= args.brute_max:
            brute_checked += 1
            best_cont, best_rel = _brute_force(ctx, poly_ids, c, p)
            if (
                expected_compute(order_optimal(ctx, hex_id, poly_ids), ctx, c, p)
                > best_cont + 1e-6
            ):
                mismatches["optimal"] += 1
            if (
                expected_compute(
                    order_optimal_relaxed(ctx, hex_id, poly_ids), ctx, c, p
                )
                > best_rel + 1e-6
            ):
                mismatches["optimal-relaxed"] += 1

    base = totals["shipped"]
    print(f"{n:,} ambiguous cells with a usable area (P2)\n")
    print(f"{'ordering':<18} {'ns / ambiguous query':>21} {'vs shipped':>12}")
    for name, v in sorted(totals.items(), key=lambda kv: kv[1]):
        print(f"{name:<18} {v / n:>21.1f} {(v / base - 1) * 100:>11.2f} %")
    print(f"{'oracle':<18} {oracle / n:>21.1f} {(oracle / base - 1) * 100:>11.2f} %")

    print(
        f"\nbrute-forced {brute_checked:,} cells (<= {args.brute_max} candidates); "
        f"constructions suboptimal in: "
        + (
            ", ".join(f"{k} {v:,}" for k, v in mismatches.items())
            if mismatches
            else "none"
        )
    )
    print(
        f"contiguity could bind on {binds_possible:,} cells and actually costs something on "
        f"{binds_real:,}"
    )

    saved = (base - totals["optimal"]) / n
    loop_share = base / n / AMBIGUOUS_QUERY_NS
    mixed = (RANDOM_AMBIGUOUS_SHARE * AMBIGUOUS_COST_RATIO) / (
        RANDOM_AMBIGUOUS_SHARE * AMBIGUOUS_COST_RATIO + (1 - RANDOM_AMBIGUOUS_SHARE)
    )
    print(
        f"\ncandidate loop is {loop_share * 100:.1f} % of a {AMBIGUOUS_QUERY_NS:.0f} ns ambiguous "
        f"query; ambiguous work is ~{mixed * 100:.0f} % of a mixed workload"
    )
    print(
        f"  optimal saves {saved:.1f} ns = {saved / AMBIGUOUS_QUERY_NS * 100:.2f} % of an "
        f"ambiguous query = {saved / AMBIGUOUS_QUERY_NS * mixed * 100:.3f} % of a mixed workload"
    )
    ceiling = (base - oracle) / n
    print(
        f"  oracle saves {ceiling:.1f} ns = "
        f"{ceiling / AMBIGUOUS_QUERY_NS * mixed * 100:.2f} % of a mixed workload - the ceiling"
    )
    print("  the benchmark suite's noise floor is 3-9 %")


def _brute_force(ctx, poly_ids, c, p):
    """(best contiguous, best final-zone-only) by enumeration, for the small cells."""
    b = ctx.group(poly_ids)
    best_cont = float("inf")
    for zperm in permutations(b):
        for combo in _within(b, zperm):
            best_cont = min(best_cont, expected_compute(combo, ctx, c, p))
    best_rel = float("inf")
    for m in b:
        rest = [i for z, arr in b.items() if z != m for i in arr]
        for perm in permutations(rest):
            best_rel = min(best_rel, expected_compute(list(perm) + b[m], ctx, c, p))
    return best_cont, best_rel


def _within(b, zperm):
    """Every ordering that keeps each zone of `zperm` contiguous."""
    if not zperm:
        yield []
        return
    head, rest = zperm[0], zperm[1:]
    for arr in permutations(b[head]):
        for tail in _within(b, rest):
            yield list(arr) + tail


def stage_build(args):
    """Write a shortcuts.bin per strategy into a data directory mirroring the packaged one."""
    ctx = _context(args)
    packaged = _packaged_data_dir()
    for name, fn in STRATEGIES.items():
        if name in NOT_LOADABLE:
            print(f"{name:<18} skipped - the shipped reader rejects it")
            continue
        hybrid: dict[int, int | list[int]] = {}
        for hex_id, poly_ids in ctx.mapping.items():
            if not poly_ids:
                continue
            zones = {ctx.zone_of(i) for i in poly_ids}
            hybrid[hex_id] = (
                zones.pop() if len(zones) == 1 else fn(ctx, hex_id, poly_ids)
            )
        target = args.work / "indices" / name
        target.mkdir(parents=True, exist_ok=True)
        out = target / "shortcuts.bin"
        write_shortcuts_binary(
            build_shortcut_index(hybrid, np.asarray(ctx.zone_ids)), out
        )
        for src in packaged.iterdir():
            if src.name != "shortcuts.bin":
                (target / src.name).unlink(missing_ok=True)
                (target / src.name).symlink_to(src)
        note = ""
        if name == "shipped":
            shipped = (packaged / "shortcuts.bin").read_bytes()
            mine = out.read_bytes()
            diff = sum(1 for a, b in zip(shipped, mine, strict=False) if a != b)
            note = f"  ({diff} bytes differ from the packaged index - finding 9)"
        print(f"{name:<18} {out.stat().st_size:>9,} bytes{note}")


def stage_count(args):
    """Exact point-in-polygon test counts and moved answers, over the committed fixtures."""
    from tests.auxiliaries import (
        AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
        ON_LAND_POINTS_FIXTURE,
        RANDOM_POINTS_FIXTURE,
        load_benchmark_points,
    )

    class Counting(TimezoneFinder):
        def __init__(self, **kw):
            super().__init__(**kw)
            self.pip_calls = 0

        def inside_of_polygon(self, boundary_id, x, y):
            self.pip_calls += 1
            return super().inside_of_polygon(boundary_id, x, y)

    names = [n for n in STRATEGIES if n not in NOT_LOADABLE]
    finders = {
        n: Counting(bin_file_location=args.work / "indices" / n, in_memory=True)
        for n in names
    }
    strata = (
        ("ambiguous", AMBIGUOUS_SHORTCUT_POINTS_FIXTURE),
        ("random", RANDOM_POINTS_FIXTURE),
        ("on_land", ON_LAND_POINTS_FIXTURE),
    )
    for label, fixture in strata:
        pts = load_benchmark_points(fixture)
        counts, answers = {}, {}
        for n, tf in finders.items():
            tf.pip_calls = 0
            answers[n] = [tf.timezone_at(lng=a, lat=b) for a, b in pts]
            counts[n] = tf.pip_calls
        print(f"\n[{label}] {len(pts):,} points")
        print(
            f"  {'ordering':<18} {'pip tests':>10} {'vs shipped':>11} {'answers moved':>14}"
        )
        for n in names:
            moved = sum(
                1 for a, b in zip(answers["shipped"], answers[n], strict=True) if a != b
            )
            print(
                f"  {n:<18} {counts[n]:>10,} "
                f"{(counts[n] / counts['shipped'] - 1) * 100:>10.2f} % {moved:>14,}"
            )


def stage_ab(args):
    """Paired, order-alternated whole-query A/B of each strategy against the shipped ordering."""
    from benchmarks.candidate_comparison import compare_candidates
    from tests.auxiliaries import (
        AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
        ON_LAND_POINTS_FIXTURE,
        RANDOM_POINTS_FIXTURE,
        UNIQUE_SHORTCUT_POINTS_FIXTURE,
        load_benchmark_points,
    )

    print(
        f"clang={TimezoneFinder.using_clang_pip()} numba={TimezoneFinder.using_numba()} "
        f"in_memory={args.in_memory}"
    )
    base = TimezoneFinder(
        bin_file_location=args.work / "indices" / "shipped", in_memory=args.in_memory
    )
    wanted = args.only or [
        n for n in STRATEGIES if n not in NOT_LOADABLE and n != "shipped"
    ]
    strata = (
        ("ambiguous", AMBIGUOUS_SHORTCUT_POINTS_FIXTURE),
        ("random", RANDOM_POINTS_FIXTURE),
        ("on_land", ON_LAND_POINTS_FIXTURE),
        # the control: no candidate ordering can reach a unique cell, so if this moves, the
        # comparison is measuring the machine
        ("unique (control)", UNIQUE_SHORTCUT_POINTS_FIXTURE),
    )
    for name in wanted:
        challenger = TimezoneFinder(
            bin_file_location=args.work / "indices" / name, in_memory=args.in_memory
        )
        print(f"\n===== {name} =====")
        for label, fixture in strata:
            result = compare_candidates(
                ("shipped", lambda pt: base.timezone_at(lng=pt[0], lat=pt[1])),
                (name, lambda pt: challenger.timezone_at(lng=pt[0], lat=pt[1])),
                load_benchmark_points(fixture),
                rounds=args.rounds,
            )
            print(f"[{label}]")
            print(result.render())


# --------------------------------------------------------------------------------------------


def _packaged_data_dir() -> Path:
    """The packaged data root - the finder's own, not ``boundaries.data_location``, which is the
    ``boundaries/`` subdirectory beneath it."""
    return Path(TimezoneFinder(in_memory=False).data_location)


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(obj, f)
    print(f"wrote {path}")


def _load(path: Path):
    if not path.exists():
        raise SystemExit(f"{path} missing - run the earlier stage first")
    with path.open("rb") as f:
        return pickle.load(f)


def _context(args) -> Context:
    cached = _load(args.work / "cells.pkl")
    if cached.get("resolution") != SHORTCUT_H3_RES:
        raise SystemExit(
            f"cells.pkl was compiled at H3 resolution {cached.get('resolution')} but this "
            f"checkout indexes at {SHORTCUT_H3_RES} - recompile with `cells --force` "
            f"(finding 8: the bound moves with the resolution)"
        )
    return Context(
        mapping=cached["mapping"],
        zone_ids=cached["zone_ids"],
        lengths=cached["lengths"],
        areas=_load(args.work / "areas.pkl")["areas"],
        costs=_load(args.work / "costs.pkl"),
    )


STAGES = {
    "cells": stage_cells,
    "areas": stage_areas,
    "costs": stage_costs,
    "calibrate": stage_calibrate,
    "enumerate": stage_enumerate,
    "build": stage_build,
    "count": stage_count,
    "ab": stage_ab,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=[*STAGES, "all"])
    parser.add_argument(
        "--geojson",
        type=Path,
        default=Path("tmp/combined-with-oceans-2026c.json"),
        help="the upstream boundaries the packaged data was built from (cells/areas only)",
    )
    parser.add_argument(
        "--work", type=Path, default=Path("tmp/ordering"), help="cache directory"
    )
    parser.add_argument("--force", action="store_true", help="recompute a cached stage")
    parser.add_argument("--rounds", type=int, default=61, help="A/B rounds")
    parser.add_argument(
        "--in-memory", action="store_true", help="A/B against in_memory=True"
    )
    parser.add_argument(
        "--only", nargs="*", help="restrict the A/B to these strategies"
    )
    parser.add_argument(
        "--brute-max",
        type=int,
        default=5,
        help="brute-force cells with at most this many candidates",
    )
    parser.add_argument("--samples", type=int, default=1500, help="calibration samples")
    parser.add_argument(
        "--reps", type=int, default=200, help="calibration reps per sample"
    )
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)

    stages = list(STAGES) if args.stage == "all" else [args.stage]
    for name in stages:
        print(f"\n{'=' * 30} {name} {'=' * 30}")
        STAGES[name](args)


if __name__ == "__main__":
    main()
