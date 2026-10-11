#!/usr/bin/env python3

"""Price longitude/latitude-aligned shortcut indexes against the shipped H3 index.

FINDINGS (2026-10-11, Apple M1 Pro, Python 3.14.2, data 2026d, fixture set v3)
==============================================================================

**A dense grid aligned with longitude and latitude beats the resolution-4 H3 index at
H3's file size on every axis measured here.** Against an H3 control ordered by the same
converter rule, the equal-area grid of 0.375-degree rows whose columns divide 7.5 degrees
(296,832 cells; 616 KB on disk against H3's 610-617 KB, 619 KB of index arrays resident
against 1,024 KB) answers 92.2 % of random and 82.2 % of on-land queries without
geometry (H3 89.4 / 81.2 %), tests 26 % and 6 % fewer polygons per query, and agrees
with the full lookup as ``TimezoneFinderL`` on 96.2 / 90.4 % of points (shipped H3
95.8 / 90.0 %). Whole ``timezone_at`` calls are 25 % faster on random points and 17-18 %
on land, 256-point ``timezone_ids_at`` batches 64-67 % and 46-50 %, every round won on
clang and numba alike. The equal-angle 0.46875-degree grid at the same size is a point
or two faster per random scalar call, since it reads no per-row table, level on land,
and less selective there. The scalar win is the removed ``h3.latlng_to_cell`` call; the
batch win is that a grid cell vectorises and an H3 cell does not.

**What makes it work is exactness, then alignment.** Cells follow the kernel's own
edge rule (a polygon owns its east and north boundary, never its west or south), so a
zone across a cell edge is not a candidate. Against the same control in this run, the
same 0.5-degree grid counting every polygon that touches a cell edge tests 50 % more
polygons per random query and gives up about 8 points of random scalar speed (under 2
on land); its counts equal those of a 2026-09-26
run that used such cells and judged the grid slower than H3, a timing taken with a
per-row lookup and never paired with a control. Alignment pays most on the ocean
meridians: unaligned grids of the same size test 14-24 % more polygons per random query.

**What does not carry.** Quadtrees - ``node-geo-tz``'s world quadrants and a
7.5-degree-rooted variant - buy the most selectivity per byte (the rooted one at depth 5
tests 57 / 42 % fewer polygons at 757 KB), but their leaf search is a ``bisect`` that
costs more than the H3 call it replaces: scalar calls 6-51 % slower, batches 28-74 %
faster. ``tzf-rs``'s tile pyramid probes one binary search per zoom and is 2.3-2.7x
slower per scalar call; its Mercator edges cannot follow the integer grid either. The
item's two-tier split is dominated by the grid it splits: larger, and a third more
polygons tested (counted, not timed). Grids larger than H3's file win more - the
equal-angle 0.375-degree grid is 30 % faster per random scalar call at 943 KB on disk
and 943 KB resident - and whether H3's footprint bounds disk or memory is IDX-2's call.

**Correctness.** All 27 gated grids, quadtrees, pyramids and controls gave the control's
answer for the 30,000 fixture points (289 of them in two overlapping zones), for points
on and one unit either side of their own cell edges, and on the 7.5-degree and
whole-degree lines borders follow, on both kernels, through both the scalar and the
batch path. The only disagreements are points on the -180 meridian and the -90
parallel, which no polygon owns, so both indexes answer the "last remaining zone"
fallback there. Every candidate offers the Strait of Malacca witness's polygon. The
verdict, with what it trades away and leaves unpriced, is in
``contributing/improvements/decisions/shortcut-index-cell-shape-and-resolution-decisions.md``;
the compact numbers are ``contributing/improvements/measurements/latlng-index-2026-10-11.json``.

METHOD
======

Every candidate is compiled from the packaged boundaries and answers through the real
``TimezoneFinder`` query path: :class:`IndexFinder` replaces only the two H3 lines of
``timezone_at`` and of the batch prologue with the candidate's cell lookup, and inherits
everything else, including the candidate loop and its stop index.

What makes the comparison fair, and why each choice was made:

* **One ordering policy for every index, the converter's own.** Candidate lists are
  ordered by ``scripts.shortcuts.optimise_shortcut_ordering`` itself (zone vertex totals,
  ties by timezone identifier), called on a sorted input, never by a copy of it. The
  shipped H3 index additionally carries the converter's geometric work optimizer, which
  is H3-specific, so it is **not** the baseline: the baseline is an **H3 control** that is
  the shipped candidate sets re-ordered by that same policy and written and read back
  through the real shortcut file functions. The shipped index is measured against the
  control separately, which states what the work optimizer adds and therefore what a
  grid would still have to gain from a port of it.
* **Cells are exact, not padded.** A cell is computed from the same truncated integer
  coordinates the point-in-polygon kernel reads, and owns its east and north edges,
  because that is the kernel's own convention: a point on a shared vertical edge is
  inside the polygon to its west, on a shared horizontal edge inside the one to its
  south, and no polygon ever contains a point on its own south or west boundary. A
  polygon is a candidate of a cell only if it can own one of the cell's integer points,
  which reduces to an interior intersection with the cell's box shifted half a unit
  south-west. So a cell bordered by an ocean meridian or a surveyed parallel is not made
  ambiguous by the zone on the far side of that line, which is the whole value of
  aligning an index with longitude and latitude. The boundary probes in the correctness
  gate test exactly this claim, on both kernels.
* **Sizes are the shipped layout's.** One ``int16`` per cell, distinct candidate lists
  once each in the narrowest offset and stop-index widths, and the 40-byte header: the
  same arithmetic reproduces the shipped ``shortcuts.bin`` to the byte before any
  candidate is priced. H3 stores ``122 * 7**4`` cells on disk and ``122 * 8**4`` resident;
  a dense grid stores the same cells in both, so a grid with H3's cell count is H3's
  file size at about half its resident table.
* **Each lookup is the cheapest correct form of its own structure** in this Python
  reader: grids are integer arithmetic and one table read; sparse structures probe a
  ``memoryview`` with ``bisect``, the mapped-capable form (a scalar ``np.searchsorted``
  costs tens of microseconds and a Python list is not mapped). Batches are vectorised
  for every candidate, never a per-point loop.
* **The family is swept, not one point.** Equal-angle grids, equal-area banded grids,
  the quadtree ``node-geo-tz`` uses (world quadrants, subdivided to a depth), the same
  quadtree under 7.5-degree root cells, grid trees (an aligned dense grid whose
  ambiguous cells refine into fixed blocks, addressed by arithmetic at every level, added
  at the maintainer's request), and ``tzf-rs``'s preindex (exact Web Mercator
  tiles at zooms 3-10 probed coarsest first, over a 1-degree candidate grid), at several
  sizes each, plus the item's two-tier split. Alignment is a parameter of the sweep:
  7.5-degree columns follow the ocean zones' meridians, whole degrees follow many
  surveyed land borders, and the controls follow neither.

What it does not do: certify coverage beyond the sampled gate; time a native reader for
the sparse structures (their Python probe cost is the cost this package would pay); time
``TimezoneFinderL`` (its agreement with the full lookup is counted); or measure loading,
construction or ``make memory``.
"""

import argparse
import bisect
import json
import math
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
from h3.api import numpy_int as h3
from shapely import STRtree

from benchmarks.candidate_comparison import CandidateComparison, compare_candidates
from scripts.assert_acceleration_path import (
    PACKED_ACCELERATION_IMPLEMENTATIONS,
    PACKED_BUFFER_FACTORIES,
    interpreted_path_name,
)
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
from timezonefinder.configs import (
    COORD2INT_FACTOR,
    DEFAULT_DATA_DIR,
    NO_ZONE_ID,
    SHORTCUT_H3_RES,
    ZONE_ID_RESULT_DTYPE,
)
from timezonefinder.shortcut_index import (
    _HEADER_SIZE,
    ABSENT,
    COMPACT_TABLE_SIZE,
    PAYLOAD_DTYPE,
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
    # H3 classifications: correctness probes only, since a different index re-labels
    # their points (the resolution decision's caveat). Only random and on_land rank.
    "h3_unique": UNIQUE_SHORTCUT_POINTS_FIXTURE,
    "h3_ambiguous": AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
}
RANKING_STRATA = ("random", "on_land")
# Pairs timed against each other rather than each against the H3 control, for the
# claims a recommendation makes between two candidates: (challenger, baseline).
HEAD_TO_HEAD = (
    ("grid_tree_0_9375deg_4x4_1levels", "equal_area_0_375deg_aligned"),
    ("grid_tree_0_9375deg_4x4_1levels", "grid_tree_0_9375deg_2x2_2levels"),
)
MALACCA_WITNESS = (100.3055, 3.4804)
WEB_MERCATOR_LIMIT = 85.0511287798066

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
MISS = -2  # two-tier exact layer: "ask the fallback"


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

    def cell_entry(self, lng: float, lat: float) -> int:
        row = (int(lat * F) + KY) // self.row_height
        if row < 0:
            row = 0
        col = (int(lng * F) + KX) // self.widths[row]
        if col < 0:
            col = 0
        return int(self.table[self.offsets[row] + col])

    def cell_entries(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        rows = ((lats * F).astype(np.int64) + KY) // self.row_height
        np.maximum(rows, 0, out=rows)
        cols = ((lngs * F).astype(np.int64) + KX) // self._widths_array[rows]
        np.maximum(cols, 0, out=cols)
        return self.table[self._offsets_array[rows] + cols]

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

    def cell_entry(self, lng: float, lat: float) -> int:
        row = (int(lat * F) + KY) // self.row_height
        col = (int(lng * F) + KX) // self.width
        if row < 0:
            row = 0
        if col < 0:
            col = 0
        return int(self.table[row * self.columns + col])

    def cell_entries(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        rows = ((lats * F).astype(np.int64) + KY) // self.row_height
        np.maximum(rows, 0, out=rows)
        cols = ((lngs * F).astype(np.int64) + KX) // self.width
        np.maximum(cols, 0, out=cols)
        return self.table[rows * self.columns + cols]


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
    index = cls(table_value(values), bounds[:-1], bounds[1:], last, payload)
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


class LinearQuadtree(ShortcutIndex):
    """A quadtree under a grid of root cells, its leaves one sorted array of keys.

    A leaf at any depth covers a contiguous run of Morton codes at the maximum depth, so
    the leaves of a root partition its code range and one ``bisect`` finds the leaf. The
    key is ``root << 2 * depth | code``; ``directory`` gives each root's leaf range, and
    a root that is a single leaf - most of the ocean - needs no search at all. ``table``
    holds one value per leaf, in the H3 table's tri-state.
    """

    __slots__ = (
        "name",
        "family",
        "params",
        "roots_x",
        "depth",
        "nx",
        "ny",
        "keys",
        "_keys_view",
        "_directory",
        "_directory_array",
        "_spread",
        "_spread_array",
        "_mask",
    )

    def cell_entry(self, lng: float, lat: float) -> int:
        col = ((int(lng * F) + X0) * self.nx - 1) // X_SPAN
        row = ((int(lat * F) + Y0) * self.ny - 1) // Y_SPAN
        if col < 0:
            col = 0
        if row < 0:
            row = 0
        depth = self.depth
        root = (row >> depth) * self.roots_x + (col >> depth)
        lo = self._directory[root]
        hi = self._directory[root + 1]
        if hi - lo == 1:
            return int(self.table[lo])
        mask = self._mask
        spread = self._spread
        key = (root << (2 * depth)) | spread[col & mask] | (spread[row & mask] << 1)
        return int(self.table[bisect.bisect_right(self._keys_view, key, lo, hi) - 1])

    def cell_entries(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        cols = (((lngs * F).astype(np.int64) + X0) * self.nx - 1) // X_SPAN
        rows = (((lats * F).astype(np.int64) + Y0) * self.ny - 1) // Y_SPAN
        np.maximum(cols, 0, out=cols)
        np.maximum(rows, 0, out=rows)
        depth = self.depth
        roots = (rows >> depth) * self.roots_x + (cols >> depth)
        keys = (
            (roots << (2 * depth))
            | self._spread_array[cols & self._mask]
            | (self._spread_array[rows & self._mask] << 1)
        )
        leaves = np.searchsorted(self.keys, keys.astype(self.keys.dtype), "right") - 1
        return self.table[leaves]

    @property
    def cells(self) -> int:
        return len(self.table)

    @property
    def payload_bytes(self) -> int:
        return (
            _HEADER_SIZE
            + self.table.nbytes
            + self.keys.nbytes
            + self._directory_array.nbytes
            + entries_file_bytes(self)
        )

    @property
    def resident_bytes(self) -> int:
        return (
            self.table.nbytes
            + self.keys.nbytes
            + self._directory_array.nbytes
            + self._spread_array.nbytes
            + entries_resident_bytes(self)
        )

    def edge_points(
        self, rng: np.random.Generator, count: int
    ) -> list[tuple[int, int]]:
        """Integer points on the edges of randomly chosen leaves (any leaf, any depth)."""
        first_x, last_x = ranges(self.nx, X_SPAN, X0)
        first_y, last_y = ranges(self.ny, Y_SPAN, Y0)
        keys = self.keys.astype(np.int64)
        points = []
        for leaf in rng.integers(0, len(keys), count // 2).tolist():
            root, code = divmod(int(keys[leaf]), 1 << (2 * self.depth))
            col = row = 0
            for bit in range(self.depth):
                col |= ((code >> (2 * bit)) & 1) << bit
                row |= ((code >> (2 * bit + 1)) & 1) << bit
            col += (root % self.roots_x) << self.depth
            row += (root // self.roots_x) << self.depth
            # the leaf's south-west depth-D cell: probe its west and south edges
            points.append(
                (
                    int(first_x[col]) - 1,
                    int(rng.integers(first_y[row], last_y[row] + 1)),
                )
            )
            points.append(
                (
                    int(rng.integers(first_x[col], last_x[col] + 1)),
                    int(first_y[row]) - 1,
                )
            )
        return points


def _spread_bits(depth: int) -> np.ndarray:
    """Each ``depth``-bit value with a zero bit after every bit: half a Morton code."""
    values = np.arange(1 << depth, dtype=np.int64)
    spread = np.zeros_like(values)
    for bit in range(depth):
        spread |= ((values >> bit) & 1) << (2 * bit)
    return spread.astype(np.uint32)


def build_quadtree(
    name: str,
    family: str,
    roots_x: int,
    roots_y: int,
    depth: int,
    polygons: np.ndarray,
    data: OrderingInput,
) -> LinearQuadtree:
    """Subdivide a node while it has candidates from several zones that it can separate.

    A node is a leaf when one zone (or none) can own its points, when every candidate
    covers the whole node - an overlap no subdivision can resolve - or at ``depth``.
    """
    spread = _spread_bits(depth)
    packer = EntryPacker(data)
    leaf_keys: list[int] = []
    leaf_values: list[int] = []
    gx = np.repeat(np.arange(roots_x, dtype=np.int64), roots_y)
    gy = np.tile(np.arange(roots_y, dtype=np.int64), roots_x)
    for level in range(depth + 1):
        nx = roots_x << level
        ny = roots_y << level
        first_x, last_x = ranges(nx, X_SPAN, X0)
        first_y, last_y = ranges(ny, Y_SPAN, Y0)
        ix0, ix1 = first_x[gx], last_x[gx]
        iy0, iy1 = first_y[gy], last_y[gy]
        cell_idx, poly_idx = owned_pairs(polygons, ix0, iy0, ix1, iy1)
        split = np.zeros(len(gx), dtype=bool)
        values = np.full(len(gx), ABSENT, dtype=np.int64)
        multi: dict[int, np.ndarray] = {}
        for cell, polys, single in grouped(cell_idx, poly_idx, data.poly_zone_ids):
            if single >= 0:
                values[cell] = single
            else:
                multi[cell] = polys
        if multi and level < depth:
            cells = np.fromiter(multi, dtype=np.int64, count=len(multi))
            lengths = [len(multi[c]) for c in cells.tolist()]
            pair_cells = np.repeat(cells, lengths)
            pair_polys = np.concatenate([multi[c] for c in cells.tolist()])
            boxes = shapely.box(ix0 - 0.5, iy0 - 0.5, ix1, iy1)
            covers = shapely.covers(polygons[pair_polys], boxes[pair_cells])
            all_cover = np.logical_and.reduceat(
                covers, np.r_[0, np.cumsum(lengths)[:-1]]
            )
            split[cells[~all_cover]] = True
        for cell, polys in multi.items():
            if not split[cell]:
                values[cell] = packer.list_value(polys)
        shift = depth - level
        for cell in np.flatnonzero(~split).tolist():
            col = int(gx[cell]) << shift
            row = int(gy[cell]) << shift
            root = (row >> depth) * roots_x + (col >> depth)
            mask = (1 << depth) - 1
            code = int(spread[col & mask]) | (int(spread[row & mask]) << 1)
            leaf_keys.append((root << (2 * depth)) | code)
            leaf_values.append(int(values[cell]))
        children_x = gx[split]
        children_y = gy[split]
        gx = np.concatenate([2 * children_x + dx for dx in (0, 1) for _ in (0, 1)])
        gy = np.concatenate([2 * children_y + dy for _ in (0, 1) for dy in (0, 1)])
    order = np.argsort(leaf_keys, kind="stable")
    keys = np.asarray(leaf_keys, dtype=np.int64)[order]
    key_dtype = narrowest_dtype_for(int(keys[-1]), what="leaf key")
    keys = keys.astype(key_dtype)
    table = table_value(np.asarray(leaf_values, dtype=np.int64)[order])
    roots = (keys.astype(np.int64) >> (2 * depth)).astype(np.int64)
    directory = np.searchsorted(roots, np.arange(roots_x * roots_y + 1)).astype(
        np.uint32
    )
    bounds, payload, last = packer.arrays()
    index = LinearQuadtree(table, bounds[:-1], bounds[1:], last, payload)
    index.name = name
    index.family = family
    index.params = {"roots": [roots_x, roots_y], "depth": depth}
    index.roots_x = roots_x
    index.depth = depth
    index.nx = roots_x << depth
    index.ny = roots_y << depth
    keys.flags.writeable = False
    index.keys = keys
    index._keys_view = memoryview(keys)
    for array in (directory, spread):
        array.flags.writeable = False
    index._directory = memoryview(directory)
    index._directory_array = directory
    index._spread = memoryview(spread)
    index._spread_array = spread
    index._mask = (1 << depth) - 1
    return index


class GridTree(ShortcutIndex):
    """A dense aligned grid whose ambiguous cells refine into k x k child blocks.

    A quadtree with its top levels flattened into a grid and its lower levels reached by
    arithmetic rather than search. Level 0 is one ``int16`` per square root cell. A value
    below ``ABSENT`` above the last level is the index of a block of k x k children on the
    next level, one per cell any two zones can own; on the last level it is a candidate
    list entry, the shipped tri-state. Every level is a whole number of coordinate units
    wide, so a level's cell is one floor division per axis, and clamping the shifted
    coordinate at 0 once covers -180 and -90 on every level.
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
        "w3",
        "b1",
        "b2",
        "b3",
        "widths",
        "_block_arrays",
    )

    def cell_entries(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        x = np.maximum((lngs * F).astype(np.int64) + KX, 0)
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
    def blocks(self) -> list[int]:
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

    def cell_entry(self, lng: float, lat: float) -> int:
        x = int(lng * F) + KX
        y = int(lat * F) + KY
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        w = self.w0
        v = int(self.table[(y // w) * self.columns + x // w])
        if v >= -1:
            return v
        w = self.w1
        km = self.km
        return self.b1[(-2 - v) * self.kk + ((y // w) & km) * self.k + ((x // w) & km)]


class GridTree2(GridTree):
    __slots__ = ()

    def cell_entry(self, lng: float, lat: float) -> int:
        x = int(lng * F) + KX
        y = int(lat * F) + KY
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        w = self.w0
        v = int(self.table[(y // w) * self.columns + x // w])
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


class GridTree3(GridTree):
    __slots__ = ()

    def cell_entry(self, lng: float, lat: float) -> int:
        x = int(lng * F) + KX
        y = int(lat * F) + KY
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        w = self.w0
        v = int(self.table[(y // w) * self.columns + x // w])
        if v >= -1:
            return v
        w = self.w1
        km = self.km
        k = self.k
        kk = self.kk
        v = self.b1[(-2 - v) * kk + ((y // w) & km) * k + ((x // w) & km)]
        if v >= -1:
            return v
        w = self.w2
        v = self.b2[(-2 - v) * kk + ((y // w) & km) * k + ((x // w) & km)]
        if v >= -1:
            return v
        w = self.w3
        return self.b3[(-2 - v) * kk + ((y // w) & km) * k + ((x // w) & km)]


def build_grid_tree(
    name: str,
    root_columns: int,
    k: int,
    levels: int,
    polygons: np.ndarray,
    data: OrderingInput,
) -> GridTree:
    """Evaluate level by level; refine every cell several zones can own, to ``levels``."""
    if k & (k - 1) or not 1 <= levels <= 3:
        raise ValueError(f"{name}: k must be a power of two and levels 1-3")
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
    cls = {1: GridTree1, 2: GridTree2, 3: GridTree3}[levels]
    tree = cls(narrow(arrays[0]), bounds[:-1], bounds[1:], last, payload)
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
    tree.w3 = widths[3] if levels >= 3 else 0
    tree._block_arrays = [narrow(a) for a in arrays[1:]]
    views = [memoryview(a) for a in tree._block_arrays] + [None, None]
    tree.b1, tree.b2, tree.b3 = views[0], views[1], views[2]
    return tree


class TilePyramid:
    """``tzf-rs``'s preindex: exact Web Mercator tiles probed coarsest first, then a grid.

    Its embedded finder's layout: one sorted key array, each zoom a contiguous range,
    one binary search per zoom until a hit. Tiles are found from the float coordinates
    as ``tzf``'s ``tile_xy`` does, so their edges cannot follow the integer grid and are
    built conservatively (padded two units, touching counts). Only exact tiles are kept;
    every miss and everything beyond the Mercator limit goes to the fallback grid, whose
    candidate lists are polygons owning a point of the cell - more selective than
    ``tzf``'s zones-by-bounding-box, which flatters the scheme.
    """

    def __init__(self, name, family, params, zooms, keys, values, fallback):
        self.name = name
        self.family = family
        self.params = params
        self.fallback = fallback
        self.max_zoom = zooms[-1]
        self.keys = keys
        self.values = values
        self._keys_view = memoryview(keys)
        self.bits = self.max_zoom
        self.levels = []
        for zoom in zooms:
            lo, hi = np.searchsorted(keys >> (2 * self.bits), [zoom, zoom + 1])
            self.levels.append((zoom, self.max_zoom - zoom, int(lo), int(hi)))
        # the slots TimezoneFinder reaches through `shortcuts`
        self.candidates_of = fallback.candidates_of
        self.stop_index_of = fallback.stop_index_of

    def _tile(self, lng: float, lat: float) -> tuple[int, int]:
        n = 1 << self.max_zoom
        tx = int((lng / 360.0 + 0.5) * n)
        if tx >= n:
            tx = n - 1
        siny = math.sin(lat * (math.pi / 180.0))
        ty = int((0.5 - math.log((1.0 + siny) / (1.0 - siny)) / (4.0 * math.pi)) * n)
        if ty >= n:
            ty = n - 1
        return tx, ty

    def cell_entry(self, lng: float, lat: float) -> int:
        if -WEB_MERCATOR_LIMIT <= lat <= WEB_MERCATOR_LIMIT:
            tx, ty = self._tile(lng, lat)
            keys = self._keys_view
            bits = self.bits
            for zoom, shift, lo, hi in self.levels:
                key = (zoom << (2 * bits)) | ((tx >> shift) << bits) | (ty >> shift)
                i = bisect.bisect_left(keys, key, lo, hi)
                if i < hi and keys[i] == key:
                    return int(self.values[i])
        return self.fallback.cell_entry(lng, lat)

    def cell_entries(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        out = self.fallback.cell_entries(lngs, lats).copy()
        inside = np.flatnonzero(np.abs(lats) <= WEB_MERCATOR_LIMIT)
        n = 1 << self.max_zoom
        tx = np.minimum(((lngs[inside] / 360.0 + 0.5) * n).astype(np.int64), n - 1)
        siny = np.sin(np.radians(lats[inside]))
        ty = ((0.5 - np.log((1.0 + siny) / (1.0 - siny)) / (4.0 * np.pi)) * n).astype(
            np.int64
        )
        np.clip(ty, 0, n - 1, out=ty)
        open_ = np.ones(len(inside), dtype=bool)
        for zoom, shift, lo, hi in self.levels:
            todo = np.flatnonzero(open_)
            if not len(todo) or lo == hi:
                continue
            bits = self.bits
            key = (
                (zoom << (2 * bits))
                | ((tx[todo] >> shift) << bits)
                | (ty[todo] >> shift)
            )
            level = self.keys[lo:hi]
            pos = np.searchsorted(level, key.astype(level.dtype))
            pos_c = np.minimum(pos, len(level) - 1)
            hit = level[pos_c] == key
            out[inside[todo[hit]]] = self.values[lo + pos_c[hit]]
            open_[todo[hit]] = False
        return out

    @property
    def cells(self) -> int:
        return len(self.keys)

    @property
    def payload_bytes(self) -> int:
        # narrowest form: the key fits uint32 (zoom 3-11 needs 26 bits) beside int16
        # values; tzf-rs's own file spends a uint64 key per tile
        return (
            len(self.keys) * (4 + 2)
            + 8 * len(self.levels)
            + self.fallback.payload_bytes
        )

    @property
    def tzf_layout_payload_bytes(self) -> int:
        return len(self.keys) * (8 + 2) + self.fallback.payload_bytes

    @property
    def resident_bytes(self) -> int:
        return self.keys.nbytes + self.values.nbytes + self.fallback.resident_bytes

    def edge_points(
        self, rng: np.random.Generator, count: int
    ) -> list[tuple[int, int]]:
        return self.fallback.edge_points(rng, count)


def build_pyramid(
    name: str,
    min_zoom: int,
    max_zoom: int,
    polygons: np.ndarray,
    data: OrderingInput,
    fallback: BandedGrid,
) -> TilePyramid:
    tiles = np.array(
        [(x, y) for x in range(1 << min_zoom) for y in range(1 << min_zoom)],
        dtype=np.int64,
    )
    keys: list[int] = []
    values: list[int] = []
    bits = max_zoom
    for zoom in range(min_zoom, max_zoom + 1):
        n = 1 << zoom
        x, y = tiles[:, 0], tiles[:, 1]
        west = (x / n * 360.0 - 180.0) * F
        east = ((x + 1) / n * 360.0 - 180.0) * F
        north = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * y / n)))) * F
        south = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * (y + 1) / n)))) * F
        boxes = shapely.box(west - 2, south - 2, east + 2, north + 2)
        poly_idx, cell_idx = STRtree(boxes).query(polygons, predicate="intersects")
        exact = np.zeros(len(tiles), dtype=bool)
        for cell, _polys, single in grouped(cell_idx, poly_idx, data.poly_zone_ids):
            if single >= 0:
                exact[cell] = True
                keys.append(
                    (zoom << (2 * bits)) | (int(x[cell]) << bits) | int(y[cell])
                )
                values.append(single)
        if zoom < max_zoom:
            parents = tiles[~exact]
            tiles = np.concatenate(
                [parents * 2 + np.array([dx, dy]) for dx in (0, 1) for dy in (0, 1)]
            )
    order = np.argsort(keys)
    key_array = np.asarray(keys, dtype=np.uint32)[order]
    value_array = table_value(np.asarray(values, dtype=np.int64)[order])
    key_array.flags.writeable = False
    return TilePyramid(
        name,
        "tzf-rs tile pyramid",
        {"zooms": [min_zoom, max_zoom], "fallback": fallback.name},
        list(range(min_zoom, max_zoom + 1)),
        key_array,
        value_array,
        fallback,
    )


class TwoTier:
    """The item's split, independent of cell shape: an exact layer before a coarse grid."""

    def __init__(self, name, exact_table, exact: BandedGrid, fallback: BandedGrid):
        self.name = name
        self.family = "two-tier split"
        self.params = {"exact": exact.name, "fallback": fallback.name}
        self.exact = exact
        self.exact_table = exact_table
        self.fallback = fallback
        self.candidates_of = fallback.candidates_of
        self.stop_index_of = fallback.stop_index_of

    def cell_entry(self, lng: float, lat: float) -> int:
        row = (int(lat * F) + KY) // self.exact.row_height
        col = (int(lng * F) + KX) // self.exact.width
        value = int(self.exact_table[max(row, 0) * self.exact.columns + max(col, 0)])
        return value if value != MISS else self.fallback.cell_entry(lng, lat)

    @property
    def cells(self) -> int:
        return len(self.exact_table)

    @property
    def payload_bytes(self) -> int:
        return self.exact_table.nbytes + self.fallback.payload_bytes

    @property
    def resident_bytes(self) -> int:
        return self.exact_table.nbytes + self.fallback.resident_bytes


# --- the query path with the H3 prologue swapped out ------------------------------------


class IndexFinder(TimezoneFinder):
    """The shipped finder, its two H3 lines replaced by ``shortcuts.cell_entry``."""

    __slots__ = ()

    def timezone_at(self, *, lng: float, lat: float) -> str | None:
        lng, lat = utils.validate_coordinates(lng, lat)
        entry = self.shortcuts.cell_entry(lng, lat)
        if entry >= 0:
            return self.zone_names.name_of(entry)
        if entry == ABSENT:
            return None
        return self.zone_names.name_of(self._zone_id_in_ambiguous_cell(entry, lng, lat))

    def _zone_ids_of_valid(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        if lngs.shape[0] == 0:
            return np.empty(0, dtype=ZONE_ID_RESULT_DTYPE)
        entries = self.shortcuts.cell_entries(lngs, lats)
        zone_ids = np.where(entries >= 0, entries, NO_ZONE_ID).astype(
            ZONE_ID_RESULT_DTYPE
        )
        ambiguous = np.flatnonzero(entries < ABSENT)
        if ambiguous.size:
            self._resolve_ambiguous_cells(entries, ambiguous, lngs, lats, zone_ids)
        return zone_ids


@contextmanager
def bound(path: str) -> Iterator[None]:
    previous = (utils.inside_polygon_packed, utils.packed_buffers)
    utils.inside_polygon_packed = PACKED_ACCELERATION_IMPLEMENTATIONS[path]
    utils.packed_buffers = PACKED_BUFFER_FACTORIES[path]
    try:
        yield
    finally:
        utils.inside_polygon_packed, utils.packed_buffers = previous


def finder_on(path: str, index=None, cls=TimezoneFinder) -> TimezoneFinder:
    with bound(path):
        finder = cls(in_memory=False)
    if index is not None:
        finder.shortcuts = index
    return finder


# --- instruments ----------------------------------------------------------------------


def h3_entry(index: ShortcutIndex) -> Callable[[float, float], int]:
    return lambda lng, lat: index.entry_of(h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES))


def work_counts(
    finder: TimezoneFinder,
    entry_of: Callable[[float, float], int],
    index,
    points: Sequence[tuple[float, float]],
) -> dict[str, float]:
    """The exact counts, and how often ``TimezoneFinderL`` on this index is right.

    Answered without geometry, candidates offered, polygons tested by the full lookup;
    and the share of points where the lightweight finder's answer - a unique cell's zone,
    else the cell's untested final zone - equals the full lookup's.
    """
    unique = offered = tested = lite_right = 0
    zone_ids = finder.zone_ids
    for lng, lat in points:
        entry = entry_of(lng, lat)
        if entry >= 0:
            unique += 1
            lite_right += 1
            continue
        if entry == ABSENT:
            continue
        candidates = index.candidates_of(entry).tolist()
        stop = index.stop_index_of(entry)
        offered += len(candidates)
        x, y = utils.coord2int(lng), utils.coord2int(lat)
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
    """Compare every answer with the H3 control and classify each disagreement.

    ``overlap``: both answers' zones contain the point - precedence among overlapping
    zones, which any index may order differently. ``uncovered``: no zone contains the
    point (the antimeridian and the south pole line), so both answers are the "last
    remaining zone" fallback. ``control_wrong``: only the candidate's zone contains it.
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
        x, y = utils.coord2int(lngs[i]), utils.coord2int(lats[i])
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
    # edge_points lists vertical-edge points first, then horizontal ones, half each;
    # the quadtree interleaves them, one of each per leaf
    if isinstance(index, LinearQuadtree):
        vertical = [i % 2 == 0 for i in range(len(on_edges))]
    else:
        half = len(on_edges) // 2
        vertical = [i < half for i in range(len(on_edges))]
    return probes(on_edges, vertical)


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
    try:
        return subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return platform.processor()


def h3_cost() -> dict[str, float]:
    """``import h3``'s cumulative import time (best of five cold processes) and install size."""
    times = []
    for _ in range(5):
        stderr = subprocess.run(
            [sys.executable, "-X", "importtime", "-c", "import h3"],
            capture_output=True,
            text=True,
            check=True,
        ).stderr
        for line in stderr.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 3 and parts[2] == "h3":
                times.append(int(parts[1]) / 1000)
    import h3 as h3_package

    package = Path(h3_package.__file__).resolve().parent
    size = sum(p.stat().st_size for p in package.rglob("*") if p.is_file())
    return {"import_ms_best_of_5": min(times), "installed_bytes": size}


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


EQUAL_ANGLE = (
    # width (degrees), what it aligns with
    ("0.75", "7.5-degree"),
    ("0.625", "7.5-degree"),
    ("0.5", "7.5-degree and whole-degree"),
    ("0.48", "neither"),
    ("0.46875", "7.5-degree"),
    ("0.45", "neither"),
    ("0.375", "7.5-degree"),
    ("0.36", "neither"),
    ("0.3125", "7.5-degree"),
    ("0.3", "7.5-degree"),
    ("0.25", "7.5-degree and whole-degree"),
)
# the exact rule's control: the same cells, every polygon meeting the closed cell
TOUCHING = ("equal_angle_0_5deg", "equal_area_0_375deg_aligned")
EQUAL_AREA = (
    # row height (degrees), columns a multiple of 48 (7.5-degree aligned) or not
    ("0.5", True),
    ("0.46875", True),
    ("0.375", True),
    ("0.375", False),
    ("0.3125", True),
    ("0.25", True),
)
GRID_TREES = (
    # root columns (360 / root degrees), block side k, levels below the root
    (192, 4, 1),
    (192, 2, 3),
    (384, 2, 1),
    (384, 2, 2),
    (384, 4, 1),
    (192, 4, 2),
    (384, 2, 3),
)
QUADTREES = (
    # family, roots (x, y), depths
    ("node-geo-tz quadtree", (2, 2), (8, 9, 10)),
    ("7.5-degree-rooted quadtree", (48, 24), (4, 5, 6)),
)


def build_sweep(polygons, data, only: list[str] | None) -> list:
    def wanted(name: str) -> bool:
        return not only or any(o in name for o in only)

    indexes: list = []
    grids: dict[str, BandedGrid] = {}
    specs: dict[str, tuple] = {}
    for width, aligns in EQUAL_ANGLE:
        name = f"equal_angle_{width.replace('.', '_')}deg"
        # the 0.5-degree grid is also the two-tier split's exact layer
        if not wanted(name) and width != "0.5":
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
        grids[name] = grid
        specs[name] = (grid.family, grid.params, rows, [columns] * rows)
        print(f"built {name}: {grid.cells:,} cells", flush=True)
        if wanted(name):
            indexes.append(grid)
    for height, aligned in EQUAL_AREA:
        name = (
            f"equal_area_{height.replace('.', '_')}deg"
            f"{'_aligned' if aligned else '_unaligned'}"
        )
        if not wanted(name):
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
        indexes.append(control)
    for family, (rx, ry), depths in QUADTREES:
        for depth in depths:
            tag = "geo_tz" if rx == 2 else "aligned"
            name = f"quadtree_{tag}_depth{depth}"
            if not wanted(name):
                continue
            started = time.perf_counter()
            tree = build_quadtree(name, family, rx, ry, depth, polygons, data)
            tree.params["build_seconds"] = round(time.perf_counter() - started, 1)
            print(f"built {name}: {tree.cells:,} leaves", flush=True)
            indexes.append(tree)
    for root_columns, k, levels in GRID_TREES:
        root = f"{360 / root_columns:g}".replace(".", "_")
        name = f"grid_tree_{root}deg_{k}x{k}_{levels}levels"
        if not wanted(name):
            continue
        started = time.perf_counter()
        tree = build_grid_tree(name, root_columns, k, levels, polygons, data)
        tree.params["build_seconds"] = round(time.perf_counter() - started, 1)
        print(
            f"built {name}: {tree.cells:,} root cells, blocks {tree.blocks}", flush=True
        )
        indexes.append(tree)
    if wanted("tzf"):
        one_degree = build_grid(
            "equal_angle_1deg",
            "equal-angle grid",
            {"width_deg": 1.0, "aligns_with": "whole-degree"},
            180,
            [360] * 180,
            polygons,
            data,
        )
        for max_zoom in (10, 11):
            name = f"tzf_pyramid_z3_z{max_zoom}_plus_1deg"
            started = time.perf_counter()
            pyramid = build_pyramid(name, 3, max_zoom, polygons, data, one_degree)
            pyramid.params["build_seconds"] = round(time.perf_counter() - started, 1)
            print(f"built {name}: {pyramid.cells:,} exact tiles", flush=True)
            indexes.append(pyramid)
    if wanted("two_tier") and "equal_angle_0_5deg" in grids:
        exact = grids["equal_angle_0_5deg"]
        table = np.where(exact.table < ABSENT, MISS, exact.table).astype(TABLE_DTYPE)
        coarse = build_grid(
            "equal_angle_1_875deg",
            "equal-angle grid",
            {"width_deg": 1.875, "aligns_with": "7.5-degree"},
            96,
            [192] * 96,
            polygons,
            data,
        )
        indexes.append(
            TwoTier("two_tier_0_5deg_exact_plus_1_875deg", table, exact, coarse)
        )
    return indexes


def compact(report: dict) -> dict:
    """What the decision record cites, in the committed measurement file's shape.

    Timing values are ``[best_round_change, challenger_wins, verdict]`` against the H3
    control; gate values are the disagreements summed over every probe set, per kernel.
    """

    def counts(strata: dict) -> dict:
        return {
            label: {k: round(v, 4) for k, v in strata[label].items() if k != "points"}
            for label in RANKING_STRATA
        }

    def timing(name: str) -> dict:
        return {
            path: {
                f"{label}_{kind}": [
                    round(c["best_challenger"] / c["best_baseline"] - 1, 4),
                    c["challenger_wins"],
                    c["verdict"],
                ]
                for label, kinds in rows[name].items()
                for kind, c in kinds.items()
            }
            for path, rows in report.get("timing", {}).items()
            if name in rows
        }

    def gate_totals(row: dict) -> dict:
        totals = {}
        for path, checks in row.get("gate", {}).items():
            summed: dict[str, int] = {}
            for check in checks.values():
                for key, value in check.items():
                    summed[key] = summed.get(key, 0) + value
            totals[path] = summed
        return totals

    rows = {
        name: {
            "cells": report[name]["cells"],
            "payload_bytes": report[name]["payload_bytes"],
            "resident_bytes": report[name]["resident_bytes"],
            "counts": counts(report[name]["strata"]),
        }
        for name in ("shipped_h3", "h3_control")
    }
    rows["shipped_h3"]["timing_against_control"] = timing("shipped_h3")
    rows["h3_control"]["answers_differing_from_shipped"] = report["h3_control"][
        "gate_against_shipped"
    ]
    candidates = {}
    for name, row in report["candidates"].items():
        candidates[name] = {
            "family": row["family"],
            "params": {k: v for k, v in row["params"].items() if k != "build_seconds"},
            "cells": row["cells"],
            "payload_bytes": row["payload_bytes"],
            "resident_bytes": row["resident_bytes"],
            "counts": counts(row["strata"]),
            "malacca_witness_offered": row["malacca_witness_offered"],
            "gate_disagreements": gate_totals(row),
            "timing_against_control": timing(name),
        }
        if "tzf_layout_payload_bytes" in row:
            candidates[name]["tzf_layout_payload_bytes"] = row[
                "tzf_layout_payload_bytes"
            ]
    return {
        "schema": 2,
        "created": report["created"],
        "command": report["command"],
        "environment": report["environment"],
        "h3": report["h3"],
        "methodology": {
            "counts": "every point of the 10,000-point random and on_land fixtures",
            "gate": "30,000 fixture points, own cell edges and 7.5-degree/whole-degree "
            "border lines, each with its neighbours one unit across, on both kernels",
            "timing": "paired and order-alternated against the H3 control: 31 rounds "
            "x 2,000 scalar calls, and 31 rounds x 8 batch calls of 256 points",
            "timing_value": "[best_round_change, challenger_wins_of_31, verdict]",
        },
        "file_size_model": report["file_size_model"],
        "h3_indexes": rows,
        "candidates": candidates,
        "head_to_head": {
            path: {
                pair: {
                    f"{label}_{kind}": [
                        round(c["best_challenger"] / c["best_baseline"] - 1, 4),
                        c["challenger_wins"],
                        c["verdict"],
                    ]
                    for label, kinds in result.items()
                    for kind, c in kinds.items()
                }
                for pair, result in pairs.items()
            }
            for path, pairs in report.get("head_to_head", {}).items()
        },
        "elapsed_seconds": report["elapsed_seconds"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output", type=Path, help="the full report")
    parser.add_argument(
        "--compact-output", type=Path, help="the summary the decision record cites"
    )
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
    model = _HEADER_SIZE + COMPACT_TABLE_SIZE * 2 + entries_file_bytes(shipped)
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

    def h3_row(index: ShortcutIndex, payload: int) -> dict:
        return {
            "cells": int(h3.get_num_cells(SHORTCUT_H3_RES)),
            "file_slots": int(COMPACT_TABLE_SIZE),
            "resident_slots": len(index.table),
            "payload_bytes": payload,
            "resident_bytes": index.table.nbytes + entries_resident_bytes(index),
            "strata": {
                label: work_counts(reference, h3_entry(index), index, points)
                for label, points in fixtures.items()
            },
        }

    report: dict[str, object] = {
        "schema": 2,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "command": "uv run python -m prototypes.latlng_index_bench "
        + " ".join(sys.argv[1:]),
        "environment": {
            "python": platform.python_version(),
            "machine": platform.machine(),
            "cpu": cpu_name(),
            "versions": {
                name: version(name) for name in ("h3", "numpy", "shapely", "numba")
            },
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
        "h3": h3_cost(),
        "file_size_model": {"shipped_bytes": model, "reproduces_shipped_file": True},
        "shipped_h3": h3_row(shipped, model),
        "h3_control": h3_row(control_index, control_path.stat().st_size),
        "candidates": {},
    }
    control_finder = finder_on("clang", control_index)
    report["h3_control"]["gate_against_shipped"] = gate(
        reference,
        control_finder,
        [p for points in fixtures.values() for p in points],
    )
    control_finder.cleanup()
    print("H3 rows done", flush=True)

    indexes = build_sweep(polygons, data, args.only)
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
                label: work_counts(reference, index.cell_entry, index, points)
                for label, points in fixtures.items()
            },
        }
        if isinstance(index, TilePyramid):
            row["tzf_layout_payload_bytes"] = index.tzf_layout_payload_bytes
        entry = index.cell_entry(*MALACCA_WITNESS)
        offered = set(index.candidates_of(entry).tolist()) if entry < ABSENT else set()
        row["malacca_witness_offered"] = bool(
            (
                entry >= 0
                and entry in {int(reference.zone_ids[b]) for b in malacca_polygons}
            )
            or offered & malacca_polygons
        )
        if not isinstance(index, TwoTier):
            own_probes = edge_probes(index, args.probes, rng)
            row["gate"] = {}
            for path in paths:
                control = finder_on(path, control_index)
                candidate = finder_on(path, index, IndexFinder)
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
            if not isinstance(index, TwoTier)
            and report["candidates"][index.name]["malacca_witness_offered"]
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
                for name, index in [("shipped_h3", None)] + [
                    (i.name, i) for i in timed
                ]:
                    finder = (
                        shipped_finder
                        if index is None
                        else finder_on(path, index, IndexFinder)
                    )
                    rows[name] = {}
                    for label in RANKING_STRATA:
                        points = fixtures[label][: args.points]
                        scalar = compare_candidates(
                            ("h3_control", scalar_call(control)),
                            (name, scalar_call(finder)),
                            points,
                            rounds=args.rounds,
                            batch_size=len(points),
                        )
                        batch_inputs = batches(points)
                        batch = compare_candidates(
                            ("h3_control", batch_call(control)),
                            (name, batch_call(finder)),
                            batch_inputs,
                            rounds=args.rounds,
                            batch_size=min(len(batch_inputs), 8),
                        )
                        rows[name][label] = {
                            "scalar": comparison(scalar),
                            "batch_256": comparison(batch),
                        }
                    if name != "shipped_h3":
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
                a = finder_on(path, by_name[challenger], IndexFinder)
                base = finder_on(path, by_name[baseline], IndexFinder)
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
    for path in (args.output, args.compact_output):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
    if args.output:
        args.output.write_text(rendered)
        print(f"wrote {args.output}")
    if args.compact_output:
        # the pretty-format-json hook's own form, so committing it changes nothing
        args.compact_output.write_text(
            json.dumps(compact(report), indent=2, sort_keys=True, ensure_ascii=False)
            + "\n"
        )
        print(f"wrote {args.compact_output}")
    if not args.output and not args.compact_output:
        print(rendered)
    reference.cleanup()


if __name__ == "__main__":
    main()
