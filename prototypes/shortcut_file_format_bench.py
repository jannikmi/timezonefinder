"""Which shortcut data structure to build: one recommendation, and what it beats.

``prototypes/shortcut_layout_bench.py`` settled the *in-memory* question - address entries
by an H3-derived slot rather than by a dict key, which is free on the query path and saves
~4 MiB. This settles the *file* question, which is a different one: changing the packaged
binary costs a ``SHORTCUT_LAYOUT_VERSION`` bump, therefore ``DATA_FORMAT_VERSION``,
therefore an ordered two-distribution release.

Three structures are measured, and only three. The exploration that produced them is over
and everything else it turned up is refused under REFUSED OPTIONS below, with its reason.

``dict``        what ships. A FlatBuffers file whose 41,162 per-entry tables are decoded
                in Python into ``dict[int, int | ndarray]``.
``keys-plain``  flat file: sorted cell ids, per-entry start and end, one payload holding
                every value back to back. Removes the per-entry decode and the dict.
``keys-dedup``  the same, storing each *distinct* entry once - only 6.9% of entries are
                distinct - so duplicates simply carry equal offsets into a shared payload.
                **This is the recommendation.**

``slot-dedup`` is measured beside them to price one question and no other: what storing the
cell ids buys. It drops them and derives the index from h3's internal bit layout instead.

All three flat structures load to the *same runtime shape* and share one lookup, so the
query comparison is about the data rather than about three different code paths::

    zone = zone_by_slot[slot]            # derived at load, int16
    if zone >= 0:        -> unique zone id
    elif zone == ABSENT  -> not covered
    else:                -> payload[starts[slot]:ends[slot]]

Correctness first: every one of the 41,162 cells must resolve to exactly what the shipped
reader returns, under every structure, before anything is timed.

Run::

    PYTHONPATH=. uv run python prototypes/shortcut_file_format_bench.py

Neither the load path nor the lookup touches point-in-polygon, so unlike the companion
script this one is backend-independent.


FINDINGS (2026-08-22, `157a476`, Apple arm64, Python 3.14.2, numpy 2.3.5, data 2026c)

    payload: 54,024 values -> 7,344 distinct (105.5 -> 14.3 KiB, 7.4x)
    offset width: uint32 plain (uint16 would leave only 1.2x headroom),
                  uint16 deduplicated (8.9x headroom)
    agreement: all 41,162 cells resolve identically under all three structures

    structure       file KiB   load ms    MiB   unique ns   amb ns
    dict (shipped)     1,530    390.2    4.44         109      117
    keys-plain           749      0.675  0.70         210      427
    keys-dedup  <=       497      0.655  0.37         210      420
    slot-dedup           258      0.512  0.37         209      428

CONCLUSIONS

1. **`keys-dedup` is the structure to build, and the choice is not a trade-off.** It
   dominates `keys-plain` outright - 497 KiB against 749, 0.37 MiB against 0.70, the same
   load and the same lookup to within noise. Deduplication is free at lookup because
   duplicates carry *equal offsets* rather than a shared index: nothing is dereferenced
   twice, so a repeated entry costs exactly what a unique one costs. There is no version
   of this comparison where storing 41,162 entries beats storing the 2,846 distinct ones.

2. **Deduplication also pays for its own addressing, which is the non-obvious part.**
   Sharing destroys the contiguity a CSR layout rests on - entry i no longer ends where
   entry i+1 begins - so each slot needs its own start *and* end, 2N numbers instead of
   N+1. That doubling would cost more than the payload it saves, except that collapsing
   54,024 values to 7,344 lets the offsets narrow from `uint32` to `uint16`, which halves
   it back. Net: the addressing is unchanged and the payload is 7.4x smaller. Note the
   narrowing is only defensible *because* of deduplication - at 54,024 values `uint16`
   has 1.2x headroom, which is a bet on the data, and at 7,344 it has 8.9x.

3. **The one real decision left is `keys-dedup` against `slot-dedup`: 239 KiB of file and
   0.14 ms of load, to keep h3 out of the data format.** `slot-dedup` drops the stored cell
   ids because the cell id *is* the index - and that bakes an encoding h3-py does not
   promise as API, plus `SHORTCUT_H3_RES`, into bytes that outlive every reader. Storing
   the ids moves that coupling into the reader, which is versioned with the package and can
   be changed in any release. Both are still 3-6x smaller than what ships. **Pay the
   239 KiB.**

4. **Load: ~390 ms to ~0.66 ms, ~600x - and most of it is not this change's to claim.**
   PERF-5 reaches ~21 ms on the *existing* file with no format change and no release, so
   what the format change adds is ~21 ms to ~0.66 ms. Rank it on that, on the 4.1 MiB, and
   on the file being 3x smaller; never on the 390.

5. **The query is unchanged in practice, though not in isolation.** A lookup on its own is
   ~210 ns against the dict's ~109. That gap does not survive contact with a real query:
   the companion script measures the same layout inside `timezone_at` at **+4 ns**, under
   the noise floor. The mechanism is that the shipped code answers a `dict.get` with
   `match value: case int(zone_id)`, a structural pattern match costing about what the flat
   lookup costs extra - so the two roughly cancel. **Quote the whole-query figure.** Note
   also that sampling cells in `mapping` order rather than at random hands `dict.get` a
   cache-friendly walk of its own table and reads 109 ns as 77; the numbers above are
   randomly sampled.

REFUSED OPTIONS, with the reason, so they are not re-proposed

* **`np.searchsorted` over sorted keys** - roughly doubles a unique-zone query, and loses
  the batch path it was proposed for: one call over N is still slower than N dict lookups.
  Measured in the companion script.
* **A Python list of values instead of arrays** (in-memory) - 2.41 MiB against 0.37 for no
  query benefit. Companion script.
* **`uint8` per-slot lengths** - the smallest non-deduplicated file at 166 KiB, and it
  rests on every entry fitting 255 where the packaged maximum is 59. A property of the
  data, not a guarantee of the format; a 256-polygon cell would need a layout version.
* **Deduplication via an entry-number index** (slot -> entry -> range) - costs +74 ns on
  the ambiguous path to save ~100 KiB, and is simply unnecessary: equal offsets achieve the
  same sharing with no indirection at all. This was a wrong turn, kept here because it
  looks like the obvious way to implement sharing and is not.
* **Deduplication with `uint32` offsets** - 502 KiB, worse than not deduplicating. The
  narrowing in conclusion 2 is what makes sharing pay.
* **Dispatching on the entry length at runtime** instead of on a derived zone table -
  +230 ns against +73 ns on the unique path, because it needs two offset reads and a
  subtraction where the table needs one read. The length is the right discriminator *in
  the file* and the wrong one at runtime; these are separate decisions.
* **Dropping the stored cell ids and enumerating them from h3's public API at load** -
  the index is dense, so this is possible; it costs 4.5 ms against 0.13 ms to read them,
  a fifth of PERF-5's entire budget to save 329 KiB.

"""

import argparse
import gc
import json
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np

from prototypes.shortcut_layout_bench import (
    SLOT_BASE_CELL_MASK,
    SLOT_BASE_CELL_SHIFT,
    SLOT_DIGITS_MASK,
    SLOT_DIGITS_SHIFT,
    SLOT_STRIDE,
    SLOT_TABLE_SIZE,
    slots_of,
    verify_slot_bijection,
)
from scripts.configs import PROJECT_ROOT
from timezonefinder import TimezoneFinder
from timezonefinder.configs import SHORTCUT_H3_RES
from timezonefinder.flatbuf.io.hybrid_shortcuts import (
    get_hybrid_shortcut_file_path,
    read_hybrid_shortcuts_binary,
)

OUT_DIR = PROJECT_ROOT / "tmp" / "shortcut_file_format"

# Zone ids (0..443 today) and polygon ids (0..1321 today) share ONE array, which works
# only because both fit the same width. `build_payload` checks rather than assumes it.
PAYLOAD_DTYPE = np.uint16

# Absent / unique-zone / polygon-list are told apart by an entry's *length*: 0, 1, >=2.
# A stored list can never have length 1 by construction - `compute_unique_shortcut_mapping`
# collapses any cell whose polygons share a zone, and a one-polygon cell trivially does -
# so no discriminator tag is needed. `build_payload` re-checks it against the packaged data.
UNIQUE_LEN = 1

POLYGON_LIST = -1
ABSENT = -2

REPEATS = 7
QUERY_SAMPLE = 2_000


# ---------------------------------------------------------------------------
# payload construction
# ---------------------------------------------------------------------------


def offset_dtype_for(n_values: int) -> np.dtype:
    """The narrowest offset width that addresses ``n_values`` with headroom to spare.

    Deliberately not "the narrowest that fits". A width chosen with 1.2x headroom is a bet
    on the data rather than a property of the format, and losing that bet costs a layout
    version bump. 4x is the bar here, and deduplication is what lets the recommended
    structure clear it where the non-deduplicated one does not.
    """
    for dtype in (np.uint16, np.uint32):
        if np.iinfo(dtype).max >= n_values * 4:
            return np.dtype(dtype)
    return np.dtype(np.uint64)


def build_payload(
    mapping: dict[int, int | np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (sorted cell ids, per-entry lengths, concatenated payload).

    Entries come out in ascending cell id order, which is also ascending slot order: the
    base cell occupies the high bits of both, so the two orders cannot disagree.
    """
    keys = np.sort(np.fromiter(mapping.keys(), dtype=np.int64, count=len(mapping)))
    lengths = np.empty(len(keys), dtype=np.int64)
    chunks: list[np.ndarray] = []
    info = np.iinfo(PAYLOAD_DTYPE)
    for i, key in enumerate(keys):
        value = mapping[int(key)]
        if isinstance(value, (int, np.integer)):
            if not (info.min <= int(value) <= info.max):
                raise AssertionError(f"zone id {value} does not fit {PAYLOAD_DTYPE}")
            chunks.append(np.array([value], dtype=PAYLOAD_DTYPE))
            lengths[i] = 1
        else:
            if len(value) == UNIQUE_LEN:
                raise AssertionError(
                    "a stored polygon list of length 1 makes the length ambiguous with "
                    "a unique zone id; the converter must make this impossible"
                )
            if len(value) and int(value.max()) > info.max:
                raise AssertionError(f"polygon id does not fit {PAYLOAD_DTYPE}")
            chunks.append(value.astype(PAYLOAD_DTYPE, copy=False))
            lengths[i] = len(value)
    payload = np.concatenate(chunks) if chunks else np.empty(0, dtype=PAYLOAD_DTYPE)
    return keys, lengths, payload


def deduplicate(
    lengths: np.ndarray, payload: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Collapse identical entries. Returns per-entry (starts, ends, deduped payload).

    Duplicates come out holding *equal* offsets into a shared payload. There is no
    indirection and no entry-number table, so a lookup does exactly what it does without
    deduplication - see REFUSED OPTIONS on the indirect variant that does add one.
    """
    seen: dict[bytes, tuple[int, int]] = {}
    starts = np.empty(len(lengths), dtype=np.int64)
    ends = np.empty(len(lengths), dtype=np.int64)
    chunks: list[np.ndarray] = []
    cursor = 0
    pos = 0
    for i, length in enumerate(lengths):
        chunk = payload[pos : pos + length]
        pos += length
        key = chunk.tobytes()
        span = seen.get(key)
        if span is None:
            span = (cursor, cursor + length)
            seen[key] = span
            chunks.append(chunk)
            cursor += length
        starts[i], ends[i] = span
    deduped = np.concatenate(chunks) if chunks else np.empty(0, dtype=PAYLOAD_DTYPE)
    return starts, ends, deduped


def scatter_to_slots(
    keys: np.ndarray, starts: np.ndarray, ends: np.ndarray, dtype: np.dtype
) -> tuple[np.ndarray, np.ndarray]:
    """Per-entry bounds onto the dense slot table. Absent slots get an empty range."""
    slot_starts = np.zeros(SLOT_TABLE_SIZE, dtype=dtype)
    slot_ends = np.zeros(SLOT_TABLE_SIZE, dtype=dtype)
    slots = slots_of(keys)
    slot_starts[slots] = starts
    slot_ends[slots] = ends
    return slot_starts, slot_ends


# ---------------------------------------------------------------------------
# the three structures
# ---------------------------------------------------------------------------
# A real implementation would carry a file identifier and a layout version the way
# `hybrid_shortcuts.py` does. Omitted on purpose: an 8-byte header cannot move any number
# below, and inventing one invites arguing about it instead of about the structure.
#
# Every reader returns the same triple - (slot starts, slot ends, payload) - so one lookup
# serves all three and the comparison is about the data rather than the code.
#
# `.copy()`, never `np.ascontiguousarray`: the latter returns an already-contiguous view
# unchanged, and a surviving view keeps the whole file buffer alive. That is the trap the
# shipped loader carries a comment about, and this script fell into it once.


def _write(path: Path, *arrays: np.ndarray) -> None:
    with open(path, "wb") as f:
        for arr in arrays:
            f.write(arr.tobytes())


def write_keys_plain(path: Path, keys, lengths, payload) -> None:
    dtype = offset_dtype_for(len(payload))
    ends = np.cumsum(lengths)
    _write(
        path,
        np.array([len(keys), dtype.itemsize], dtype=np.int64),
        keys,
        (ends - lengths).astype(dtype),
        ends.astype(dtype),
        payload,
    )


def write_keys_dedup(path: Path, keys, lengths, payload) -> None:
    starts, ends, deduped = deduplicate(lengths, payload)
    dtype = offset_dtype_for(len(deduped))
    _write(
        path,
        np.array([len(keys), dtype.itemsize], dtype=np.int64),
        keys,
        starts.astype(dtype),
        ends.astype(dtype),
        deduped,
    )


def read_keys(buf: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n, width = (int(v) for v in np.frombuffer(buf, dtype=np.int64, count=2))
    dtype = np.dtype(f"uint{width * 8}")
    pos = 16
    keys = np.frombuffer(buf, dtype=np.int64, count=n, offset=pos)
    pos += n * 8
    starts = np.frombuffer(buf, dtype=dtype, count=n, offset=pos)
    pos += n * width
    ends = np.frombuffer(buf, dtype=dtype, count=n, offset=pos)
    pos += n * width
    payload = np.frombuffer(buf, dtype=PAYLOAD_DTYPE, offset=pos).copy()
    # the format says nothing about h3's bit layout; the reader derives the slot table
    slot_starts, slot_ends = scatter_to_slots(keys, starts, ends, dtype)
    return slot_starts, slot_ends, payload


def write_slot_dedup(path: Path, keys, lengths, payload) -> None:
    starts, ends, deduped = deduplicate(lengths, payload)
    dtype = offset_dtype_for(len(deduped))
    slot_starts, slot_ends = scatter_to_slots(keys, starts, ends, dtype)
    _write(
        path,
        np.array([dtype.itemsize], dtype=np.int64),
        slot_starts,
        slot_ends,
        deduped,
    )


def read_slot_dedup(buf: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    width = int(np.frombuffer(buf, dtype=np.int64, count=1)[0])
    dtype = np.dtype(f"uint{width * 8}")
    pos = 8
    starts = np.frombuffer(buf, dtype=dtype, count=SLOT_TABLE_SIZE, offset=pos).copy()
    pos += SLOT_TABLE_SIZE * width
    ends = np.frombuffer(buf, dtype=dtype, count=SLOT_TABLE_SIZE, offset=pos).copy()
    pos += SLOT_TABLE_SIZE * width
    return starts, ends, np.frombuffer(buf, dtype=PAYLOAD_DTYPE, offset=pos).copy()


STRUCTURES: dict[str, tuple[Callable, Callable]] = {
    "keys-plain": (write_keys_plain, read_keys),
    "keys-dedup": (write_keys_dedup, read_keys),
    "slot-dedup": (write_slot_dedup, read_slot_dedup),
}
RECOMMENDED = "keys-dedup"


def derive_zone_table(
    starts: np.ndarray, ends: np.ndarray, payload: np.ndarray
) -> np.ndarray:
    """An ``int16`` zone-or-sentinel per slot, built once at load.

    Worth its ~122 KiB and ~0.5 ms: without it the unique-zone path - 30,651 of the 41,162
    cells, and the case the hybrid shortcut design exists to make fast - has to read two
    offsets and subtract them to discover it is a single value. Measured at +230 ns
    against +73 ns for one read of this table.
    """
    lens = ends.astype(np.int64) - starts.astype(np.int64)
    out = np.full(SLOT_TABLE_SIZE, ABSENT, dtype=np.int16)
    out[lens >= 2] = POLYGON_LIST
    unique = lens == UNIQUE_LEN
    out[unique] = payload[starts[unique]].astype(np.int16)
    return out


def lookup(starts, ends, payload, zone_by_slot, hex_id: int):
    slot = ((hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * SLOT_STRIDE + (
        (hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK
    )
    zone_id = zone_by_slot[slot]
    if zone_id >= 0:
        return int(zone_id)
    if zone_id == ABSENT:
        return None
    return payload[starts[slot] : ends[slot]]


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------


def measure(fn: Callable[[], object], repeats: int = REPEATS) -> float:
    fn()
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - start)
    return best


def table(header: str, columns: Sequence[str], rows) -> None:
    rows = list(rows)
    widths = [
        max(len(columns[c]), *(len(r[c]) for r in rows)) for c in range(len(columns))
    ]
    print(f"\n{header}")
    print("  " + "  ".join(h.rjust(w) for h, w in zip(columns, widths)))
    print("  " + "-" * (sum(widths) + 2 * (len(widths) - 1)))
    for row in rows:
        print("  " + "  ".join(c.rjust(w) for c, w in zip(row, widths)))


def check_agreement(mapping, starts, ends, payload, zone_by_slot, label: str) -> None:
    """Every cell resolves exactly as the shipped reader says, or nothing below counts."""
    for hex_id, expected in mapping.items():
        got = lookup(starts, ends, payload, zone_by_slot, hex_id)
        if isinstance(expected, (int, np.integer)):
            ok = isinstance(got, int) and got == int(expected)
        else:
            ok = isinstance(got, np.ndarray) and np.array_equal(got, expected)
        if not ok:
            raise AssertionError(
                f"{label} disagrees on cell {hex_id:#x}: {got!r} != {expected!r}"
            )
    absent = int((zone_by_slot == ABSENT).sum())
    if absent != SLOT_TABLE_SIZE - len(mapping):
        raise AssertionError(
            f"{label}: {absent} absent slots, expected {SLOT_TABLE_SIZE - len(mapping)}"
        )


def lookup_ns(cells, starts, ends, payload, zone_by_slot) -> float:
    """ns per lookup, with the dispatch inlined so no Python call is charged to it."""
    return (
        measure(
            lambda: [
                (
                    int(z)
                    if (z := zone_by_slot[sl]) >= 0
                    else (None if z == ABSENT else payload[starts[sl] : ends[sl]])
                )
                for c in cells
                for sl in (
                    ((c >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * SLOT_STRIDE
                    + ((c >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK),
                )
            ]
        )
        / len(cells)
        * 1e9
    )


# ---------------------------------------------------------------------------
# memory: one subprocess per structure, as scripts/_memory_probe.py argues
# ---------------------------------------------------------------------------

MEMORY_TARGETS = ("dict", *STRUCTURES)


def memory_probe(target: str) -> dict:
    import tracemalloc  # noqa: PLC0415

    tf = TimezoneFinder()
    shortcut_path = get_hybrid_shortcut_file_path(tf.zone_ids.dtype, tf.data_location)
    del tf
    gc.collect()

    if target == "dict":
        tracemalloc.start()
        kept: object = read_hybrid_shortcuts_binary(shortcut_path)
    else:
        path = OUT_DIR / f"{target}.bin"
        tracemalloc.start()
        buf = path.read_bytes()
        starts, ends, payload = STRUCTURES[target][1](buf)
        kept = (starts, ends, payload, derive_zone_table(starts, ends, payload))
        del buf
    gc.collect()
    current, _peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert kept is not None
    return {"target": target, "current": current}


def measure_memory() -> dict[str, int]:
    out = {}
    for target in MEMORY_TARGETS:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--memory-probe", target],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(PROJECT_ROOT),
        )
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        out[result["target"]] = result["current"]
    return out


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-probe", choices=MEMORY_TARGETS)
    parser.add_argument("--skip-memory", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.memory_probe:
        print(json.dumps(memory_probe(args.memory_probe)))
        return

    n_cells, invariant = verify_slot_bijection()
    print(
        f"slot map: injective over all {n_cells:,} cells at resolution {SHORTCUT_H3_RES}; "
        f"invariant {invariant:#x}"
    )

    tf = TimezoneFinder()
    shortcut_path = get_hybrid_shortcut_file_path(tf.zone_ids.dtype, tf.data_location)
    mapping = read_hybrid_shortcuts_binary(shortcut_path)
    keys, lengths, payload = build_payload(mapping)
    _s, _e, deduped = deduplicate(lengths, payload)
    plain_dtype = offset_dtype_for(len(payload))
    dedup_dtype = offset_dtype_for(len(deduped))
    print(
        f"payload: {len(payload):,} values -> {len(deduped):,} distinct "
        f"({payload.nbytes / 1024:,.1f} -> {deduped.nbytes / 1024:,.1f} KiB, "
        f"{len(payload) / len(deduped):.1f}x)"
    )
    print(
        f"offset width: {plain_dtype.name} for the plain payload "
        f"(uint16 would leave only {np.iinfo(np.uint16).max / len(payload):.1f}x headroom), "
        f"{dedup_dtype.name} deduplicated "
        f"({np.iinfo(dedup_dtype).max / len(deduped):.1f}x headroom)"
    )

    loaded = {}
    for name, (write, read) in STRUCTURES.items():
        path = OUT_DIR / f"{name}.bin"
        write(path, keys, lengths, payload)
        starts, ends, pay = read(path.read_bytes())
        zbs = derive_zone_table(starts, ends, pay)
        check_agreement(mapping, starts, ends, pay, zbs, name)
        loaded[name] = (starts, ends, pay, zbs)
    print(
        f"agreement: every one of {len(mapping):,} cells resolves identically under all "
        f"{len(STRUCTURES)} structures"
    )

    mem = {} if args.skip_memory else measure_memory()

    # Sampled at random, not taken in `mapping` order. Iterating a dict's keys in its own
    # order walks its table front to back and hands `dict.get` a cache-friendly access
    # pattern no real query stream has - measured at 77 ns that way against 121 ns
    # shuffled, i.e. the artifact is a third of the number being compared.
    rng = np.random.default_rng(0)

    def sample(want_unique: bool) -> list[int]:
        cells = [
            k
            for k, v in mapping.items()
            if isinstance(v, (int, np.integer)) is want_unique
        ]
        idx = rng.permutation(len(cells))[:QUERY_SAMPLE]
        return [cells[i] for i in idx]

    uniq, amb = sample(True), sample(False)

    # The dict pays the `match` the shipped `timezone_at` performs on what it gets back.
    # Without it the comparison is a dict that *stores* the answer against a structure
    # that *computes* it, which flatters the dict by exactly the dispatch it really pays.
    get = mapping.get
    dict_ns = {
        label: measure(
            lambda cells=cells: [
                (v if isinstance(v, int) else v) for c in cells for v in (get(c),)
            ]
        )
        / len(cells)
        * 1e9
        for label, cells in (("unique", uniq), ("ambiguous", amb))
    }

    rows = [
        [
            "dict (shipped)",
            f"{shortcut_path.stat().st_size / 1024:,.0f}",
            f"{measure(lambda: read_hybrid_shortcuts_binary(shortcut_path), 3) * 1e3:,.1f}",
            f"{mem['dict'] / 2**20:,.2f}" if mem else "-",
            f"{dict_ns['unique']:,.0f}",
            f"{dict_ns['ambiguous']:,.0f}",
        ]
    ]
    for name in STRUCTURES:
        starts, ends, pay, zbs = loaded[name]
        path = OUT_DIR / f"{name}.bin"
        read = STRUCTURES[name][1]

        def load(read=read, path=path):
            s, e, p = read(path.read_bytes())
            return s, e, p, derive_zone_table(s, e, p)

        rows.append(
            [
                name + ("  <=" if name == RECOMMENDED else ""),
                f"{path.stat().st_size / 1024:,.0f}",
                f"{measure(load, 30) * 1e3:,.3f}",
                f"{mem[name] / 2**20:,.2f}" if mem else "-",
                f"{lookup_ns(uniq, starts, ends, pay, zbs):,.0f}",
                f"{lookup_ns(amb, starts, ends, pay, zbs):,.0f}",
            ]
        )
    table(
        "One row per structure. Query columns are the lookup alone, inlined.",
        ["structure", "file KiB", "load ms", "MiB", "unique ns", "amb ns"],
        rows,
    )
    print(
        "  `load ms` includes deriving the zone table. The two query columns are a lookup\n"
        "  with no query around it; inside a real `timezone_at` the companion script\n"
        "  measures this layout at +4 ns, under the noise floor - quote that, not these."
    )

    tf.cleanup()


if __name__ == "__main__":
    main()
