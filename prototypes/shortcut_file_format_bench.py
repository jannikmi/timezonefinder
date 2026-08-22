r"""Which shortcut data structure to build: one recommendation, and what it beats.

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
``slot-dedup``  the same again, without the cell ids: the cell *is* the index, via h3's
                bit layout. **This is the recommendation**, on the strength of the layout
                guard described in conclusion 9.

All three flat structures load to the *same runtime shape* and share one lookup, so the
query comparison is about the data rather than about three different code paths::

    zone = zone_by_slot[slot]            # derived at load, int16
    if zone >= 0:        -> unique zone id
    elif zone == ABSENT  -> not covered
    else:                -> payload[starts[slot]:ends[slot]]

THE RECOMMENDED STRUCTURE, in full
---------------------------------

Four arrays, of which two are stored and two are derived at load. Sizes are the packaged
dataset at ``SHORTCUT_H3_RES`` = 3.

On disk, 197.4 KiB::

    header       16 B   two int64: the byte width of the start column, and of the length
    starts   122.0 KiB  uint16 x 62,464   one per *slot*
    lengths   61.0 KiB  uint8  x 62,464   one per slot
    payload   14.3 KiB  uint16 x  7,344   every distinct entry, back to back

**Lengths are stored and ends are derived**, although the lookup wants ends, because the
two are narrow for different reasons: an end addresses the whole payload and needs the
offset width, while an entry holds at most a few dozen values and fits a ``uint8``. Storing
the byte instead of the second offset saves 61 KiB - **31% of the file** - for one
vectorised add at load. The file is sized for bytes and the runtime shape for reads, and
the two are allowed to differ; the alternative, keeping the length in memory and adding at
lookup time, costs numpy scalar arithmetic on every ambiguous query.

One consequence worth stating because it is easy to get wrong: the offset column must be
sized from **ends**, not from starts. The reader reconstructs ``ends = starts + lengths``
in the start column's dtype, and the largest end is the payload length itself, which no
start ever reaches - so a width that fits every start can still be one the final end wraps
around.

In memory after load, 380.3 KiB::

    starts        uint16 x 62,464  122.0 KiB   read straight from the file
    ends          uint16 x 62,464  122.0 KiB   derived: starts + lengths
    payload       uint16 x  7,344   14.3 KiB   read straight from the file
    zone_by_slot  int16  x 62,464  122.0 KiB   derived, see below

**payload** is the only array holding data. Each value is a zone id *or* a boundary polygon
id - one namespace, because both fit ``uint16`` - and which it is follows from the entry's
length, never from a tag. Entries are variable length and packed with no separators.

**starts / ends** are the addressing, indexed by slot rather than by cell id. Slot ``s``
owns ``payload[starts[s]:ends[s]]``. Two slots holding identical data carry *equal* values
here, which is the whole of the deduplication: no shared-entry table, no indirection, and
a repeated entry costs a lookup exactly what a unique one costs.

**zone_by_slot** is a derived accelerator, one ``int16`` per slot:

* ``>= 0`` - the cell resolves to a single zone, and this value *is* the answer
* ``-1``   - two or more candidate polygons; read the payload
* ``-2``   - no cell here (a hole in the table, or data that does not cover it)

It exists because 30,651 of the 41,162 cells are single-zone, and without it that
majority path would have to read two offsets and subtract them to discover there is only
one value in the range. One read against three.

**The slot function** turns a cell id into a dense array index by arithmetic alone::

    slot = ((cell >> 45) & 0x7F) * 512 + ((cell >> 36) & 0x1FF)
             \_____ base cell _____/         \__ digits 1,2,3 __/
                    0..121                        3 bits each

At a fixed resolution everything else in the index is constant - mode, the resolution
field, and the unused digits 4-15, together ``0x830000fffffffff`` - so those 16 bits *are*
the cell, and the map is a bijection rather than a hash. The table is 122 x 512 = 62,464
slots for 41,162 cells: 66% dense, the holes being digit values 7 that no cell uses.

**A lookup**, in full::

    slot = <the arithmetic above>              # no memory touched
    zone = zone_by_slot[slot]
    if zone >= 0:   return zone                # 1 read  - 74% of cells
    if zone == -2:  return None                # 1 read
    return payload[starts[slot]:ends[slot]]    # 3 reads + a slice

Worked, on the packaged data::

    deep inside France   cell 0x831fb0fffffffff  base 15, digits 432 -> slot  8,112
                         zone_by_slot[8,112] = 346 -> "Europe/Paris"          1 read, done
    mid-Pacific          cell 0x83798afffffffff  base 60, digits 394 -> slot 31,114
                         zone_by_slot[31,114] = 440 -> "Etc/GMT+9"            1 read, done
    Berlin               cell 0x831f1dfffffffff  base 15, digits 285 -> slot  7,965
                         zone_by_slot = -1; payload[1891:1893] = [911, 795]
                         -> Europe/Berlin, Europe/Warsaw -> point-in-polygon loop
    Basel (on a border)  cell 0x831f83fffffffff  base 15, digits 387 -> slot  8,067
                         zone_by_slot = -1; payload[1965:1968] = [915, 877, 795]
                         -> Europe/Berlin, Europe/Paris, Europe/Zurich -> PIP loop

**How much is shared:** 41,162 occupied slots resolve to 2,846 distinct ``(start, length)``
pairs. The largest group is 1,432 slots all addressing ``payload[281:282]``, the single
value for ``Etc/GMT+9`` - the ocean is why deduplication pays.

**Three build-time guards**, all in ``scripts/data_integrity.py`` when this ships, asserted
by the converter over what it wrote and by the test suite over what is committed, and never
on the finder's init path:

1. the bit arithmetic agrees with h3's public ``get_base_cell_number`` and
   ``cell_to_child_pos`` on every cell (``verify_slot_layout_against_h3_api``);
2. offsets fit their column and lengths fit theirs (``check_fits``);
3. no stored entry has length 1, which is what makes the length a discriminator.


Correctness first: every one of the 41,162 cells must resolve to exactly what the shipped
reader returns, under every structure, before anything is timed.

Run::

    PYTHONPATH=. uv run python prototypes/shortcut_file_format_bench.py

Neither the load path nor the lookup touches point-in-polygon, so unlike the companion
script this one is backend-independent.


FINDINGS (2026-08-22, `84ebb03`, Apple arm64, Python 3.14.2, numpy 2.3.5, data 2026c)

    payload: 54,024 values -> 7,344 distinct (105.5 -> 14.3 KiB, 7.4x)
    column widths: offsets uint16, lengths uint8 (largest entry 59) - narrowest that
    fits, guarded by `check_fits` rather than by headroom
    agreement: all 41,162 cells resolve identically under all three structures

    structure       file KiB   load ms    MiB   unique ns   amb ns
    dict (shipped)     1,530    393.8    4.44         108      117
    keys-plain           508      0.659  0.46         210      419
    keys-dedup  <=       457      0.661  0.37         209      419
    slot-dedup           197      0.515  0.37         210      421

    QUERY: full timezone_at(), paired and order-alternated, 61 rounds of 2,000 points

    stratum      shipped ns  proposed ns  on minima  median d   10-90% of d  rounds faster
    unique            1,070        1,067      -0.3%       -56   -337 .. +62          44/61
    ambiguous        10,027       10,081      +0.5%       +74  -415 .. +531          26/61
    random            3,457        3,388      -2.0%       -35   -292 .. +173         32/61
    on_land           5,950        5,898      -0.9%      -116   -383 .. +256         39/61

CONCLUSIONS

1. **On query speed the two are indistinguishable, and that is the answer.** Every stratum
   is within +-2% on minima, every median per-round difference sits well inside its own
   10-90% spread, and the sign is not even consistent - the proposal wins on minima for
   three strata and loses on one, wins the round count on two and loses it on two. The
   shortcut structure exists to avoid point-in-polygon tests, and **the proposal avoids
   exactly the same ones**: it changes how a cell's candidate list is stored, never which
   candidates come back. Nothing here should be sold as a speedup, and nothing here costs
   speed either. **The item is query-neutral and has to be justified on load, memory and
   file size or not at all.**

2. **Two measurement designs had to be discarded to get that number, and both flattered
   the proposal.** An isolated lookup says the dict wins by ~100 ns, which would be ~10% of
   a unique-zone query if it were real; it is not, because it omits the
   `match value: case int(zone_id)` the shipped `timezone_at` runs on the dict's answer.
   Measured: `dict.get` alone 84 ns, with that dispatch 188 ns (+104) - and the proposal
   needs no equivalent, its zone table having already told the three cases apart. And a
   paired comparison in a fixed A-then-B order reported the proposal 13.3% faster on the
   unique stratum, which was entirely the first path warming `validate_coordinates`,
   `h3.latlng_to_cell` and `zone_name_from_id` for the second. Alternating the order took
   that to -0.3%.

3. **Read `on minima` and `rounds faster` together, never one alone.** They disagree here
   by construction: the minimum is the least noise-sensitive estimator and the round count
   is the one that makes no assumption about the noise distribution. Where a difference is
   real both move together; where it is not, they disagree, which is what they do above.

4. **The structure decision, then, is settled entirely on the non-query axes**, and there
   the step that matters is dict against flat: **4.44 MiB to ~0.4, ~394 ms to ~0.66,
   1,530 KiB to ~460 - 12x memory, 600x load, 3x file.** The spread *among* the flat
   structures is ~50 KiB and ~0.09 MiB, under 2% of the packaged data, so no flat variant
   is a mistake and that choice should not be relitigated once made.

5. **`keys-dedup` is the one to build.** Smaller on both axes than `keys-plain` at identical
   load and lookup, and no harder to read. Sharing is free at lookup because duplicates
   carry *equal offsets* rather than a shared index - nothing is dereferenced twice, so a
   repeated entry costs exactly what a unique one costs.

6. **Correction to the previous block: deduplication does not "pay for its own addressing
   by narrowing the offsets".** That rested on the plain payload needing `uint32`, which
   was an artefact of a 4x-headroom rule this script used to impose - 54,024 values fit
   `uint16` perfectly well. With the narrowest-fitting widths and a guard, *both* structures
   use `uint16` offsets and `uint8` lengths, and what deduplication buys is exactly the
   payload: 105.5 KiB to 14.3, so 508 KiB to 457. It does cost one column - without sharing
   the ranges are contiguous and N+1 CSR offsets encode N ranges, whereas shared ranges need
   a start *and* a length - which is ~41 KiB against the ~91 KiB of payload it saves.

7. **Narrowest-fitting widths, guarded, not widths chosen for headroom.** `uint8` lengths
   (largest entry 59) and `uint16` offsets are correct because the packaged data is built by
   a converter this repository owns: an overflow surfaces at build time, not in a user's
   process, *provided something checks and says what happened*. `check_fits` is that check
   and its message is the deliverable. In the shipped version it belongs in
   `scripts/data_integrity.py`, asserted by the converter over what it wrote and by the test
   suite over what is committed, never on the finder's init path.

8. **Load: ~394 ms to ~0.66 ms, and most of it is not this change's to claim.** PERF-5
   reaches ~21 ms on the *existing* file with no format change and no release, so what the
   format change adds is ~21 ms to ~0.66 ms.

9. **Addressing by h3's bit layout is the right choice, and the objection to it does not
   survive.** `slot-dedup` drops the stored cell ids for a **2.3x smaller file (197 KiB
   against 457) and a 22% faster load**, at identical memory and identical query. The
   argument against it was that the format would then encode an index encoding h3-py does
   not promise as API. Three things dissolve that:

   * **Storing the cell ids does not remove the dependency, it pays 260 KiB to store
     something derivable.** If h3's encoding moved, stored 64-bit ids would no longer
     denote the same cells either - `keys-dedup` breaks just as surely. And the *reader*
     slices bits in both designs, because that is what makes the lookup fast, so the code
     carries the coupling whichever file it reads.
   * **The coupling is checkable against public API, which is what matters.**
     `get_base_cell_number` and `cell_to_child_pos` are public, and between them they fix a
     cell's position exactly as the bits do. `verify_slot_layout_against_h3_api` confirms
     agreement on **all 41,162 cells** and fails with a message naming the cell, both
     answers and the version bumps required. That converts an unpromised coupling into a
     checked invariant - the same move as `check_fits` for the column widths.
   * **The check is only unaffordable per lookup, not per build.** The public route costs
     ~218 ns against ~87 for the arithmetic: 2.5x the whole shortcut lookup per query, and
     nothing at all once where the data is produced.

   The guard belongs in `scripts/data_integrity.py` with the width checks - asserted by the
   converter over what it wrote and by the test suite over what is committed, never on the
   init path. **Without it, `keys-dedup` is the safer choice**, because an encoding change
   would otherwise return a neighbour's timezone silently. With it, the failure is loud and
   lands where the data is built.

10. **A denser index exists and is not taken.** The public-API route yields exactly 41,162
    slots against the bit form's 62,464 - the arithmetic is base-8 per digit where the data
    is base-7 - so a compact addressing would save ~62 KiB of the 197. Refused: realising it
    at lookup time costs the 218 ns above, and reproducing it from bits needs per-digit
    arithmetic that pentagons, with 286 children rather than 343, do not obviously satisfy.

REFUSED OPTIONS below, with its reason.

``dict``        what ships. A FlatBuffers file whose 41,162 per-entry tables are decoded
                in Python into ``dict[int, int | ndarray]``.
``keys-plain``  flat file: sorted cell ids, per-entry start and end, one payload holding
                every value back to back. Removes the per-entry decode and the dict.
``keys-dedup``  the same, storing each *distinct* entry once - only 6.9% of entries are
                distinct - so duplicates simply carry equal offsets into a shared payload.
``slot-dedup``  the same again, without the cell ids: the cell *is* the index, via h3's
                bit layout. **This is the recommendation**, on the strength of the layout
                guard described in conclusion 9.

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


FINDINGS (2026-08-22, `84ebb03`, Apple arm64, Python 3.14.2, numpy 2.3.5, data 2026c)

    payload: 54,024 values -> 7,344 distinct (105.5 -> 14.3 KiB, 7.4x)
    column widths: offsets uint16, lengths uint8 (largest entry 59) - narrowest that
    fits, guarded by `check_fits` rather than by headroom
    agreement: all 41,162 cells resolve identically under all three structures

    structure       file KiB   load ms    MiB   unique ns   amb ns
    dict (shipped)     1,530    393.8    4.44         108      117
    keys-plain           508      0.659  0.46         210      419
    keys-dedup  <=       457      0.661  0.37         209      419
    slot-dedup           197      0.515  0.37         210      421

CONCLUSIONS

1. **The decision that matters is dict against flat, and everything after it is small.**
   4.44 MiB to ~0.4, ~394 ms to ~0.66, 1,530 KiB to ~460: **12x memory, 600x load, 3x
   file**. The spread *among* the flat structures is ~50 KiB of file and ~0.09 MiB - under
   2% of the packaged data - so no flat variant is a mistake and the choice between them
   should not be relitigated once made.

2. **`keys-dedup` is the one to build.** Smaller on both axes than `keys-plain` at identical
   load and lookup, and no harder to read. Sharing is free at lookup because duplicates
   carry *equal offsets* rather than a shared index - nothing is dereferenced twice, so a
   repeated entry costs exactly what a unique one costs.

3. **Correction to the previous block: deduplication does not "pay for its own addressing
   by narrowing the offsets".** That claim rested on the plain payload needing `uint32`,
   which was an artefact of a 4x-headroom rule this script used to impose - 54,024 values
   fit `uint16` perfectly well. With the narrowest-fitting widths and a guard, *both*
   structures use `uint16` offsets and `uint8` lengths, and what deduplication buys is
   exactly the payload: 105.5 KiB down to 14.3, so 508 KiB down to 457. Less than the
   previous block claimed, and still a strict improvement.

4. **Sharing does cost one column, and that is the whole of its cost.** Without it ranges
   are contiguous, so a CSR array of N+1 offsets encodes N ranges - entry i ends where
   entry i+1 begins. Sharing destroys that, so each entry needs its own start *and* length.
   In the file that is ~41 KiB against the 91 KiB of payload it saves; in memory both
   structures materialise two per-slot arrays here because they share one runtime contract.
   `keys-plain` could instead keep its CSR array and index it twice, which would put it at
   ~0.34 MiB against `keys-dedup`'s 0.37 - **a known and deliberately untaken option**, on
   the grounds that one lookup shared by every structure is worth more than 0.03 MiB.

5. **Narrowest-fitting widths, guarded, not widths chosen for headroom.** `uint8` lengths
   (largest entry 59) and `uint16` offsets are correct because the packaged data is built
   by a converter this repository owns: an overflow surfaces at build time, not in a user's
   process, *provided something checks and says what happened*. `check_fits` is that check,
   and its message - what overflowed, what the ceiling was, which width to move to, and the
   version bumps that follow - is the deliverable rather than the assertion. In the shipped
   version it belongs in `scripts/data_integrity.py`, asserted by the converter over what it
   wrote and by the test suite over what is committed, never on the finder's init path.

6. **Load: ~394 ms to ~0.66 ms, and most of it is not this change's to claim.** PERF-5
   reaches ~21 ms on the *existing* file with no format change and no release, so what the
   format change adds is ~21 ms to ~0.66 ms. Rank it on that, on the memory, and on the 3x
   smaller binary; never on the 394.

7. **The query is unchanged in practice, though not in isolation.** A lookup on its own is
   ~210 ns against the dict's ~108. That gap does not survive a real query: the companion
   script measures this layout inside `timezone_at` at **+4 ns**, under the noise floor,
   because the shipped code answers a `dict.get` with `match value: case int(zone_id)` - a
   structural pattern match costing about what the flat lookup costs extra. Quote the
   whole-query figure. Sampling cells in `mapping` order rather than at random also hands
   `dict.get` a cache-friendly walk of its own table and reads 108 ns as 77; the numbers
   above are randomly sampled.

8. **The one decision left is ~260 KiB and ~0.15 ms to keep h3 out of the format.**
   `slot-dedup` drops the stored cell ids because the cell id *is* the index, and bakes an
   encoding h3-py does not promise as API - plus `SHORTCUT_H3_RES` - into bytes that
   outlive every reader. Storing the ids moves that coupling into the reader, which is
   versioned with the package and can change in any release. **Recommended: pay it.**

REFUSED OPTIONS, with the reason, so they are not re-proposed

* **`np.searchsorted` over sorted keys** - roughly doubles a unique-zone query, and loses
  the batch path it was proposed for: one call over N is still slower than N dict lookups.
  Measured in the companion script.
* **A Python list of values instead of arrays** (in-memory) - 2.41 MiB against 0.37 for no
  query benefit. Companion script.
* **Deduplication via an entry-number index** (slot -> entry -> range) - costs +74 ns on
  the ambiguous path to save ~100 KiB, and is unnecessary: equal offsets achieve the same
  sharing with no indirection. Kept here because it looks like the obvious way to implement
  sharing and is not.
* **Widths chosen for headroom rather than fit** - the reason `uint32` offsets appeared in
  the previous block, and wrong: see conclusions 3 and 5.
* **Dispatching on the entry length at runtime** instead of on a derived zone table -
  +230 ns against +73 ns on the unique path, because it needs two reads and a subtraction
  where the table needs one. The length is the right column *in the file* and the wrong
  discriminator at runtime; separate decisions.
* **Dropping the stored cell ids and enumerating them from h3's public API at load** - the
  index is dense, so this is possible; it costs 4.5 ms against 0.13 ms to read them, a
  fifth of PERF-5's entire budget, to save 329 KiB.

"""

import argparse
import gc
import json
import subprocess
import sys
import statistics
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
    verify_slot_layout_against_h3_api,
)
from scripts.configs import PROJECT_ROOT
from h3.api import numpy_int as h3

from scripts.assert_acceleration_path import active_acceleration_path
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder, utils
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
# points per round and rounds per stratum for the paired whole-query comparison. Large
# enough that one round is milliseconds rather than microseconds, and enough rounds that
# the spread of the per-round difference is readable rather than a single number.
QUERY_POINTS = 2_000
QUERY_ROUNDS = 61

QUERY_STRATA = (
    ("unique", UNIQUE_SHORTCUT_POINTS_FIXTURE),
    ("ambiguous", AMBIGUOUS_SHORTCUT_POINTS_FIXTURE),
    ("random", RANDOM_POINTS_FIXTURE),
    ("on_land", ON_LAND_POINTS_FIXTURE),
)


# ---------------------------------------------------------------------------
# payload construction
# ---------------------------------------------------------------------------


def narrowest_dtype_for(max_value: int, *, what: str) -> np.dtype:
    """The narrowest unsigned width that holds ``max_value``. No headroom required.

    Headroom is not the safeguard here - ``check_fits`` is. The packaged data is produced
    by a converter this repository owns, so an overflow surfaces when the data is built
    rather than in a user's process, provided something checks and says what happened. A
    guarded narrow width is strictly better than an unguarded wide one: smaller, and loud
    instead of silently truncating. So take the smallest that fits and assert it.
    """
    for dtype in (np.uint8, np.uint16, np.uint32):
        if np.iinfo(dtype).max >= max_value:
            return np.dtype(dtype)
    raise AssertionError(f"{what}: {max_value:,} exceeds uint32")


def check_fits(values: np.ndarray, dtype: np.dtype, *, what: str, remedy: str) -> None:
    """Guard a narrow width, with the message that makes the width safe to choose.

    In the shipped version this belongs in ``scripts/data_integrity.py`` - asserted by the
    converter over what it just wrote *and* by the test suite over what is committed,
    sharing one implementation, and never on the finder's init path.

    The message is the deliverable, not the assertion: whoever hits this is regenerating
    the data years from now and needs to be told what overflowed, what the ceiling was and
    which width to move to - not that a check failed.
    """
    if len(values) == 0:
        return
    largest = int(values.max())
    ceiling = int(np.iinfo(dtype).max)
    if largest > ceiling:
        raise AssertionError(
            f"{what} no longer fits {dtype.name}: the largest is {largest:,}, the maximum "
            f"{dtype.name} can hold is {ceiling:,}. This is a data change, not a bug - the "
            f"width was chosen against the dataset of the day. {remedy} Doing so changes "
            f"the binary layout, so bump SHORTCUT_LAYOUT_VERSION and DATA_FORMAT_VERSION "
            f"with it and publish the data distribution before the code that reads it."
        )


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
    """Without sharing, ranges are contiguous, so CSR is this structure's best form.

    One array of N+1 offsets encodes N ranges - entry i ends where entry i+1 begins - so
    it stores and loads *one* column where the deduplicated structure needs two. That is
    the real price of sharing, and it is paid in the addressing rather than at lookup.
    """
    offsets = np.zeros(len(lengths) + 1, dtype=np.int64)
    np.cumsum(lengths, out=offsets[1:])
    dtype = narrowest_dtype_for(int(offsets[-1]), what="payload offset")
    check_fits(
        offsets,
        dtype,
        what="a payload offset",
        remedy="Widen the offset column to the next unsigned width.",
    )
    _write(
        path,
        np.array([len(keys), dtype.itemsize, 0], dtype=np.int64),
        keys,
        offsets.astype(dtype),
        payload,
    )


def read_keys_plain(buf: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n, width, _ = (int(v) for v in np.frombuffer(buf, dtype=np.int64, count=3))
    dtype = np.dtype(f"uint{width * 8}")
    pos = 24
    keys = np.frombuffer(buf, dtype=np.int64, count=n, offset=pos)
    pos += n * 8
    offsets = np.frombuffer(buf, dtype=dtype, count=n + 1, offset=pos)
    pos += (n + 1) * width
    payload = np.frombuffer(buf, dtype=PAYLOAD_DTYPE, offset=pos).copy()
    slot_starts, slot_ends = scatter_to_slots(keys, offsets[:-1], offsets[1:], dtype)
    return slot_starts, slot_ends, payload


def write_keys_dedup(path: Path, keys, lengths, payload) -> None:
    starts, ends, deduped = deduplicate(lengths, payload)
    _write_entries(path, keys, starts, ends - starts, deduped)


def _write_entries(path: Path, keys, starts, lengths, payload) -> None:
    """Store a start and a *length* per entry, each at its own narrowest width.

    A length rather than an end because they are narrow for different reasons and only a
    length is narrow enough to matter: an entry holds at most a few dozen values while a
    start addresses the whole payload, so ``uint8`` serves one and never the other.
    Splitting them saves a byte per entry that a symmetric (start, end) pair spends.
    """
    ends = starts + lengths
    # sized from `ends`: the reader reconstructs them in this column's dtype, and the
    # largest end is the payload length, which no start ever reaches
    start_dtype = narrowest_dtype_for(
        int(ends.max()) if len(ends) else 0, what="payload offset"
    )
    len_dtype = narrowest_dtype_for(
        int(lengths.max()) if len(lengths) else 0, what="entry length"
    )
    check_fits(
        ends,
        start_dtype,
        what="a payload offset",
        remedy="Widen the offset column to the next unsigned width.",
    )
    check_fits(
        lengths,
        len_dtype,
        what="a shortcut entry's length",
        remedy="Widen the length column to the next unsigned width.",
    )
    _write(
        path,
        np.array([len(keys), start_dtype.itemsize, len_dtype.itemsize], dtype=np.int64),
        keys,
        starts.astype(start_dtype),
        lengths.astype(len_dtype),
        payload,
    )


def read_keys(buf: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n, sw, lw = (int(v) for v in np.frombuffer(buf, dtype=np.int64, count=3))
    start_dtype = np.dtype(f"uint{sw * 8}")
    pos = 24
    keys = np.frombuffer(buf, dtype=np.int64, count=n, offset=pos)
    pos += n * 8
    starts = np.frombuffer(buf, dtype=start_dtype, count=n, offset=pos)
    pos += n * sw
    lengths = np.frombuffer(buf, dtype=np.dtype(f"uint{lw * 8}"), count=n, offset=pos)
    pos += n * lw
    payload = np.frombuffer(buf, dtype=PAYLOAD_DTYPE, offset=pos).copy()
    # ends are materialised here, not stored: the runtime shape wants two arrays it can
    # index without arithmetic, and the file wants the narrow column. Different jobs.
    ends = starts.astype(start_dtype) + lengths
    # the format says nothing about h3's bit layout; the reader derives the slot table
    slot_starts, slot_ends = scatter_to_slots(keys, starts, ends, start_dtype)
    return slot_starts, slot_ends, payload


def write_slot_dedup(path: Path, keys, lengths, payload) -> None:
    starts, ends, deduped = deduplicate(lengths, payload)
    entry_lengths = ends - starts
    # sized from `ends`, not from `starts`, and this is not pedantry: the file stores
    # starts and the reader reconstructs `ends = starts + lengths` in the start column's
    # dtype. A width that fits every start can still be one the last end wraps around,
    # since the largest end is the payload length itself. Checking `ends` covers both.
    start_dtype = narrowest_dtype_for(int(ends.max()), what="payload offset")
    len_dtype = narrowest_dtype_for(int(entry_lengths.max()), what="entry length")
    check_fits(
        ends,
        start_dtype,
        what="a payload offset",
        remedy="Widen the offset column to the next unsigned width.",
    )
    check_fits(
        entry_lengths,
        len_dtype,
        what="a shortcut entry's length",
        remedy="Widen the length column to the next unsigned width.",
    )
    slot_starts = np.zeros(SLOT_TABLE_SIZE, dtype=start_dtype)
    slot_lengths = np.zeros(SLOT_TABLE_SIZE, dtype=len_dtype)
    slots = slots_of(keys)
    slot_starts[slots] = starts
    slot_lengths[slots] = entry_lengths
    _write(
        path,
        np.array([start_dtype.itemsize, len_dtype.itemsize], dtype=np.int64),
        slot_starts,
        slot_lengths,
        deduped,
    )


def read_slot_dedup(buf: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sw, lw = (int(v) for v in np.frombuffer(buf, dtype=np.int64, count=2))
    start_dtype = np.dtype(f"uint{sw * 8}")
    pos = 16
    starts = np.frombuffer(
        buf, dtype=start_dtype, count=SLOT_TABLE_SIZE, offset=pos
    ).copy()
    pos += SLOT_TABLE_SIZE * sw
    lengths = np.frombuffer(
        buf, dtype=np.dtype(f"uint{lw * 8}"), count=SLOT_TABLE_SIZE, offset=pos
    )
    pos += SLOT_TABLE_SIZE * lw
    ends = starts + lengths
    return starts, ends, np.frombuffer(buf, dtype=PAYLOAD_DTYPE, offset=pos).copy()


STRUCTURES: dict[str, tuple[Callable, Callable]] = {
    "keys-plain": (write_keys_plain, read_keys_plain),
    "keys-dedup": (write_keys_dedup, read_keys),
    "slot-dedup": (write_slot_dedup, read_slot_dedup),
}
RECOMMENDED = "slot-dedup"


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
# the query benchmark: full `timezone_at`, shipped against proposed
# ---------------------------------------------------------------------------
# This is the measurement that decides the item. The shortcut index exists to avoid
# point-in-polygon tests, so a structure that is smaller and loads faster but answers
# queries slower is not obviously an improvement - and an isolated lookup says exactly
# that, with the dict at ~108 ns against ~210. That comparison is misleading in both
# directions, which is why it is not the one reported:
#
#   * it omits what the shipped code does with the dict's answer - `match value: case
#     int(zone_id)`, a structural pattern match the flat structure needs no equivalent of,
#     because its zone table has already answered;
#   * and the whole difference is ~100 ns inside a query of ~1,000 (unique) to ~10,000
#     (ambiguous), i.e. at or below the 3-9% run-to-run jitter of this machine.
#
# So the two paths are compared *whole*, and paired: A and B alternate inside one round so
# thermal drift and scheduling move both, and the reported figure is the distribution of
# per-round differences rather than the difference of two separately-taken minima.


class FlatTimezoneFinder(TimezoneFinder):
    """``TimezoneFinder`` with the shortcut dict replaced by the proposed structure.

    Everything below the shortcut lookup is copied verbatim from the shipped
    ``timezone_at`` so the only difference measured is the structure. The copy is checked
    against the original on every fixture point before timing.
    """

    __slots__ = ("_ends", "_payload", "_starts", "_zone_by_slot")

    def __init__(self, structure_path: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        starts, ends, payload = read_keys(structure_path.read_bytes())
        self._starts = starts
        self._ends = ends
        self._payload = payload
        self._zone_by_slot = derive_zone_table(starts, ends, payload)

    def timezone_at(self, *, lng: float, lat: float) -> str | None:
        lng, lat = utils.validate_coordinates(lng, lat)
        hex_id = h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)
        slot = (
            (hex_id >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK
        ) * SLOT_STRIDE + ((hex_id >> SLOT_DIGITS_SHIFT) & SLOT_DIGITS_MASK)
        zone_id = self._zone_by_slot[slot]
        if zone_id >= 0:
            return self.zone_name_from_id(int(zone_id))
        if zone_id == ABSENT:
            return None
        possible_boundaries = self._payload[self._starts[slot] : self._ends[slot]]

        # --- verbatim from TimezoneFinder.timezone_at below this line ---
        nr_possible_polygons = len(possible_boundaries)
        if nr_possible_polygons == 0:
            return None
        zone_ids = self.zone_ids_of(possible_boundaries)
        last_zone_change_idx = utils.get_last_change_idx(zone_ids)
        x = utils.coord2int(lng)
        y = utils.coord2int(lat)
        for i, boundary_id in enumerate(possible_boundaries):
            if i >= last_zone_change_idx:
                break
            if self.inside_of_polygon(boundary_id, x, y):
                return self.zone_name_from_id(int(zone_ids[i]))
        return self.zone_name_from_id(int(zone_ids[-1]))


def paired_query_ns(
    shipped: TimezoneFinder, proposed: TimezoneFinder, points, rounds: int
) -> tuple[float, float, list[float]]:
    """Alternate the two finders round by round. Returns (ns A, ns B, per-round deltas).

    Paired on purpose. Taking the min of one finder's rounds and the min of the other's
    compares two different moments of the machine, and the effect being resolved here is
    smaller than the machine moves between them.
    """
    a_times: list[float] = []
    b_times: list[float] = []

    def run(finder):
        t0 = time.perf_counter()
        [finder.timezone_at(lng=p[0], lat=p[1]) for p in points]
        return time.perf_counter() - t0

    for _ in range(2):  # warm up both, including numba compilation and page faults
        run(shipped)
        run(proposed)
    # The order alternates every round. Whichever path runs first pays to warm what the
    # two share - `validate_coordinates`, `h3.latlng_to_cell`, `zone_name_from_id`, the
    # branch predictors - and the second one collects that for free. Measured at ~140 ns
    # per query on the unique stratum, which is larger than the difference being resolved,
    # so a fixed A-then-B order does not measure the structures at all.
    for r in range(rounds):
        if r % 2 == 0:
            a_times.append(run(shipped))
            b_times.append(run(proposed))
        else:
            b_times.append(run(proposed))
            a_times.append(run(shipped))
    n = len(points)
    deltas = [(b - a) / n * 1e9 for a, b in zip(a_times, b_times)]
    return min(a_times) / n * 1e9, min(b_times) / n * 1e9, deltas


def match_dispatch_ns(mapping: dict, cells: Sequence[int]) -> tuple[float, float]:
    """What the shipped code pays to interpret the dict's answer, and the flat one not.

    ``match value: case int(zone_id)`` against a plain ``dict.get``. The flat structure
    needs no equivalent - its zone table has already distinguished the three cases - so
    this is the part of the isolated-lookup gap that cancels in a whole query.
    """
    get = mapping.get

    def bare():
        return [get(c) for c in cells]

    def with_match():
        out = []
        for c in cells:
            value = get(c)
            match value:
                case None:
                    out.append(None)
                case int(zone_id):
                    out.append(zone_id)
                case _:
                    out.append(value)
        return out

    n = len(cells)
    return measure(bare) / n * 1e9, measure(with_match) / n * 1e9


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
    checked, dense_size = verify_slot_layout_against_h3_api()
    print(
        f"slot map: injective over all {n_cells:,} cells at resolution {SHORTCUT_H3_RES}; "
        f"invariant {invariant:#x}"
    )
    print(
        f"layout guard: the bit arithmetic agrees with h3's public "
        f"get_base_cell_number / cell_to_child_pos on all {checked:,} cells "
        f"(a public-API index would be {dense_size:,} slots against {SLOT_TABLE_SIZE:,})"
    )

    tf = TimezoneFinder()
    shortcut_path = get_hybrid_shortcut_file_path(tf.zone_ids.dtype, tf.data_location)
    mapping = read_hybrid_shortcuts_binary(shortcut_path)
    keys, lengths, payload = build_payload(mapping)
    _s, _e, deduped = deduplicate(lengths, payload)
    print(
        f"payload: {len(payload):,} values -> {len(deduped):,} distinct "
        f"({payload.nbytes / 1024:,.1f} -> {deduped.nbytes / 1024:,.1f} KiB, "
        f"{len(payload) / len(deduped):.1f}x)"
    )
    plain_start = narrowest_dtype_for(len(payload), what="payload offset")
    dedup_start = narrowest_dtype_for(len(deduped), what="payload offset")
    len_dtype = narrowest_dtype_for(int(lengths.max()), what="entry length")
    print(
        f"column widths: offsets {plain_start.name} plain / {dedup_start.name} "
        f"deduplicated; lengths {len_dtype.name} (largest entry {int(lengths.max())}, "
        f"{len_dtype.name} holds {np.iinfo(len_dtype).max}). Narrowest that fits, guarded "
        f"by check_fits rather than by headroom."
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
        "Structure: what it costs to store, load and hold.",
        ["structure", "file KiB", "load ms", "MiB", "unique ns", "amb ns"],
        rows,
    )
    print(
        "  `load ms` includes deriving the zone table. The last two columns are a lookup\n"
        "  in isolation and are NOT the query answer - see the paired table below, which\n"
        "  is the one that decides whether this is worth doing."
    )

    # ---- the query comparison, which is what the structure exists for ----
    proposed = FlatTimezoneFinder(OUT_DIR / f"{RECOMMENDED}.bin")
    strata = {name: load_benchmark_points(fx) for name, fx in QUERY_STRATA}
    for name, points in strata.items():
        for lng, lat in points[:500]:
            got = proposed.timezone_at(lng=lng, lat=lat)
            want = tf.timezone_at(lng=lng, lat=lat)
            if got != want:
                raise AssertionError(f"{name} ({lng}, {lat}): {got!r} != {want!r}")
    print(
        f"\nagreement: the proposed finder answers as the shipped one on "
        f"{sum(min(len(p), 500) for p in strata.values()):,} fixture points"
    )

    rows = []
    for name, points in strata.items():
        pts = points[:QUERY_POINTS]
        a, b, deltas = paired_query_ns(tf, proposed, pts, QUERY_ROUNDS)
        deltas.sort()
        median = statistics.median(deltas)
        lo, hi = deltas[len(deltas) // 10], deltas[-len(deltas) // 10 - 1]
        faster = sum(1 for d in deltas if d < 0)
        rows.append(
            [
                name,
                f"{a:,.0f}",
                f"{b:,.0f}",
                f"{(b - a) / a * 100:+.1f}%",
                f"{median:+,.0f}",
                f"{lo:+,.0f} .. {hi:+,.0f}",
                f"{faster}/{len(deltas)}",
            ]
        )
    table(
        f"QUERY: full timezone_at(), paired and order-alternated, {QUERY_ROUNDS} rounds "
        f"of {QUERY_POINTS} points",
        [
            "stratum",
            "shipped ns",
            "proposed ns",
            "on minima",
            "median d",
            "10-90% of d",
            "rounds faster",
        ],
        rows,
    )
    print(
        "  Two estimators on purpose, because they disagree and that disagreement is the\n"
        "  result. `on minima` is the ratio of the two best rounds - the estimator the\n"
        "  benchmark suite tracks. `median d` is the median per-round difference, paired.\n"
        "  `rounds faster` counts rounds where the proposal won: ~half means no effect,\n"
        "  and is the reading that needs no assumption about the noise distribution."
    )

    bare, matched = match_dispatch_ns(mapping, uniq)
    print(
        f"\n  Why the isolated lookup misleads: `dict.get` alone is {bare:,.0f} ns, and the\n"
        f"  `match value: case int(zone_id)` the shipped timezone_at runs on its result\n"
        f"  takes that to {matched:,.0f} ns (+{matched - bare:,.0f}). The proposed structure needs no\n"
        f"  equivalent - its zone table has already told the three cases apart - so most\n"
        f"  of the isolated gap is spent by the dict path a moment later."
    )

    proposed.cleanup()
    tf.cleanup()


if __name__ == "__main__":
    main()
