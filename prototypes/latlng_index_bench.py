#!/usr/bin/env python3

"""Price longitude/latitude-aligned shortcut indexes against the shipped grid tree.

FINDINGS (Intel Xeon, Cascade Lake @ 2.8 GHz, 4 vCPUs of a KVM cloud VM, Linux,
Python 3.13.16, data 2026d, fixture set v4, master at 6b99331)
==============================================================================

**Within the 400-800 KB index budget the grid tree wins every trade-off measured; the
flat structures lose on selectivity, and the equal-area band costs its own lookup.** All
candidates answer through the real finder against a control of the shipped cells, on
clang and numba; ranges span both, and a time is a candidate's change against the
control.

* **Grid tree** (0.9375-degree root refining where several zones meet): 0.048 / 0.115
  polygons tested per random / on-land query and ``TimezoneFinderL`` agreeing with the
  full lookup on 97.6 / 93.7 % of points, at 442-507 KB. One level of 4x4 blocks (507
  KB, the shipped shape) times level with the control, which checks the sweep. Two
  levels of 2x2 reach the same cells 65 KB cheaper but descend once more: level per
  random scalar call, 3-4 % slower on land and 10-18 % slower per batch. Head to head,
  one level of 4x4 is 6-11 % faster per batch and -1 to +7 % per scalar call, mostly
  unresolved.

* **Flat equal-angle grid** (one width everywhere, the simplest lookup): 0.095-0.111 /
  0.201-0.211 tests and 95.1-95.7 / 89.4-90.1 % agreement at 539-663 KB, since it spends
  2 bytes on every ocean cell. 2-17 % slower per random scalar call, 8-45 % per batch,
  and 9-21 % / 32-60 % on land.

* **Equal-area banded grid** (columns per row scaled by the cosine of latitude): the
  most selective flat grid at its size - 0.375-degree rows test 0.083 / 0.189 at 616 KB,
  but the per-row width and offset reads cost it what the selectivity bought: 8-19 %
  slower per scalar call and 18-24 % per batch. Head to head the shipped tree beats it
  by 7-11 % per scalar call and 16-26 % per batch.

* **Alignment with the 7.5-degree ocean meridians**: the unaligned 0.375-degree
  equal-area grid tests 24 % more polygons per random query than the aligned one at the
  same size, and the unaligned 0.48 and 0.45-degree equal-angle grids 9-17 % more than
  the aligned 0.46875.

* **Exact against touch-inclusive cells**: counting every polygon that touches a cell
  edge costs 50-60 % more polygon tests per random query on the same cells and 17-22 %
  per random scalar call against the control.

Shapes outside the budget are not built - above it they are refused by the cap, below it
they give up selectivity the cap would pay for. Which grid tree configuration is best
within it is a sweep of its own, not this comparison.

**Correctness.** All 11 candidates gave the control's answer for 30,000 fixture points,
for points on and one unit either side of their own cell edges, and on the 7.5-degree
and whole-degree lines borders follow - the -180 meridian included, which every
candidate reads as +180 the way the shipped lookup does - on both kernels and both the
scalar and the batch path.

The H3 index the grid tree replaced is priced in
``contributing/improvements/decisions/longitude-latitude-aligned-index-decisions.md``,
not here. ``--output`` writes every candidate's numbers in about a minute: the counts
exactly, the times for the machine it runs on.

METHOD
======

Every candidate is compiled from the packaged boundaries and answers through the real
``TimezoneFinder`` query path: a candidate is a ``ShortcutIndex`` whose ``entry_at`` and
``entries_at`` - the two methods the scalar lookup and the batch prologue call - are its
own cell lookup, put in the shipped index's place. Only those two methods are replaced,
so a candidate index answers nothing else a finder can be asked.

* **One ordering policy, the converter's own.** Candidate lists are ordered by
  ``scripts.shortcuts.optimise_shortcut_ordering`` itself, called on a sorted input. The
  baseline is a **control**: the shipped grid tree's candidate sets re-ordered by that
  policy and written and read back through the real shortcut file functions, because the
  shipped index also carries the converter's work optimizer, which the candidates do
  not. The control and ``grid_tree_0_9375deg_4x4_1levels`` are the same cells, so their
  counts must agree exactly; that is the sweep's own consistency check.
* **Exact cells.** A cell is computed from the truncated integer coordinates the kernel
  reads and owns its east and north edges, the kernel's own convention; -180 reads as
  +180 and -90 as the point one unit north, as the shipped lookup reads them. A polygon is a
  candidate only if it can own one of the cell's integer points: an interior
  intersection with the cell's box shifted half a unit south-west. The gate's boundary
  probes test exactly this, on both kernels.
* **The shipped layout's sizes.** One ``int16`` per cell, distinct candidate lists once
  each in the narrowest widths, and the shipped header; the same arithmetic reproduces
  the shipped ``shortcuts.bin`` to the byte.
* **The structures are compared within the budget**: flat equal-angle and equal-area
  grids, aligned with the ocean meridians and not, grid trees, and touch-inclusive
  controls, every one sized by the shipped file layout between 400 and 800 KB, with the
  shipped shape also timed head to head against its two nearest rivals.

It does not certify coverage beyond the sampled gate, time ``TimezoneFinderL``, or
measure loading, construction or ``make memory``. Times decide only when taken on
server hardware (x86-64 Linux), which the report's ``environment`` block records.
"""

import argparse
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np
import shapely
from shapely import STRtree

from benchmarks.candidate_comparison import CandidateComparison, compare_candidates
from scripts.assert_acceleration_path import (
    PACKED_ACCELERATION_IMPLEMENTATIONS,
    PACKED_BUFFER_FACTORIES,
    interpreted_path_name,
)
from scripts.benchmark_utils import cpu_info
from scripts.shortcuts import optimise_shortcut_ordering
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    benchmark_fixture_provenance,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import COORD2INT_FACTOR, DEFAULT_DATA_DIR
from timezonefinder.shortcut_index import (
    _HEADER_SIZE,
    ABSENT,
    BLOCK_CELLS,
    PAYLOAD_DTYPE,
    ROOT_CELLS,
    TABLE_DTYPE,
    ShortcutIndex,
    build_shortcut_index,
    get_last_change_idx,
    get_shortcut_file_path,
    narrowest_dtype_for,
    read_shortcuts_binary,
    write_shortcuts_binary,
)

STRATA = {
    "random": RANDOM_POINTS_FIXTURE,
    "on_land": ON_LAND_POINTS_FIXTURE,
    # the shipped index's classifications: correctness probes only, since a different
    # index re-labels their points. Only random and on_land rank.
    "shipped_unique": UNIQUE_SHORTCUT_POINTS_FIXTURE,
    "shipped_ambiguous": AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
}
RANKING_STRATA = ("random", "on_land")
# Pairs timed against each other rather than each against the control, for the
# claims a recommendation makes between two candidates: (challenger, baseline).
HEAD_TO_HEAD = (
    ("grid_tree_0_9375deg_4x4_1levels", "equal_area_0_375deg_aligned"),
    ("grid_tree_0_9375deg_4x4_1levels", "grid_tree_0_9375deg_2x2_2levels"),
)
MALACCA_WITNESS = (100.3055, 3.4804)

F = float(COORD2INT_FACTOR)
SCALE = int(COORD2INT_FACTOR)
X0 = 180 * SCALE
Y0 = 90 * SCALE
X_SPAN = 2 * X0
Y_SPAN = 2 * Y0
# ceil ownership: column of x is ((x + X0) * n - 1) // X_SPAN, i.e. (x + KX) // width
KX = X0 - 1
KY = Y0 - 1
OCEAN_MERIDIAN = 75 * SCALE // 10  # 7.5 degrees, where the Etc/GMT ocean zones meet
DEGREE = SCALE


# --- the converter's ordering, on the finder's arrays ---------------------------------


@dataclass(frozen=True)
class OrderingInput:
    """The three fields of the converter's ``TimezoneData`` that the legacy order reads."""

    boundaries: object
    poly_zone_ids: np.ndarray
    all_tz_names: list[str]


def legacy_order(data: OrderingInput, polygon_ids: Sequence[int]) -> list[int]:
    """The converter's order for one candidate set, from a fixed input order."""
    return optimise_shortcut_ordering(data, sorted(int(p) for p in polygon_ids))


class EntryPacker:
    """Distinct candidate lists, packed and narrowed exactly as the shortcut file is."""

    def __init__(self, data: OrderingInput):
        self.data = data
        self.entry_of: dict[bytes, int] = {}
        self.payloads: list[np.ndarray] = []

    def list_value(self, polygon_ids: Sequence[int]) -> int:
        ordered = np.asarray(legacy_order(self.data, polygon_ids), dtype=PAYLOAD_DTYPE)
        key = ordered.tobytes()
        found = self.entry_of.get(key)
        if found is None:
            found = len(self.payloads)
            self.entry_of[key] = found
            self.payloads.append(ordered)
        return -(found + 2)

    def arrays(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """``bounds``, ``payload`` and ``last_change`` as ``read_shortcuts_binary`` holds them."""
        lengths = np.array([len(p) for p in self.payloads], dtype=np.int64)
        bounds = np.concatenate([np.zeros(1, dtype=np.int64), np.cumsum(lengths)])
        bounds = bounds.astype(narrowest_dtype_for(int(bounds[-1]), what="offset"))
        payload = (
            np.concatenate(self.payloads)
            if self.payloads
            else np.empty(0, dtype=PAYLOAD_DTYPE)
        )
        last = np.array(
            [
                get_last_change_idx(self.data.poly_zone_ids[p.astype(np.int64)])
                for p in self.payloads
            ],
            dtype=np.int64,
        )
        last = last.astype(
            narrowest_dtype_for(int(last.max()) if len(last) else 0, what="stop")
        )
        for array in (bounds, payload, last):
            array.flags.writeable = False
        return bounds, payload, last


def entries_file_bytes(index: ShortcutIndex) -> int:
    """Bytes the shortcut file spends on the distinct lists: offsets, payload, stops."""
    nr_entries = len(index.last_change)
    return (
        (nr_entries + 1) * index.starts.dtype.itemsize
        + index.payload.nbytes
        + nr_entries * index.last_change.dtype.itemsize
    )


def entries_resident_bytes(index: ShortcutIndex) -> int:
    # starts and ends are two views of one bounds array
    return (
        index.starts.nbytes
        + index.starts.dtype.itemsize
        + index.payload.nbytes
        + index.last_change.nbytes
    )


def no_blocks() -> np.ndarray:
    """The shipped ``blocks`` array for a candidate that keeps its own levels."""
    blocks = np.empty(0, dtype=TABLE_DTYPE)
    blocks.flags.writeable = False
    return blocks


def table_value(values: np.ndarray) -> np.ndarray:
    if len(values) and (values.min() < np.iinfo(TABLE_DTYPE).min):
        raise OverflowError("more distinct candidate lists than an int16 table holds")
    table = values.astype(TABLE_DTYPE)
    table.flags.writeable = False
    return table


# --- geometry: which polygons can own an integer point of a cell ----------------------


def polygons_of(finder: TimezoneFinder) -> np.ndarray:
    """Every boundary polygon, holes cut out, in the stored integer coordinates."""
    geometries = []
    for boundary_id in range(len(finder.boundaries)):
        outer = finder.boundaries.coords_of(boundary_id).T.astype(np.float64)
        holes = [
            finder.holes.coords_of(hole_id).T.astype(np.float64)
            for hole_id in finder.holes.ids_of(boundary_id)
        ]
        geometry = shapely.Polygon(outer, holes)
        if not geometry.is_valid:
            raise ValueError(
                f"invalid polygon {boundary_id}: {shapely.is_valid_reason(geometry)}"
            )
        geometries.append(geometry)
    array = np.asarray(geometries, dtype=object)
    shapely.prepare(array)
    return array


def owned_pairs(
    polygons: np.ndarray,
    ix0: np.ndarray,
    iy0: np.ndarray,
    ix1: np.ndarray,
    iy1: np.ndarray,
    touching: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """``(cell, polygon)`` pairs where the polygon can own one of the cell's integer points.

    A cell owns the integer points ``[ix0, ix1] x [iy0, iy1]``. The kernel never puts a
    point on a polygon's south or west boundary inside it, and does put one on its north
    or east boundary inside, so a polygon that only touches the box
    ``[ix0 - 0.5, ix1] x [iy0 - 0.5, iy1]`` owns none of those points, and one whose
    interior meets it may. Pairs whose polygon reaches the box shrunk by a further quarter
    unit are interior without a ``touches`` test, which is the expensive one.

    ``touching`` is the control the exact rule is measured against: every polygon that
    meets the closed cell, edges included - what a plain ``intersects`` gives.
    """
    if touching:
        boxes = shapely.box(ix0 - 1, iy0 - 1, ix1, iy1)
        poly_idx, cell_idx = STRtree(boxes).query(polygons, predicate="intersects")
        return cell_idx, poly_idx
    outer = shapely.box(ix0 - 0.5, iy0 - 0.5, ix1, iy1)
    core = shapely.box(ix0 - 0.25, iy0 - 0.25, ix1 - 0.25, iy1 - 0.25)
    poly_idx, cell_idx = STRtree(outer).query(polygons, predicate="intersects")
    interior = shapely.intersects(polygons[poly_idx], core[cell_idx])
    edge = np.flatnonzero(~interior)
    if len(edge):
        interior[edge] = ~shapely.touches(
            polygons[poly_idx[edge]], outer[cell_idx[edge]]
        )
    return cell_idx[interior], poly_idx[interior]


def grouped(
    cell_idx: np.ndarray, poly_idx: np.ndarray, zone_ids: np.ndarray
) -> Iterator[tuple[int, np.ndarray, int]]:
    """Per cell with any candidate: the cell, its polygon ids, and its single zone or -1."""
    order = np.lexsort((poly_idx, cell_idx))
    cells = cell_idx[order]
    polys = poly_idx[order]
    if not len(cells):
        return
    starts = np.flatnonzero(np.r_[True, cells[1:] != cells[:-1]])
    ends = np.r_[starts[1:], len(cells)]
    zones = zone_ids[polys].astype(np.int64)
    zmin = np.minimum.reduceat(zones, starts)
    zmax = np.maximum.reduceat(zones, starts)
    for i, (start, end) in enumerate(zip(starts.tolist(), ends.tolist(), strict=True)):
        single = int(zmin[i]) if zmin[i] == zmax[i] else -1
        yield int(cells[start]), polys[start:end], single


def ranges(count: int, span: int, offset: int) -> tuple[np.ndarray, np.ndarray]:
    """First and last integer coordinate of each of ``count`` equal divisions of ``span``.

    Division ``c`` owns ``(c * span / count, (c + 1) * span / count]`` shifted by
    ``-offset``, so exact rational boundaries need no integer cell width.
    """
    c = np.arange(count, dtype=np.int64)
    first = (c * span) // count - offset + 1
    last = ((c + 1) * span) // count - offset
    return first, last


# --- candidate indexes ----------------------------------------------------------------
#
# Every scalar lookup reads its root level through ``_root``, the memoryview the shipped
# ``ShortcutIndex`` builds over ``table``, as the shipped lookup does. ``int(table[i])``
# instead put the shipped shape 4-5 % behind the control per scalar call with identical
# cells and counts: the comparison would have priced the read, not the cells.


class BandedGrid(ShortcutIndex):
    """Rows of equal latitude height, each split into its own number of equal columns.

    Equal-angle grids are the case of one column count for every row; equal-area grids
    scale it with the cosine of the row's latitude. Every count divides the integer
    longitude span, so a column is an integer width and the lookup is two divisions.
    """

    # ``widths`` and ``offsets`` are memoryviews over the int32 arrays beside them: a
    # scalar read costs what a list index does, and nothing but the array is resident
    __slots__ = (
        "name",
        "family",
        "params",
        "row_height",
        "widths",
        "offsets",
        "_widths_array",
        "_offsets_array",
    )

    def entry_at(self, lng: float, lat: float) -> int:
        row = (int(lat * F) + KY) // self.row_height
        if row < 0:
            row = 0
        x = int(lng * F) + KX
        if x < 0:
            x += X_SPAN
        return self._root[self.offsets[row] + x // self.widths[row]]

    def entries_at(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        rows = ((lats * F).astype(np.int64) + KY) // self.row_height
        np.maximum(rows, 0, out=rows)
        x = (lngs * F).astype(np.int64) + KX
        np.add(x, X_SPAN, out=x, where=x < 0)
        return self.table[self._offsets_array[rows] + x // self._widths_array[rows]]

    @property
    def cells(self) -> int:
        return len(self.table)

    @property
    def payload_bytes(self) -> int:
        rows = len(self.widths)
        uniform = len(set(self.widths)) == 1
        column_counts = 0 if uniform else 2 * rows
        return (
            _HEADER_SIZE + self.table.nbytes + column_counts + entries_file_bytes(self)
        )

    @property
    def resident_bytes(self) -> int:
        per_row = 0
        if not isinstance(self, UniformGrid):
            per_row = self._widths_array.nbytes + self._offsets_array.nbytes
        return self.table.nbytes + entries_resident_bytes(self) + per_row

    def edge_points(
        self, rng: np.random.Generator, count: int
    ) -> list[tuple[int, int]]:
        """Integer points on randomly chosen cell edges, half on columns, half on rows."""
        rows = len(self.widths)
        row_first, row_last = ranges(rows, Y_SPAN, Y0)
        points = []
        for r in rng.integers(0, rows, count // 2).tolist():
            width = self.widths[r]
            c = int(rng.integers(1, X_SPAN // width))
            y = int(rng.integers(row_first[r], row_last[r] + 1))
            points.append((c * width - X0, y))
        for r in rng.integers(1, rows, count // 2).tolist():
            points.append((int(rng.integers(-X0, X0 + 1)), int(row_first[r]) - 1))
        return points


class UniformGrid(BandedGrid):
    """An equal-angle grid: one width, so the cell is ``row * columns + col``."""

    __slots__ = ("width", "columns")

    def entry_at(self, lng: float, lat: float) -> int:
        row = (int(lat * F) + KY) // self.row_height
        if row < 0:
            row = 0
        x = int(lng * F) + KX
        if x < 0:
            x += X_SPAN
        return self._root[row * self.columns + x // self.width]

    def entries_at(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        rows = ((lats * F).astype(np.int64) + KY) // self.row_height
        np.maximum(rows, 0, out=rows)
        x = (lngs * F).astype(np.int64) + KX
        np.add(x, X_SPAN, out=x, where=x < 0)
        return self.table[rows * self.columns + x // self.width]


def build_grid(
    name: str,
    family: str,
    params: dict,
    rows: int,
    column_counts: Sequence[int],
    polygons: np.ndarray,
    data: OrderingInput,
    touching: bool = False,
) -> BandedGrid:
    if Y_SPAN % rows:
        raise ValueError(f"{rows} rows do not divide the latitude span")
    if any(X_SPAN % c for c in column_counts):
        raise ValueError(f"{name}: a column count does not divide the longitude span")
    row_first, row_last = ranges(rows, Y_SPAN, Y0)
    ix0, iy0, ix1, iy1 = [], [], [], []
    for r, count in enumerate(column_counts):
        first, last = ranges(count, X_SPAN, X0)
        ix0.append(first)
        ix1.append(last)
        iy0.append(np.full(count, row_first[r]))
        iy1.append(np.full(count, row_last[r]))
    ix0, iy0, ix1, iy1 = (np.concatenate(a) for a in (ix0, iy0, ix1, iy1))
    values = np.full(len(ix0), ABSENT, dtype=np.int64)
    packer = EntryPacker(data)
    for cell, polys, single in grouped(
        *owned_pairs(polygons, ix0, iy0, ix1, iy1, touching), data.poly_zone_ids
    ):
        values[cell] = single if single >= 0 else packer.list_value(polys)
    bounds, payload, last = packer.arrays()
    widths = np.asarray([X_SPAN // c for c in column_counts], dtype=np.int32)
    uniform = len(set(column_counts)) == 1
    cls = UniformGrid if uniform else BandedGrid
    index = cls(
        table_value(values), no_blocks(), bounds[:-1], bounds[1:], last, payload
    )
    index.name = name
    index.family = family
    index.params = params
    index.row_height = Y_SPAN // rows
    offsets = np.concatenate(
        [np.zeros(1, dtype=np.int64), np.cumsum(column_counts, dtype=np.int64)[:-1]]
    ).astype(np.int32)
    for array in (widths, offsets):
        array.flags.writeable = False
    index.widths = memoryview(widths)
    index.offsets = memoryview(offsets)
    index._widths_array = widths
    index._offsets_array = offsets
    if uniform:
        index.width = int(widths[0])
        index.columns = column_counts[0]
    return index


class GridTree(ShortcutIndex):
    """A dense aligned grid whose ambiguous cells refine into k x k child blocks.

    A quadtree with its top levels flattened into a grid and its lower levels reached by
    arithmetic rather than search. Level 0 is one ``int16`` per square root cell. A value
    below ``ABSENT`` above the last level is the index of a block of k x k children on the
    next level, one per cell any two zones can own; on the last level it is a candidate
    list entry, the shipped tri-state. Every level is a whole number of coordinate units
    wide, so a level's cell is one floor division per axis. Clamping the shifted latitude
    at 0 once covers -90 on every level, and wrapping a negative shifted longitude by the
    full span reads -180 as +180 on every level, as the shipped lookup does.
    """

    __slots__ = (
        "name",
        "family",
        "params",
        "k",
        "km",
        "kk",
        "levels",
        "columns",
        "w0",
        "w1",
        "w2",
        "b1",
        "b2",
        "widths",
        "_block_arrays",
    )

    def entries_at(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        x = (lngs * F).astype(np.int64) + KX
        np.add(x, X_SPAN, out=x, where=x < 0)
        y = np.maximum((lats * F).astype(np.int64) + KY, 0)
        w = self.widths[0]
        v = self.table[(y // w) * self.columns + x // w].astype(np.int64)
        for level in range(1, self.levels + 1):
            todo = np.flatnonzero(v < ABSENT)
            if not len(todo):
                break
            w = self.widths[level]
            child = ((y[todo] // w) & self.km) * self.k + ((x[todo] // w) & self.km)
            v[todo] = self._block_arrays[level - 1][(-2 - v[todo]) * self.kk + child]
        return v

    @property
    def cells(self) -> int:
        return len(self.table)

    @property
    def block_counts(self) -> list[int]:
        return [len(a) // self.kk for a in self._block_arrays]

    @property
    def payload_bytes(self) -> int:
        return (
            _HEADER_SIZE
            + self.table.nbytes
            + sum(a.nbytes for a in self._block_arrays)
            + entries_file_bytes(self)
        )

    @property
    def resident_bytes(self) -> int:
        return (
            self.table.nbytes
            + sum(a.nbytes for a in self._block_arrays)
            + entries_resident_bytes(self)
        )

    def edge_points(
        self, rng: np.random.Generator, count: int
    ) -> list[tuple[int, int]]:
        """Integer points on the finest level's lines, which carry every cell edge."""
        w = self.widths[-1]
        points = []
        for c in rng.integers(1, X_SPAN // w, count // 2).tolist():
            points.append((c * w - X0, int(rng.integers(-Y0, Y0 + 1))))
        for r in rng.integers(1, Y_SPAN // w, count // 2).tolist():
            points.append((int(rng.integers(-X0, X0 + 1)), r * w - Y0))
        return points


# One lookup per depth, unrolled: a generic loop over the levels measured ~280 ns per
# lookup more than these, enough to turn the tree from faster than a flat grid to slower.
class GridTree1(GridTree):
    __slots__ = ()

    def entry_at(self, lng: float, lat: float) -> int:
        x = int(lng * F) + KX
        y = int(lat * F) + KY
        if x < 0:
            x += X_SPAN
        if y < 0:
            y = 0
        w = self.w0
        v = self._root[(y // w) * self.columns + x // w]
        if v >= -1:
            return v
        w = self.w1
        km = self.km
        return self.b1[(-2 - v) * self.kk + ((y // w) & km) * self.k + ((x // w) & km)]


class GridTree2(GridTree):
    __slots__ = ()

    def entry_at(self, lng: float, lat: float) -> int:
        x = int(lng * F) + KX
        y = int(lat * F) + KY
        if x < 0:
            x += X_SPAN
        if y < 0:
            y = 0
        w = self.w0
        v = self._root[(y // w) * self.columns + x // w]
        if v >= -1:
            return v
        w = self.w1
        km = self.km
        k = self.k
        v = self.b1[(-2 - v) * self.kk + ((y // w) & km) * k + ((x // w) & km)]
        if v >= -1:
            return v
        w = self.w2
        return self.b2[(-2 - v) * self.kk + ((y // w) & km) * k + ((x // w) & km)]


def build_grid_tree(
    name: str,
    root_columns: int,
    k: int,
    levels: int,
    polygons: np.ndarray,
    data: OrderingInput,
) -> GridTree:
    """Evaluate level by level; refine every cell several zones can own, to ``levels``."""
    if k & (k - 1) or not 1 <= levels <= 2:
        raise ValueError(f"{name}: k must be a power of two and levels 1-2")
    widths = []
    for level in range(levels + 1):
        n = root_columns * k**level
        if X_SPAN % n:
            raise ValueError(f"{name}: level {level} is not a whole number of units")
        widths.append(X_SPAN // n)
    packer = EntryPacker(data)
    rows = root_columns // 2
    gx = np.tile(np.arange(root_columns, dtype=np.int64), rows)
    gy = np.repeat(np.arange(rows, dtype=np.int64), root_columns)
    arrays: list[np.ndarray] = []
    dy, dx = np.divmod(np.arange(k * k), k)
    for level, w in enumerate(widths):
        # cell g owns (g * w, (g + 1) * w] after the shift by -X0 / -Y0
        ix0, ix1 = gx * w - X0 + 1, (gx + 1) * w - X0
        iy0, iy1 = gy * w - Y0 + 1, (gy + 1) * w - Y0
        values = np.full(len(gx), ABSENT, dtype=np.int64)
        refine: list[int] = []
        for cell, polys, single in grouped(
            *owned_pairs(polygons, ix0, iy0, ix1, iy1), data.poly_zone_ids
        ):
            if single >= 0:
                values[cell] = single
            elif level == levels:
                values[cell] = packer.list_value(polys)
            else:
                values[cell] = -(len(refine) + 2)
                refine.append(cell)
        arrays.append(values)
        if level < levels:
            cells = np.asarray(refine, dtype=np.int64)
            gx = (gx[cells, None] * k + dx[None, :]).reshape(-1)
            gy = (gy[cells, None] * k + dy[None, :]).reshape(-1)

    def narrow(values: np.ndarray) -> np.ndarray:
        dtype = (
            np.int16 if values.min(initial=0) >= np.iinfo(np.int16).min else np.int32
        )
        array = values.astype(dtype)
        array.flags.writeable = False
        return array

    bounds, payload, last = packer.arrays()
    cls = {1: GridTree1, 2: GridTree2}[levels]
    tree = cls(narrow(arrays[0]), no_blocks(), bounds[:-1], bounds[1:], last, payload)
    tree.name = name
    tree.family = "grid tree"
    tree.params = {
        "root_deg": 360 / root_columns,
        "block": f"{k}x{k}",
        "levels": levels,
        "finest_deg": 360 / (root_columns * k**levels),
    }
    tree.k, tree.km, tree.kk, tree.levels = k, k - 1, k * k, levels
    tree.columns = root_columns
    tree.widths = widths
    tree.w0, tree.w1 = widths[0], widths[1]
    tree.w2 = widths[2] if levels >= 2 else 0
    tree._block_arrays = [narrow(a) for a in arrays[1:]]
    views = [memoryview(a) for a in tree._block_arrays] + [None]
    tree.b1, tree.b2 = views[0], views[1]
    return tree


# --- the query path, with a candidate index in the shipped one's place ----------------
#
# A candidate subclasses ``ShortcutIndex`` and overrides ``entry_at`` and ``entries_at``,
# the two methods the lookups call to turn a coordinate into a stored value, so it
# answers through the unmodified ``TimezoneFinder``. Only those two are replaced: a
# candidate answers nothing else a finder can be asked, which is why the finder is
# never asked for anything else here.


@contextmanager
def bound(path: str) -> Iterator[None]:
    previous = (utils.inside_polygon_packed, utils.packed_buffers)
    utils.inside_polygon_packed = PACKED_ACCELERATION_IMPLEMENTATIONS[path]
    utils.packed_buffers = PACKED_BUFFER_FACTORIES[path]
    try:
        yield
    finally:
        utils.inside_polygon_packed, utils.packed_buffers = previous


def finder_on(path: str, index=None) -> TimezoneFinder:
    with bound(path):
        finder = TimezoneFinder(in_memory=False)
    if index is not None:
        finder.shortcuts = index
    return finder


# --- instruments ----------------------------------------------------------------------


def work_counts(
    finder: TimezoneFinder, index, points: Sequence[tuple[float, float]]
) -> dict[str, float]:
    """The exact counts, and how often ``TimezoneFinderL`` on this index is right.

    Answered without geometry, candidates offered, polygons tested by the full lookup;
    and the share of points where the lightweight finder's answer - a unique cell's zone,
    else the cell's untested final zone - equals the full lookup's.
    """
    unique = offered = tested = lite_right = 0
    zone_ids = finder.zone_ids
    for lng, lat in points:
        entry = index.entry_at(lng, lat)
        if entry >= 0:
            unique += 1
            lite_right += 1
            continue
        if entry == ABSENT:
            continue
        candidates = index.candidates_of(entry).tolist()
        stop = index.stop_index_of(entry)
        offered += len(candidates)
        x, y = utils.query2int(lng, lat)
        answer = candidates[-1]
        for i, boundary_id in enumerate(candidates):
            if i >= stop:
                break
            tested += 1
            if finder.inside_of_polygon(boundary_id, x, y):
                answer = boundary_id
                break
        lite_right += int(zone_ids[answer]) == int(zone_ids[candidates[-1]])
    n = len(points)
    return {
        "points": n,
        "unique_share": unique / n,
        "candidates_per_query": offered / n,
        "tests_per_query": tested / n,
        "lite_agreement": lite_right / n,
    }


def zone_contains(finder: TimezoneFinder, zone_id: int, x: int, y: int) -> bool:
    return any(
        finder.inside_of_polygon(boundary_id, x, y)
        for boundary_id in finder._iter_boundary_ids_of_zone(zone_id)
    )


def gate(
    control: TimezoneFinder,
    candidate: TimezoneFinder,
    points: Sequence[tuple[float, float]],
) -> dict[str, int]:
    """Compare every answer with the control's and classify each disagreement.

    ``overlap``: both answers' zones contain the point - precedence among overlapping
    zones, which any index may order differently. ``uncovered``: no zone contains the
    point (a sliver between neighbouring stored boundaries), so both answers are the
    "last remaining zone" fallback. Containment is tested at the point the lookup tests,
    ``utils.query2int``'s, so a -180 meridian point answered from the wrong column is a
    ``defect`` rather than ``uncovered``. ``control_wrong``: only the candidate's zone contains it.
    ``defect``: some zone contains the point and the candidate's does not.
    ``scalar_differs``: the candidate's ``timezone_at`` disagrees with its own batch
    answer, which would leave the scalar timing measuring an unverified path.
    """
    lngs = np.asarray([p[0] for p in points], dtype=np.float64)
    lats = np.asarray([p[1] for p in points], dtype=np.float64)
    expected = control.timezone_ids_at(lngs=lngs, lats=lats)
    actual = candidate.timezone_ids_at(lngs=lngs, lats=lats)
    names = candidate.zone_names.names
    scalar_differs = sum(
        candidate.timezone_at(lng=lng, lat=lat) != names[zone]
        for lng, lat, zone in zip(
            lngs.tolist(), lats.tolist(), actual.tolist(), strict=True
        )
    )
    classes = {
        "points": len(points),
        "overlap": 0,
        "uncovered": 0,
        "control_wrong": 0,
        "defect": 0,
        "scalar_differs": scalar_differs,
    }
    for i in np.flatnonzero(expected != actual).tolist():
        if expected[i] < 0 or actual[i] < 0:
            classes["defect"] += 1
            continue
        x, y = utils.query2int(lngs[i], lats[i])
        in_expected = zone_contains(control, int(expected[i]), x, y)
        in_actual = zone_contains(control, int(actual[i]), x, y)
        if in_expected and in_actual:
            classes["overlap"] += 1
        elif in_actual:
            classes["control_wrong"] += 1
        elif in_expected:
            classes["defect"] += 1
        elif any(
            control.inside_of_polygon(b, x, y) for b in range(len(control.boundaries))
        ):
            classes["defect"] += 1
        else:
            classes["uncovered"] += 1
    return classes


def float_for(value: int) -> float | None:
    """A float coordinate the query truncates to exactly ``value``."""
    f = value / F
    for _ in range(4):
        got = int(f * F)
        if got == value:
            return f
        f = math.nextafter(f, math.inf if got < value else -math.inf)
    return None


def probes(
    on_edges: list[tuple[int, int]], vertical: list[bool]
) -> list[tuple[float, float]]:
    """Each edge point, and its neighbours one unit across the edge, as query floats."""
    points = []
    for (x, y), is_vertical in zip(on_edges, vertical, strict=True):
        for offset in (-1, 0, 1):
            px, py = (x + offset, y) if is_vertical else (x, y + offset)
            if -X0 <= px <= X0 and -Y0 <= py <= Y0:
                lng, lat = float_for(px), float_for(py)
                if lng is not None and lat is not None:
                    points.append((lng, lat))
    return points


def edge_probes(
    index, count: int, rng: np.random.Generator
) -> list[tuple[float, float]]:
    on_edges = index.edge_points(rng, count // 3)
    # edge_points lists vertical-edge points first, then horizontal ones, half each
    half = len(on_edges) // 2
    return probes(on_edges, [i < half for i in range(len(on_edges))])


def border_probes(count: int, rng: np.random.Generator) -> list[tuple[float, float]]:
    """Points on lines real borders follow: 7.5-degree ocean meridians, whole degrees."""
    meridians = np.array(
        [OCEAN_MERIDIAN * k for k in range(-24, 25)]
        + [DEGREE * k for k in range(-180, 181)]
    )
    parallels = np.array([DEGREE * k for k in range(-90, 91)])
    n = count // 6
    on_edges = [
        (int(x), int(rng.integers(-Y0, Y0 + 1))) for x in rng.choice(meridians, n)
    ] + [(int(rng.integers(-X0, X0 + 1)), int(y)) for y in rng.choice(parallels, n)]
    return probes(on_edges, [True] * n + [False] * n)


def scalar_call(finder) -> Callable[[tuple[float, float]], object]:
    return lambda point: finder.timezone_at(lng=point[0], lat=point[1])


def batch_call(finder) -> Callable[[tuple[np.ndarray, np.ndarray]], object]:
    return lambda batch: finder.timezone_ids_at(lngs=batch[0], lats=batch[1])


def batches(points, size: int = 256) -> list[tuple[np.ndarray, np.ndarray]]:
    return [
        (
            np.asarray([p[0] for p in points[i : i + size]], dtype=np.float64),
            np.asarray([p[1] for p in points[i : i + size]], dtype=np.float64),
        )
        for i in range(0, len(points), size)
    ]


def comparison(result: CandidateComparison) -> dict[str, object]:
    return {**asdict(result), "verdict": result.verdict}


def cpu_name() -> str:
    """The CPU model, which ``platform.processor()`` reduces to ``x86_64`` on Linux."""
    return str(cpu_info().get("brand_raw") or platform.processor() or "unknown")


# --- the sweep ------------------------------------------------------------------------


def allowed_counts(multiple_of: int, exclude_factor: int | None) -> list[int]:
    counts = [
        c
        for c in range(1, 8000)
        if X_SPAN % c == 0
        and c % multiple_of == 0
        and (exclude_factor is None or c % exclude_factor)
    ]
    return counts


def equal_area_counts(rows: int, aligned: bool) -> list[int]:
    allowed = allowed_counts(48, None) if aligned else allowed_counts(1, 3)
    height = 180.0 / rows
    counts = []
    for r in range(rows):
        lat = -90.0 + (r + 0.5) * height
        ideal = 360.0 * math.cos(math.radians(lat)) / height
        counts.append(min(allowed, key=lambda c: (abs(math.log(c / ideal)), c)))
    return counts


# Only designs whose index binary falls in this window are compared: the cap is the
# project's (contributing/project/project-purpose-runtime-constraints-and-non-goals.md),
# and a design above it is refused whatever it measures, while one far below it trades
# away selectivity the cap would pay for. The specs below are the shapes that land in it
# on the packaged data; a data change that moves one out drops it from the sweep, which
# the report's ``outside_budget`` lists rather than comparing it unfairly.
INDEX_BUDGET_BYTES = (400_000, 800_000)
EQUAL_ANGLE = (
    # width (degrees), what it aligns with
    ("0.5", "7.5-degree and whole-degree"),
    ("0.48", "neither"),
    ("0.46875", "7.5-degree"),
    ("0.45", "neither"),
)
# the exact rule's control: the same cells, every polygon meeting the closed cell
TOUCHING = ("equal_angle_0_5deg", "equal_area_0_375deg_aligned")
EQUAL_AREA = (
    # row height (degrees), columns a multiple of 48 (7.5-degree aligned) or not
    ("0.46875", True),
    ("0.375", True),
    ("0.375", False),
)
GRID_TREES = (
    # root columns (360 / root degrees), block side k, levels below the root. Only the
    # two shapes the budget admits; sweeping tree configurations is its own study.
    (384, 2, 2),
    (384, 4, 1),
)


def within_budget(index, outside: list[dict]) -> bool:
    """Whether ``index`` is in the compared size window; records it in ``outside`` if not."""
    low, high = INDEX_BUDGET_BYTES
    if low <= index.payload_bytes <= high:
        return True
    outside.append({"name": index.name, "payload_bytes": index.payload_bytes})
    print(f"skipped {index.name}: {index.payload_bytes:,} B is outside the budget")
    return False


def build_sweep(polygons, data, only: list[str] | None, outside: list[dict]) -> list:
    def wanted(name: str) -> bool:
        return not only or any(o in name for o in only)

    indexes: list = []
    specs: dict[str, tuple] = {}
    for width, aligns in EQUAL_ANGLE:
        name = f"equal_angle_{width.replace('.', '_')}deg"
        # also built when only its touch-inclusive control is wanted
        if not (wanted(name) or wanted(f"{name}_touching")):
            continue
        columns = round(360 / float(width))
        rows = round(180 / float(width))
        started = time.perf_counter()
        grid = build_grid(
            name,
            "equal-angle grid",
            {"width_deg": float(width), "aligns_with": aligns},
            rows,
            [columns] * rows,
            polygons,
            data,
        )
        grid.params["build_seconds"] = round(time.perf_counter() - started, 1)
        specs[name] = (grid.family, grid.params, rows, [columns] * rows)
        print(f"built {name}: {grid.cells:,} cells", flush=True)
        if wanted(name) and within_budget(grid, outside):
            indexes.append(grid)
    for height, aligned in EQUAL_AREA:
        name = (
            f"equal_area_{height.replace('.', '_')}deg"
            f"{'_aligned' if aligned else '_unaligned'}"
        )
        if not (wanted(name) or wanted(f"{name}_touching")):
            continue
        rows = round(180 / float(height))
        started = time.perf_counter()
        params = {
            "row_height_deg": float(height),
            "aligns_with": "7.5-degree" if aligned else "neither",
        }
        counts = equal_area_counts(rows, aligned)
        grid = build_grid(
            name, "equal-area banded grid", params, rows, counts, polygons, data
        )
        grid.params["build_seconds"] = round(time.perf_counter() - started, 1)
        specs[name] = (grid.family, grid.params, rows, counts)
        print(f"built {name}: {grid.cells:,} cells", flush=True)
        if wanted(name) and within_budget(grid, outside):
            indexes.append(grid)
    for base in TOUCHING:
        name = f"{base}_touching"
        if base not in specs or not wanted(name):
            continue
        family, params, rows, counts = specs[base]
        control = build_grid(
            name,
            f"{family}, touch-inclusive control",
            {k: v for k, v in params.items() if k != "build_seconds"},
            rows,
            counts,
            polygons,
            data,
            touching=True,
        )
        print(f"built {name}: {control.cells:,} cells", flush=True)
        if within_budget(control, outside):
            indexes.append(control)
    for root_columns, k, levels in GRID_TREES:
        root = f"{360 / root_columns:g}".replace(".", "_")
        name = f"grid_tree_{root}deg_{k}x{k}_{levels}levels"
        if not wanted(name):
            continue
        started = time.perf_counter()
        tree = build_grid_tree(name, root_columns, k, levels, polygons, data)
        tree.params["build_seconds"] = round(time.perf_counter() - started, 1)
        print(
            f"built {name}: {tree.cells:,} root cells, blocks {tree.block_counts}",
            flush=True,
        )
        if within_budget(tree, outside):
            indexes.append(tree)
    return indexes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output", type=Path, help="the report, as JSON")
    parser.add_argument("--rounds", type=int, default=31)
    parser.add_argument("--points", type=int, default=2_000)
    parser.add_argument("--probes", type=int, default=6_000)
    parser.add_argument("--no-timing", action="store_true")
    parser.add_argument("--only", nargs="*", help="substrings of candidate names")
    args = parser.parse_args()

    started = time.perf_counter()
    rng = np.random.default_rng(2026)
    paths = ("clang", interpreted_path_name())
    reference = finder_on("clang")
    data = OrderingInput(
        reference.boundaries, reference.zone_ids, reference.zone_names.names
    )
    polygons = polygons_of(reference)
    fixtures = {label: load_benchmark_points(f) for label, f in STRATA.items()}

    shipped = reference.shortcuts
    shipped_file = get_shortcut_file_path(DEFAULT_DATA_DIR)
    model = (
        _HEADER_SIZE
        + shipped.table.nbytes
        + shipped.blocks.nbytes
        + entries_file_bytes(shipped)
    )
    if model != shipped_file.stat().st_size:
        raise AssertionError(
            f"file-size model {model} != shipped {shipped_file.stat().st_size}"
        )
    workdir = Path(tempfile.mkdtemp(prefix="latlng-index-"))
    mapping = {
        cell: value if isinstance(value, int) else legacy_order(data, value)
        for cell, value in shipped.items()
    }
    control_path = workdir / "shortcuts.bin"
    write_shortcuts_binary(
        build_shortcut_index(mapping, reference.zone_ids), control_path
    )
    control_index = read_shortcuts_binary(control_path)

    def shipped_row(index: ShortcutIndex, payload: int) -> dict:
        return {
            "cells": ROOT_CELLS + index.nr_of_blocks * BLOCK_CELLS,
            "blocks": index.nr_of_blocks,
            "payload_bytes": payload,
            "resident_bytes": index.table.nbytes
            + index.blocks.nbytes
            + entries_resident_bytes(index),
            "strata": {
                label: work_counts(reference, index, points)
                for label, points in fixtures.items()
            },
        }

    report: dict[str, object] = {
        "schema": 3,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "command": "uv run python -m prototypes.latlng_index_bench "
        + " ".join(sys.argv[1:]),
        "environment": {
            "python": platform.python_version(),
            "machine": platform.machine(),
            "system": platform.system(),
            "cpu": cpu_name(),
            "logical_cpus": os.cpu_count(),
            "versions": {name: version(name) for name in ("numpy", "shapely", "numba")},
            "paths": list(paths),
            "commit": subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
            ).stdout.strip(),
            # the branch commit disappears in a squash merge; its master base does not
            "base_commit": subprocess.run(
                ["git", "merge-base", "HEAD", "origin/master"],
                capture_output=True,
                text=True,
            ).stdout.strip()[:8],
            "fixture": benchmark_fixture_provenance(),
        },
        "file_size_model": {"shipped_bytes": model, "reproduces_shipped_file": True},
        "shipped": shipped_row(shipped, model),
        "control": shipped_row(control_index, control_path.stat().st_size),
        "candidates": {},
    }
    control_finder = finder_on("clang", control_index)
    report["control"]["gate_against_shipped"] = gate(
        reference,
        control_finder,
        [p for points in fixtures.values() for p in points],
    )
    control_finder.cleanup()
    print("shipped and control rows done", flush=True)

    report["index_budget_bytes"] = list(INDEX_BUDGET_BYTES)
    report["outside_budget"] = []
    indexes = build_sweep(polygons, data, args.only, report["outside_budget"])
    shared_probes = border_probes(args.probes, rng)
    malacca_x = utils.coord2int(MALACCA_WITNESS[0])
    malacca_y = utils.coord2int(MALACCA_WITNESS[1])
    malacca_polygons = {
        b
        for b in range(len(reference.boundaries))
        if reference.inside_of_polygon(b, malacca_x, malacca_y)
    }
    for index in indexes:
        row: dict[str, object] = {
            "family": index.family,
            "params": index.params,
            "cells": index.cells,
            "payload_bytes": index.payload_bytes,
            "resident_bytes": index.resident_bytes,
            "strata": {
                label: work_counts(reference, index, points)
                for label, points in fixtures.items()
            },
        }
        entry = index.entry_at(*MALACCA_WITNESS)
        offered = set(index.candidates_of(entry).tolist()) if entry < ABSENT else set()
        row["malacca_witness_offered"] = bool(
            (
                entry >= 0
                and entry in {int(reference.zone_ids[b]) for b in malacca_polygons}
            )
            or offered & malacca_polygons
        )
        own_probes = edge_probes(index, args.probes, rng)
        row["gate"] = {}
        for path in paths:
            control = finder_on(path, control_index)
            candidate = finder_on(path, index)
            try:
                row["gate"][path] = {
                    "fixtures": gate(
                        control,
                        candidate,
                        [p for points in fixtures.values() for p in points],
                    ),
                    "own_cell_edges": gate(control, candidate, own_probes),
                    "border_lines": gate(control, candidate, shared_probes),
                }
            finally:
                control.cleanup()
                candidate.cleanup()
        report["candidates"][index.name] = row
        print(f"priced {index.name}", flush=True)

    if not args.no_timing:
        timed = [
            index
            for index in indexes
            if report["candidates"][index.name]["malacca_witness_offered"]
            and all(
                checks[probe]["defect"] == checks[probe]["scalar_differs"] == 0
                for checks in report["candidates"][index.name]["gate"].values()
                for probe in checks
            )
        ]
        report["timing"] = {}
        for path in paths:
            print(f"timing on {path} ...", flush=True)
            control = finder_on(path, control_index)
            shipped_finder = finder_on(path)
            try:
                rows = {}
                for name, index in [("shipped", None)] + [(i.name, i) for i in timed]:
                    finder = shipped_finder if index is None else finder_on(path, index)
                    rows[name] = {}
                    for label in RANKING_STRATA:
                        points = fixtures[label][: args.points]
                        scalar = compare_candidates(
                            ("control", scalar_call(control)),
                            (name, scalar_call(finder)),
                            points,
                            rounds=args.rounds,
                            batch_size=len(points),
                        )
                        batch_inputs = batches(points)
                        batch = compare_candidates(
                            ("control", batch_call(control)),
                            (name, batch_call(finder)),
                            batch_inputs,
                            rounds=args.rounds,
                            batch_size=min(len(batch_inputs), 8),
                        )
                        rows[name][label] = {
                            "scalar": comparison(scalar),
                            "batch_256": comparison(batch),
                        }
                    if name != "shipped":
                        finder.cleanup()
                    print(f"  timed {name}", flush=True)
                report["timing"][path] = rows
            finally:
                control.cleanup()
                shipped_finder.cleanup()
        by_name = {index.name: index for index in timed}
        report["head_to_head"] = {}
        for path in paths:
            pairs = {}
            for challenger, baseline in HEAD_TO_HEAD:
                if challenger not in by_name or baseline not in by_name:
                    continue
                a = finder_on(path, by_name[challenger])
                base = finder_on(path, by_name[baseline])
                result = {}
                for label in RANKING_STRATA:
                    points = fixtures[label][: args.points]
                    scalar = compare_candidates(
                        (baseline, scalar_call(base)),
                        (challenger, scalar_call(a)),
                        points,
                        rounds=args.rounds,
                        batch_size=len(points),
                    )
                    batch_inputs = batches(points)
                    batch = compare_candidates(
                        (baseline, batch_call(base)),
                        (challenger, batch_call(a)),
                        batch_inputs,
                        rounds=args.rounds,
                        batch_size=min(len(batch_inputs), 8),
                    )
                    result[label] = {
                        "scalar": comparison(scalar),
                        "batch_256": comparison(batch),
                    }
                pairs[f"{challenger} vs {baseline}"] = result
                a.cleanup()
                base.cleanup()
            report["head_to_head"][path] = pairs

    report["elapsed_seconds"] = round(time.perf_counter() - started, 1)
    rendered = json.dumps(report, indent=1) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
        print(f"wrote {args.output}")
    else:
        print(rendered)
    reference.cleanup()


if __name__ == "__main__":
    main()
