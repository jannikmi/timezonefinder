"""Price the flat-array shortcut layouts of #477, on the scalar and the batch path.

``AbstractTimezoneFinder.shortcut_mapping`` is a ``dict[int, int | np.ndarray]`` whose
41,162 ``PyLong`` keys and 10,511 ``ndarray`` view objects are ~99% of its 4.5 MiB, around
46 KB of actual payload. Issue #477 proposes flat arrays instead, and a microbenchmark
there concluded that the obvious implementation (``np.searchsorted``) loses: +355 ns
against a ~1 us unique-zone query. Issue #499 then argued the opposite way - that a flat
layout is the only shape the lookup *vectorises* in, so the scalar penalty is beside the
point for a batch API.

Both arguments rest on lookup-in-isolation timings. This script measures them where they
are actually cashed: through a real ``TimezoneFinder.timezone_at`` with the layout
swapped underneath it, and through a prototype batch resolver over N points. It answers
three questions the issue leaves open:

1. what each layout costs a *whole* scalar query, not a lookup;
2. whether the batch path recovers the scalar loss, and how much of a batch query the
   shortcut lookup even is once the stages around it are paid for;
3. whether the direct-index variant's bit slicing is a lucky hash on the current key set
   or a bijection.

Layouts measured, all built from one loaded dict so they hold identical data:

``dict``          today. ``dict.get(hex_id)`` -> ``int`` or ``ndarray``.
``searchsorted``  sorted ``int64`` keys, ``int16`` zone ids (-1 = polygon list) and a
                  CSR ``offsets``/``poly_ids`` pair. ``np.searchsorted`` plus the bounds
                  and equality check a shipped version needs and the issue's
                  microbenchmark omits.
``direct-csr``    the cell id turned into a dense table index by integer arithmetic on
                  the H3 bit layout (``SLOT_*`` below), into the same CSR payload.
``direct-list``   the same index into a Python ``list`` of ``int | ndarray`` - no key
                  objects, but today's ``match`` dispatch and today's array views kept.

Correctness first: every layout must reproduce the shipped answer for the fixture points
before anything is timed, and the batch resolvers must agree with the scalar ones.

Both backends must be measured - ``timezonefinder/utils.py`` binds point-in-polygon at
import time and numba wins whenever it is importable::

    # numba (what a dev checkout runs)
    PYTHONPATH=. uv run python prototypes/shortcut_layout_bench.py

    # clang (what a plain `pip install timezonefinder` runs, and what CI tracks)
    PYTHONPATH=. uv run --isolated --no-group numba --group proto --group test \
        python prototypes/shortcut_layout_bench.py

``--in-memory`` repeats either against ``TimezoneFinder(in_memory=True)``. Memory is
measured by re-invoking this file as a subprocess per layout (``--memory-probe``), for
the reason ``scripts/_memory_probe.py`` gives: a second layout built in a process that
already built the first measures the allocator.


FINDINGS (2026-08-21, `fcd032c`, Apple arm64, Python 3.14.2, numpy 2.3.5, h3 4.4.2,
data 2026c, fixture set v2)

Taken at `fcd032c`; `bcd78f5` since then changes comments and adds a test, and leaves
every figure below standing. Re-run the script rather than reasoning from these numbers
if anything under ``timezonefinder/`` or the packaged data has moved since.

Both backends were run on the same tree and agree throughout - none of this is geometry,
so the point-in-polygon implementation has nothing to say about it. The tables below are
the ``clang`` / ``in_memory=False`` run, the configuration a plain ``pip install`` in a
constrained container gets and the one CI tracks; the numba run differs by less than the
machine's own jitter and the ``--in-memory`` run by nothing at all. Absolute nanoseconds
are this machine's; what travels is the *ratios* between layouts within one run, which
is all that is claimed.

The noise floor matters here because two of the three candidates land inside it. Repeated
runs move a stratum total by 3-5%, i.e. +-35 ns on a ~1,000 ns unique query and +-400 ns
on a ~10,000 ns ambiguous one. A delta below that is reported as unmeasurable rather than
as a number, and a delta that is small but reproduces its *sign* across seven runs (the
CSR ambiguous row) is reported as real.

The slot map, first, because it is a precondition rather than a measurement: masking off
the base cell and digits 1-3 leaves **the same constant `0x830000fffffffff` on every one
of the 41,162 res-3 cells**, so nothing outside those 16 bits can distinguish two cells
and the map is a **bijection**, not a hash that happens to fit. #477's "collision-free
for all 41,162 cells" is a statement about the packaged key set; this is one about the
resolution. Its open question - pentagons and deleted digit subsequences - dissolves with
it: a deleted subsequence leaves a slot unused, and an unused slot is a hole, not a
collision. The two couplings it buys this with are unchanged and are asserted in code:
h3's internal index encoding, which h3-py does not promise as API, and a table of
``122 * 8**res`` slots, which is fine at res 3 (62,464) and res 4 (499,712) and untenable
beyond.

One lookup in isolation, ns per call, net of the harness's own call:

    step                    ns   vs dict.get
    dict.get                47          1.0x
    slot arithmetic         84          1.8x
    slot + int16 table     120          2.6x
    slot + value list       86          1.9x
    int64 searchsorted     822         17.6x
    uint64 searchsorted 15,019        321.9x

Scalar path, ns per whole ``TimezoneFinder.timezone_at`` query. ``real`` is the shipped
method, ``dict`` this file's reconstruction of it; the delta columns are against ``dict``:

    stratum      real    dict  srchsrt  dir-csr  dir-list   d-srch  d-dcsr  d-dlist
    unique      1,001     986    1,982      990       993     +996      +4       +7
    ambiguous   9,982   9,968   11,383   10,192     9,993   +1,415    +224      +25
    random      3,367   3,360    4,453    3,383     3,379   +1,093     +23      +19

``TimezoneFinderL``, which is the shortcut lookup and nothing else - the worst case, and
the finder whose entire heap is the structure under discussion:

    stratum      real    dict  srchsrt  dir-csr  dir-list   d-srch  d-dcsr  d-dlist
    unique      1,001     956    1,956      958       969   +1,000      +2      +13
    ambiguous   1,121   1,091    2,325    1,331     1,106   +1,234    +240      +15
    random      1,036   1,004    2,064    1,068     1,007   +1,060     +64       +3

The lookup stage alone, ns per point, against batch size - the vectorisation claim:

    N        dict loop  srch raw  srch full   direct  srch gain  dir gain
    1            164.1     747.8    5,483.7  3,168.0      0.03x     0.05x
    10           110.4     131.5      572.7    315.7      0.19x     0.35x
    100           94.1      77.4      144.4     33.0      0.65x     2.85x
    1,000         90.8      95.9      104.8      5.4      0.87x    16.86x
    10,000        90.8      95.1       97.4      2.8      0.93x    32.68x

The whole batch pipeline, ns per point, N = 2,000 in one call:

    stratum    scalar  validate  h3 cells    dict  searchsrt  direct  best gain
    unique        999         3       490     738        595     498      2.01x
    ambiguous  10,003         3       488   9,794     10,055   9,933      1.02x
    random      3,356         3       490   3,122      3,060   2,928      1.15x

Memory, MiB traced by tracemalloc, one fresh subprocess per layout:

    layout          MiB   vs dict
    dict           4.44     +0.00
    searchsorted   0.60     -3.84
    direct-csr     0.40     -4.03
    direct-list    2.41     -2.03

CONCLUSIONS

1. **``searchsorted`` is worse than #477 concluded, and the extra is the check the
   microbenchmark omitted.** It does not cost +355 ns, it costs **+996 ns on a 986 ns
   unique query** - it roughly *doubles* it - and +1,093 ns on a random workload, ~33%.
   In isolation it is 822 ns against ``dict.get``'s 47, and part of that gap to the
   issue's figure is a correct lookup needing a bounds and equality check that
   ``dict.get`` answers for free. The verdict stands, harder: **refuse this variant.**

2. **The direct index costs nothing measurable on the path the hybrid design exists to
   make fast.** +4 ns on a 986 ns unique query, +2 ns on ``TimezoneFinderL`` - both under
   the noise floor, where the isolated probe predicts +45…+75. The issue's "+57 ns, ~6% of
   a query" is right in isolation and overstated in context, and #497's ~5%-of-query
   estimate with it. It is also the *smallest* structure of the three (0.40 MiB), so on
   the unique stratum it is not a trade at all.

3. **The direct index's cost is the Python bit arithmetic, not the table.** Slot
   arithmetic alone is 84 ns, ``slot + value list`` 86 ns - the list index is free - and
   ``slot + int16 table`` 120 ns, so a numpy scalar read costs +34 ns and nothing else
   distinguishes the two payloads on the unique path. Two consequences: the array-vs-list
   choice is decided by the ambiguous path and by memory, not by the fast path; and the
   arithmetic would be nearly free in the C extension or under numba, which is where a
   further win lives if one is ever wanted.

4. **The CSR payload costs ~+200 ns on the ambiguous scalar path, and it is not noise** -
   it reproduced its sign across seven runs. Reconstructing a candidate slice takes three
   numpy scalar reads and a slice where the dict hands out a ready ``ndarray``. That is
   ~2% of an ambiguous query, **+0.7% of a random ``TimezoneFinder`` workload**, and
   **+6% of a random ``TimezoneFinderL`` one** (+240 ns, ~22%, on its ambiguous stratum,
   which reads only the last candidate). ``direct-list`` pays +15 ns there instead and
   gives up half the memory saving - so the real choice is **-4.03 MiB for +0.7% / +6%**,
   or **-2.03 MiB for roughly nothing**, and it is a different answer for the two finders.

5. **The vectorisation argument in #499 is half wrong, and it is the half the sequencing
   rests on.** "``np.searchsorted`` over an array of N cell ids is one call, not N" is
   true and does not help: **one call over N is still not faster than N dict lookups** -
   0.93x at N = 10,000, i.e. *slower*, at every size measured. A binary search over 41,162
   keys is memory-latency-bound at ~90 ns per point, which is what a Python dict lookup
   already costs. Only the **direct index** actually vectorises into a win: 2.85x at
   N = 100 and **32.7x at N = 10,000**, at 2.8 ns per point. So "a flat layout is the only
   shape the lookup vectorises in" needs narrowing to *the direct-index layout*; the
   sorted-key layout enables nothing on either path.

6. **A batch API's ceiling is h3, not the shortcut structure.** With the direct index a
   unique-stratum batch costs 498 ns per point, of which **490 is
   ``h3.latlng_to_cell``** - h3-py 4.4 exposes no vectorised version, so N points cost N
   scalar C calls and no layout touches that. The layout is worth ~240 ns per point of a
   738 ns batch; the batch itself is worth ~260 ns per point of a 999 ns scalar query. On
   a random workload the whole batch path is **1.15x** and the layout is about a third of
   it. Both are real and neither is the order-of-magnitude the "~1 M lookups/s ceiling
   made of interpreter overhead" framing suggests. **The next lever for #499 is h3.**

   Bounding caveat, in the honest direction: this prototype's ambiguous fallback is
   entirely scalar and unoptimised - per point ``zone_ids_of``, ``get_last_change_idx``
   and the candidate loop, exactly as the scalar path runs them. The ambiguous and random
   rows are therefore a *lower* bound on what a batch API could reach; the unique row,
   where there is no fallback at all, is not.

7. **The memory saving is confirmed and slightly larger than estimated.** #477 predicted
   ~0.67 MiB and -3.8 MiB for the sorted-key layout from ``sys.getsizeof``; measured
   0.60 MiB and -3.84. The direct index beats it at 0.40 MiB / **-4.03 MiB**, ~91% of the
   4.44 MiB the dict occupies. Its 66% slot density costs ~0.12 MiB against a tighter
   base-7 packing, which is not worth the extra arithmetic at this size.

8. **The ``uint64`` landmine reproduces exactly and belongs in the loader as a comment.**
   15,019 ns against 822 ns for the same search over ``int64`` keys, and **322x
   ``dict.get``** - silently correct, so only a benchmark ever catches it. h3 cell ids
   have bit 63 clear, so ``int64`` is always safe.

WHAT THIS SETTLES

The layout to build, if #477 is built, is the **direct index**, and the payload question
(CSR arrays vs a list of values) is a separate 2 MiB-against-6%-of-``TimezoneFinderL``
decision that these numbers price but do not make. The sorted-key layout is refused on
both paths. And #499's dependency on #477 is weaker than recorded: a batch API on today's
dict already reaches 1.15x on a random workload and 1.35x on the unique stratum, so the
flat layout is an improvement to it rather than a precondition for it.

"""

import argparse
import gc
import json
import subprocess
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

import numpy as np
from h3.api import numpy_int as h3

from scripts.assert_acceleration_path import active_acceleration_path
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder, TimezoneFinderL, utils
from timezonefinder.configs import SHORTCUT_H3_RES

# one pass over this many points is a round; the reported value is the min over
# ``REPEATS`` rounds, the estimator the benchmark suite tracks
BATCH_SIZE = 2_000
REPEATS = 15
# batch sizes the amortisation curve is taken at
BATCH_SIZES = (1, 10, 100, 1_000, 10_000)

# ---------------------------------------------------------------------------
# the direct index: H3 cell id -> dense table slot
# ---------------------------------------------------------------------------
# H3 packs a cell index as: bit 63 reserved, bits 62-59 mode, bits 58-56
# mode-dependent, bits 55-52 resolution, bits 51-45 base cell, then fifteen 3-bit
# digits from bit 44 down to bit 0. For a *fixed* resolution r, everything except the
# base cell and digits 1..r is constant - the unused digits r+1..15 are all 7. So at
# resolution 3 the 16 varying bits below are the whole index, and the map to a slot is
# a bijection rather than a hash. ``verify_slot_bijection`` proves that over the full
# domain (every res-3 cell), not just over the packaged keys.
#
# The cost: this hard-codes an encoding h3-py does not promise as API, and the table is
# ``122 * 8**res`` slots - fine at res 3 (62,464) and res 4 (499,712), untenable past
# that. Both are asserted rather than commented.
SLOT_BASE_CELL_SHIFT = 45
SLOT_BASE_CELL_MASK = 0x7F
SLOT_DIGIT_BITS = 3
SLOT_DIGITS_SHIFT = SLOT_BASE_CELL_SHIFT - SLOT_DIGIT_BITS * SHORTCUT_H3_RES
SLOT_DIGITS_MASK = (1 << (SLOT_DIGIT_BITS * SHORTCUT_H3_RES)) - 1
SLOT_STRIDE = SLOT_DIGITS_MASK + 1
NUM_BASE_CELLS = 122
SLOT_TABLE_SIZE = NUM_BASE_CELLS * SLOT_STRIDE

# -1 marks an entry whose value is a polygon list, -2 an absent cell. Custom data can
# leave cells uncovered, so "absent" is a real state and not just padding.
POLYGON_LIST = -1
ABSENT = -2


def slot_of(hex_id: int) -> int:
    """Dense table index of one H3 cell id. Scalar; see ``slots_of`` for arrays."""
    return ((hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * SLOT_STRIDE + (
        (hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK
    )


def slots_of(hex_ids: np.ndarray) -> np.ndarray:
    """Dense table indices of an array of H3 cell ids, vectorised."""
    return ((hex_ids >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * SLOT_STRIDE + (
        (hex_ids >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK
    )


def all_cells_at_shortcut_res() -> np.ndarray:
    """Every H3 cell id at ``SHORTCUT_H3_RES``, as ``int64``."""
    cells: list[int] = []
    for res0 in h3.get_res0_cells():
        cells.extend(int(c) for c in h3.cell_to_children(res0, SHORTCUT_H3_RES))
    return np.array(sorted(cells), dtype=np.int64)


def verify_slot_layout_against_h3_api() -> tuple[int, int]:
    """Check the bit arithmetic against h3's *public* API, cell by cell.

    This is what makes addressing entries by H3 bit position a checked invariant rather
    than a trusted one, and it is the whole answer to "h3-py does not promise the index
    encoding as API". It does not have to: ``get_base_cell_number`` and
    ``cell_to_child_pos`` are public, and between them they determine a cell's position
    exactly as the bits do. So the fast path can slice bits while a build-time check
    proves that slicing agrees with the supported accessors over every cell that exists.
    If h3 ever changes the layout, this fails loudly where the data is produced instead
    of silently returning a neighbour's timezone.

    Cost is why it lives here and not on the lookup path: the public route is ~218 ns
    against ~87 ns for the arithmetic, which is irrelevant once per build and 2.5x the
    whole shortcut lookup per query.

    Returns (cells checked, size of the dense index the public API would give).
    """
    cells = all_cells_at_shortcut_res()

    # a dense index derived only from public API, used as the reference
    res0 = sorted(int(c) for c in h3.get_res0_cells())
    base_offset: dict[int, int] = {}
    run = 0
    for cell in res0:
        base_offset[int(h3.get_base_cell_number(cell))] = run
        run += int(h3.cell_to_children_size(cell, SHORTCUT_H3_RES))

    base_from_bits = (cells >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK
    public_index = np.empty(len(cells), dtype=np.int64)
    for i, cell in enumerate(cells):
        cell = int(cell)
        base = int(h3.get_base_cell_number(cell))
        if base != int(base_from_bits[i]):
            raise AssertionError(
                f"h3's index encoding has moved: cell {cell:#x} reports base cell {base} "
                f"through get_base_cell_number and {int(base_from_bits[i])} at bits "
                f"{SLOT_BASE_CELL_SHIFT}-{SLOT_BASE_CELL_SHIFT + 6}. The shortcut binary "
                f"addresses entries by those bits, so every lookup in it is now wrong. "
                f"Regenerate the data and bump SHORTCUT_LAYOUT_VERSION with "
                f"DATA_FORMAT_VERSION."
            )
        public_index[i] = base_offset[base] + int(h3.cell_to_child_pos(cell, 0))

    slots = slots_of(cells)
    # the two must order the cells identically: same base cell first, then same digit
    # sequence. Equality of the indices themselves is not expected - the bit form is
    # base-8 per digit and therefore sparser than the public form.
    if not np.array_equal(np.argsort(slots), np.argsort(public_index)):
        raise AssertionError(
            "the bit-derived slot orders cells differently from h3's public "
            "get_base_cell_number / cell_to_child_pos. The shortcut binary's entry order "
            "no longer means what it did; regenerate the data and bump "
            "SHORTCUT_LAYOUT_VERSION with DATA_FORMAT_VERSION."
        )
    return len(cells), int(public_index.max()) + 1


def verify_slot_bijection() -> tuple[int, int]:
    """Prove the slot map is injective over the whole resolution, not the key set.

    The issue records the direct-index variant as "collision-free for all 41,162
    cells", which is a statement about the packaged data, and notes that pentagons and
    deleted digit subsequences were never examined. The stronger statement is
    available: mask off the base cell and the used digits, and every valid cell id at
    this resolution leaves the *same* constant behind, so nothing outside those 16 bits
    can distinguish two cells. That, plus injectivity over the enumerated domain, is
    the whole proof. Pentagons cost nothing here either - their deleted subsequences
    leave slots unused, and an unused slot is a hole, not a collision.
    """
    if SHORTCUT_H3_RES != 3:
        raise AssertionError(
            f"the slot table is {NUM_BASE_CELLS} * 8**{SHORTCUT_H3_RES} = "
            f"{SLOT_TABLE_SIZE} entries; this prototype was measured at resolution 3"
        )
    cells = all_cells_at_shortcut_res()
    invariant = cells & ~np.int64(
        (SLOT_BASE_CELL_MASK << SLOT_BASE_CELL_SHIFT)
        | (SLOT_DIGITS_MASK << SLOT_DIGITS_SHIFT)
    )
    distinct_invariants = np.unique(invariant)
    if len(distinct_invariants) != 1:
        raise AssertionError(
            "cell ids at this resolution differ outside the slot bits: "
            f"{[hex(int(v)) for v in distinct_invariants[:8]]}"
        )
    slots = slots_of(cells)
    if len(np.unique(slots)) != len(cells):
        raise AssertionError("the slot map collides on the full cell domain")
    if int(slots.max()) >= SLOT_TABLE_SIZE:
        raise AssertionError("a slot fell outside the table")
    return len(cells), int(distinct_invariants[0])


# ---------------------------------------------------------------------------
# the layouts
# ---------------------------------------------------------------------------


class FlatShortcuts:
    """The flat layouts, all built from one loaded dict so they hold identical data.

    ``sorted_keys`` / ``zone_ids`` / ``offsets`` / ``poly_ids`` are the sorted-key
    (``searchsorted``) layout; ``zone_by_slot`` / ``offsets_by_slot`` the direct-index
    one; ``value_by_slot`` the direct-index list variant. A shipped version would build
    exactly one of them straight out of the FlatBuffer, without the dict ever existing.
    """

    def __init__(self, mapping: dict[int, int | np.ndarray]) -> None:
        keys = np.fromiter(mapping.keys(), dtype=np.int64, count=len(mapping))
        self.sorted_keys = np.sort(keys)
        n = len(keys)

        # int16 rather than the data's uint16 because of the two sentinels; it holds
        # while there are fewer than 2**15 zones, which the check below pins
        zone_ids = np.empty(n, dtype=np.int16)
        offsets = np.zeros(n + 1, dtype=np.int32)
        payload: list[np.ndarray] = []
        cursor = 0
        for i, key in enumerate(self.sorted_keys):
            value = mapping[int(key)]
            if isinstance(value, (int, np.integer)):
                if value >= np.iinfo(np.int16).max:
                    raise AssertionError("zone id too large for an int16 layout")
                zone_ids[i] = value
            else:
                zone_ids[i] = POLYGON_LIST
                payload.append(value)
                cursor += len(value)
            offsets[i + 1] = cursor
        self.zone_ids = zone_ids
        self.offsets = offsets
        self.poly_ids = (
            np.concatenate(payload) if payload else np.empty(0, dtype=np.uint16)
        )

        # direct-index: the same content addressed by slot, so no key array and no
        # search. Absent slots are real - the packaged index is dense, custom data
        # need not be.
        self.zone_by_slot = np.full(SLOT_TABLE_SIZE, ABSENT, dtype=np.int16)
        self.value_by_slot: list[int | np.ndarray | None] = [None] * SLOT_TABLE_SIZE
        # a per-slot length that is cumulatively summed, rather than the sorted-key
        # offsets copied across: an absent slot has to yield an empty range without
        # overwriting the start offset of the present slot that follows it
        lengths_by_slot = np.zeros(SLOT_TABLE_SIZE, dtype=np.int32)
        for i, key in enumerate(self.sorted_keys):
            slot = slot_of(int(key))
            self.zone_by_slot[slot] = zone_ids[i]
            self.value_by_slot[slot] = mapping[int(key)]
            lengths_by_slot[slot] = offsets[i + 1] - offsets[i]
        self.offsets_by_slot = np.zeros(SLOT_TABLE_SIZE + 1, dtype=np.int32)
        np.cumsum(lengths_by_slot, out=self.offsets_by_slot[1:])
        # slot order and sorted-key order are the same (the base cell occupies the high
        # bits of both), so the payload built above is already in slot order


def resolve_candidate_zone(
    finder: TimezoneFinder, poly_ids: np.ndarray, lng: float, lat: float
) -> int | None:
    """The half of ``timezone_at`` below the shortcut lookup, as a zone id.

    Shared verbatim by every layout, scalar and batch, including the ``dict``
    prototype, so that a difference between two rows is the lookup and nothing else.
    It is a *copy* of the tail of ``TimezoneFinder.timezone_at`` and pays one function
    call the real inlined method does not - which is why the tables also carry a
    ``real`` row, to price that harness overhead rather than hide it.

    A zone id rather than a name because that is what #499 decided the batch API
    returns primarily; the scalar prototypes convert at the end, as the real method
    does.
    """
    if len(poly_ids) == 0:
        return None
    zone_ids = finder.zone_ids_of(poly_ids)
    last_zone_change_idx = utils.get_last_change_idx(zone_ids)
    x = utils.coord2int(lng)
    y = utils.coord2int(lat)
    for i, boundary_id in enumerate(poly_ids):
        if i >= last_zone_change_idx:
            break
        if finder.inside_of_polygon(boundary_id, x, y):
            return int(zone_ids[i])
    return int(zone_ids[-1])


# ---------------------------------------------------------------------------
# scalar prototypes: one `timezone_at` per layout, differing only above the tail
# ---------------------------------------------------------------------------
# ``slot_of`` is inlined at every call site below. Charging the direct-index variants a
# Python function call (~60 ns, comparable to the whole dict lookup) would measure this
# file rather than the layout.


def scalar_dict(tf: TimezoneFinder, flat: FlatShortcuts, lng: float, lat: float):
    lng, lat = utils.validate_coordinates(lng, lat)
    hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
    value = tf.shortcut_mapping.get(hex_id)
    if value is None:
        return None
    match value:
        case int(zone_id):
            return tf.zone_name_from_id(zone_id)
    zone_id = resolve_candidate_zone(tf, value, lng, lat)
    return None if zone_id is None else tf.zone_name_from_id(zone_id)


def scalar_searchsorted(
    tf: TimezoneFinder, flat: FlatShortcuts, lng: float, lat: float
):
    lng, lat = utils.validate_coordinates(lng, lat)
    hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
    keys = flat.sorted_keys
    i = np.searchsorted(keys, hex_id)
    # the bounds and equality check the issue's microbenchmark omits: `dict.get`
    # answers "absent" for free and `searchsorted` does not, and custom data with
    # uncovered cells makes absence reachable
    if i == len(keys) or keys[i] != hex_id:
        return None
    zone_id = flat.zone_ids[i]
    if zone_id >= 0:
        return tf.zone_name_from_id(int(zone_id))
    poly_ids = flat.poly_ids[flat.offsets[i] : flat.offsets[i + 1]]
    zone_id = resolve_candidate_zone(tf, poly_ids, lng, lat)
    return None if zone_id is None else tf.zone_name_from_id(zone_id)


def scalar_direct_csr(tf: TimezoneFinder, flat: FlatShortcuts, lng: float, lat: float):
    lng, lat = utils.validate_coordinates(lng, lat)
    hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
    slot = ((hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * SLOT_STRIDE + (
        (hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK
    )
    zone_id = flat.zone_by_slot[slot]
    if zone_id >= 0:
        return tf.zone_name_from_id(int(zone_id))
    if zone_id == ABSENT:
        return None
    poly_ids = flat.poly_ids[
        flat.offsets_by_slot[slot] : flat.offsets_by_slot[slot + 1]
    ]
    zone_id = resolve_candidate_zone(tf, poly_ids, lng, lat)
    return None if zone_id is None else tf.zone_name_from_id(zone_id)


def scalar_direct_list(tf: TimezoneFinder, flat: FlatShortcuts, lng: float, lat: float):
    lng, lat = utils.validate_coordinates(lng, lat)
    hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
    slot = ((hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * SLOT_STRIDE + (
        (hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK
    )
    value = flat.value_by_slot[slot]
    if value is None:
        return None
    match value:
        case int(zone_id):
            return tf.zone_name_from_id(zone_id)
    zone_id = resolve_candidate_zone(tf, value, lng, lat)
    return None if zone_id is None else tf.zone_name_from_id(zone_id)


SCALAR_LAYOUTS: dict[str, Callable] = {
    "dict": scalar_dict,
    "searchsorted": scalar_searchsorted,
    "direct-csr": scalar_direct_csr,
    "direct-list": scalar_direct_list,
}


# ---------------------------------------------------------------------------
# batch prototypes: N points in one call, per layout
# ---------------------------------------------------------------------------
# Shaped after #499's decided design - zone *ids* are the primary return, names a
# convenience - because that is what decides how much of the batch vectorises. With
# ids, a unique-shortcut cell needs no per-point Python at all once the lookup is
# vectorised; with names, every point pays a list index whatever the layout is.
#
# NO_ZONE is what a batch API returns for a cell the index does not cover. It is -1
# because that is the sentinel #499 settled on, and BUG-1 has to land first because -1
# is currently a *valid* zone id argument elsewhere.
NO_ZONE = -1


def validate_batch(lngs: np.ndarray, lats: np.ndarray) -> None:
    """The vectorised equivalent of ``validate_coordinates``, paid once per call."""
    if not (np.isfinite(lngs).all() and np.isfinite(lats).all()):
        raise ValueError("coordinates must be finite")
    if lngs.min() < -180.0 or lngs.max() > 180.0:
        raise ValueError("longitude out of bounds")
    if lats.min() < -90.0 or lats.max() > 90.0:
        raise ValueError("latitude out of bounds")


def cells_of(lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
    """H3 cell ids for N points.

    N scalar calls, and there is no way around it: h3-py 4.4 exposes no vectorised
    ``latlng_to_cell`` - passing arrays raises ``TypeError: only length-1 arrays can be
    converted to Python scalars`` - and ``h3.api.numpy_int`` only changes the types of
    the set-returning functions. This stage is therefore identical for every layout,
    and its size decides how much a vectorised lookup can possibly be worth.
    """
    return np.fromiter(
        (h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES) for lat, lng in zip(lats, lngs)),
        dtype=np.int64,
        count=len(lngs),
    )


def lookup_searchsorted(
    flat: FlatShortcuts, cells: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """One ``searchsorted`` over all N cells. Returns (entry index, zone id)."""
    idx = np.searchsorted(flat.sorted_keys, cells)
    np.clip(idx, 0, len(flat.sorted_keys) - 1, out=idx)
    zone_ids = np.where(flat.sorted_keys[idx] == cells, flat.zone_ids[idx], ABSENT)
    return idx, zone_ids


def lookup_direct(
    flat: FlatShortcuts, cells: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Pure integer arithmetic over all N cells. Returns (slot, zone id)."""
    slots = slots_of(cells)
    return slots, flat.zone_by_slot[slots]


def batch_dict(tf: TimezoneFinder, flat: FlatShortcuts, lngs, lats) -> np.ndarray:
    validate_batch(lngs, lats)
    cells = cells_of(lngs, lats)
    mapping = tf.shortcut_mapping
    # accumulated as a Python list and converted once: writing into an int16 array per
    # element costs more than the lookup being measured
    out: list[int] = []
    for k, hex_id in enumerate(cells.tolist()):
        value = mapping.get(hex_id)
        if value is None:
            out.append(NO_ZONE)
            continue
        match value:
            case int(zone_id):
                out.append(zone_id)
            case _:
                zone_id = resolve_candidate_zone(tf, value, lngs[k], lats[k])
                out.append(NO_ZONE if zone_id is None else zone_id)
    return np.array(out, dtype=np.int16)


def _batch_flat(
    tf: TimezoneFinder,
    flat: FlatShortcuts,
    lngs,
    lats,
    lookup: Callable[[FlatShortcuts, np.ndarray], tuple[np.ndarray, np.ndarray]],
    offsets: np.ndarray,
) -> np.ndarray:
    validate_batch(lngs, lats)
    cells = cells_of(lngs, lats)
    idx, zone_ids = lookup(flat, cells)
    out = zone_ids.astype(np.int16, copy=True)
    # unique-shortcut cells are already answered - no per-point Python at all
    out[zone_ids == ABSENT] = NO_ZONE
    for k in np.flatnonzero(zone_ids == POLYGON_LIST):
        i = idx[k]
        poly_ids = flat.poly_ids[offsets[i] : offsets[i + 1]]
        zone_id = resolve_candidate_zone(tf, poly_ids, lngs[k], lats[k])
        out[k] = NO_ZONE if zone_id is None else zone_id
    return out


def batch_searchsorted(tf, flat, lngs, lats) -> np.ndarray:
    return _batch_flat(tf, flat, lngs, lats, lookup_searchsorted, flat.offsets)


def batch_direct(tf, flat, lngs, lats) -> np.ndarray:
    return _batch_flat(tf, flat, lngs, lats, lookup_direct, flat.offsets_by_slot)


BATCH_LAYOUTS: dict[str, Callable] = {
    "dict": batch_dict,
    "searchsorted": batch_searchsorted,
    "direct": batch_direct,
}


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------

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


def check_agreement(
    tf: TimezoneFinder, flat: FlatShortcuts, strata: dict[str, Points]
) -> int:
    """Every layout must answer as the shipped method, or nothing below is comparable."""
    checked = 0
    for name, points in strata.items():
        for lng, lat in points:
            expected = tf.timezone_at(lng=lng, lat=lat)
            for layout, fn in SCALAR_LAYOUTS.items():
                got = fn(tf, flat, lng, lat)
                if got != expected:
                    raise AssertionError(
                        f"{layout} disagrees on {name} point ({lng}, {lat}): "
                        f"{got!r} != {expected!r}"
                    )
            checked += 1
    # the batch resolvers must agree with the scalar ones too, over the same points
    for name, points in strata.items():
        lngs = np.array([p[0] for p in points], dtype=np.float64)
        lats = np.array([p[1] for p in points], dtype=np.float64)
        expected_ids = np.array(
            [
                NO_ZONE
                if (n := tf.timezone_at(lng=lng, lat=lat)) is None
                else tf.timezone_names.index(n)
                for lng, lat in points
            ],
            dtype=np.int16,
        )
        for layout, fn in BATCH_LAYOUTS.items():
            got = fn(tf, flat, lngs, lats)
            if not np.array_equal(got, expected_ids):
                bad = int(np.flatnonzero(got != expected_ids)[0])
                raise AssertionError(
                    f"batch {layout} disagrees on {name} point {bad}: "
                    f"{got[bad]} != {expected_ids[bad]}"
                )
    return checked


def scalar_probes(mapping: dict, flat: FlatShortcuts, hex_id: int) -> dict[str, float]:
    """Time the individual scalar lookup steps, in ns per call.

    Two of these exist to attribute a result rather than to produce one. ``slot
    arithmetic`` is the direct index's five Python integer operations with no table
    access at all: if it dominates, the choice between an ``int16`` array and a Python
    list of values is not a choice. ``uint64 searchsorted`` re-measures the trap #477
    records so it does not have to be taken on trust - ``uint64`` is the natural dtype
    for an H3 cell id, numpy has no common type for ``uint64`` and a Python ``int``, so
    the comparison falls back to ``object`` dtype, and the result is silently correct
    and catastrophically slow.
    """
    keys64 = flat.sorted_keys
    keysu = keys64.astype(np.uint64)
    zone_by_slot = flat.zone_by_slot
    value_by_slot = flat.value_by_slot

    # the slot expression is written out at every probe below rather than calling
    # ``slot_of``, for the same reason the scalar prototypes inline it: a Python
    # function call is the size of the whole lookup being measured
    def slot_only():
        return (
            (hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK
        ) * SLOT_STRIDE + ((hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK)

    def slot_table():
        return zone_by_slot[
            ((hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * SLOT_STRIDE
            + ((hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK)
        ]

    def slot_list():
        return value_by_slot[
            ((hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * SLOT_STRIDE
            + ((hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK)
        ]

    def per_call(fn: Callable[[], object], reps: int, repeats: int = 5) -> float:
        return measure(lambda: [fn() for _ in range(reps)], repeats) / reps * 1e9

    # every row is net of the harness's own call, measured the same way
    empty = per_call(lambda: None, 20_000)
    return {
        "(harness call)": empty,
        "dict.get": per_call(lambda: mapping.get(hex_id), 20_000) - empty,
        "slot arithmetic": per_call(slot_only, 20_000) - empty,
        "slot + int16 table": per_call(slot_table, 20_000) - empty,
        "slot + value list": per_call(slot_list, 20_000) - empty,
        "int64 searchsorted": per_call(lambda: np.searchsorted(keys64, hex_id), 5_000)
        - empty,
        "uint64 searchsorted": per_call(lambda: np.searchsorted(keysu, hex_id), 200, 3)
        - empty,
    }


# ---------------------------------------------------------------------------
# memory: one subprocess per layout
# ---------------------------------------------------------------------------
# Same reasoning as scripts/_memory_probe.py: a second layout built in a process that
# already built the first measures the allocator, not the layout. The probe builds the
# dict, builds the layout from it, drops the dict and reports what tracemalloc still
# traces - so a real loader's *transient* peak (which would not route through a dict at
# all) is deliberately not what is reported.

MEMORY_LAYOUTS = ("dict", "searchsorted", "direct-csr", "direct-list")


def memory_probe(layout: str) -> dict[str, int]:
    import tracemalloc  # noqa: PLC0415 - only the probe process pays for it

    from timezonefinder.flatbuf.io.hybrid_shortcuts import (  # noqa: PLC0415
        get_hybrid_shortcut_file_path,
        read_hybrid_shortcuts_binary,
    )

    tf = TimezoneFinder()
    path = get_hybrid_shortcut_file_path(tf.zone_ids.dtype, tf.data_location)
    del tf
    gc.collect()

    tracemalloc.start()
    mapping = read_hybrid_shortcuts_binary(path)
    kept: object
    if layout == "dict":
        kept = mapping
    else:
        flat = FlatShortcuts(mapping)
        if layout == "searchsorted":
            kept = (flat.sorted_keys, flat.zone_ids, flat.offsets, flat.poly_ids)
        elif layout == "direct-csr":
            kept = (flat.zone_by_slot, flat.offsets_by_slot, flat.poly_ids)
        elif layout == "direct-list":
            kept = flat.value_by_slot
        else:
            raise ValueError(layout)
        del flat
        del mapping
    gc.collect()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert kept is not None
    return {"layout": layout, "current": current, "peak": peak}


def measure_memory(python: str) -> list[dict[str, int]]:
    results = []
    for layout in MEMORY_LAYOUTS:
        proc = subprocess.run(
            [python, str(Path(__file__).resolve()), "--memory-probe", layout],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        results.append(json.loads(proc.stdout.strip().splitlines()[-1]))
    return results


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

QUERY_STRATA = (
    ("unique", UNIQUE_SHORTCUT_POINTS_FIXTURE),
    ("ambiguous", AMBIGUOUS_SHORTCUT_POINTS_FIXTURE),
    ("random", RANDOM_POINTS_FIXTURE),
)


def table(header: str, columns: Sequence[str], rows: Iterable[Sequence[str]]) -> None:
    rows = list(rows)
    widths = [
        max(len(columns[c]), *(len(r[c]) for r in rows)) for c in range(len(columns))
    ]
    print(f"\n{header}")
    print("  " + "  ".join(h.rjust(w) for h, w in zip(columns, widths)))
    print("  " + "-" * (sum(widths) + 2 * (len(widths) - 1)))
    for row in rows:
        print("  " + "  ".join(c.rjust(w) for c, w in zip(row, widths)))


def _ns_per_point(fn: Callable[[], object], n: int) -> float:
    return measure(fn) / n * 1e9


def report_scalar(
    tf: TimezoneFinder, flat: FlatShortcuts, strata: dict[str, Points]
) -> None:
    rows = []
    for stratum, points in strata.items():
        batch = points[:BATCH_SIZE]
        real = _ns_per_point(
            lambda: [tf.timezone_at(lng=p[0], lat=p[1]) for p in batch], len(batch)
        )
        cells = [f"{real:,.0f}"]
        for fn in SCALAR_LAYOUTS.values():
            per_call = _ns_per_point(
                lambda fn=fn: [fn(tf, flat, p[0], p[1]) for p in batch], len(batch)
            )
            cells.append(f"{per_call:,.0f}")
        base = float(cells[1].replace(",", ""))
        deltas = [f"{float(c.replace(',', '')) - base:+,.0f}" for c in cells[2:]]
        rows.append([stratum, *cells, *deltas])
    table(
        "Scalar path - ns per timezone_at() query, min over "
        f"{REPEATS} passes of {BATCH_SIZE} points",
        [
            "stratum",
            "real",
            "dict",
            "srchsrt",
            "dir-csr",
            "dir-list",
            "d-srch",
            "d-dcsr",
            "d-dlist",
        ],
        rows,
    )
    print(
        "  `real` is the shipped TimezoneFinder.timezone_at; `dict` is this file's\n"
        "  reconstruction of it, and the gap between the two is the prototype's own\n"
        "  overhead. The three delta columns are against `dict`, not against `real`."
    )


def report_finder_l(strata: dict[str, Points], flat: FlatShortcuts) -> None:
    """The worst case: a finder that is nothing but the shortcut lookup."""
    tfl = TimezoneFinderL()
    names = tfl.timezone_names
    mapping = tfl.shortcut_mapping

    def l_dict(lng, lat):
        lng, lat = utils.validate_coordinates(lng, lat)
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
        value = mapping.get(hex_id)
        match value:
            case None:
                return None
            case int(zone_id):
                return names[zone_id]
            case polygon_array if len(polygon_array) == 0:
                return None
            case polygon_array:
                return names[int(tfl.zone_id_of(polygon_array[-1]))]

    def l_searchsorted(lng, lat):
        lng, lat = utils.validate_coordinates(lng, lat)
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
        keys = flat.sorted_keys
        i = np.searchsorted(keys, hex_id)
        if i == len(keys) or keys[i] != hex_id:
            return None
        zone_id = flat.zone_ids[i]
        if zone_id >= 0:
            return names[int(zone_id)]
        start, end = flat.offsets[i], flat.offsets[i + 1]
        if start == end:
            return None
        return names[int(tfl.zone_id_of(flat.poly_ids[end - 1]))]

    def l_direct(lng, lat):
        lng, lat = utils.validate_coordinates(lng, lat)
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
        slot = (
            (hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK
        ) * SLOT_STRIDE + ((hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK)
        zone_id = flat.zone_by_slot[slot]
        if zone_id >= 0:
            return names[int(zone_id)]
        if zone_id == ABSENT:
            return None
        start, end = flat.offsets_by_slot[slot], flat.offsets_by_slot[slot + 1]
        if start == end:
            return None
        return names[int(tfl.zone_id_of(flat.poly_ids[end - 1]))]

    def l_direct_list(lng, lat):
        lng, lat = utils.validate_coordinates(lng, lat)
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
        value = flat.value_by_slot[
            ((hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * SLOT_STRIDE
            + ((hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK)
        ]
        match value:
            case None:
                return None
            case int(zone_id):
                return names[zone_id]
            case polygon_array if len(polygon_array) == 0:
                return None
            case polygon_array:
                return names[int(tfl.zone_id_of(polygon_array[-1]))]

    variants = {
        "dict": l_dict,
        "searchsorted": l_searchsorted,
        "direct-csr": l_direct,
        "direct-list": l_direct_list,
    }
    for stratum, points in strata.items():
        for fn in variants.values():
            for lng, lat in points[:200]:
                assert fn(lng, lat) == tfl.timezone_at(lng=lng, lat=lat), (
                    stratum,
                    lng,
                    lat,
                )
    rows = []
    for stratum, points in strata.items():
        batch = points[:BATCH_SIZE]
        real = _ns_per_point(
            lambda: [tfl.timezone_at(lng=p[0], lat=p[1]) for p in batch], len(batch)
        )
        cells = [f"{real:,.0f}"]
        for fn in variants.values():
            per_call = _ns_per_point(
                lambda fn=fn: [fn(p[0], p[1]) for p in batch], len(batch)
            )
            cells.append(f"{per_call:,.0f}")
        base = float(cells[1].replace(",", ""))
        rows.append(
            [
                stratum,
                *cells,
                *(f"{float(c.replace(',', '')) - base:+,.0f}" for c in cells[2:]),
            ]
        )
    table(
        "TimezoneFinderL - ns per query (the shortcut lookup is the whole query)",
        [
            "stratum",
            "real",
            "dict",
            "srchsrt",
            "dir-csr",
            "dir-list",
            "d-srch",
            "d-dcsr",
            "d-dlist",
        ],
        rows,
    )
    print(
        "  The ambiguous row is the one place the CSR payload costs something: this\n"
        "  finder reads only the *last* candidate, which is one index on a stored\n"
        "  ndarray and three numpy scalar reads through offsets_by_slot."
    )
    tfl.cleanup()


def report_lookup_only(flat: FlatShortcuts, cells: np.ndarray) -> None:
    """The lookup stage alone, scalar and vectorised, against batch size.

    This is the claim under test: that the flat layout's scalar loss disappears when N
    cell ids are resolved in one call. The ``dict`` column is a Python loop over the
    same cells, which is what a batch API on today's structure would have to do.
    """
    rows = []
    for n in BATCH_SIZES:
        chunk = np.ascontiguousarray(cells[:n])
        as_list = chunk.tolist()
        mapping_get = {int(k): i for i, k in enumerate(flat.sorted_keys)}.get
        reps = max(1, 20_000 // n)
        per_dict = (
            measure(lambda: [[mapping_get(c) for c in as_list] for _ in range(reps)], 7)
            / (reps * n)
            * 1e9
        )
        keys = flat.sorted_keys
        per_raw = (
            measure(lambda: [np.searchsorted(keys, chunk) for _ in range(reps)], 7)
            / (reps * n)
            * 1e9
        )
        per_srch = (
            measure(lambda: [lookup_searchsorted(flat, chunk) for _ in range(reps)], 7)
            / (reps * n)
            * 1e9
        )
        per_dir = (
            measure(lambda: [lookup_direct(flat, chunk) for _ in range(reps)], 7)
            / (reps * n)
            * 1e9
        )
        rows.append(
            [
                f"{n:,}",
                f"{per_dict:,.1f}",
                f"{per_raw:,.1f}",
                f"{per_srch:,.1f}",
                f"{per_dir:,.1f}",
                f"{per_dict / per_srch:.2f}x",
                f"{per_dict / per_dir:.2f}x",
            ]
        )
    table(
        "Lookup stage only - ns per point, by batch size",
        ["N", "dict loop", "srch raw", "srch full", "direct", "srch gain", "dir gain"],
        rows,
    )
    print(
        "  `srch raw` is np.searchsorted alone; `srch full` adds the equality check\n"
        "  against the keys and the zone id gather, which a correct lookup needs.\n"
        "  `direct` is the whole thing - the slot arithmetic *is* the lookup."
    )


def report_batch(
    tf: TimezoneFinder, flat: FlatShortcuts, strata: dict[str, Points]
) -> None:
    """The whole batch pipeline, per point, per layout - the lookup in its context."""
    rows = []
    for stratum, points in strata.items():
        batch = points[:BATCH_SIZE]
        n = len(batch)
        lngs = np.array([p[0] for p in batch], dtype=np.float64)
        lats = np.array([p[1] for p in batch], dtype=np.float64)
        scalar = _ns_per_point(
            lambda: [tf.timezone_at(lng=p[0], lat=p[1]) for p in batch], n
        )
        validate_ns = _ns_per_point(lambda: validate_batch(lngs, lats), n)
        cells_ns = _ns_per_point(lambda: cells_of(lngs, lats), n)
        row = [stratum, f"{scalar:,.0f}", f"{validate_ns:,.0f}", f"{cells_ns:,.0f}"]
        totals = []
        for fn in BATCH_LAYOUTS.values():
            per_point = _ns_per_point(lambda fn=fn: fn(tf, flat, lngs, lats), n)
            totals.append(per_point)
            row.append(f"{per_point:,.0f}")
        row.append(f"{scalar / min(totals):.2f}x")
        rows.append(row)
    table(
        f"Batch path - ns per point for N = {BATCH_SIZE} points resolved in one call",
        [
            "stratum",
            "scalar",
            "validate",
            "h3 cells",
            "dict",
            "searchsrt",
            "direct",
            "best gain",
        ],
        rows,
    )
    print(
        "  `scalar` is N separate tf.timezone_at() calls, the thing a batch API\n"
        "  replaces. `validate` and `h3 cells` are stages every layout pays\n"
        "  identically; they bound what any lookup layout can be worth here."
    )


def report_memory() -> None:
    rows = []
    baseline = None
    for result in measure_memory(sys.executable):
        current = result["current"]
        if baseline is None:
            baseline = current
        rows.append(
            [
                result["layout"],
                f"{current / 2**20:,.2f}",
                f"{(current - baseline) / 2**20:+,.2f}",
            ]
        )
    table(
        "Memory - MiB traced by tracemalloc, one fresh subprocess per layout",
        ["layout", "MiB", "vs dict"],
        rows,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--memory-probe",
        choices=MEMORY_LAYOUTS,
        help="internal: build one layout in this process and print its footprint",
    )
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help="use TimezoneFinder(in_memory=True) instead of the mapped default",
    )
    parser.add_argument(
        "--skip-memory", action="store_true", help="skip the subprocess memory table"
    )
    args = parser.parse_args()

    if args.memory_probe:
        print(json.dumps(memory_probe(args.memory_probe)))
        return

    n_cells, invariant = verify_slot_bijection()
    print(
        f"acceleration path: {active_acceleration_path()}   in_memory={args.in_memory}"
    )
    print(
        f"slot map: injective over all {n_cells:,} cells at resolution "
        f"{SHORTCUT_H3_RES}; every cell id outside the {SLOT_TABLE_SIZE:,}-slot index "
        f"bits carries the constant {invariant:#x}"
    )

    tf = TimezoneFinder(in_memory=args.in_memory)
    flat = FlatShortcuts(tf.shortcut_mapping)
    strata = {name: load_benchmark_points(fixture) for name, fixture in QUERY_STRATA}
    checked = check_agreement(tf, flat, {k: v[:400] for k, v in strata.items()})
    print(f"agreement: all layouts match the shipped answer on {checked:,} points")

    middle = int(flat.sorted_keys[len(flat.sorted_keys) // 2])
    probes = scalar_probes(tf.shortcut_mapping, flat, middle)
    table(
        "One scalar lookup, in isolation - ns per call, net of the harness call",
        ["step", "ns", "vs dict.get"],
        [
            [
                name,
                f"{ns:,.0f}",
                "" if name.startswith("(") else f"{ns / probes['dict.get']:.1f}x",
            ]
            for name, ns in probes.items()
        ],
    )

    report_scalar(tf, flat, strata)
    report_finder_l(strata, flat)
    report_lookup_only(
        flat,
        cells_of(
            np.array([p[0] for p in strata["random"]], dtype=np.float64),
            np.array([p[1] for p in strata["random"]], dtype=np.float64),
        ),
    )
    report_batch(tf, flat, strata)
    if not args.skip_memory:
        report_memory()
    tf.cleanup()


if __name__ == "__main__":
    main()
