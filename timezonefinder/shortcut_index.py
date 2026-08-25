"""The H3 shortcut index: reader, writer and the slot arithmetic both share.

The shortcut index answers "which timezone polygons can possibly cover this point" for
every H3 cell at :data:`~timezonefinder.configs.SHORTCUT_H3_RES`. Most cells are covered
by a single zone and need no answer beyond its id; the rest carry a list of candidate
boundary polygons for the point-in-polygon loop to work through.

``docs/data_format.rst`` is the authoritative description of the binary layout. What
belongs here is why it is shaped that way:

* **The cell id is the index.** H3 packs a cell as a base cell (bits 45-51) followed by
  fifteen 3-bit digits; at a fixed resolution everything else in the index is constant,
  so those bits *are* the cell and :func:`slot_of` is a bijection onto a dense table
  rather than a hash. No keys are stored and no search runs at lookup time.
* **The table holds the answer, not a pointer to it.** One ``int16`` per slot: a zone id
  for a cell a single zone covers, ``ABSENT`` for a cell with no coverage, and otherwise
  the index of a candidate list. Three quarters of the cells are answered by that one
  read, and their offsets and payload entries therefore need not exist at all.
* **Only the candidate lists are stored, each distinct one once.** Duplicates carry
  *equal* offsets into the shared payload rather than an index to a shared entry, so a
  repeated list costs a lookup exactly what a unique one costs.
* **The file is stored base-7, the table is used base-8.** H3 digits only take 0-6, so a
  third of the base-8 slots can never be addressed. Which ones follow from the resolution
  and never from the data, so the file omits them and :func:`expand_compact` drops the
  compact block into the corner of the padded table - a slice assignment, an order of
  magnitude cheaper than scattering through an index array. The *table* keeps its padding:
  addressing it base-7 per query costs more than the padding is worth.

The four arrays live in **one** file rather than one file each, and in a raw layout rather than
``.npy``: they are a single structure with cross-references, four files load ~1.6x slower and four
``.npy`` files ~3x, and a ``.npy`` carries neither of the two markers that let a stale data
directory be rejected. ``potential-improvements.md`` records the measurement.

Everything the layout assumes is checked where the data is produced -
``scripts/data_integrity.validate_shortcut_index`` - and never when a finder is built. In
particular the bit arithmetic above is confirmed against h3's public
``get_base_cell_number`` / ``cell_to_child_pos`` over every cell that exists, which turns
an encoding h3-py does not promise as API into an invariant that fails loudly at build
time instead of silently returning a neighbour's timezone.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Final

import numpy as np

from timezonefinder.configs import DEFAULT_DATA_DIR, SHORTCUT_H3_RES
from timezonefinder.layout import incompatible_layout_error


class ShortcutOverflowError(ValueError):
    """A shortcut index column can no longer hold what the dataset puts in it.

    Raised where the data is built, never where it is read: the columns are sized to fit
    the dataset of the day, so growing past one of them is a data change to act on rather
    than a condition a user's process can encounter.
    """


# What a shortcut index file means. Bump it when what the file holds changes, and bump
# DATA_FORMAT_VERSION with it (tests/test_data_version.py pins the pairing). Deliberately
# not tied to the package version, for the same reason as POLYGON_LAYOUT_VERSION: a
# `bin_file_location` directory compiled once stays readable across ordinary releases.
SHORTCUT_LAYOUT_VERSION: Final[int] = 2

#: Stamped into the file so a truncated, foreign or pre-guard file is rejected rather
#: than read as coordinates that happen to parse.
FILE_IDENTIFIER: Final[bytes] = b"TZSC"

SHORTCUT_FILE_NAME: Final[str] = "shortcuts.bin"

# H3's index encoding, at the one resolution this index is built for.
SLOT_BASE_CELL_SHIFT: Final[int] = 45
SLOT_BASE_CELL_MASK: Final[int] = 0x7F
SLOT_DIGIT_BITS: Final[int] = 3
SLOT_DIGITS_SHIFT: Final[int] = SLOT_BASE_CELL_SHIFT - SLOT_DIGIT_BITS * SHORTCUT_H3_RES
SLOT_DIGITS_MASK: Final[int] = (1 << (SLOT_DIGIT_BITS * SHORTCUT_H3_RES)) - 1
SLOT_STRIDE: Final[int] = SLOT_DIGITS_MASK + 1
NUM_BASE_CELLS: Final[int] = 122

# The slot is one contiguous bit field, which is why the lookup is a shift and a mask
# rather than the two shifts, two masks, multiply and add it reads as. H3 puts the base
# cell immediately above the digits, so
#
#     base * SLOT_STRIDE + digits  ==  (base << digit_bits) | digits
#
# and those bits are already adjacent in the cell id: the whole slot is the field from
# SLOT_DIGITS_SHIFT upwards, seven bits of base cell on top of the digits. That is an
# identity over any 64-bit value, not a property of the cells that exist, and it is worth
# ~5 % of a unique-zone query. `test_the_slot_is_one_contiguous_bit_field` pins it.
SLOT_MASK: Final[int] = (1 << (SLOT_DIGIT_BITS * SHORTCUT_H3_RES + 7)) - 1
#: Slots in the table the lookup indexes. ``122 * 8**res``.
SLOT_TABLE_SIZE: Final[int] = NUM_BASE_CELLS * SLOT_STRIDE

#: H3 digits take 0-6, so the file stores ``122 * 7**res`` slots and the reader pads.
COMPACT_DIGIT_BASE: Final[int] = 7
COMPACT_STRIDE: Final[int] = COMPACT_DIGIT_BASE**SHORTCUT_H3_RES
COMPACT_TABLE_SIZE: Final[int] = NUM_BASE_CELLS * COMPACT_STRIDE

#: Table value for a cell no polygon covers. Custom data can leave cells uncovered, so
#: this is a real state and not only padding. ``-1`` is available for it because a stored
#: candidate list can never have length 1 - a single candidate is unambiguous and is
#: therefore stored as a zone id - so the entry indices start at 0 and map to ``-2``.
ABSENT: Final[int] = -1

#: The table's dtype. Zone ids and entry indices share it; both are guarded at build time.
TABLE_DTYPE: Final[np.dtype] = np.dtype(np.int16)

#: Boundary polygon ids, as stored in the payload.
PAYLOAD_DTYPE: Final[np.dtype] = np.dtype(np.uint16)

# Everything outside the slot bits of a cell id at this resolution: mode 1, the
# resolution field, and the unused digits, which H3 sets to 7. Reconstructing a cell id
# from a slot is what lets the index be iterated (reporting, tests) without storing keys.
SLOT_INVARIANT: Final[int] = (
    (1 << 59)
    | (SHORTCUT_H3_RES << 52)
    | ((1 << (SLOT_DIGIT_BITS * (15 - SHORTCUT_H3_RES))) - 1)
)

# header: identifier, layout version, then the four int64 the reader needs to make sense of
# the arrays. Sized so that the int16 table starts 8-byte aligned.
#
# The H3 resolution is one of them because nothing else in the file records it, and it
# changes what every slot *means* without changing anything a reader would notice: a
# resolution 3 file read by resolution 4 code indexes a table of the wrong size with the
# wrong bits and answers with a different cell's timezone. The layout version does not
# cover it - the layout is identical at every resolution.
_HEADER_SIZE: Final[int] = 40


def slot_of(hex_id: int) -> int:
    """Table index of one H3 cell id, by arithmetic alone - no memory touched."""
    return (hex_id >> SLOT_DIGITS_SHIFT) & SLOT_MASK


def slots_of(hex_ids: np.ndarray) -> np.ndarray:
    """Table indices of an array of H3 cell ids."""
    return (hex_ids >> SLOT_DIGITS_SHIFT) & SLOT_MASK


def compact_slots_of(hex_ids: np.ndarray) -> np.ndarray:
    """File indices of an array of H3 cell ids: the same order, without the holes."""
    digits = np.zeros_like(hex_ids)
    for digit in range(SHORTCUT_H3_RES):
        shift = SLOT_BASE_CELL_SHIFT - SLOT_DIGIT_BITS * (digit + 1)
        digits = digits * COMPACT_DIGIT_BASE + ((hex_ids >> shift) & 7)
    base = (hex_ids >> SLOT_BASE_CELL_SHIFT) & SLOT_BASE_CELL_MASK
    return base * COMPACT_STRIDE + digits


def cell_of_slot(slot: int) -> int:
    """The H3 cell id a table slot addresses - the inverse of :func:`slot_of`."""
    base, digits = divmod(slot, SLOT_STRIDE)
    return (
        SLOT_INVARIANT | (base << SLOT_BASE_CELL_SHIFT) | (digits << SLOT_DIGITS_SHIFT)
    )


def expand_compact(compact: np.ndarray, fill: int) -> np.ndarray:
    """Compact base-7 file table -> the base-8 table the lookup indexes.

    A base-8 slot is exactly the C-order ravel of a ``(122,) + (8,) * res`` array, so the
    base-7 block lands correctly when dropped into its corner. That slice assignment is
    an order of magnitude cheaper than scattering through a computed index array, and it
    is the whole of what loading the table costs.

    ``fill`` is what the unreachable slots get. No valid cell addresses them, so it cannot
    change an answer - but it must still be the value that *means* "nothing here", or a
    table whose padding reads as zone id 0 is one nobody can assert over.
    """
    shape = (NUM_BASE_CELLS,) + (8,) * SHORTCUT_H3_RES
    block = (slice(None),) + (slice(0, COMPACT_DIGIT_BASE),) * SHORTCUT_H3_RES
    out = np.full(shape, fill, dtype=compact.dtype)
    out[block] = compact.reshape(
        (NUM_BASE_CELLS,) + (COMPACT_DIGIT_BASE,) * SHORTCUT_H3_RES
    )
    return out.reshape(-1)


def compact_of_expanded(table: np.ndarray) -> np.ndarray:
    """The inverse of :func:`expand_compact` - what the file holds, from the table."""
    shape = (NUM_BASE_CELLS,) + (8,) * SHORTCUT_H3_RES
    block = (slice(None),) + (slice(0, COMPACT_DIGIT_BASE),) * SHORTCUT_H3_RES
    return table.reshape(shape)[block].reshape(-1)


class ShortcutIndex:
    """The loaded index, and the only thing that knows how a cell's answer is stored.

    Callers ask it three questions and never touch its arrays. What a cell resolves to is
    a tri-state, and :meth:`entry_of` returns it as one integer so that the common case
    costs one comparison rather than an allocation:

    ============================ ===========================================
    ``entry >= 0``               the timezone id, and the whole answer
    ``entry == ABSENT``          no timezone covers this cell
    ``entry < ABSENT``           several zones; ask :meth:`candidates_of`
    ============================ ===========================================

    That tri-state is the lookup's own vocabulary - a cell is covered by one zone, by
    none, or by several - so branching on it is domain logic. **How** it is encoded (the
    slot arithmetic, the ``-(entry + 2)`` entry index, the CSR bounds) stops here, which
    is what lets the storage change without touching ``timezonefinder.py``.

    The arrays stay public because the build-time checks in ``scripts/data_integrity.py``
    and the format tests legitimately inspect them; the query path does not.
    """

    __slots__ = ("table", "starts", "ends", "last_change", "payload")

    def __init__(
        self,
        table: np.ndarray,
        starts: np.ndarray,
        ends: np.ndarray,
        last_change: np.ndarray,
        payload: np.ndarray,
    ) -> None:
        #: ``int16`` per slot: ``>= 0`` zone id, ``ABSENT`` uncovered, else ``-(entry + 2)``
        self.table = table
        #: start of each distinct candidate list in ``payload``
        self.starts = starts
        #: end of each distinct candidate list; a view of the same CSR array as ``starts``
        self.ends = ends
        #: per distinct list, the index past which no other zone can be matched
        self.last_change = last_change
        #: every distinct candidate list, back to back
        self.payload = payload

    # --- the query contract -------------------------------------------------------

    def entry_of(self, hex_id: int) -> int:
        """What the cell resolves to, as the tri-state integer documented above.

        The slot arithmetic is inlined rather than delegated to :func:`slot_of`: this runs
        on every query, and a call here would cost more than the arithmetic it wraps.
        """
        return int(self.table[(hex_id >> SLOT_DIGITS_SHIFT) & SLOT_MASK])

    def entries_of(self, hex_ids: np.ndarray) -> np.ndarray:
        """What each of many cells resolves to, as the same tri-state integers.

        The batch sibling of :meth:`entry_of`, and it lives here for the same reason
        that one does: the slot arithmetic and the table are this class's business, so
        a caller that indexed ``table`` itself would pin the layout from outside. Two
        numpy calls for the whole batch, whatever its size.
        """
        return self.table[slots_of(hex_ids)]

    def candidates_of(self, entry: int) -> np.ndarray:
        """The boundary polygon ids to test, for an ``entry`` below ``ABSENT``."""
        i = -(entry + 2)
        return self.payload[self.starts[i] : self.ends[i]]

    def stop_index_of(self, entry: int) -> int:
        """Index into :meth:`candidates_of` past which no other zone can be matched.

        Precomputed when the index is built, so a query reads it rather than scanning for
        it. ``get_last_change_idx`` is the definition, and ``scripts/data_integrity.py``
        holds the stored values to it.

        Cast to ``int`` here, like :meth:`entry_of`: the column is a narrow unsigned dtype,
        and the candidate loop compares this against a Python ``int`` once per candidate.
        One cast per query is cheaper than a numpy scalar comparison per iteration.
        """
        return int(self.last_change[-(entry + 2)])

    # --- build and reporting ------------------------------------------------------

    @property
    def nr_of_entries(self) -> int:
        """How many *distinct* candidate lists the index stores."""
        return len(self.last_change)

    def polygons_of_entry(self, entry_idx: int) -> np.ndarray:
        """The candidate polygon ids of one distinct entry, by its own index.

        Addressed by entry index rather than by the table's encoding of it, which is what
        separates it from :meth:`candidates_of`: the build side iterates entries, the
        query side follows a table value.
        """
        return self.payload[self.starts[entry_idx] : self.ends[entry_idx]]

    def value_of(self, hex_id: int) -> int | np.ndarray | None:
        """What one cell resolves to: a zone id, a candidate list, or ``None``.

        Reporting and test-side convenience, not the query path - the callers that care
        about speed dispatch on the raw table value instead of building this union.
        """
        zone_id = int(self.table[slot_of(hex_id)])
        if zone_id >= 0:
            return zone_id
        if zone_id == ABSENT:
            return None
        return self.polygons_of_entry(-(zone_id + 2))

    def items(self) -> Iterator[tuple[int, int | np.ndarray]]:
        """Every covered cell, in slot order, as ``(cell id, zone id | polygon ids)``.

        Slot order is ascending cell id: the base cell occupies the high bits of both.
        """
        for slot in np.flatnonzero(self.table != ABSENT):
            zone_id = int(self.table[slot])
            value = zone_id if zone_id >= 0 else self.polygons_of_entry(-(zone_id + 2))
            yield cell_of_slot(int(slot)), value

    def as_mapping(self) -> dict[int, int | np.ndarray]:
        """Materialise the index as the cell -> value dict reports and tests work over."""
        return dict(self.items())


def get_shortcut_file_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """Path of the shortcut index binary inside a compiled data directory."""
    return output_path / SHORTCUT_FILE_NAME


def read_shortcuts_binary(file_path: Path) -> ShortcutIndex:
    """Read a shortcut index file.

    Nothing is derived here beyond padding the table: the file holds what the lookup
    indexes, which is why loading it is a fraction of a millisecond.

    :raises ValueError: if the file carries no known identifier or an unreadable layout
        version.
    """
    with open(file_path, "rb") as f:
        buf = f.read()

    if buf[:4] != FILE_IDENTIFIER:
        # Written before this format existed, when the index was a FlatBuffers file under
        # a different name. Reported as layout version 0 rather than as a corrupt file,
        # since that is what it is for everyone who will ever hit this.
        raise incompatible_layout_error(
            "shortcut index file", 0, SHORTCUT_LAYOUT_VERSION, file_path
        )
    layout_version = int(np.frombuffer(buf, dtype=np.uint32, count=1, offset=4)[0])
    if layout_version != SHORTCUT_LAYOUT_VERSION:
        raise incompatible_layout_error(
            "shortcut index file", layout_version, SHORTCUT_LAYOUT_VERSION, file_path
        )

    resolution, nr_entries, offset_width, length_width = (
        int(v) for v in np.frombuffer(buf, dtype=np.int64, count=4, offset=8)
    )
    if resolution != SHORTCUT_H3_RES:
        raise ValueError(
            f"the shortcut index {file_path} is built for H3 resolution {resolution}, but "
            f"this timezonefinder reads resolution {SHORTCUT_H3_RES}. Every slot in it "
            f"means a different cell, so reading it would return a neighbour's timezone "
            f"rather than an error. Regenerate this data directory with "
            f"scripts/file_converter.py from the current checkout."
        )
    pos = _HEADER_SIZE
    # `.copy()`, never `np.ascontiguousarray`: the latter hands back an already-contiguous
    # view unchanged, and a surviving view keeps the whole file buffer alive.
    table = expand_compact(
        np.frombuffer(buf, dtype=TABLE_DTYPE, count=COMPACT_TABLE_SIZE, offset=pos),
        fill=ABSENT,
    )
    pos += COMPACT_TABLE_SIZE * TABLE_DTYPE.itemsize
    # One CSR array read as two views: entry i spans bounds[i]:bounds[i+1]. The distinct
    # entries are packed back to back, so no length column exists to disagree with it.
    bounds = np.frombuffer(
        buf, dtype=np.dtype(f"uint{offset_width * 8}"), count=nr_entries + 1, offset=pos
    ).copy()
    pos += (nr_entries + 1) * offset_width
    # before `last_change`, so that the payload's offset stays a multiple of its width
    payload = np.frombuffer(
        buf, dtype=PAYLOAD_DTYPE, count=int(bounds[-1]), offset=pos
    ).copy()
    pos += int(bounds[-1]) * PAYLOAD_DTYPE.itemsize
    last_change = np.frombuffer(
        buf, dtype=np.dtype(f"uint{length_width * 8}"), count=nr_entries, offset=pos
    ).copy()
    # read-only, because cells with identical candidate lists share one range of it:
    # writing through one cell's slice would change another cell's answer
    payload.flags.writeable = False
    return ShortcutIndex(table, bounds[:-1], bounds[1:], last_change, payload)


def narrowest_dtype_for(max_value: int, *, what: str) -> np.dtype:
    """The narrowest unsigned width that holds ``max_value``. No headroom required.

    Headroom is not the safeguard here - being handed the column's *maximum* is. Callers
    pass ``values.max()``, so the width fits by construction and there is nothing left for
    a follow-up guard to catch; what a narrow width still needs is a check that the file
    it produced holds together, which ``scripts/data_integrity.validate_shortcut_index``
    does over what is committed. A guarded narrow width is strictly better than an
    unguarded wide one: smaller, and loud instead of silently truncating.
    """
    for dtype in (np.uint8, np.uint16, np.uint32):
        if np.iinfo(dtype).max >= max_value:
            return np.dtype(dtype)
    raise ShortcutOverflowError(f"{what}: {max_value:,} exceeds uint32")


def check_fits(values: np.ndarray, dtype: np.dtype, *, what: str, remedy: str) -> None:
    """Guard a narrow column, with the message that makes choosing it by fit safe.

    For the columns whose width is *fixed* by the format rather than chosen by fit -
    which is the slot table, and only it. The two data-dependent columns need no such
    guard: their width is derived from the maximum they have to hold, so it fits by
    construction. Called by the builder, never when a finder is constructed.

    The message is the deliverable, not the assertion: whoever hits this is regenerating
    the data years from now and needs to be told what overflowed, what the ceiling was and
    which width to move to, not that a check failed.
    """
    if len(values) == 0:
        return
    largest = int(np.max(values))
    ceiling = int(np.iinfo(dtype).max)
    if largest > ceiling:
        raise ShortcutOverflowError(
            f"{what} no longer fits {dtype.name}: the largest is {largest:,}, the maximum "
            f"{dtype.name} can hold is {ceiling:,}. This is a data change, not a bug - the "
            f"width was chosen against the dataset of the day. {remedy} Doing so changes "
            f"the binary layout, so bump SHORTCUT_LAYOUT_VERSION and DATA_FORMAT_VERSION "
            f"with it and publish the data distribution before the code that reads it."
        )


def get_last_change_idx(zone_ids: np.ndarray) -> int:
    """Index past which no zone other than the last one can still be matched.

    A candidate list is ordered so that a zone's polygons are contiguous and the largest
    zone comes last, so once the scan reaches the final run there is nothing left to rule
    out and the answer is that zone whether or not its polygons are tested.

    **Build-time only.** The query used to call this per lookup; it now reads the answer
    out of the shortcut index, which stores one value per *distinct* candidate list. It
    lives here beside the builder that writes those values rather than in
    ``timezonefinder/utils_numba.py``, where it was compiled at import for a function no
    query calls - and ``scripts/data_integrity.py`` re-checks the committed values against
    this same implementation, so the two cannot drift.
    """
    nr_entries = zone_ids.shape[0]
    if nr_entries <= 1:
        return 0
    last = zone_ids[-1]
    for ptr in range(2, nr_entries + 1):
        # from the back: the first element that differs ends the final run
        if zone_ids[-ptr] != last:
            return nr_entries - ptr + 1
    return 0


def build_shortcut_index(
    mapping: dict[int, int | list[int] | np.ndarray],
    poly_zone_ids: np.ndarray,
) -> ShortcutIndex:
    """Build the index from the compiled cell -> zone id | polygon ids mapping.

    :param mapping: what ``scripts/shortcuts.py`` compiles: a cell covered by a single
        zone maps to that zone id, any other covered cell to its candidate polygon ids.
    :param poly_zone_ids: zone id per boundary polygon, needed to precompute
        ``last_change``.
    :raises ShortcutOverflowError: if a value no longer fits the column that holds it.
    """
    keys = np.sort(np.fromiter(mapping.keys(), dtype=np.int64, count=len(mapping)))
    compact_slots = compact_slots_of(keys)
    table = np.full(COMPACT_TABLE_SIZE, ABSENT, dtype=TABLE_DTYPE)

    unique_slots: list[int] = []
    unique_zone_ids: list[int] = []
    list_slots: list[int] = []
    # distinct candidate lists, in first-seen (= slot) order
    entry_of: dict[bytes, int] = {}
    entry_index: list[int] = []
    entry_payloads: list[np.ndarray] = []

    for key, compact_slot in zip(keys, compact_slots):
        hex_id = int(key)
        value = mapping[hex_id]
        if isinstance(value, (int, np.integer)):
            unique_slots.append(int(compact_slot))
            unique_zone_ids.append(int(value))
            continue
        poly_ids = np.asarray(value, dtype=PAYLOAD_DTYPE)
        if len(poly_ids) == 0:
            # A cell no polygon covers. Recorded as absent rather than as an empty entry:
            # every caller answers `None` for both, and storing nothing needs no index.
            continue
        if len(poly_ids) == 1:
            raise ValueError(
                f"cell {hex_id:#x} stores a single candidate polygon. A single candidate "
                "is unambiguous and has to be stored as a zone id - "
                "scripts.shortcuts.compute_unique_shortcut_mapping is what guarantees "
                "that - and the index needs the one-candidate case to stay impossible, "
                "since that is what leaves a spare table value to mean 'no cell here'."
            )
        list_slots.append(int(compact_slot))
        key_bytes = poly_ids.tobytes()
        found = entry_of.get(key_bytes)
        if found is None:
            found = len(entry_payloads)
            entry_of[key_bytes] = found
            entry_payloads.append(poly_ids)
        entry_index.append(found)

    zone_id_column = np.asarray(unique_zone_ids, dtype=np.int64)
    check_fits(
        zone_id_column,
        TABLE_DTYPE,
        what="a unique cell's zone id",
        remedy="Widen the slot table to int32.",
    )
    markers = -(np.asarray(entry_index, dtype=np.int64) + 2)
    check_fits(
        -markers,
        TABLE_DTYPE,
        what="a distinct entry index",
        remedy="Widen the slot table to int32.",
    )
    if unique_slots:
        table[unique_slots] = zone_id_column.astype(TABLE_DTYPE)
    if list_slots:
        table[list_slots] = markers.astype(TABLE_DTYPE)

    payload = (
        np.concatenate(entry_payloads)
        if entry_payloads
        else np.empty(0, dtype=PAYLOAD_DTYPE)
    )
    lengths = np.array([len(chunk) for chunk in entry_payloads], dtype=np.int64)
    bounds = np.concatenate([np.zeros(1, dtype=np.int64), np.cumsum(lengths)])
    last_change = np.array(
        [
            get_last_change_idx(poly_zone_ids[chunk.astype(np.int64)])
            for chunk in entry_payloads
        ],
        dtype=np.int64,
    )
    return ShortcutIndex(
        expand_compact(table, fill=ABSENT),
        bounds[:-1],
        bounds[1:],
        last_change,
        payload,
    )


def write_shortcuts_binary(index: ShortcutIndex, output_file: Path) -> None:
    """Write a built index to its binary file, in the narrowest columns that fit.

    The two data-dependent widths are recorded in the header rather than fixed by the
    format, which is what lets them be chosen by fit rather than by headroom: each is the
    narrowest that holds its column's maximum, and ``scripts/data_integrity.py`` asserts
    over the committed file that it still is.

    **One file, and a raw layout rather than four ``.npy`` arrays.** The obvious
    alternative is one file per array, self-described by the ``.npy`` header the way
    ``zone_ids.npy`` and its neighbours next to it are. Measured over the packaged data,
    loading the identical structure: **one raw file 0.081 ms, four raw files 0.129 ms
    (+59 %), four ``.npy`` files 0.241 ms (+197 %)**, at the same total size to within
    0.5 % - and the ``.npy`` cost is the format itself rather than ``np.load``'s
    dispatch, since the low-level ``np.lib.format.read_array`` reads 0.236 ms of that.
    Load time is the axis this format exists for, so that settles it on its own; two
    things make the self-description not worth buying back either:

    * **a ``.npy`` carries no file identifier and no layout version.** Splitting into
      them would move the shortcut index out of the guarded set and into the one
      ``docs/data_format.rst`` records as still undetectable across a format change,
      losing what makes a stale ``bin_file_location`` directory fail loudly instead of
      answering with wrong timezones.
    * these four arrays are **one structure with cross-references** - the table indexes
      the bounds, the bounds index the payload - so four files can be individually stale
      or mismatched where one cannot, and the separability buys nothing that reads them.

    What a ``.npy`` would genuinely add is the dtype of each array, and the header's two
    width fields already carry that in 16 bytes. None of this argues against ``.npy`` for
    the rest of the data directory: those are single independent vectors with no
    cross-references and no per-query load budget.
    """
    bounds = np.concatenate([index.starts, index.ends[-1:]]).astype(np.int64)
    if len(bounds) == 0:
        bounds = np.zeros(1, dtype=np.int64)
    # Sized from the whole column, not from its last entry. For an index this module
    # builds the last end *is* the maximum - the entries are packed back to back - but
    # sizing from `max` holds for any index handed to this function and leaves no
    # assumption behind for a later guard to re-check. A guard that cannot fail is not
    # one, and one placed after `narrowest_dtype_for` never can.
    offset_dtype = narrowest_dtype_for(int(bounds.max()), what="payload offset")
    length_dtype = narrowest_dtype_for(
        int(index.last_change.max()) if index.nr_of_entries else 0,
        what="a last-zone-change index",
    )
    header = (
        FILE_IDENTIFIER
        + np.array([SHORTCUT_LAYOUT_VERSION], dtype=np.uint32).tobytes()
        + np.array(
            [
                SHORTCUT_H3_RES,
                index.nr_of_entries,
                offset_dtype.itemsize,
                length_dtype.itemsize,
            ],
            dtype=np.int64,
        ).tobytes()
    )
    assert len(header) == _HEADER_SIZE
    with open(output_file, "wb") as f:
        f.write(header)
        f.write(compact_of_expanded(index.table).astype(TABLE_DTYPE).tobytes())
        f.write(bounds.astype(offset_dtype).tobytes())
        f.write(index.payload.astype(PAYLOAD_DTYPE).tobytes())
        f.write(index.last_change.astype(length_dtype).tobytes())
