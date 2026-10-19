"""The grid-tree shortcut index: reader, writer and the cell arithmetic both share.

The shortcut index answers "which timezone polygons can possibly cover this point" for
every cell of a longitude/latitude-aligned grid tree. Most cells are covered by a single
zone and need no answer beyond its id; the rest carry a list of candidate boundary
polygons for the point-in-polygon loop to work through.

``docs/data_format.rst`` is the authoritative description of the binary layout. What
belongs here is why it is shaped that way:

* **A dense aligned grid, refined where borders are.** Level 0 is one ``int16`` per
  square root cell of :data:`ROOT_WIDTH` units. A root cell several zones can own holds
  the index of a block of :data:`BLOCK_SIDE` x :data:`BLOCK_SIDE` children instead, and
  the child is where its candidate list lives. A flat grid of the finest cells would
  spend two bytes on every cell of the open ocean; the tree spends them where zones
  meet, which is how it reaches 0.1875 degree cells in well under a megabyte.
  ``docs/data_report.rst`` carries what the shipped index weighs.
* **The cell is arithmetic, not a search.** Each level is a whole number of coordinate
  units wide, so a level's cell is one floor division per axis of the truncated integer
  coordinates the kernel reads - no key array, no ``bisect``, and the whole descent
  unrolled per depth. A generic loop over the levels measured ~280 ns per lookup more,
  which is the difference between beating a flat grid and losing to it.
* **The table holds the answer, not a pointer to it.** One ``int16`` per root cell: a
  zone id for a cell a single zone covers, ``ABSENT`` for a cell with no coverage, and
  otherwise the index of a child block. The large majority of root cells are answered by
  that one read. The block array is the same tri-state one level down, with a candidate list
  index where the table had a block index.
* **Only the candidate lists are stored, each distinct one once.** Duplicates carry
  *equal* offsets into the shared payload rather than an index to a shared entry, so a
  repeated list costs a lookup exactly what a unique one costs.
* **Cells are exact, and that is where the selectivity comes from.** A cell owns the
  integer points ``[x0, x1] x [y0, y1]`` of :func:`cell_bounds`, so it owns its north
  and east edges and not its south or west - the point-in-polygon kernel's own
  convention, which ``tests/test_point_in_polygon_boundary_convention.py`` pins. A zone
  whose polygons only reach across a cell edge therefore is not a candidate in it, and
  which is where the index's selectivity comes from. A kernel change moving boundary
  points to the other polygon would make these cells misanswer one-unit strips along
  every aligned border while every sampled test still passed, which is why that test is
  the one this layout rests on.

The five arrays live in **one** file rather than one file each, and in a raw layout rather
than ``.npy``: they are a single structure with cross-references, four files load ~1.6x
slower and four ``.npy`` files ~3x, and a ``.npy`` carries neither of the two markers that
let a stale data directory be rejected. :func:`write_shortcuts_binary` records the
measurement.

Everything the layout assumes is checked where the data is produced -
``timezonefinder._data_integrity.validate_shortcut_index`` - and never when a finder is
built.
"""

from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Final

import numpy as np

from timezonefinder.configs import (
    COORD2INT_FACTOR,
    DEFAULT_DATA_DIR,
    MAX_LAT_VAL_INT,
    MAX_LNG_VAL_INT,
    SHORTCUT_BLOCK_SIDE,
    SHORTCUT_ROOT_COLUMNS,
)
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
SHORTCUT_LAYOUT_VERSION: Final[int] = 3

#: Stamped into the file so a truncated, foreign or pre-guard file is rejected rather
#: than read as coordinates that happen to parse.
FILE_IDENTIFIER: Final[bytes] = b"TZSC"

SHORTCUT_FILE_NAME: Final[str] = "shortcuts.bin"


# --- the grid the cells are made of ---------------------------------------------------

#: Root cells across the full longitude span, and rows across the latitude span. The
#: rows follow from the columns because the cells are square in degrees: half as much
#: latitude as longitude.
ROOT_COLUMNS: Final[int] = SHORTCUT_ROOT_COLUMNS
ROOT_ROWS: Final[int] = ROOT_COLUMNS // 2
ROOT_CELLS: Final[int] = ROOT_COLUMNS * ROOT_ROWS

#: Side of the block a refined root cell holds, in child cells.
BLOCK_SIDE: Final[int] = SHORTCUT_BLOCK_SIDE
BLOCK_CELLS: Final[int] = BLOCK_SIDE * BLOCK_SIDE
#: ``& BLOCK_MASK`` is the child's position within its block, which is why the side has
#: to be a power of two.
BLOCK_MASK: Final[int] = BLOCK_SIDE - 1

CHILD_COLUMNS: Final[int] = ROOT_COLUMNS * BLOCK_SIDE
CHILD_ROWS: Final[int] = ROOT_ROWS * BLOCK_SIDE
CHILD_CELLS: Final[int] = CHILD_COLUMNS * CHILD_ROWS

#: Full coordinate span of each axis, in the scaled integers everything here works in.
X_SPAN: Final[int] = 2 * MAX_LNG_VAL_INT
Y_SPAN: Final[int] = 2 * MAX_LAT_VAL_INT

#: Width of one cell per level. Whole numbers of coordinate units, which is the property
#: that makes a cell one floor division: 0.75 and 0.1875 degrees both divide the
#: integer span exactly.
ROOT_WIDTH: Final[int] = X_SPAN // ROOT_COLUMNS
CHILD_WIDTH: Final[int] = X_SPAN // CHILD_COLUMNS

# A cell owns `(c * w, (c + 1) * w]` of the shifted axis - its north and east edges and
# not its south or west, the kernel's convention - so the column of a coordinate is
# `ceil(x' / w) - 1` for `x' = x + span/2`. Folding the `- 1` into the shift turns that
# into the single floor division `(x + SHIFT) // w` the lookup runs.
X_SHIFT: Final[int] = MAX_LNG_VAL_INT - 1
Y_SHIFT: Final[int] = MAX_LAT_VAL_INT - 1

if X_SPAN % CHILD_COLUMNS or Y_SPAN % CHILD_ROWS:
    raise AssertionError(
        f"a grid of {CHILD_COLUMNS}x{CHILD_ROWS} finest cells is not a whole number of "
        "coordinate units wide; the lookup's floor division would not address them"
    )
if BLOCK_SIDE & BLOCK_MASK:
    raise AssertionError(f"the block side {BLOCK_SIDE} is not a power of two")

#: Table value for a cell no polygon covers. Custom data can leave cells uncovered, so
#: this is a real state and not only padding. ``-1`` is available for it because a stored
#: candidate list can never have length 1 - a single candidate is unambiguous and is
#: therefore stored as a zone id - so the entry indices start at 0 and map to ``-2``.
ABSENT: Final[int] = -1

#: The dtype of both levels. Zone ids, block indices and entry indices share it; all
#: three are guarded at build time.
TABLE_DTYPE: Final[np.dtype] = np.dtype(np.int16)

#: Boundary polygon ids, as stored in the payload.
PAYLOAD_DTYPE: Final[np.dtype] = np.dtype(np.uint16)

# header: identifier, layout version, then the six int64 the reader needs to make sense
# of the arrays. Sized so that the int16 table starts 8-byte aligned.
#
# The grid shape is in there because nothing else in the file records it, and it changes
# what every cell *means* without changing anything a reader would notice: a 192-column
# file read by 384-column code indexes a table of the wrong size with the wrong
# arithmetic and answers with a different cell's timezone. The layout version does not
# cover it - the layout is identical at every grid shape.
_HEADER_SIZE: Final[int] = 56


def shifted(lng: float, lat: float) -> tuple[int, int]:
    """A coordinate as the shifted integer pair the cell arithmetic divides.

    The two lines no polygon owns as spelled are rewritten exactly as
    :func:`timezonefinder.utils.query2int` rewrites them, so that the cell a point falls
    in agrees with the polygons it is tested against: -180 degrees reads as +180, which
    here is the last column rather than the first, and -90 as the point one unit north,
    which clamping the row at zero gives. Only those two spellings can go negative after
    the shift - ``x + X_SHIFT < 0`` holds for ``x == -MAX_LNG_VAL_INT`` and nothing else -
    so the rewrite needs no range check.

    Off the query path: the lookups inline this, because a call per query is a
    measurable share of the one stage every query pays. It is here for the tooling that
    asks which cell a coordinate falls in, and so that the rewrite is written down once.
    """
    x = int(lng * COORD2INT_FACTOR) + X_SHIFT
    if x < 0:
        x += X_SPAN
    y = int(lat * COORD2INT_FACTOR) + Y_SHIFT
    if y < 0:
        y = 0
    return x, y


def root_cell_of(x: int, y: int) -> int:
    """The root cell a shifted integer pair falls in, as a cell id."""
    return (y // ROOT_WIDTH) * ROOT_COLUMNS + x // ROOT_WIDTH


def child_cell_of(x: int, y: int) -> int:
    """The finest-level cell a shifted integer pair falls in, as a cell id.

    Addresses a cell whether or not its root refines; whether that cell is stored is the
    index's business, not the grid's.
    """
    return ROOT_CELLS + (y // CHILD_WIDTH) * CHILD_COLUMNS + x // CHILD_WIDTH


def is_root_cell(cell_id: int) -> bool:
    """Whether a cell id names a root cell rather than one of the finer ones.

    Cell ids number the root grid first and the finest grid after it, so the level is the
    id's own magnitude and no cell id means two things. The numbering is a property of the
    *grid* and not of the data: it does not move when a different root cell happens to
    refine, which is what lets a fixture or a measurement record cell ids at all.
    """
    return cell_id < ROOT_CELLS


def cell_bounds(cell_id: int) -> tuple[int, int, int, int]:
    """The first and last integer coordinate a cell owns: ``(x0, y0, x1, y1)``.

    Inclusive on both ends and in unshifted coordinates, so it is directly what the
    converter intersects polygons with and what an audit probes. A cell owns its north
    and east edges and not its south or west, so ``x0`` is one unit east of the
    neighbour's ``x1``.
    """
    if is_root_cell(cell_id):
        row, col = divmod(cell_id, ROOT_COLUMNS)
        width = ROOT_WIDTH
    else:
        row, col = divmod(cell_id - ROOT_CELLS, CHILD_COLUMNS)
        width = CHILD_WIDTH
    return (
        col * width - MAX_LNG_VAL_INT + 1,
        row * width - MAX_LAT_VAL_INT + 1,
        (col + 1) * width - MAX_LNG_VAL_INT,
        (row + 1) * width - MAX_LAT_VAL_INT,
    )


def cell_bounds_of(cell_ids: np.ndarray) -> tuple[np.ndarray, ...]:
    """:func:`cell_bounds` over an array of cell ids, as four arrays, levels mixed.

    What the converter hands ``shapely.box`` and what an audit probes: one array per
    bound beats a list of tuples, because every consumer builds boxes in bulk.
    """
    ids = np.asarray(cell_ids, dtype=np.int64)
    root = ids < ROOT_CELLS
    columns = np.where(root, ROOT_COLUMNS, CHILD_COLUMNS)
    width = np.where(root, ROOT_WIDTH, CHILD_WIDTH)
    row, col = np.divmod(np.where(root, ids, ids - ROOT_CELLS), columns)
    return (
        col * width - MAX_LNG_VAL_INT + 1,
        row * width - MAX_LAT_VAL_INT + 1,
        (col + 1) * width - MAX_LNG_VAL_INT,
        (row + 1) * width - MAX_LAT_VAL_INT,
    )


def child_cells_of(root_cell_id: int) -> np.ndarray:
    """The ``BLOCK_CELLS`` finest-level cell ids one root cell refines into.

    In block order - row-major within the block - which is the order the block array
    stores them in, so the two can be zipped.
    """
    row, col = divmod(root_cell_id, ROOT_COLUMNS)
    rows = row * BLOCK_SIDE + np.arange(BLOCK_SIDE, dtype=np.int64)
    cols = col * BLOCK_SIDE + np.arange(BLOCK_SIDE, dtype=np.int64)
    return (ROOT_CELLS + rows[:, None] * CHILD_COLUMNS + cols[None, :]).reshape(-1)


def parent_cell_of(child_cell_id: int) -> int:
    """The root cell id a finest-level cell id belongs to."""
    row, col = divmod(child_cell_id - ROOT_CELLS, CHILD_COLUMNS)
    return (row // BLOCK_SIDE) * ROOT_COLUMNS + col // BLOCK_SIDE


def block_position_of(child_cell_id: int) -> int:
    """Where a finest-level cell sits inside its parent's block, in ``0 .. BLOCK_CELLS``."""
    row, col = divmod(child_cell_id - ROOT_CELLS, CHILD_COLUMNS)
    return (row & BLOCK_MASK) * BLOCK_SIDE + (col & BLOCK_MASK)


class ShortcutIndex:
    """The loaded index, and the only thing that knows its cells and their stored answers.

    Callers ask it three questions and never touch its arrays. What the cell holding a
    coordinate resolves to is a tri-state, and :meth:`entry_at` returns it as one integer
    so that the common case costs one comparison rather than an allocation:

    ============================ ===========================================
    ``entry >= 0``               the timezone id, and the whole answer
    ``entry == ABSENT``          no timezone covers this cell
    ``entry < ABSENT``           several zones; ask :meth:`candidates_of`
    ============================ ===========================================

    That tri-state is the lookup's own vocabulary - a cell is covered by one zone, by
    none, or by several - so branching on it is domain logic. **How** it is encoded (the
    cell a coordinate falls in, the grid arithmetic, the descent into a block, the
    ``-(entry + 2)`` entry index, the CSR bounds) stops here, which is what lets the
    cells be replaced without touching ``timezonefinder.py``. Keep it that way: a lookup
    method that computes a cell pins the layout from outside.

    The arrays stay public because the build-time checks in ``timezonefinder/_data_integrity.py``
    and the format tests legitimately inspect them; the query path does not.
    """

    __slots__ = (
        "table",
        "blocks",
        "starts",
        "ends",
        "last_change",
        "payload",
        "_root",
        "_block",
    )

    def __init__(
        self,
        table: np.ndarray,
        blocks: np.ndarray,
        starts: np.ndarray,
        ends: np.ndarray,
        last_change: np.ndarray,
        payload: np.ndarray,
    ) -> None:
        #: ``int16`` per root cell: ``>= 0`` zone id, ``ABSENT`` uncovered, else
        #: ``-(block + 2)``
        self.table = table
        #: ``int16`` per child cell of every refined root cell, ``BLOCK_CELLS`` at a
        #: time: ``>= 0`` zone id, ``ABSENT`` uncovered, else ``-(entry + 2)``
        self.blocks = blocks
        #: start of each distinct candidate list in ``payload``
        self.starts = starts
        #: end of each distinct candidate list; a view of the same CSR array as ``starts``
        self.ends = ends
        #: per distinct list, the index past which no other zone can be matched
        self.last_change = last_change
        #: every distinct candidate list, back to back
        self.payload = payload
        # The same two levels as memoryviews, for the scalar descent alone. Indexing a
        # memoryview of int16 yields a Python int directly, where `int(array[i])` builds
        # a numpy scalar and unwraps it. That is worth 6 % of a whole random
        # `timezone_at` and 8 % of a unique-cell one, winning 52 and 55 of 61 paired
        # rounds (`benchmarks/candidate_comparison.py`), because the root read is the
        # single largest stage of a query that needs no geometry. Nothing but the arrays
        # themselves is resident - a memoryview is a view - and the batch path needs the
        # arrays for its gathers, so each pair of names refers to one allocation.
        self._root = memoryview(table)
        self._block = memoryview(blocks)

    # --- the query contract -------------------------------------------------------

    def entry_at(self, lng: float, lat: float) -> int:
        """What the cell holding a coordinate resolves to, as the tri-state above.

        The lookups hand this the coordinate and never see a cell, so replacing the cells
        is a change to this class alone. Written as one unrolled descent rather than as
        calls to :func:`shifted` and :func:`root_cell_of`: this is the one stage every
        query pays, and a Python call per level measured ~280 ns of it.

        The two lines no polygon owns as spelled are rewritten here as
        :func:`timezonefinder.utils.query2int` rewrites them for the geometry - -180
        degrees wraps to the *last* column, not clamped to the first, and -90 clamps to
        row 0, which is the point one unit north. A tree that clamped the longitude
        instead would answer the far side of the globe there;
        ``tests/test_minus_180_meridian_and_minus_90_parallel.py`` fails on it.
        """
        x = int(lng * COORD2INT_FACTOR) + X_SHIFT
        if x < 0:
            x += X_SPAN
        y = int(lat * COORD2INT_FACTOR) + Y_SHIFT
        if y < 0:
            y = 0
        entry = self._root[(y // ROOT_WIDTH) * ROOT_COLUMNS + x // ROOT_WIDTH]
        if entry >= ABSENT:
            return entry
        return self._block[
            (-2 - entry) * BLOCK_CELLS
            + ((y // CHILD_WIDTH) & BLOCK_MASK) * BLOCK_SIDE
            + ((x // CHILD_WIDTH) & BLOCK_MASK)
        ]

    def entries_at(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        """What the cells holding many coordinates resolve to, as the same tri-state.

        The batch sibling of :meth:`entry_at`, and the whole of it is numpy: the scaling,
        the two floor divisions and the table gather run once over the batch. **Keep every
        stage of it vectorised** - this is most of what a batch lookup buys, and one
        per-point call here would put the loop back.

        The descent is the only part that is not uniform, and it runs on the points that
        need it rather than on the batch: one gather for every point whose root cell
        refines, whatever the batch's mix.
        """
        x = (lngs * COORD2INT_FACTOR).astype(np.int64)
        x += X_SHIFT
        # the -180 meridian, and only it, lands at -1 here; wrapping it by a full span
        # puts it in the last column, which is the +180 meridian's
        np.add(x, X_SPAN, out=x, where=x < 0)
        y = (lats * COORD2INT_FACTOR).astype(np.int64)
        y += Y_SHIFT
        np.maximum(y, 0, out=y)
        entries = self.table[(y // ROOT_WIDTH) * ROOT_COLUMNS + x // ROOT_WIDTH]
        refined = np.flatnonzero(entries < ABSENT)
        if refined.size:
            # int64 throughout: a block index times BLOCK_CELLS leaves int16 long before
            # the table's own range does
            blocks = -2 - entries[refined].astype(np.int64)
            entries[refined] = self.blocks[
                blocks * BLOCK_CELLS
                + ((y[refined] // CHILD_WIDTH) & BLOCK_MASK) * BLOCK_SIDE
                + ((x[refined] // CHILD_WIDTH) & BLOCK_MASK)
            ]
        return entries

    def entry_of(self, cell_id: int) -> int:
        """What a cell resolves to, for a caller that already holds the cell id.

        The lookups ask :meth:`entry_at`; this form serves the tooling that walks cells
        rather than points - the converter-side scripts and the tests.

        :raises ValueError: if ``cell_id`` names a finest-level cell whose root does not
            refine. Such a cell has no stored value, and reading one would answer with
            an unrelated block's.
        """
        if is_root_cell(cell_id):
            return int(self.table[cell_id])
        parent = int(self.table[parent_cell_of(cell_id)])
        if parent >= ABSENT:
            raise ValueError(
                f"cell {cell_id} is a finest-level cell, but its root cell "
                f"{parent_cell_of(cell_id)} stores an answer of its own rather than a "
                "block of children. Ask for the root cell instead."
            )
        return int(
            self.blocks[(-2 - parent) * BLOCK_CELLS + block_position_of(cell_id)]
        )

    def entries_of(self, cell_ids: np.ndarray) -> np.ndarray:
        """What each of many cells resolves to, as the same tri-state integers.

        The batch sibling of :meth:`entry_of`, and it lives here for the same reason that
        one does: the grid arithmetic and the arrays are this class's business, so a
        caller that indexed ``table`` itself would pin the layout from outside. Takes the
        two levels mixed, since :meth:`items` yields them mixed.
        """
        ids = np.asarray(cell_ids, dtype=np.int64)
        out = np.empty(ids.shape, dtype=TABLE_DTYPE)
        root = ids < ROOT_CELLS
        out[root] = self.table[ids[root]]
        children = ids[~root] - ROOT_CELLS
        if children.size:
            rows, cols = np.divmod(children, CHILD_COLUMNS)
            parents = (rows // BLOCK_SIDE) * ROOT_COLUMNS + cols // BLOCK_SIDE
            blocks = -2 - self.table[parents].astype(np.int64)
            if np.any(blocks < 0):
                raise ValueError(
                    "a finest-level cell id was asked for whose root cell stores an "
                    "answer of its own rather than a block of children"
                )
            out[~root] = self.blocks[
                blocks * BLOCK_CELLS
                + (rows & BLOCK_MASK) * BLOCK_SIDE
                + (cols & BLOCK_MASK)
            ]
        return out

    def candidates_of(self, entry: int) -> np.ndarray:
        """The boundary polygon ids to test, for an ``entry`` below ``ABSENT``."""
        i = -(entry + 2)
        return self.payload[self.starts[i] : self.ends[i]]

    def stop_index_of(self, entry: int) -> int:
        """Index into :meth:`candidates_of` past which no other zone can be matched.

        Precomputed when the index is built, so a query reads it rather than scanning for
        it. ``get_last_change_idx`` is the definition, and ``timezonefinder/_data_integrity.py``
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

    @property
    def nr_of_blocks(self) -> int:
        """How many root cells refine, which is how many child blocks are stored."""
        return len(self.blocks) // BLOCK_CELLS

    def polygons_of_entry(self, entry_idx: int) -> np.ndarray:
        """The candidate polygon ids of one distinct entry, by its own index.

        Addressed by entry index rather than by the encoding of it, which is what
        separates it from :meth:`candidates_of`: the build side iterates entries, the
        query side follows a stored value.
        """
        return self.payload[self.starts[entry_idx] : self.ends[entry_idx]]

    def cell_at(self, lng: float, lat: float) -> int:
        """The id of the cell a coordinate's answer is stored in.

        The leaf, so the level depends on whether the point's root cell refines. Not on
        the query path - :meth:`entry_at` answers without ever naming a cell - but it is
        what lets tooling and tests address the one cell a point reads.
        """
        x, y = shifted(lng, lat)
        root = root_cell_of(x, y)
        if int(self.table[root]) >= ABSENT:
            return root
        return child_cell_of(x, y)

    def replacing(self, cell_id: int, value: int) -> "ShortcutIndex":
        """A copy of this index in which ``cell_id`` resolves to ``value``.

        Loaded index arrays are the dataset and are frozen, so changing one cell means a
        new index rather than a write. One array is copied and the rest are shared, since
        they are read-only in both.

        What it is for: the packaged ocean zones cover every cell, so ``ABSENT`` is a
        state only custom data reaches, and the tests that have to reach it would
        otherwise each re-derive which array a cell lives in - the one thing this class
        exists to keep inside it.
        """
        if is_root_cell(cell_id):
            table = self.table.copy()
            table[cell_id] = value
            table.flags.writeable = False
            return ShortcutIndex(
                table,
                self.blocks,
                self.starts,
                self.ends,
                self.last_change,
                self.payload,
            )
        parent = int(self.table[parent_cell_of(cell_id)])
        if parent >= ABSENT:
            raise ValueError(
                f"cell {cell_id}'s root cell does not refine, so the cell is not stored"
            )
        blocks = self.blocks.copy()
        blocks[(-2 - parent) * BLOCK_CELLS + block_position_of(cell_id)] = value
        blocks.flags.writeable = False
        return ShortcutIndex(
            self.table, blocks, self.starts, self.ends, self.last_change, self.payload
        )

    def value_of(self, cell_id: int) -> int | np.ndarray | None:
        """What one cell resolves to: a zone id, a candidate list, or ``None``.

        Reporting and test-side convenience, not the query path - the callers that care
        about speed dispatch on the raw stored value instead of building this union.
        """
        entry = self.entry_of(cell_id)
        if entry >= 0:
            return entry
        if entry == ABSENT:
            return None
        return self.polygons_of_entry(-(entry + 2))

    def items(self) -> Iterator[tuple[int, int | np.ndarray]]:
        """Every covered cell the index stores, as ``(cell id, zone id | polygon ids)``.

        The leaves and only the leaves: a root cell that refines is not itself an answer,
        and its children are yielded instead. In ascending cell id, which puts every root
        leaf before every finer one - the ids number the grids in that order.
        """
        table = self.table
        for cell_id in np.flatnonzero(table != ABSENT).tolist():
            value = int(table[cell_id])
            if value >= 0:
                yield cell_id, value
        blocks = self.blocks
        # child cell ids ascend with the *grid*, not with the block array, so the block
        # order has to be mapped back through the parents rather than walked
        for parent in np.flatnonzero(table < ABSENT).tolist():
            base = (-2 - int(table[parent])) * BLOCK_CELLS
            for position, child in enumerate(child_cells_of(parent).tolist()):
                value = int(blocks[base + position])
                if value == ABSENT:
                    continue
                yield (
                    child,
                    value if value >= 0 else self.polygons_of_entry(-(value + 2)),
                )

    def as_mapping(self) -> dict[int, int | np.ndarray]:
        """Materialise the index as the cell -> value dict reports and tests work over.

        Sorted by cell id explicitly, not by the pair: a value may be an array, and a
        tuple comparison that ever reached the second element would raise on one rather
        than order it. It cannot today, because cell ids are distinct - which is exactly
        the kind of reason that stops being true quietly.
        """
        return dict(sorted(self.items(), key=lambda item: item[0]))


def get_shortcut_file_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """Path of the shortcut index binary inside a compiled data directory."""
    return output_path / SHORTCUT_FILE_NAME


def read_shortcuts_binary(file_path: Path) -> ShortcutIndex:
    """Read a shortcut index file.

    Nothing is derived here: the file holds exactly what the lookup indexes, which is why
    loading it is a fraction of a millisecond.

    :raises ValueError: if the file carries no known identifier, an unreadable layout
        version, or a grid this reader's arithmetic does not address.
    """
    with open(file_path, "rb") as f:
        buf = f.read()

    if buf[:4] != FILE_IDENTIFIER:
        # A file written before this format carried an identifier at all. Reported as
        # layout version 0 rather than as a corrupt file, since an outdated index is what
        # it is for everyone who will ever hit this.
        raise incompatible_layout_error(
            "shortcut index file", 0, SHORTCUT_LAYOUT_VERSION, file_path
        )
    layout_version = int(np.frombuffer(buf, dtype=np.uint32, count=1, offset=4)[0])
    if layout_version != SHORTCUT_LAYOUT_VERSION:
        raise incompatible_layout_error(
            "shortcut index file", layout_version, SHORTCUT_LAYOUT_VERSION, file_path
        )

    root_columns, block_side, nr_blocks, nr_entries, offset_width, length_width = (
        int(v) for v in np.frombuffer(buf, dtype=np.int64, count=6, offset=8)
    )
    if (root_columns, block_side) != (ROOT_COLUMNS, BLOCK_SIDE):
        raise ValueError(
            f"the shortcut index {file_path} is built for a grid of {root_columns} root "
            f"columns refining into {block_side}x{block_side} blocks, but this "
            f"timezonefinder reads {ROOT_COLUMNS} and {BLOCK_SIDE}x{BLOCK_SIDE}. Every "
            f"cell in it means a different region, so reading it would return another "
            f"cell's timezone rather than an error. Regenerate this data directory with "
            f"scripts/file_converter.py from the current checkout."
        )
    pos = _HEADER_SIZE
    # `.copy()`, never `np.ascontiguousarray`: the latter hands back an already-contiguous
    # view unchanged, and a surviving view keeps the whole file buffer alive.
    table = np.frombuffer(buf, dtype=TABLE_DTYPE, count=ROOT_CELLS, offset=pos).copy()
    pos += ROOT_CELLS * TABLE_DTYPE.itemsize
    blocks = np.frombuffer(
        buf, dtype=TABLE_DTYPE, count=nr_blocks * BLOCK_CELLS, offset=pos
    ).copy()
    pos += nr_blocks * BLOCK_CELLS * TABLE_DTYPE.itemsize
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
    # Loaded index arrays are the dataset, not caller-owned working state. Some are
    # publicly reachable for build-time checks and reporting, so freeze every owner
    # before handing out views. In particular, cells with identical candidate lists
    # share one payload range, and starts/ends share the bounds array.
    for array in (table, blocks, bounds, last_change, payload):
        array.flags.writeable = False
    return ShortcutIndex(table, blocks, bounds[:-1], bounds[1:], last_change, payload)


def narrowest_dtype_for(max_value: int, *, what: str) -> np.dtype:
    """The narrowest unsigned width that holds ``max_value``. No headroom required.

    Headroom is not the safeguard here - being handed the column's *maximum* is. Callers
    pass ``values.max()``, so the width fits by construction and there is nothing left for
    a follow-up guard to catch; what a narrow width still needs is a check that the file
    it produced holds together, which ``timezonefinder._data_integrity.validate_shortcut_index``
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
    the root table, the block array and the payload. The two data-dependent columns need
    no such guard: their width is derived from the maximum they have to hold, so it fits
    by construction. Called by the builder, never when a finder is constructed.

    The payload is the one that reads as safe and is not: a boundary id past ``uint16``
    wraps to a *valid* id, and no reader can tell the difference afterwards - the
    committed-data check compares the payload's maximum against the polygon count, and a
    wrapped value is below it by construction. So it has to be caught where the value is
    still known.

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

    A candidate list is ordered so that the *final* zone's polygons are a complete,
    contiguous suffix, so once the scan reaches that run there is nothing left to rule out
    and the answer is that zone whether or not its polygons are tested.

    That suffix is the whole of the ordering contract - see ``scripts.shortcuts``'s
    ``check_shortcut_sorting``, which asserts it and nothing else. The tested prefix may
    interleave zones freely, and the final zone is *not* required to be the largest one:
    the converter orders the prefix by estimated full-predicate work, so a zone may
    appear before another zone's remaining polygons. That is why this scans from the back:
    a forward scan stopping at the first zone change would answer the start of the *first*
    run rather than the last, and on an interleaved prefix that is too small -
    the query would then break out of the candidate loop with zones still unruled-out and
    return the final zone for a point one of them contains.

    **Build-time only.** The query used to call this per lookup; it now reads the answer
    out of the shortcut index, which stores one value per *distinct* candidate list. It
    lives here beside the builder that writes those values rather than in
    ``timezonefinder/utils_numba.py``, where it was compiled at import for a function no
    query calls - and ``timezonefinder/_data_integrity.py`` re-checks the committed values against
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
    mapping: Mapping[int, int | list[int] | np.ndarray],
    poly_zone_ids: np.ndarray,
) -> ShortcutIndex:
    """Build the index from the compiled cell -> zone id | polygon ids mapping.

    The mapping holds the tree's **leaves**, keyed by the cell ids
    :func:`root_cell_of` and :func:`child_cell_of` produce: a root cell a single zone
    covers, and the finest-level cells of every root cell that several zones can own.
    Which root cells refine is therefore the mapping's own shape, read off the child keys
    it carries, and the block indices follow in ascending parent order so that one input
    always compiles to one file.

    :param mapping: what ``scripts/shortcuts.py`` compiles: a cell covered by a single
        zone maps to that zone id, a finest-level cell several zones can own to its
        candidate polygon ids.
    :param poly_zone_ids: zone id per boundary polygon, needed to precompute
        ``last_change``.
    :raises ShortcutOverflowError: if a value no longer fits the column that holds it.
    :raises ValueError: if the mapping is not a tree this layout can hold.
    """
    table = np.full(ROOT_CELLS, ABSENT, dtype=np.int64)
    parents = sorted(
        {parent_cell_of(cell) for cell in mapping if not is_root_cell(cell)}
    )
    block_of = {parent: i for i, parent in enumerate(parents)}
    blocks = np.full(len(parents) * BLOCK_CELLS, ABSENT, dtype=np.int64)
    for parent, block in block_of.items():
        table[parent] = -(block + 2)

    # distinct candidate lists, in first-seen (= ascending cell id) order
    entry_of: dict[bytes, int] = {}
    entry_payloads: list[np.ndarray] = []

    for cell_id in sorted(mapping):
        value = mapping[cell_id]
        root = is_root_cell(cell_id)
        if root:
            if cell_id in block_of:
                raise ValueError(
                    f"root cell {cell_id} stores an answer of its own and also has "
                    "finest-level cells in the mapping. A root cell either answers or "
                    "refines; the lookup reads its one stored value as whichever the "
                    "sign says, so it cannot be both."
                )
            position = cell_id
            level_table = table
        else:
            position = block_of[parent_cell_of(cell_id)] * BLOCK_CELLS
            position += block_position_of(cell_id)
            level_table = blocks
        if isinstance(value, (int, np.integer)):
            level_table[position] = int(value)
            continue
        requested = np.asarray(value, dtype=np.int64)
        check_fits(
            requested,
            PAYLOAD_DTYPE,
            what="a candidate boundary polygon id",
            remedy="Widen PAYLOAD_DTYPE to uint32.",
        )
        poly_ids = requested.astype(PAYLOAD_DTYPE)
        if len(poly_ids) == 0:
            # A cell no polygon covers. Recorded as absent rather than as an empty entry:
            # every caller answers `None` for both, and storing nothing needs no index.
            continue
        if len(poly_ids) == 1:
            raise ValueError(
                f"cell {cell_id} stores a single candidate polygon. A single candidate "
                "is unambiguous and has to be stored as a zone id - "
                "scripts.shortcuts.compile_shortcut_mapping is what guarantees that - "
                "and the index needs the one-candidate case to stay impossible, since "
                "that is what leaves a spare table value to mean 'no cell here'."
            )
        if root:
            raise ValueError(
                f"root cell {cell_id} stores a candidate list. Only a finest-level cell "
                "may: a root cell several zones can own refines, and the lookup reads a "
                "negative root value as the index of its block of children."
            )
        key_bytes = poly_ids.tobytes()
        found = entry_of.get(key_bytes)
        if found is None:
            found = len(entry_payloads)
            entry_of[key_bytes] = found
            entry_payloads.append(poly_ids)
        level_table[position] = -(found + 2)

    check_fits(
        table[table >= 0],
        TABLE_DTYPE,
        what="a root cell's zone id",
        remedy="Widen the root table and the block array to int32.",
    )
    check_fits(
        -table[table < ABSENT],
        TABLE_DTYPE,
        what="a child block index",
        remedy=(
            "Refine fewer root cells, by making the root grid finer, or widen the root "
            "table and the block array to int32."
        ),
    )
    check_fits(
        blocks[blocks >= 0],
        TABLE_DTYPE,
        what="a finest-level cell's zone id",
        remedy="Widen the root table and the block array to int32.",
    )
    check_fits(
        -blocks[blocks < ABSENT],
        TABLE_DTYPE,
        what="a distinct entry index",
        remedy="Widen the root table and the block array to int32.",
    )

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
        table.astype(TABLE_DTYPE),
        blocks.astype(TABLE_DTYPE),
        bounds[:-1],
        bounds[1:],
        last_change,
        payload,
    )


def write_shortcuts_binary(index: ShortcutIndex, output_file: Path) -> None:
    """Write a built index to its binary file, in the narrowest columns that fit.

    The two data-dependent widths are recorded in the header rather than fixed by the
    format, which is what lets them be chosen by fit rather than by headroom: each is the
    narrowest that holds its column's maximum, and ``timezonefinder/_data_integrity.py`` asserts
    over the committed file that it still is.

    **One file, and a raw layout rather than ``.npy`` arrays.** The obvious
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
    * these arrays are **one structure with cross-references** - the table indexes the
      blocks, the blocks index the bounds, the bounds index the payload - so separate
      files can be individually stale or mismatched where one cannot, and the
      separability buys nothing that reads them.

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
                ROOT_COLUMNS,
                BLOCK_SIDE,
                index.nr_of_blocks,
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
        f.write(index.table.astype(TABLE_DTYPE).tobytes())
        f.write(index.blocks.astype(TABLE_DTYPE).tobytes())
        f.write(bounds.astype(offset_dtype).tobytes())
        f.write(index.payload.astype(PAYLOAD_DTYPE).tobytes())
        f.write(index.last_change.astype(length_dtype).tobytes())
