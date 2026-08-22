"""Prototype the flat shortcut *binary* of GH-477: is the format change worth a release?

``prototypes/shortcut_layout_bench.py`` settled the in-memory question - the direct index
is free on the query path and saves ~4 MiB. It left the load path alone, and that is where
the shortcut structure actually costs something: decoding 41,162 per-entry FlatBuffers
tables in Python is ~400 ms, ~97% of a ``TimezoneFinder()`` construction and effectively
all of a ``TimezoneFinderL()`` one, paid per instance and therefore per thread.

Two different changes address it and they are not alternatives:

* **PERF-5** walks the same file's entries vector with whole-array numpy arithmetic instead
  of the generated accessors, and materialises the same dict. Measured elsewhere at ~21 ms.
  No schema change, so no version bump and no release.
* **This** replaces the file: one payload holding every entry's values back to back,
  addressed by an offset and a length, so there is no per-entry decode and no dict at all.
  Costs a ``SHORTCUT_LAYOUT_VERSION`` bump, therefore ``DATA_FORMAT_VERSION``, therefore an
  ordered two-distribution release.

So the question this script answers is **not** "is 400 ms worth removing" - PERF-5 removes
most of it for free. It is **what the format change is worth on top of PERF-5**, which is
the ~21 ms of dict materialisation, the memory, and the file size. The residue is measured
directly rather than by reimplementing PERF-5's vtable walk: given values already extracted,
building today's dict is exactly what a flat file does not do.

Three encodings, because the choice is not obvious:

``slot-offsets``  ``uint32`` offsets per H3 slot, plus the payload. No keys in the file at
                  all - the cell id *is* the index, via the bijection the companion script
                  proves. Smallest and simplest to load; bakes h3's internal index encoding
                  and ``SHORTCUT_H3_RES`` into the data format.
``slot-lengths``  the same, storing per-slot lengths and prefix-summing them at load.
                  Smaller still while lengths fit a ``uint8``, which is a property of the
                  data rather than of the format - so it is measured, not recommended.
``keys-offsets``  sorted ``int64`` cell ids plus per-entry offsets. The format then says
                  nothing about h3's bit layout; the slot table is derived at load by one
                  scatter. Larger file, and the coupling moves from the format to the reader.

and the same two again with **identical entries stored once**, since most are not distinct:

``slot-dedup``    a ``uint16`` index per slot into a small table of distinct entries.
``keys-dedup``    the same, keyed by stored cell ids rather than by slot.

And two runtime dispatches over the same bytes, because the length-as-discriminator trick
is elegant in the file and not obviously free in the query:

``len-dispatch``    read ``offsets[slot]`` and ``offsets[slot+1]``; length 0 absent, 1 a
                    zone id, >=2 polygon ids. Three numpy scalar reads on the unique path.
``derived-table``   additionally build an ``int16`` zone-or-sentinel table per slot at load
                    (~122 KiB, one vectorised pass), so the unique path is one read. This is
                    the ``direct-csr`` shape the companion script already priced.

Correctness first: every one of the 41,162 cells must resolve to exactly what the shipped
reader returns, for every encoding, before anything is timed.

Run::

    PYTHONPATH=. uv run python prototypes/shortcut_file_format_bench.py

Both backends were checked and neither the load path nor the dispatch touches
point-in-polygon, so unlike the companion script this one is backend-independent.


FINDINGS (2026-08-22, `3352a5a`, Apple arm64, Python 3.14.2, numpy 2.3.5, data 2026c)

Every encoding reproduces the shipped mapping exactly - all 41,162 cells, three plain
encodings x two dispatches plus two deduplicated ones - before anything below was timed.

    payload: 54,024 uint16 values (105.5 KiB) over 41,162 entries; lengths 1-59,
    30,651 of them unique-zone
    dedup:   2,847 distinct entries of 41,162 (6.9%), payload 54,024 -> 7,344 values
             (105.5 -> 14.3 KiB, 7.4x)

File size, KiB on disk:

    FlatBuffers (shipped)   1,530.1     1.0x
    slot-offsets              349.5     4.4x
    slot-lengths              166.5     9.2x
    keys-offsets              587.9     2.6x
    slot-dedup                147.5    10.4x
    keys-dedup                427.5     3.6x

Load, ms for a cold construction of the shortcut structure:

    FlatBuffers -> dict       377.17         1x
    slot-offsets                0.034   11,245x   parse 0.009 / +zone table 0.464
    slot-lengths                0.164    2,305x   parse 0.142 / +zone table 0.466
    keys-offsets                0.297    1,271x   parse 0.262 / +zone table 0.466
    slot-dedup                  0.026   14,483x   parse 0.006 / +zone table 0.550
    keys-dedup                  0.131    2,878x   parse 0.107 / +zone table 0.552

One lookup, inlined, with no query around it - ns per call:

    stratum      dict.get  len-disp  derived   d-len  d-derived
    unique            121       352      194    +230        +73
    ambiguous         131       412      438    +281       +307

    what deduplication adds, both sides on the derived table:
    stratum         plain  deduped   delta
    unique            195      194      -1
    ambiguous         426      535    +109

Memory, MiB traced, one fresh subprocess per structure: the dict 4.44, every plain
encoding 0.46 (**-3.98**), both deduplicated ones 0.26 (**-4.17**). The plain three
converge because they hold identical arrays once loaded; an earlier run had them
differing, which was this script returning `np.frombuffer` views that kept the file buffer
alive - `np.ascontiguousarray` does not copy an already-contiguous view, and only
`.copy()` does. Exactly the trap the shipped loader carries a comment about, reproduced
here by accident.

CONCLUSIONS

1. **The load win is real but it is almost all PERF-5's, not this change's.** 377 ms to
   0.03 ms is four orders of magnitude, and it is the wrong comparison to rank on: PERF-5
   takes the same construction to ~21 ms with no format change and no release. What a flat
   file takes *on top* of that is the ~21 ms PERF-5 leaves - of which **at least 5.1 ms is
   dict insertion alone**, measured here from values already extracted, and the rest is the
   per-entry value objects a flat file never builds. Sequence PERF-5 first; then this is
   worth ~21 ms, not ~400.

2. **The format shrinks the packaged binary 2.6-10.4x**, which no in-memory change can do
   and which the memory item alone never claimed. That is the argument this change has that
   neither GH-477's original framing nor PERF-5 has.

3. **Most entries are not distinct, and this is the largest single lever in the format.**
   2,847 distinct of 41,162 - **6.9%** - collapsing the payload 7.4x. It is not a
   coincidence to be re-checked per release but a consequence of the shape of the data:
   30,651 entries are a single zone id and only 271 distinct values appear among them,
   because the ocean zones cover enormous areas at one zone id each (`(440,)` alone repeats
   1,432 times). Deduplication also **shrinks memory a further 0.20 MiB** and costs
   **nothing on the unique path** (-1 ns; the derived zone table answers before the
   indirection is reached) and **+109 ns on the ambiguous one**, ~1 % of an ambiguous query
   - though ~10 % of `TimezoneFinderL`'s, which has no geometry to hide it.

   A further ~26 % of the distinct polygon lists (658 of 2,575) are a *suffix* of a longer
   one, so overlap-sharing would compress further. Not prototyped: it turns a hash-consing
   pass into a substring-packing problem for a payload already down to 14 KiB.

4. **Dispatch on a derived table, never on the length.** The length discriminator is right
   in the *file* - it removes the union tag and costs nothing to store - and wrong at
   runtime: +230 ns against +73 ns on the unique path, because it needs two offset reads
   and a subtraction where an `int16` zone table needs one read. Deriving that table costs
   ~0.5 ms at load, more than the parse itself and still nothing against 21 ms. So the file
   stores lengths implicitly and the reader materialises a zone table; those are not the
   same decision and the elegant answer to the first is the wrong answer to the second.

   The +73 ns here is a lookup in isolation and **overstates the query cost**: it compares
   against an `isinstance` dispatch where the shipped code uses a `match` statement, which
   is slower. `prototypes/shortcut_layout_bench.py` measured the same layout inside a real
   `timezone_at` at +4 ns, under the noise floor, and that whole-query figure is the one to
   quote.

5. **Do not put h3's bit layout in the data format.** Addressing by slot is smallest and
   fastest because the cell id *is* the index - and it bakes an encoding h3-py does not
   promise as API, plus `SHORTCUT_H3_RES`, into bytes that outlive the reader. Storing the
   cell ids instead moves that coupling into the reader, which is versioned with the
   package and can change freely.

   **Deduplication raises this premium and does not overturn it.** Before dedup it cost
   238 KiB (587.9 against 349.5); after, the keys are 329 KiB of a 427.5 KiB file and the
   premium is 2.9x rather than 1.7x. Still 3.6x smaller than what ships today, and still
   worth it against a format that cannot be revised without a release.

   The obvious escape - drop the keys entirely and enumerate the cells at load, since the
   index is dense and h3's *public* API can list them - is **refused on measurement**:
   enumerating all 41,162 res-3 cells takes **4.5 ms**, 35x the whole `keys-dedup` load and
   about a fifth of PERF-5's 21 ms. Storing 329 KiB is far cheaper than recomputing it.

6. **`slot-lengths` is the smallest non-deduplicated file and should still be refused.** Its
   166.5 KiB rests on every entry fitting a `uint8` length - the packaged maximum is 59,
   which is a fact about the data and not a guarantee of the format. A dataset with a
   256-polygon cell would silently need a new layout version. Note the same caution does
   *not* apply to the `uint16` dedup index, which is checked against the distinct-entry
   count at write time and has four orders of magnitude of headroom.

RECOMMENDATION

If this is built: **`keys-dedup` on disk** - stored cell ids, a `uint16` index per entry
into a deduplicated entry table, one `uint16` payload - **with the zone table derived at
load**. ~428 KiB (3.6x smaller than today), ~0.13 ms to load, **-4.17 MiB** resident, no
h3 internals in the format, free on the unique query path and ~1 % of an ambiguous one.

But build **PERF-5 first**. It is free, needs no release, and it takes this item's headline
number from ~400 ms to ~21 ms before the format question is even asked.

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

# Values are zone ids (0..443 today) and polygon ids (0..1321 today) in ONE array, which
# only works because both fit the same width. A converter would assert it rather than
# assume it; here it is checked in `build_payload` so the prototype cannot quietly lie.
PAYLOAD_DTYPE = np.uint16
OFFSET_DTYPE = np.uint32

# Absent / unique-zone / polygon-list are distinguished by the entry's *length*: 0, 1, >=2.
# A stored list can never have length 1 by construction - `compute_unique_shortcut_mapping`
# collapses any cell whose polygons all share a zone, and a one-polygon cell trivially
# does - so this needs no tag. `build_payload` re-checks it against the packaged data.
UNIQUE_LEN = 1

# for the derived-table dispatch; matches the companion script's sentinels
POLYGON_LIST = -1
ABSENT = -2

REPEATS = 7


# ---------------------------------------------------------------------------
# building the payload
# ---------------------------------------------------------------------------


def build_payload(
    mapping: dict[int, int | np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (sorted cell ids, per-entry lengths, concatenated payload).

    Entries are emitted in ascending cell id order, which is also ascending slot order:
    the base cell occupies the high bits of both, so the two orders cannot disagree.
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
                    "a stored polygon list of length 1 makes the length ambiguous with a "
                    "unique zone id; the converter is expected to make this impossible"
                )
            if len(value) and int(value.max()) > info.max:
                raise AssertionError(f"polygon id does not fit {PAYLOAD_DTYPE}")
            chunks.append(value.astype(PAYLOAD_DTYPE, copy=False))
            lengths[i] = len(value)
    payload = np.concatenate(chunks) if chunks else np.empty(0, dtype=PAYLOAD_DTYPE)
    return keys, lengths, payload


def lengths_by_slot(keys: np.ndarray, lengths: np.ndarray) -> np.ndarray:
    """Scatter per-entry lengths onto the dense slot table. Absent slots stay 0."""
    out = np.zeros(SLOT_TABLE_SIZE, dtype=np.int64)
    out[slots_of(keys)] = lengths
    return out


def offsets_from_lengths(lengths: np.ndarray) -> np.ndarray:
    offsets = np.zeros(len(lengths) + 1, dtype=OFFSET_DTYPE)
    np.cumsum(lengths, out=offsets[1:], dtype=OFFSET_DTYPE)
    return offsets


# ---------------------------------------------------------------------------
# the three encodings: write and read
# ---------------------------------------------------------------------------
# A real implementation would carry a file identifier and a layout version the way
# `hybrid_shortcuts.py` does. Omitted here on purpose: an 8-byte header cannot move any
# number below, and inventing one invites arguing about it instead of about the layout.


def write_slot_offsets(path: Path, keys, lengths, payload) -> None:
    offsets = offsets_from_lengths(lengths_by_slot(keys, lengths))
    with open(path, "wb") as f:
        f.write(offsets.tobytes())
        f.write(payload.tobytes())


def read_slot_offsets(buf: bytes) -> tuple[np.ndarray, np.ndarray]:
    n_off = SLOT_TABLE_SIZE + 1
    split = n_off * OFFSET_DTYPE().itemsize
    # `.copy()`, not `np.ascontiguousarray`: the latter returns an already-contiguous
    # view unchanged, and a surviving view keeps the whole file buffer alive - the trap
    # the shipped loader carries a comment about. A reader must own its arrays.
    offsets = np.frombuffer(buf, dtype=OFFSET_DTYPE, count=n_off).copy()
    payload = np.frombuffer(buf, dtype=PAYLOAD_DTYPE, offset=split).copy()
    return offsets, payload


def write_slot_lengths(path: Path, keys, lengths, payload) -> None:
    per_slot = lengths_by_slot(keys, lengths)
    if per_slot.max() > np.iinfo(np.uint8).max:
        raise AssertionError("a shortcut entry is too long for uint8 lengths")
    with open(path, "wb") as f:
        f.write(per_slot.astype(np.uint8).tobytes())
        f.write(payload.tobytes())


def read_slot_lengths(buf: bytes) -> tuple[np.ndarray, np.ndarray]:
    per_slot = np.frombuffer(buf, dtype=np.uint8, count=SLOT_TABLE_SIZE)
    payload = np.frombuffer(buf, dtype=PAYLOAD_DTYPE, offset=SLOT_TABLE_SIZE).copy()
    return offsets_from_lengths(per_slot), payload


def write_keys_offsets(path: Path, keys, lengths, payload) -> None:
    offsets = offsets_from_lengths(lengths)
    with open(path, "wb") as f:
        f.write(np.int64(len(keys)).tobytes())
        f.write(keys.tobytes())
        f.write(offsets.tobytes())
        f.write(payload.tobytes())


def read_keys_offsets(buf: bytes) -> tuple[np.ndarray, np.ndarray]:
    n = int(np.frombuffer(buf, dtype=np.int64, count=1)[0])
    pos = 8
    keys = np.frombuffer(buf, dtype=np.int64, count=n, offset=pos)
    pos += n * 8
    entry_offsets = np.frombuffer(buf, dtype=OFFSET_DTYPE, count=n + 1, offset=pos)
    pos += (n + 1) * OFFSET_DTYPE().itemsize
    payload = np.frombuffer(buf, dtype=PAYLOAD_DTYPE, offset=pos).copy()
    # the format says nothing about h3's bit layout; the reader derives the slot table
    per_slot = np.zeros(SLOT_TABLE_SIZE, dtype=np.int64)
    per_slot[slots_of(keys)] = np.diff(entry_offsets.astype(np.int64))
    return offsets_from_lengths(per_slot), payload


ENCODINGS: dict[str, tuple[Callable, Callable]] = {
    "slot-offsets": (write_slot_offsets, read_slot_offsets),
    "slot-lengths": (write_slot_lengths, read_slot_lengths),
    "keys-offsets": (write_keys_offsets, read_keys_offsets),
}


# ---------------------------------------------------------------------------
# deduplication: most entries are not distinct
# ---------------------------------------------------------------------------
# 30,651 of the 41,162 entries are a single zone id and there are only a few hundred
# zones, so the unique-zone half of the payload is almost entirely repetition - the
# ocean cells especially, since `Etc/GMT+-XX` covers vast areas at one zone id each.
# Pointing every entry that holds the same sequence at the same payload range costs
# nothing at runtime beyond one extra array read, and only on the ambiguous path: the
# unique path is answered by the derived zone table either way.
#
# The deduped runtime shape is deliberately NOT a CSR `offsets` array. Dedup breaks the
# contiguity CSR relies on - slot i and slot i+1 no longer point at adjacent ranges - so
# expanding it back to per-slot starts and ends would need two full-width arrays and come
# out *larger* than not deduplicating at all. Keeping the indirection is both smaller and
# simpler: a narrow index per slot into a small table of (offset, length).

DEDUP_INDEX_DTYPE = np.uint16


def build_dedup(
    keys: np.ndarray, lengths: np.ndarray, payload: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (entry index per entry, distinct-entry offsets, deduped payload)."""
    seen: dict[bytes, int] = {}
    index = np.empty(len(keys), dtype=np.int64)
    chunks: list[np.ndarray] = []
    starts: list[int] = []
    cursor = 0
    pos = 0
    for i, length in enumerate(lengths):
        chunk = payload[pos : pos + length]
        pos += length
        key = chunk.tobytes()
        found = seen.get(key)
        if found is None:
            found = len(starts)
            seen[key] = found
            starts.append(cursor)
            chunks.append(chunk)
            cursor += length
        index[i] = found
    if len(starts) + 1 > np.iinfo(DEDUP_INDEX_DTYPE).max:
        raise AssertionError(
            f"{len(starts):,} distinct entries do not fit {DEDUP_INDEX_DTYPE.__name__}; "
            "the per-slot index would have to widen"
        )
    # twice: the first closes the last real entry, the second gives the absent marker
    # (index `len(starts) - 2` after both appends) an empty range of its own, so an
    # uncovered slot slices nothing rather than running off the end
    starts.append(cursor)
    starts.append(cursor)
    deduped = np.concatenate(chunks) if chunks else np.empty(0, dtype=PAYLOAD_DTYPE)
    return index, np.array(starts, dtype=OFFSET_DTYPE), deduped


def index_by_slot(keys: np.ndarray, index: np.ndarray, absent: int) -> np.ndarray:
    """Scatter the per-entry index onto the dense slot table."""
    out = np.full(SLOT_TABLE_SIZE, absent, dtype=DEDUP_INDEX_DTYPE)
    out[slots_of(keys)] = index
    return out


def write_slot_dedup(path: Path, keys, lengths, payload) -> None:
    index, entry_offsets, deduped = build_dedup(keys, lengths, payload)
    # the absent marker is one past the last real entry; its range is empty
    absent = len(entry_offsets) - 2
    per_slot = index_by_slot(keys, index, absent)
    with open(path, "wb") as f:
        f.write(np.int64(len(entry_offsets)).tobytes())
        f.write(per_slot.tobytes())
        f.write(entry_offsets.tobytes())
        f.write(deduped.tobytes())


def read_slot_dedup(buf: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n_off = int(np.frombuffer(buf, dtype=np.int64, count=1)[0])
    pos = 8
    per_slot = np.frombuffer(
        buf, dtype=DEDUP_INDEX_DTYPE, count=SLOT_TABLE_SIZE, offset=pos
    ).copy()
    pos += SLOT_TABLE_SIZE * DEDUP_INDEX_DTYPE().itemsize
    entry_offsets = np.frombuffer(
        buf, dtype=OFFSET_DTYPE, count=n_off, offset=pos
    ).copy()
    pos += n_off * OFFSET_DTYPE().itemsize
    payload = np.frombuffer(buf, dtype=PAYLOAD_DTYPE, offset=pos).copy()
    return per_slot, entry_offsets, payload


def write_keys_dedup(path: Path, keys, lengths, payload) -> None:
    index, entry_offsets, deduped = build_dedup(keys, lengths, payload)
    with open(path, "wb") as f:
        f.write(np.int64(len(keys)).tobytes())
        f.write(np.int64(len(entry_offsets)).tobytes())
        f.write(keys.tobytes())
        f.write(index.astype(DEDUP_INDEX_DTYPE).tobytes())
        f.write(entry_offsets.tobytes())
        f.write(deduped.tobytes())


def read_keys_dedup(buf: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n, n_off = np.frombuffer(buf, dtype=np.int64, count=2)
    n, n_off = int(n), int(n_off)
    pos = 16
    keys = np.frombuffer(buf, dtype=np.int64, count=n, offset=pos)
    pos += n * 8
    index = np.frombuffer(buf, dtype=DEDUP_INDEX_DTYPE, count=n, offset=pos)
    pos += n * DEDUP_INDEX_DTYPE().itemsize
    entry_offsets = np.frombuffer(
        buf, dtype=OFFSET_DTYPE, count=n_off, offset=pos
    ).copy()
    pos += n_off * OFFSET_DTYPE().itemsize
    payload = np.frombuffer(buf, dtype=PAYLOAD_DTYPE, offset=pos).copy()
    per_slot = index_by_slot(keys, index, len(entry_offsets) - 2)
    return per_slot, entry_offsets, payload


DEDUP_ENCODINGS: dict[str, tuple[Callable, Callable]] = {
    "slot-dedup": (write_slot_dedup, read_slot_dedup),
    "keys-dedup": (write_keys_dedup, read_keys_dedup),
}


def derive_zone_table_dedup(
    per_slot: np.ndarray, entry_offsets: np.ndarray, payload: np.ndarray
) -> np.ndarray:
    """The ``int16`` zone-or-sentinel table, over the deduped shape."""
    lens = np.diff(entry_offsets.astype(np.int64))[per_slot]
    out = np.full(SLOT_TABLE_SIZE, ABSENT, dtype=np.int16)
    out[lens >= 2] = POLYGON_LIST
    unique = lens == UNIQUE_LEN
    out[unique] = payload[entry_offsets[per_slot[unique]]].astype(np.int16)
    return out


def lookup_dedup(per_slot, entry_offsets, payload, zone_by_slot, hex_id: int):
    slot = ((hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * SLOT_STRIDE + (
        (hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK
    )
    zone_id = zone_by_slot[slot]
    if zone_id >= 0:
        return int(zone_id)
    if zone_id == ABSENT:
        return None
    e = per_slot[slot]
    return payload[entry_offsets[e] : entry_offsets[e + 1]]


def derive_zone_table(offsets: np.ndarray, payload: np.ndarray) -> np.ndarray:
    """An ``int16`` zone-or-sentinel per slot, for the ``derived-table`` dispatch.

    One vectorised pass at load. Absent slots read ABSENT, polygon-list slots
    POLYGON_LIST, and unique slots the zone id itself.
    """
    lens = np.diff(offsets.astype(np.int64))
    out = np.full(SLOT_TABLE_SIZE, ABSENT, dtype=np.int16)
    out[lens >= 2] = POLYGON_LIST
    unique = lens == UNIQUE_LEN
    out[unique] = payload[offsets[:-1][unique]].astype(np.int16)
    return out


# ---------------------------------------------------------------------------
# the two runtime dispatches
# ---------------------------------------------------------------------------


def lookup_len_dispatch(offsets, payload, hex_id: int):
    slot = ((hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * SLOT_STRIDE + (
        (hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK
    )
    start = offsets[slot]
    end = offsets[slot + 1]
    n = end - start
    if n == 0:
        return None
    if n == UNIQUE_LEN:
        return int(payload[start])
    return payload[start:end]


def lookup_derived_table(offsets, payload, zone_by_slot, hex_id: int):
    slot = ((hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK) * SLOT_STRIDE + (
        (hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK
    )
    zone_id = zone_by_slot[slot]
    if zone_id >= 0:
        return int(zone_id)
    if zone_id == ABSENT:
        return None
    return payload[offsets[slot] : offsets[slot + 1]]


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


def check_agreement(mapping, offsets, payload, zone_by_slot, label: str) -> None:
    """Every cell must resolve exactly as the shipped reader says, both dispatches."""
    for hex_id, expected in mapping.items():
        for name, got in (
            ("len-dispatch", lookup_len_dispatch(offsets, payload, hex_id)),
            (
                "derived-table",
                lookup_derived_table(offsets, payload, zone_by_slot, hex_id),
            ),
        ):
            if isinstance(expected, (int, np.integer)):
                ok = isinstance(got, int) and got == int(expected)
            else:
                ok = isinstance(got, np.ndarray) and np.array_equal(got, expected)
            if not ok:
                raise AssertionError(
                    f"{label}/{name} disagrees on cell {hex_id:#x}: {got!r} != {expected!r}"
                )
    # and no cell outside the index may be invented
    absent = int((zone_by_slot == ABSENT).sum())
    if absent != SLOT_TABLE_SIZE - len(mapping):
        raise AssertionError(
            f"{label}: {absent} absent slots, expected {SLOT_TABLE_SIZE - len(mapping)}"
        )


def check_agreement_dedup(
    mapping, per_slot, entry_offsets, payload, zone_by_slot, label: str
) -> None:
    """Same gate, over the deduplicated shape - sharing must not leak a neighbour's ids."""
    for hex_id, expected in mapping.items():
        got = lookup_dedup(per_slot, entry_offsets, payload, zone_by_slot, hex_id)
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


# ---------------------------------------------------------------------------
# memory: one subprocess per structure, as scripts/_memory_probe.py argues
# ---------------------------------------------------------------------------

MEMORY_TARGETS = (
    "dict",
    "slot-offsets",
    "slot-lengths",
    "keys-offsets",
    "slot-dedup",
    "keys-dedup",
)


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
        if target in DEDUP_ENCODINGS:
            per_slot, ent_off, payload = DEDUP_ENCODINGS[target][1](buf)
            kept = (
                per_slot,
                ent_off,
                payload,
                derive_zone_table_dedup(per_slot, ent_off, payload),
            )
        else:
            offsets, payload = ENCODINGS[target][1](buf)
            kept = (offsets, payload, derive_zone_table(offsets, payload))
        del buf
    gc.collect()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert kept is not None
    return {"target": target, "current": current, "peak": peak}


def measure_memory() -> list[dict]:
    results = []
    for target in MEMORY_TARGETS:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--memory-probe", target],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(PROJECT_ROOT),
        )
        results.append(json.loads(proc.stdout.strip().splitlines()[-1]))
    return results


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
    print(
        f"payload: {len(payload):,} {PAYLOAD_DTYPE.__name__} values "
        f"({payload.nbytes / 1024:,.1f} KiB) over {len(keys):,} entries; "
        f"lengths {lengths.min()}-{lengths.max()}, "
        f"{int((lengths == UNIQUE_LEN).sum()):,} unique-zone"
    )

    for name, (write, _read) in {**ENCODINGS, **DEDUP_ENCODINGS}.items():
        write(OUT_DIR / f"{name}.bin", keys, lengths, payload)

    index, entry_offsets, deduped = build_dedup(keys, lengths, payload)
    print(
        f"dedup: {len(entry_offsets) - 1:,} distinct entries of {len(keys):,} "
        f"({(len(entry_offsets) - 1) / len(keys) * 100:.1f}%), payload "
        f"{len(payload):,} -> {len(deduped):,} values "
        f"({payload.nbytes / 1024:,.1f} -> {deduped.nbytes / 1024:,.1f} KiB, "
        f"{len(payload) / len(deduped):.1f}x)"
    )

    # correctness gate, before any timing
    for name, (_write, read) in ENCODINGS.items():
        buf = (OUT_DIR / f"{name}.bin").read_bytes()
        offsets, pay = read(buf)
        check_agreement(mapping, offsets, pay, derive_zone_table(offsets, pay), name)
    for name, (_write, read) in DEDUP_ENCODINGS.items():
        buf = (OUT_DIR / f"{name}.bin").read_bytes()
        per_slot, ent_off, pay = read(buf)
        zbs = derive_zone_table_dedup(per_slot, ent_off, pay)
        check_agreement_dedup(mapping, per_slot, ent_off, pay, zbs, name)
    print(
        f"agreement: every one of {len(mapping):,} cells resolves identically under "
        f"{len(ENCODINGS)} plain encodings x 2 dispatches and "
        f"{len(DEDUP_ENCODINGS)} deduplicated ones"
    )

    # ---- size ----
    shipped = shortcut_path.stat().st_size
    rows = [["FlatBuffers (shipped)", f"{shipped / 1024:,.1f}", "1.00x"]]
    for name in {**ENCODINGS, **DEDUP_ENCODINGS}:
        size = (OUT_DIR / f"{name}.bin").stat().st_size
        rows.append([name, f"{size / 1024:,.1f}", f"{shipped / size:.1f}x"])
    table("File size - KiB on disk", ["encoding", "KiB", "smaller by"], rows)

    # ---- load ----
    shipped_load = measure(lambda: read_hybrid_shortcuts_binary(shortcut_path), 3)
    rows = [
        [
            "FlatBuffers -> dict (shipped)",
            f"{shipped_load * 1e3:,.2f}",
            "1.00x",
            "",
        ]
    ]
    for name, (_write, read) in ENCODINGS.items():
        path = OUT_DIR / f"{name}.bin"
        buf = path.read_bytes()

        def load_full(read=read, path=path):
            return read(path.read_bytes())

        def load_and_derive(read=read, path=path):
            offsets, pay = read(path.read_bytes())
            return offsets, pay, derive_zone_table(offsets, pay)

        t_parse = measure(lambda read=read, buf=buf: read(buf), 50)
        t_full = measure(load_full, 50)
        t_derived = measure(load_and_derive, 50)
        rows.append(
            [
                name,
                f"{t_full * 1e3:,.3f}",
                f"{shipped_load / t_full:,.0f}x",
                f"parse {t_parse * 1e3:.3f} / +table {(t_derived - t_full) * 1e3:.3f}",
            ]
        )
    for name, (_write, read) in DEDUP_ENCODINGS.items():
        path = OUT_DIR / f"{name}.bin"
        buf = path.read_bytes()

        def load_full(read=read, path=path):
            return read(path.read_bytes())

        def load_and_derive(read=read, path=path):
            per_slot, ent_off, pay = read(path.read_bytes())
            return (
                per_slot,
                ent_off,
                pay,
                derive_zone_table_dedup(per_slot, ent_off, pay),
            )

        t_parse = measure(lambda read=read, buf=buf: read(buf), 50)
        t_full = measure(load_full, 50)
        t_derived = measure(load_and_derive, 50)
        rows.append(
            [
                name,
                f"{t_full * 1e3:,.3f}",
                f"{shipped_load / t_full:,.0f}x",
                f"parse {t_parse * 1e3:.3f} / +table {(t_derived - t_full) * 1e3:.3f}",
            ]
        )
    table(
        "Load - ms for a cold construction of the shortcut structure",
        ["encoding", "ms", "faster by", "breakdown (ms)"],
        rows,
    )

    # ---- what PERF-5 leaves ----
    hex_ids = [int(k) for k in keys]
    values = [mapping[k] for k in hex_ids]
    pairs = list(zip(hex_ids, values))
    t_dict = measure(lambda: dict(pairs), 20)
    t_dict_loop = measure(lambda: {k: v for k, v in pairs}, 20)
    print(
        f"\nThe residue PERF-5 leaves: materialising the dict from values already extracted "
        f"is {t_dict * 1e3:.2f} ms (dict(pairs)) / {t_dict_loop * 1e3:.2f} ms "
        f"(comprehension).\n  That is what a flat file removes on top of PERF-5's ~21 ms; "
        f"everything above it is PERF-5's to win."
    )

    # ---- query dispatch ----
    buf = (OUT_DIR / "slot-offsets.bin").read_bytes()
    offsets, pay = read_slot_offsets(buf)
    zone_by_slot = derive_zone_table(offsets, pay)
    uniq = [k for k, v in pairs if isinstance(v, (int, np.integer))][:2000]
    amb = [k for k, v in pairs if not isinstance(v, (int, np.integer))][:2000]
    # Every variant below is written out inline in its own comprehension rather than
    # called through `lookup_*`. A Python function call is ~60 ns - two thirds of the
    # dict lookup being compared against - and `mapping.get` in a comprehension pays
    # none, so routing only the flat variants through a helper would measure this file.
    rows = []
    get = mapping.get
    for label, cells in (("unique", uniq), ("ambiguous", amb)):
        n = len(cells)
        # The dict column carries the `match` the shipped `timezone_at` performs on the
        # value it gets back. Without it the comparison is a dict that *stores* the
        # answer against a flat layout that *computes* it, which flatters the dict by
        # exactly the dispatch it actually pays.
        t_dict_get = (
            measure(
                lambda cells=cells: [
                    (v if isinstance(v, int) else (None if v is None else v))
                    for c in cells
                    for v in (get(c),)
                ]
            )
            / n
        )
        t_len = (
            measure(
                lambda cells=cells: [
                    (
                        None
                        if (e := offsets[s + 1]) == (b := offsets[s])
                        else (int(pay[b]) if e - b == UNIQUE_LEN else pay[b:e])
                    )
                    for c in cells
                    for s in (
                        ((c >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK)
                        * SLOT_STRIDE
                        + ((c >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK),
                    )
                ]
            )
            / n
        )
        t_tab = (
            measure(
                lambda cells=cells: [
                    (
                        int(z)
                        if (z := zone_by_slot[s]) >= 0
                        else (None if z == ABSENT else pay[offsets[s] : offsets[s + 1]])
                    )
                    for c in cells
                    for s in (
                        ((c >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK)
                        * SLOT_STRIDE
                        + ((c >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK),
                    )
                ]
            )
            / n
        )
        rows.append(
            [
                label,
                f"{t_dict_get * 1e9:,.0f}",
                f"{t_len * 1e9:,.0f}",
                f"{t_tab * 1e9:,.0f}",
                f"{(t_len - t_dict_get) * 1e9:+,.0f}",
                f"{(t_tab - t_dict_get) * 1e9:+,.0f}",
            ]
        )
    table(
        "Lookup dispatch over the flat bytes - ns per call, inlined, no query around it",
        ["stratum", "dict.get", "len-disp", "derived", "d-len", "d-derived"],
        rows,
    )

    # what the extra indirection costs: dedup adds one array read, and only where the
    # derived zone table does not already answer - the ambiguous path
    dbuf = (OUT_DIR / "slot-dedup.bin").read_bytes()
    d_slot, d_off, d_pay = read_slot_dedup(dbuf)
    d_zbs = derive_zone_table_dedup(d_slot, d_off, d_pay)
    rows = []
    for label, cells in (("unique", uniq), ("ambiguous", amb)):
        n = len(cells)
        t_plain = (
            measure(
                lambda cells=cells: [
                    (
                        int(z)
                        if (z := zone_by_slot[s]) >= 0
                        else (None if z == ABSENT else pay[offsets[s] : offsets[s + 1]])
                    )
                    for c in cells
                    for s in (
                        ((c >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK)
                        * SLOT_STRIDE
                        + ((c >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK),
                    )
                ]
            )
            / n
        )
        t_dedup = (
            measure(
                lambda cells=cells: [
                    (
                        int(z)
                        if (z := d_zbs[s]) >= 0
                        else (
                            None
                            if z == ABSENT
                            else d_pay[d_off[(e := d_slot[s])] : d_off[e + 1]]
                        )
                    )
                    for c in cells
                    for s in (
                        ((c >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK)
                        * SLOT_STRIDE
                        + ((c >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK),
                    )
                ]
            )
            / n
        )
        rows.append(
            [
                label,
                f"{t_plain * 1e9:,.0f}",
                f"{t_dedup * 1e9:,.0f}",
                f"{(t_dedup - t_plain) * 1e9:+,.0f}",
            ]
        )
    table(
        "What deduplication costs at lookup - ns per call, both on the derived table",
        ["stratum", "plain", "deduped", "delta"],
        rows,
    )

    if not args.skip_memory:
        rows = []
        base = None
        for result in measure_memory():
            current = result["current"]
            if base is None:
                base = current
            rows.append(
                [
                    result["target"],
                    f"{current / 2**20:,.2f}",
                    f"{(current - base) / 2**20:+,.2f}",
                ]
            )
        table(
            "Memory - MiB traced, one fresh subprocess per structure",
            ["structure", "MiB", "vs dict"],
            rows,
        )

    tf.cleanup()


if __name__ == "__main__":
    main()
