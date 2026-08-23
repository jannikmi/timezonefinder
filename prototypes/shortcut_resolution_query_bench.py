r"""Does H3 resolution 4 pay for itself on a real query? Paired A/B against resolution 3.

``prototypes/single_resolution_bench.py`` settled everything about a resolution *except*
the question that decides it. It shows resolution 4 removing **60 % of the point-in-polygon
tests** a random workload runs, for **+857 KiB** of resident table - but it measures queries
through its own dict-based finder, and the one cost it cannot see is what a 7x larger table
does to the single read every query makes. That read is ~20 % of a unique-zone query, and
75-89 % of queries are unique-zone, so a few percent there can eat the whole gain.

So this script swaps a resolution-4 index underneath the **real**
``TimezoneFinder.timezone_at`` and compares whole queries, which is the only design this
repository trusts for a difference this small (``docs/benchmarking_methodology.rst``):

* **paired and order-alternated.** A and B run inside one round, and the order flips every
  round. A fixed A-then-B order once credited a shortcut change with 13.3 % that was
  entirely the first path warming ``validate_coordinates``, ``h3.latlng_to_cell`` and
  ``zone_name_from_id`` for the second.
* **two estimators, reported together.** The minimum is the least noise-sensitive; the
  count of rounds where B wins assumes nothing about the noise distribution. Where a
  difference is real both move together. Where they disagree, the answer is "no effect".
* **correctness first.** Every fixture point must resolve identically under both indices
  before anything is timed.

The strata are the committed fixtures, classified against the **resolution 3** index - so
"ambiguous" means ambiguous at resolution 3, which is exactly the set resolution 4 is
supposed to improve. ``random`` is the workload-representative one; read it last and rank
on it, remembering that uniformly random points are ~25 % ambiguous and an ambiguous query
costs ~11x a unique one.

Both backends have to be measured, since ``timezonefinder/utils.py`` binds the
point-in-polygon implementation at import and numba wins whenever it is importable::

    # numba (what a dev checkout runs)
    PYTHONPATH=. uv run python prototypes/shortcut_resolution_query_bench.py \
        tmp/combined-with-oceans.json

    # clang (what a plain `pip install` runs, and what CI tracks - rank on this one)
    PYTHONPATH=. uv run --isolated --no-group numba --group proto --group test \
        python prototypes/shortcut_resolution_query_bench.py tmp/combined-with-oceans.json

Building the resolution 4 index takes ~40 s; the comparison itself is seconds.

FINDINGS (2026-08-23, `bc2029a`, Apple arm64, Python 3.14.2, data 2026c)

**The timing comparison never ran, because the correctness gate refused - and that was the
answer.** Of 8,000 fixture points the two indices disagreed on one, and inspection showed
resolution 4 to be the wrong one there:

    lng=100.3055 lat=3.4804          (the Strait of Malacca, not a polar case)
    truly inside polygon 1213        Etc/GMT-7, confirmed by brute force over every
                                     polygon and by certain_timezone_at
    resolution 3 candidates          [495, 1213, 518]  -> Etc/GMT-7          correct
    resolution 4 candidates          [495, 518]        -> Asia/Kuala_Lumpur  wrong

The cause is not the index and not the deduplication - it is ``Hex.lies_in_cell``, which
tests **vertex inclusion only**::

    # assumption: the polygons and cells have a similar size
    # and are small enough to just check vertex inclusion
    # valid simplification

For this cell no hexagon vertex lies inside the polygon and no polygon vertex lies inside
the hexagon, yet a polygon *edge* crosses the cell. Edge intersections are never tested, so
the overlap goes unseen. At resolution 3 the same cell is caught because the larger hexagon
happens to contain a polygon vertex. **The simplification's stated precondition degrades as
cells shrink, which is exactly what raising the resolution does.**

**Resolved 2026-08-23: ``lies_in_cell`` now tests segment intersection**, and that cell
resolves correctly at resolution 4. The gate should pass on a re-run, and the timing
question this script was written for is finally the one standing in the way. Re-run it on
both backends before ranking resolution 4 — the numbers above are from the state where it
refused, not from a completed comparison.

**A separate, pre-existing gap, found while checking the above and worth its own entry.**
Brute-forcing every polygon for 3,000 points sampled *uniformly in latitude and longitude*
finds the containing polygon absent from the shortcut for 7 points at resolution 3 and 1 at
resolution 4 - every one of them above latitude 88, where ``timezone_at`` returns a
neighbouring ocean zone and ``certain_timezone_at`` returns ``None``. **Sampled by area
instead - a realistic workload - both resolutions return 0 wrong answers in 3,000 points.**
Uniform latitude oversamples the poles enormously, so quote the area-weighted figure and
treat the polar cells as the narrow defect they are. ``hex_utils`` already special-cases
them (``surrounds_north_pole``, ``is_special``), which is where a fix would go.

Neither finding is caused by the shortcut index format; both predate it.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import statistics
import sys
import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from h3.api import numpy_int as h3

from scripts.configs import PROJECT_ROOT
from scripts.shortcuts import optimise_shortcut_ordering
from scripts.timezone_data import TimezoneData
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import SHORTCUT_H3_RES
from timezonefinder.shortcut_index import (
    get_last_change_idx,
    ABSENT,
    NUM_BASE_CELLS,
    PAYLOAD_DTYPE,
    SLOT_BASE_CELL_MASK,
    SLOT_BASE_CELL_SHIFT,
    TABLE_DTYPE,
    check_fits,
)

#: the resolution to compare the packaged `SHORTCUT_H3_RES` against. Set it to whichever
#: resolution is *not* the one that ships - the script builds that one and pairs it
#: against the real finder.
CANDIDATE_RES = 3

QUERY_POINTS = 2_000
QUERY_ROUNDS = 61
STRATA = (
    ("unique", UNIQUE_SHORTCUT_POINTS_FIXTURE),
    ("ambiguous", AMBIGUOUS_SHORTCUT_POINTS_FIXTURE),
    ("random", RANDOM_POINTS_FIXTURE),
    ("on_land", ON_LAND_POINTS_FIXTURE),
)

# Resolution-dependent slot arithmetic, which `timezonefinder.shortcut_index` fixes at
# import from SHORTCUT_H3_RES. Restated here for the candidate resolution rather than
# parameterising the library: the shipped constants are folded into the lookup on purpose,
# and a resolution argument on that path would be a cost the real thing does not pay.
DIGIT_BITS = 3
CAND_DIGITS_SHIFT = SLOT_BASE_CELL_SHIFT - DIGIT_BITS * CANDIDATE_RES
CAND_DIGITS_MASK = (1 << (DIGIT_BITS * CANDIDATE_RES)) - 1
CAND_STRIDE = CAND_DIGITS_MASK + 1
CAND_TABLE_SIZE = NUM_BASE_CELLS * CAND_STRIDE
COMPACT_BASE = 7
CAND_COMPACT_STRIDE = COMPACT_BASE**CANDIDATE_RES
CAND_COMPACT_TABLE_SIZE = NUM_BASE_CELLS * CAND_COMPACT_STRIDE


def compact_slots_at(hex_ids: np.ndarray, resolution: int) -> np.ndarray:
    """Base-7 compact slot of each cell id, at an arbitrary resolution."""
    digits = np.zeros_like(hex_ids)
    for digit in range(resolution):
        shift = SLOT_BASE_CELL_SHIFT - DIGIT_BITS * (digit + 1)
        digits = digits * COMPACT_BASE + ((hex_ids >> shift) & 7)
    return ((hex_ids >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * (
        COMPACT_BASE**resolution
    ) + digits


def expand_compact_at(compact: np.ndarray, resolution: int, fill: int) -> np.ndarray:
    """Compact base-7 table -> the padded base-8 table the lookup indexes."""
    shape = (NUM_BASE_CELLS,) + (8,) * resolution
    block = (slice(None),) + (slice(0, COMPACT_BASE),) * resolution
    out = np.full(shape, fill, dtype=compact.dtype)
    out[block] = compact.reshape((NUM_BASE_CELLS,) + (COMPACT_BASE,) * resolution)
    return out.reshape(-1)


def build_index_at(data: TimezoneData, resolution: int) -> dict[str, np.ndarray]:
    """The shipped structure, built at an arbitrary resolution.

    Deliberately the same shape as ``timezonefinder.shortcut_index.build_shortcut_index``
    rather than a call to it: that one is fixed to ``SHORTCUT_H3_RES`` by module constants,
    which is correct for the library and useless here.
    """
    cells: list[int] = []
    for res0 in h3.get_res0_cells():
        cells.extend(int(c) for c in h3.cell_to_children(res0, resolution))
    cells.sort()
    keys = np.array(cells, dtype=np.int64)
    compact = compact_slots_at(keys, resolution)

    zone_ids = data.poly_zone_ids
    table = np.full(
        NUM_BASE_CELLS * COMPACT_BASE**resolution, ABSENT, dtype=TABLE_DTYPE
    )
    unique_slots: list[int] = []
    unique_zone_ids: list[int] = []
    list_slots: list[int] = []
    entry_of: dict[bytes, int] = {}
    entry_index: list[int] = []
    entry_payloads: list[np.ndarray] = []

    for cell, slot in zip(cells, compact):
        polygons = list(data.get_hex(cell).polys_in_cell)
        # the hex cache is unbounded and holds a candidate set per cell; a leaf is never
        # a true parent of another leaf, so evicting it is exact. See
        # single_resolution_bench.py FINDINGS conclusion 6.
        data.hex_cache.cache.pop(cell, None)
        if not polygons:
            continue
        zones = zone_ids[np.asarray(polygons, dtype=np.int64)]
        if np.all(zones == zones[0]):
            unique_slots.append(int(slot))
            unique_zone_ids.append(int(zones[0]))
            continue
        ordered = np.asarray(
            optimise_shortcut_ordering(data, polygons), dtype=PAYLOAD_DTYPE
        )
        list_slots.append(int(slot))
        key = ordered.tobytes()
        found = entry_of.get(key)
        if found is None:
            found = len(entry_payloads)
            entry_of[key] = found
            entry_payloads.append(ordered)
        entry_index.append(found)

    zone_column = np.asarray(unique_zone_ids, dtype=np.int64)
    markers = -(np.asarray(entry_index, dtype=np.int64) + 2)
    check_fits(zone_column, TABLE_DTYPE, what="a zone id", remedy="Widen the table.")
    check_fits(-markers, TABLE_DTYPE, what="an entry index", remedy="Widen the table.")
    if unique_slots:
        table[unique_slots] = zone_column.astype(TABLE_DTYPE)
    if list_slots:
        table[list_slots] = markers.astype(TABLE_DTYPE)

    payload = (
        np.concatenate(entry_payloads)
        if entry_payloads
        else np.empty(0, dtype=PAYLOAD_DTYPE)
    )
    lengths = np.array([len(c) for c in entry_payloads], dtype=np.int64)
    bounds = np.concatenate([np.zeros(1, dtype=np.int64), np.cumsum(lengths)])
    last_change = np.array(
        [
            get_last_change_idx(zone_ids[chunk.astype(np.int64)])
            for chunk in entry_payloads
        ],
        dtype=np.int64,
    )
    return {
        "table": expand_compact_at(table, resolution, fill=ABSENT),
        "starts": bounds[:-1],
        "ends": bounds[1:],
        "last_change": last_change,
        "payload": payload,
        "cells": len(cells),
        "unique": len(unique_slots),
        "lists": len(entry_payloads),
    }


class CandidateResolutionFinder(TimezoneFinder):
    """``TimezoneFinder`` whose shortcut index is built at ``CANDIDATE_RES``.

    Everything below the shortcut lookup is copied verbatim from the shipped
    ``timezone_at``, so the only difference measured is the resolution. ``check_agreement``
    holds the copy to the original on every fixture point before anything is timed.
    """

    __slots__ = ("_table", "_starts", "_ends", "_last_change", "_payload")

    def __init__(self, index: dict[str, np.ndarray], **kwargs) -> None:
        super().__init__(**kwargs)
        self._table = index["table"]
        self._starts = index["starts"]
        self._ends = index["ends"]
        self._last_change = index["last_change"]
        self._payload = index["payload"]

    def timezone_at(self, *, lng: float, lat: float) -> str | None:
        lng, lat = utils.validate_coordinates(lng, lat)
        hex_id = h3.latlng_to_cell(lat, lng, CANDIDATE_RES)
        entry = int(
            self._table[
                ((hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * CAND_STRIDE
                + ((hex_id >> CAND_DIGITS_SHIFT) & CAND_DIGITS_MASK)
            ]
        )
        if entry >= 0:
            return self.zone_name_from_id(entry)
        if entry == ABSENT:
            return None
        i = -(entry + 2)
        possible_boundaries = self._payload[self._starts[i] : self._ends[i]]

        # --- verbatim from TimezoneFinder.timezone_at below ---
        zone_ids = self.zone_ids_of(possible_boundaries)
        last_zone_change_idx = self._last_change[i]
        x = utils.coord2int(lng)
        y = utils.coord2int(lat)
        for j, boundary_id in enumerate(possible_boundaries):
            if j >= last_zone_change_idx:
                break
            if self.inside_of_polygon(boundary_id, x, y):
                return self.zone_name_from_id(int(zone_ids[j]))
        return self.zone_name_from_id(int(zone_ids[-1]))


def check_agreement(
    shipped: TimezoneFinder, candidate: TimezoneFinder, points: Sequence
) -> int:
    """Both indices must answer every point identically. Returns the mismatch count.

    A disagreement is not automatically a bug in either: ``timezone_at`` returns the last
    remaining zone without a point-in-polygon test, so two indices offering different
    candidate *orders* can differ on a point covered by none of them. With the packaged
    ocean data that case does not arise, so any mismatch here is worth reading.
    """
    mismatches = 0
    for lng, lat in points:
        if shipped.timezone_at(lng=lng, lat=lat) != candidate.timezone_at(
            lng=lng, lat=lat
        ):
            mismatches += 1
    return mismatches


def paired_ns(
    shipped: TimezoneFinder, candidate: TimezoneFinder, points: Sequence, rounds: int
) -> tuple[float, float, list[float]]:
    """Per-round timings of both finders, alternating which goes first."""
    a_times: list[float] = []
    b_times: list[float] = []
    for round_nr in range(rounds):

        def run(finder):
            start = time.perf_counter()
            for lng, lat in points:
                finder.timezone_at(lng=lng, lat=lat)
            return (time.perf_counter() - start) / len(points) * 1e9

        if round_nr % 2 == 0:
            a = run(shipped)
            b = run(candidate)
        else:
            b = run(candidate)
            a = run(shipped)
        a_times.append(a)
        b_times.append(b)
    return min(a_times), min(b_times), [b - a for a, b in zip(a_times, b_times)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "input", type=Path, help="the timezone-boundary-builder GeoJSON"
    )
    parser.add_argument("--rounds", type=int, default=QUERY_ROUNDS)
    parser.add_argument("--points", type=int, default=QUERY_POINTS)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"input not found: {args.input}", file=sys.stderr)
        raise SystemExit(1)

    from scripts.assert_acceleration_path import active_acceleration_path

    print(
        f"backend: {active_acceleration_path()} | "
        f"resolution {SHORTCUT_H3_RES} (shipped) against {CANDIDATE_RES} (candidate)\n"
    )

    print("loading boundary data...")
    with contextlib.redirect_stdout(io.StringIO()):
        data = TimezoneData.from_path(args.input)

    print(f"building the resolution {CANDIDATE_RES} index...")
    started = time.perf_counter()
    index = build_index_at(data, CANDIDATE_RES)
    print(
        f"  {index['cells']:,} cells, {index['unique']:,} unique "
        f"({index['unique'] / index['cells']:.1%}), {index['lists']:,} distinct lists, "
        f"built in {time.perf_counter() - started:.0f}s"
    )
    table_kib = index["table"].nbytes / 1024
    rest_kib = (
        index["starts"].nbytes + index["last_change"].nbytes + index["payload"].nbytes
    ) / 1024
    print(f"  resident: {table_kib:,.0f} KiB table + {rest_kib:,.0f} KiB rest")
    del data

    shipped = TimezoneFinder()
    candidate = CandidateResolutionFinder(index)

    print("\nagreement, before anything is timed:")
    total_mismatches = 0
    for label, fixture in STRATA:
        points = load_benchmark_points(fixture)[: args.points]
        mismatches = check_agreement(shipped, candidate, points)
        total_mismatches += mismatches
        print(f"  {label:<10} {len(points):,} points, {mismatches} mismatches")
    if total_mismatches:
        print(
            "\nthe two indices disagree - the comparison below is meaningless until that "
            "is understood",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(
        f"\npaired query comparison, {args.rounds} rounds x {args.points:,} points, "
        "order alternated\n"
    )
    shipped_label = f"res {SHORTCUT_H3_RES} ns"
    candidate_label = f"res {CANDIDATE_RES} ns"
    print(
        f"{'stratum':<12}{shipped_label:>10}{candidate_label:>10}{'on minima':>12}"
        f"{'median d':>11}{'10-90% of d':>22}{'rounds faster':>15}"
    )
    for label, fixture in STRATA:
        points = load_benchmark_points(fixture)[: args.points]
        a_min, b_min, deltas = paired_ns(shipped, candidate, points, args.rounds)
        deltas_sorted = sorted(deltas)
        low = deltas_sorted[int(0.10 * len(deltas))]
        high = deltas_sorted[int(0.90 * len(deltas))]
        faster = sum(1 for d in deltas if d < 0)
        print(
            f"{label:<12}{a_min:>10,.0f}{b_min:>10,.0f}"
            f"{(b_min - a_min) / a_min:>11.1%}"
            f"{statistics.median(deltas):>11,.0f}"
            f"{f'{low:,.0f} .. {high:,.0f}':>22}"
            f"{f'{faster}/{len(deltas)}':>15}"
        )
    print(
        f"\nNegative means resolution {CANDIDATE_RES} is faster than the packaged "
        f"resolution {SHORTCUT_H3_RES}.\nRead `on minima` and `rounds faster` together: "
        "where a difference is real both move;\nwhere they disagree the answer is no effect."
    )


if __name__ == "__main__":
    if PROJECT_ROOT not in [Path(p).resolve() for p in sys.path if p]:
        sys.path.insert(0, str(PROJECT_ROOT))
    main()
