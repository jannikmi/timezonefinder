#!/usr/bin/env python3

"""Sweep grid tree configurations within the shortcut index cap and pick one.

FINDINGS
========

Decided and confirmed on two x86-64 Intel Xeon cloud VMs, Linux, clang, data 2026d, with
the 0.9375-degree root the package then shipped as the control's cells.

**Outcome (B): a 0.75-degree root with one level of 4x4 blocks (480 root columns)
beats the 0.9375-degree root within the cap, and now ships.**

* **Why it wins.** Under full refinement the finest cell width alone sets the polygon
  work; the root and the depth set only lookups and bytes. Scalar time follows the
  polygon work, and batch time follows the depth, because the NumPy batch descent pays a
  fixed cost per level. So the best tree reaches the finest cells the cap allows in a
  single level, and a 0.75-degree root with 4x4 blocks is that tree: every one-level
  tree with finer cells is over the cap.
* **decide** found it faster than the control in every cell - scalar and batch, random
  and on land - and not slower on numba. On the ladder it displaced the 0.9375-degree shape,
  and the runner-up, a 1.25-degree root with two levels, was faster than the control but
  lost to it head to head.
* **confirm**, on a second machine with fresh points and seeds, found it faster than the
  control and than the 0.9375-degree shape in every cell, and it gates clean on clang, numba
  and pure Python.
* **Deeper and selective trees** can test fewer polygons within the cap, but every one
  screened was slower than the control per random batch.
* **What it trades** is a larger index, still within the cap. Unpriced here and owed by
  the change that ships it: the converter's work optimizer, which neither side here
  carries, loading and construction time, and ``make memory``.

PRE-REGISTERED DECISION RULE
============================

Fixed before any deciding run, so the run cannot choose its own criterion.

* **Eligible**: ``shortcuts.bin`` at most 800 KB as the shipped converter would write it
  (the candidate's exact bytes, with its candidate lists scaled by the shipped/control
  ratio, since the converter's work optimizer deduplicates lists differently); zero gate
  defects, scalar answers equal to batch answers, and the Strait of Malacca witness
  offered; not ``slower`` than the control in any of the four cells (scalar and 256-point
  batch, random and on-land) by the majority of three replicate processes on clang, and
  not ``slower`` in a single numba run.
* **Winner**: the incumbent ladder. Eligible configurations sorted by bytes, smallest
  first, the shipped shape among them; a larger one displaces the incumbent only if, head
  to head on clang by the majority of three replicates, it is ``faster`` in at least one
  cell and ``slower`` in none. Being level on speed therefore keeps the smaller index.
* **Adopted** only if ``confirm`` reproduces it on a second machine, with fresh seeds
  and freshly drawn points: the winner not ``slower`` than the control in any cell, and
  every cell the winner won in ``decide`` not reversed.
* **Outcomes.** (A) the shipped shape wins: it is the best configuration in the swept
  space by this rule. (B) the winner has one level, refines every multi-zone cell and
  fits ``int16``: the shipped reader reads it, so adopting it changes two constants in
  ``timezonefinder/configs.py`` and regenerates the data. (C) anything else needs a
  reader and format change of its own.

Only numbers from ``decide`` and ``confirm`` are quoted: ``screen`` picked its survivors
by them, so its margins are biased towards the survivors.

METHOD
======

This is a hyperparameter search shaped by the repository's measurement rules
(``contributing/development/designing-a-candidate-comparison.md``): every time is a
paired, order-alternated comparison inside one process, and no ratio crosses processes
or machines. The space is small and discrete, so it is enumerated rather than searched,
and the expensive instrument is spent only where the cheap exact one leaves a question.

* **The space.** Root columns that keep every cell edge on the 7.5-degree ocean
  meridians and whose root table alone fits the cap (``ROOT_COLUMNS``); one to three
  levels below the root, each with its own power-of-two block side (``SIDES``); every
  level a whole number of coordinate units wide; the finest level at most
  ``--finest-columns`` across. Each shape is built twice over: refining every cell
  several zones can own (the shipped rule), and *selectively* - an unrefined multi-zone
  cell above the last level holds its candidate list directly - under byte budgets.
* **Selective refinement** is cost-complexity pruning of the full tree. Each multi-zone
  cell either stays a leaf, costing its query share times the polygons it may test times
  ``TEST_NS``, or refines, costing one more read (``READ_NS``) for its share, its block's
  bytes times a price per byte, and its children's costs. One price per byte picks the
  cheapest tree, bottom up; the price is bisected until the tree fits a budget. A query's
  share is half its cell's surface area and half its land area, matching the two ranking
  strata, and no evaluation point is ever seen by the builder.
* **counts** (any machine; exact). Every configuration is built from candidate sets
  computed once per cell width by the converter's own rule
  (``scripts.grid_cells.owned_pairs``), lists in the converter's legacy order as the
  control's are, and counted on the committed random and on-land fixtures: reads,
  candidates, polygon tests and vertices of the polygons actually ray-cast per query.
  Configurations over the cap, or testing more than ``SELECTIVITY_FLOOR`` times the
  control's polygons, are dropped, and the rest are Pareto-pruned on bytes (exact) and
  the counts (within ``EPSILON``). The best ``--max-configs`` by the cost model go on,
  with the shipped shape and one sentinel just past the selectivity floor.
* **screen** (server). Each survivor is gated against the control and timed against it
  on clang, 31 rounds. The rebuilt shipped shape against the control is an A/A pair: the
  run is void unless it reads level in all four cells. A configuration ``slower`` in two
  cells, or by more than ``SCREEN_DROP`` in one, is dropped - a single ``slower`` is
  within the false-positive rate of this many comparisons.
* **decide** (server). The best ``--keep`` survivors are re-timed in three replicate
  processes at 61 rounds with distinct seeds, majority verdict per cell, plus one numba
  run; then the incumbent ladder above.
* **confirm** (a second server). The winner and runner-up against the control and each
  other on fresh points drawn by the fixture samplers under a new seed, and the winner
  gated on numba and on the pure-Python fallback.

The control is the shipped cells with the converter's legacy order, as in
``prototypes/latlng_index_bench.py``, because no candidate carries the converter's work
optimizer; the follow-up that ships a winner measures it against the shipped index.

USAGE
=====

::

    uv run python -m prototypes.grid_tree_config_sweep counts
    uv run python -m prototypes.grid_tree_config_sweep screen
    uv run python -m prototypes.grid_tree_config_sweep decide
    # on a second machine, from the first one's decide.json
    uv run python -m prototypes.grid_tree_config_sweep counts
    uv run python -m prototypes.grid_tree_config_sweep confirm --decide <decide.json>
    uv run python -m prototypes.grid_tree_config_sweep report

``all`` runs counts, screen and decide in a row. Every stage writes
``<workdir>/<stage>.json`` and reads the one before it, refusing it if the packaged
data changed in between.
"""

import argparse
import hashlib
import itertools
import json
import random
import re
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from prototypes.latlng_index_bench import (
    KX,
    KY,
    RANKING_STRATA,
    STRATA,
    X0,
    X_SPAN,
    Y0,
    Y_SPAN,
    EntryPacker,
    F,
    OrderingInput,
    border_probes,
    build_control,
    edge_probes,
    entries_file_bytes,
    environment,
    finder_on,
    gate_passed,
    gate_row,
    legacy_order,
    malacca_offered,
    malacca_polygons,
    narrow,
    no_blocks,
    polygons_of,
    shipped_file_size_model,
    time_pair,
)
from scripts.assert_acceleration_path import interpreted_path_name
from scripts.grid_cells import grouped, owned_pairs
from tests.auxiliaries import get_rnd_query_pt_area_weighted, load_benchmark_points
from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import (
    DEFAULT_DATA_DIR,
    OCEAN_TIMEZONE_PREFIX,
    SHORTCUT_BLOCK_SIDE,
    SHORTCUT_ROOT_COLUMNS,
)
from timezonefinder.shortcut_index import (
    _HEADER_SIZE,
    ABSENT,
    PAYLOAD_DTYPE,
    ShortcutIndex,
    get_last_change_idx,
    read_shortcuts_binary,
)

MODULE = "prototypes.grid_tree_config_sweep"
SCALE = 10**7

#: The project's cap on ``shortcuts.bin``
#: (contributing/project/project-purpose-runtime-constraints-and-non-goals.md).
CAP_BYTES = 800_000
#: Multiples of 48, so every cell edge lies on a 7.5-degree ocean meridian (an unaligned
#: grid tests 9-24 % more polygons per random query), dividing the coordinate span, with
#: a root table (C x C/2 int16) that fits the cap on its own.
ROOT_COLUMNS = tuple(
    c for c in range(48, 1_000, 48) if X_SPAN % c == 0 and c * c <= CAP_BYTES
)
#: Block sides per level. 16 spends 512 bytes on every refined cell.
SIDES = (2, 4, 8)
MAX_DEPTH = 3
#: The finest level's columns: 6,144 is 0.0586 degrees, past which the build dominates
#: the sweep's hour without reaching anything the cap admits.
FINEST_COLUMNS = 6_144

#: Budgets selective trees are fitted to, and how many prefixes get them.
SELECTIVE_BUDGETS = (600_000, 700_000, 800_000)
SELECTIVE_PREFIXES = 8
#: How far under its budget a selective tree may stop.
BUDGET_SLACK = 10_000

#: The cost model ranks and selects; it never decides. A random grid-tree query costs
#: ~650 ns of which the cell and root read are ~344 ns, so a further level's floor
#: divisions and read are put at 80 ns; the polygon loop is ~112 ns per random and ~308
#: ns per on-land query at 0.048 and 0.115 tests per query, ~2.5 us per polygon tested
#: (prototypes/query_stage_profile.py's FINDINGS, clang).
READ_NS = 80.0
TEST_NS = 2_500.0

#: A configuration testing more than this times the control's polygons per query, on
#: either stratum, is not timed: the selectivity it gives up costs more than the bytes
#: it saves. One sentinel just past it is timed to check that.
SELECTIVITY_FLOOR = 1.25
#: Tolerance on the count axes of the Pareto prune; bytes are compared exactly, so the
#: smallest of several equal configurations survives.
EPSILON = 0.02
#: A survivor of the screen reading slower than the control by more than this in a cell
#: is dropped however the other cells read.
SCREEN_DROP = 0.06

MULTI_LIMIT = -2  # a catalog value at or below this is -(set id + 2): several zones
CHUNK = 250_000  # cells per owned_pairs call, which holds a box per cell


# --- the configurations ---------------------------------------------------------------


@dataclass(frozen=True)
class TreeSpec:
    """A grid tree: root columns, a block side per level below, and a byte budget.

    ``budget`` is set only for a selective tree, whose multi-zone cells above the last
    level refine only where the cost model says they pay.
    """

    root_columns: int
    sides: tuple[int, ...]
    budget: int | None = None

    @property
    def selective(self) -> bool:
        return self.budget is not None

    @property
    def depth(self) -> int:
        return len(self.sides)

    @property
    def columns(self) -> list[int]:
        columns = [self.root_columns]
        for side in self.sides:
            columns.append(columns[-1] * side)
        return columns

    @property
    def widths(self) -> list[int]:
        return [X_SPAN // c for c in self.columns]

    @property
    def name(self) -> str:
        name = f"c{self.root_columns}_{'x'.join(str(k) for k in self.sides)}"
        return f"{name}_sel{self.budget // 1000}k" if self.selective else name

    @property
    def label(self) -> str:
        blocks = ", then ".join(f"{k}x{k}" for k in self.sides)
        text = f"{360 / self.root_columns:g} deg root, {blocks} -> {360 / self.columns[-1]:g} deg"
        return (
            f"{text}, selective <= {self.budget // 1000} KB" if self.selective else text
        )

    def valid(self) -> bool:
        return (
            self.root_columns % 2 == 0
            and 1 <= self.depth <= MAX_DEPTH
            and all(k >= 2 and not k & (k - 1) for k in self.sides)
            and all(X_SPAN % c == 0 for c in self.columns)
        )

    def as_json(self) -> dict:
        return {
            "root_columns": self.root_columns,
            "sides": list(self.sides),
            "budget": self.budget,
        }

    @classmethod
    def of_json(cls, value: dict) -> "TreeSpec":
        return cls(value["root_columns"], tuple(value["sides"]), value["budget"])


#: The shape the package ships, whose cells the control is: the A/A pair and the ladder's
#: incumbent follow the constants rather than any one release.
SHIPPED = TreeSpec(SHORTCUT_ROOT_COLUMNS, (SHORTCUT_BLOCK_SIDE,))


def enumerate_specs(finest_columns: int) -> list[TreeSpec]:
    """Every valid refine-all shape the space holds."""
    specs = []
    for root in ROOT_COLUMNS:
        for depth in range(1, MAX_DEPTH + 1):
            for sides in itertools.product(SIDES, repeat=depth):
                spec = TreeSpec(root, sides)
                if spec.valid() and spec.columns[-1] <= finest_columns:
                    specs.append(spec)
    return specs


# --- candidate sets, computed once per cell ------------------------------------------


class ListCatalog:
    """Each distinct candidate set once: its legacy-ordered list, stop index, land flag."""

    def __init__(self, data: OrderingInput, ocean_zone: np.ndarray):
        self.data = data
        self.ocean_zone = ocean_zone
        self._id: dict[bytes, int] = {}
        self.sets: list[np.ndarray] = []
        self._ordered: dict[int, np.ndarray] = {}
        self._stop: dict[int, int] = {}
        self._land: dict[int, bool] = {}

    def intern(self, polygon_ids: np.ndarray) -> int:
        key = np.asarray(polygon_ids, dtype=np.uint16).tobytes()
        found = self._id.get(key)
        if found is None:
            found = self._id[key] = len(self.sets)
            self.sets.append(np.asarray(polygon_ids, dtype=np.int64))
        return found

    def ordered(self, set_id: int) -> np.ndarray:
        found = self._ordered.get(set_id)
        if found is None:
            found = np.asarray(
                legacy_order(self.data, self.sets[set_id]), dtype=PAYLOAD_DTYPE
            )
            self._ordered[set_id] = found
        return found

    def stop(self, set_id: int) -> int:
        found = self._stop.get(set_id)
        if found is None:
            ordered = self.ordered(set_id).astype(np.int64)
            found = get_last_change_idx(self.data.poly_zone_ids[ordered])
            self._stop[set_id] = found
        return found

    def land(self, set_id: int) -> bool:
        found = self._land.get(set_id)
        if found is None:
            zones = self.data.poly_zone_ids[self.sets[set_id]]
            found = self._land[set_id] = bool((~self.ocean_zone[zones]).any())
        return found


@dataclass
class Level:
    """One level of the tree that refines every multi-zone cell: cells and their values.

    ``values`` is a zone id, ``ABSENT``, or ``-(set id + 2)`` for a cell several zones
    can own; ``multi`` lists those cells' positions, and the next level holds their
    children in that order, a block of ``k x k`` each.
    """

    columns: int
    gx: np.ndarray
    gy: np.ndarray
    values: np.ndarray
    multi: np.ndarray


class CellCatalog:
    """Every cell's candidates at every width, each computed once and shared.

    A cell's candidate set does not depend on the tree it belongs to, and a cell several
    zones can own lies inside a multi-zone cell at every coarser width that nests with
    it, so refine-all trees sharing a width share every cell of it.
    """

    def __init__(self, polygons: np.ndarray, lists: ListCatalog):
        self.polygons = polygons
        self.lists = lists
        self._store: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        self._levels: dict[tuple, list[Level]] = {}
        self.seconds_per_width: dict[int, float] = {}

    def values(self, columns: int, gx: np.ndarray, gy: np.ndarray) -> np.ndarray:
        keys = gy.astype(np.int64) * columns + gx
        known_keys, known_values = self._store.get(
            columns, (np.empty(0, np.int64), np.empty(0, np.int32))
        )
        missing = np.setdiff1d(keys, known_keys)
        if missing.size:
            started = time.perf_counter()
            fresh = np.full(len(missing), ABSENT, dtype=np.int32)
            width = X_SPAN // columns
            zone_ids = self.lists.data.poly_zone_ids
            for start in range(0, len(missing), CHUNK):
                chunk = missing[start : start + CHUNK]
                cy, cx = np.divmod(chunk, columns)
                x0, x1 = cx * width - X0 + 1, (cx + 1) * width - X0
                y0, y1 = cy * width - Y0 + 1, (cy + 1) * width - Y0
                for cell, polys, single in grouped(
                    *owned_pairs(self.polygons, x0, y0, x1, y1), zone_ids
                ):
                    fresh[start + cell] = (
                        single if single >= 0 else -(self.lists.intern(polys) + 2)
                    )
            merged = np.concatenate([known_keys, missing])
            order = np.argsort(merged, kind="stable")
            known_keys = merged[order]
            known_values = np.concatenate([known_values, fresh])[order]
            self._store[columns] = (known_keys, known_values)
            self.seconds_per_width[columns] = self.seconds_per_width.get(
                columns, 0.0
            ) + (time.perf_counter() - started)
        return known_values[np.searchsorted(known_keys, keys)]

    def levels(self, root_columns: int, sides: tuple[int, ...]) -> list[Level]:
        """The refine-all tree's levels down to ``sides``, shared across shapes."""
        key = (root_columns, sides)
        found = self._levels.get(key)
        if found is not None:
            return found
        if not sides:
            rows = root_columns // 2
            gx = np.tile(np.arange(root_columns, dtype=np.int32), rows)
            gy = np.repeat(np.arange(rows, dtype=np.int32), root_columns)
            columns = root_columns
            above: list[Level] = []
        else:
            above = self.levels(root_columns, sides[:-1])
            parent = above[-1]
            k = sides[-1]
            dy, dx = np.divmod(np.arange(k * k, dtype=np.int32), k)
            gx = (parent.gx[parent.multi, None] * k + dx[None, :]).reshape(-1)
            gy = (parent.gy[parent.multi, None] * k + dy[None, :]).reshape(-1)
            columns = parent.columns * k
        values = self.values(columns, gx, gy)
        level = Level(columns, gx, gy, values, np.flatnonzero(values <= MULTI_LIMIT))
        found = self._levels[key] = [*above, level]
        return found


# --- the trees ------------------------------------------------------------------------
#
# A tree subclasses ``ShortcutIndex`` and overrides the two methods the lookups call,
# ``entry_at`` and ``entries_at``, so it answers through the unmodified finder, as in
# latlng_index_bench.py. The scalar lookup is unrolled per depth - a generic loop over
# the levels measured ~280 ns per lookup more - and reads its root through ``_root``,
# the memoryview the shipped lookup reads, without which the shipped shape timed 4-5 %
# behind its own control.
#
# A selective tree's levels above the last hold both kinds of reference below ABSENT:
# ``-(b + 2)`` for block ``b < n`` of the next level, ``-(n + 2 + j)`` for candidate list
# ``j``, which the lookup returns as ``-(j + 2)``, the shipped encoding. Entries referenced
# from shallower levels are numbered first, keeping those values small.


class Tree(ShortcutIndex):
    __slots__ = (
        "spec",
        "columns",
        "widths",
        "sides",
        "level_arrays",
        "limits",
        "offsets",
        "wide",
        "w0",
        "w1",
        "w2",
        "w3",
        "k1",
        "k2",
        "k3",
        "m1",
        "m2",
        "m3",
        "q1",
        "q2",
        "q3",
        "b1",
        "b2",
        "b3",
        "e0",
        "e1",
        "e2",
        "n0",
        "n1",
        "n2",
    )

    def configure(self, spec: TreeSpec, level_arrays: list[np.ndarray]) -> None:
        self.spec = spec
        self.columns = spec.root_columns
        self.widths = spec.widths
        self.sides = spec.sides
        self.level_arrays = level_arrays
        blocks = [len(a) // (k * k) for a, k in zip(level_arrays, spec.sides)]
        self.offsets = blocks
        self.limits = [-(n + 2) for n in blocks]
        self.wide = any(
            a.dtype.itemsize > self.table.dtype.itemsize for a in level_arrays
        )
        pad = 3 - spec.depth
        self.w0, self.w1, self.w2, self.w3 = [*self.widths, *([0] * pad)]
        sides = [*spec.sides, *([1] * pad)]
        self.k1, self.k2, self.k3 = sides
        self.m1, self.m2, self.m3 = (k - 1 for k in sides)
        self.q1, self.q2, self.q3 = (k * k for k in sides)
        self.b1, self.b2, self.b3 = [
            *(memoryview(a) for a in level_arrays),
            *([None] * pad),
        ]
        self.n0, self.n1, self.n2 = [*blocks, *([0] * pad)]
        self.e0, self.e1, self.e2 = [*self.limits, *([0] * pad)]

    def entries_at(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        """The batch descent, level by level on the points still descending."""
        x = (lngs * F).astype(np.int64)
        x += KX
        np.add(x, X_SPAN, out=x, where=x < 0)
        y = (lats * F).astype(np.int64)
        y += KY
        np.maximum(y, 0, out=y)
        w = self.w0
        v = self.table[(y // w) * self.columns + x // w]
        if self.wide:
            v = v.astype(np.int32)
        todo = np.flatnonzero(v < ABSENT)
        last = len(self.level_arrays) - 1
        for level, below in enumerate(self.level_arrays):
            if not todo.size:
                break
            current = v[todo]
            if self.spec.selective:
                entry = current <= self.limits[level]
                if entry.any():
                    v[todo[entry]] = current[entry] + self.offsets[level]
                    keep = ~entry
                    todo = todo[keep]
                    current = current[keep]
                    if not todo.size:
                        break
            w = self.widths[level + 1]
            k = self.sides[level]
            m = k - 1
            v[todo] = below[
                (-2 - current.astype(np.int64)) * (k * k)
                + ((y[todo] // w) & m) * k
                + ((x[todo] // w) & m)
            ]
            if level < last:
                todo = todo[v[todo] < ABSENT]
        return v

    @property
    def payload_bytes(self) -> int:
        """The file this tree would be: the shipped header, one more ``int64`` per extra
        level for its block side, the levels, and the distinct lists."""
        return (
            _HEADER_SIZE
            + 8 * (self.spec.depth - 1)
            + self.table.nbytes
            + sum(a.nbytes for a in self.level_arrays)
            + entries_file_bytes(self)
        )

    @property
    def level_dtypes(self) -> list[str]:
        return [str(self.table.dtype), *(str(a.dtype) for a in self.level_arrays)]

    @property
    def reader_compatible(self) -> bool:
        """Whether the shipped reader reads it once its two constants are changed."""
        return (
            self.spec.depth == 1
            and not self.spec.selective
            and set(self.level_dtypes) == {"int16"}
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


class Tree1(Tree):
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
        m = self.m1
        return self.b1[(-2 - v) * self.q1 + ((y // w) & m) * self.k1 + ((x // w) & m)]

    def entries_at(self, lngs: np.ndarray, lats: np.ndarray) -> np.ndarray:
        """The shipped batch lookup line for line, with this tree's widths."""
        x = (lngs * F).astype(np.int64)
        x += KX
        np.add(x, X_SPAN, out=x, where=x < 0)
        y = (lats * F).astype(np.int64)
        y += KY
        np.maximum(y, 0, out=y)
        w = self.w0
        entries = self.table[(y // w) * self.columns + x // w]
        if self.wide:
            entries = entries.astype(np.int32)
        refined = np.flatnonzero(entries < ABSENT)
        if refined.size:
            blocks = -2 - entries[refined].astype(np.int64)
            w = self.w1
            m = self.m1
            entries[refined] = self.level_arrays[0][
                blocks * self.q1
                + ((y[refined] // w) & m) * self.k1
                + ((x[refined] // w) & m)
            ]
        return entries


class Tree2(Tree):
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
        m = self.m1
        v = self.b1[(-2 - v) * self.q1 + ((y // w) & m) * self.k1 + ((x // w) & m)]
        if v >= -1:
            return v
        w = self.w2
        m = self.m2
        return self.b2[(-2 - v) * self.q2 + ((y // w) & m) * self.k2 + ((x // w) & m)]


class Tree3(Tree):
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
        m = self.m1
        v = self.b1[(-2 - v) * self.q1 + ((y // w) & m) * self.k1 + ((x // w) & m)]
        if v >= -1:
            return v
        w = self.w2
        m = self.m2
        v = self.b2[(-2 - v) * self.q2 + ((y // w) & m) * self.k2 + ((x // w) & m)]
        if v >= -1:
            return v
        w = self.w3
        m = self.m3
        return self.b3[(-2 - v) * self.q3 + ((y // w) & m) * self.k3 + ((x // w) & m)]


class Tree1Selective(Tree):
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
        if v <= self.e0:
            return v + self.n0
        w = self.w1
        m = self.m1
        return self.b1[(-2 - v) * self.q1 + ((y // w) & m) * self.k1 + ((x // w) & m)]


class Tree2Selective(Tree):
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
        if v <= self.e0:
            return v + self.n0
        w = self.w1
        m = self.m1
        v = self.b1[(-2 - v) * self.q1 + ((y // w) & m) * self.k1 + ((x // w) & m)]
        if v >= -1:
            return v
        if v <= self.e1:
            return v + self.n1
        w = self.w2
        m = self.m2
        return self.b2[(-2 - v) * self.q2 + ((y // w) & m) * self.k2 + ((x // w) & m)]


class Tree3Selective(Tree):
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
        if v <= self.e0:
            return v + self.n0
        w = self.w1
        m = self.m1
        v = self.b1[(-2 - v) * self.q1 + ((y // w) & m) * self.k1 + ((x // w) & m)]
        if v >= -1:
            return v
        if v <= self.e1:
            return v + self.n1
        w = self.w2
        m = self.m2
        v = self.b2[(-2 - v) * self.q2 + ((y // w) & m) * self.k2 + ((x // w) & m)]
        if v >= -1:
            return v
        if v <= self.e2:
            return v + self.n2
        w = self.w3
        m = self.m3
        return self.b3[(-2 - v) * self.q3 + ((y // w) & m) * self.k3 + ((x // w) & m)]


TREE_CLASSES = {
    (1, False): Tree1,
    (2, False): Tree2,
    (3, False): Tree3,
    (1, True): Tree1Selective,
    (2, True): Tree2Selective,
    (3, True): Tree3Selective,
}


def make_tree(
    spec: TreeSpec,
    table: np.ndarray,
    level_arrays: list[np.ndarray],
    bounds: np.ndarray,
    payload: np.ndarray,
    last_change: np.ndarray,
    selective_lookup: bool | None = None,
) -> Tree:
    """``selective_lookup`` overrides the class choice, for the encoding's self-check."""
    selective = spec.selective if selective_lookup is None else selective_lookup
    cls = TREE_CLASSES[(spec.depth, selective)]
    tree = cls(table, no_blocks(), bounds[:-1], bounds[1:], last_change, payload)
    tree.configure(spec, level_arrays)
    return tree


def tree_of_shipped(index: ShortcutIndex) -> Tree:
    """A shipped-format index as the one-level tree it is, for counting it alike."""
    bounds = np.concatenate([index.starts, index.ends[-1:]])
    return make_tree(
        SHIPPED, index.table, [index.blocks], bounds, index.payload, index.last_change
    )


class ListPacker(EntryPacker):
    """Distinct lists numbered in first-reference order, from the list catalog."""

    def __init__(self, lists: ListCatalog):
        super().__init__(lists.data)
        self.lists = lists
        self.entry_of_set: dict[int, int] = {}

    def entry(self, set_id: int) -> int:
        found = self.entry_of_set.get(set_id)
        if found is None:
            found = self.entry_of_set[set_id] = len(self.payloads)
            self.payloads.append(self.lists.ordered(set_id))
        return found


def pack(
    spec: TreeSpec,
    levels: list[Level],
    lists: ListCatalog,
    refine: list[np.ndarray] | None = None,
) -> tuple[np.ndarray, list[np.ndarray], np.ndarray, np.ndarray, np.ndarray]:
    """The tree's arrays. ``refine[l]`` says which multi-zone cells of level ``l`` hold a
    block (``None``: all of them, the shipped rule), in the order of ``levels[l].multi``."""
    packer = ListPacker(lists)
    arrays = []
    present = np.arange(len(levels[0].values))
    for level_index in range(spec.depth + 1):
        level = levels[level_index]
        values = level.values[present].astype(np.int64)
        multi = np.flatnonzero(values <= MULTI_LIMIT)
        set_ids = (-2 - values[multi]).tolist()
        if level_index < spec.depth:
            ranks = np.searchsorted(level.multi, present[multi])
            refined = (
                np.ones(len(multi), dtype=bool)
                if refine is None
                else refine[level_index][ranks]
            )
            nr_blocks = int(refined.sum())
            values[multi[refined]] = -(np.arange(nr_blocks, dtype=np.int64) + 2)
            leaves = np.flatnonzero(~refined)
            values[multi[leaves]] = [
                -(nr_blocks + 2 + packer.entry(set_ids[i])) for i in leaves.tolist()
            ]
            q = spec.sides[level_index] ** 2
            present = (
                ranks[refined][:, None] * q + np.arange(q, dtype=np.int64)[None, :]
            ).reshape(-1)
        else:
            values[multi] = [-(packer.entry(s) + 2) for s in set_ids]
        arrays.append(narrow(values))
    bounds, payload, last = packer.arrays()
    return arrays[0], arrays[1:], bounds, payload, last


# --- selective refinement -------------------------------------------------------------


def query_weights(levels: list[Level], lists: ListCatalog) -> list[np.ndarray]:
    """Each multi-zone cell's share of queries: half by surface area, half by land area.

    Matches the two ranking strata - points uniform per unit of surface, and points on
    land - without reading either fixture.
    """
    root = levels[0]

    def area(level: Level, cells: np.ndarray) -> np.ndarray:
        w = X_SPAN // level.columns
        lat = ((level.gy[cells] + 0.5) * w - Y0) / SCALE
        return (w / SCALE) ** 2 * np.cos(np.radians(lat))

    def land(level: Level, cells: np.ndarray) -> np.ndarray:
        values = level.values[cells]
        flags = np.zeros(len(cells), dtype=bool)
        zones = values >= 0
        flags[zones] = ~lists.ocean_zone[values[zones]]
        multi = np.flatnonzero(values <= MULTI_LIMIT)
        flags[multi] = [lists.land(-2 - int(v)) for v in values[multi].tolist()]
        return flags

    all_root = np.arange(len(root.values))
    root_area = area(root, all_root)
    total_area = root_area.sum()
    total_land = (root_area * land(root, all_root)).sum()
    weights = []
    for level in levels:
        a = area(level, level.multi)
        weights.append(
            0.5 * a / total_area + 0.5 * a * land(level, level.multi) / total_land
        )
    return weights


def select_refinement(
    spec: TreeSpec, levels: list[Level], lists: ListCatalog, target_bytes: float
) -> list[np.ndarray]:
    """Which multi-zone cells refine: the cheapest tree by the cost model within bytes.

    Each multi-zone cell above the last level either stays a leaf - ``TEST_NS`` per
    polygon its list may test, weighted by its query share, plus its list's bytes at the
    price ``lam`` - or refines - ``READ_NS`` weighted by its share, its block's bytes at
    ``lam``, and its children's own cheapest costs. Solved bottom up per price; the price
    is bisected for the cheapest tree whose estimated bytes fit.
    """
    depth = spec.depth
    weights = query_weights(levels, lists)
    set_ids = [(-2 - level.values[level.multi]).tolist() for level in levels]
    leaf_ns = [
        w * np.array([lists.stop(s) for s in ids], dtype=np.float64) * TEST_NS
        for w, ids in zip(weights, set_ids)
    ]
    leaf_bytes = [
        np.array([2 * len(lists.sets[s]) + 5 for s in ids], dtype=np.float64)
        for ids in set_ids
    ]
    block_bytes = [2.0 * k * k for k in spec.sides]

    def solve(lam: float) -> tuple[list[np.ndarray], float]:
        refine: list[np.ndarray] = [np.zeros(0, dtype=bool)] * depth
        below = None
        for level_index in range(depth, -1, -1):
            leaf = leaf_ns[level_index] + lam * leaf_bytes[level_index]
            if level_index == depth:
                cost = leaf
            else:
                q = spec.sides[level_index] ** 2
                children = below.reshape(-1, q).sum(axis=1)
                refined = (
                    weights[level_index] * READ_NS
                    + lam * block_bytes[level_index]
                    + children
                )
                refine[level_index] = refined < leaf
                cost = np.minimum(leaf, refined)
            if level_index:
                below = np.zeros(len(levels[level_index].values))
                below[levels[level_index].multi] = cost
        size = float(spec.root_columns**2)
        in_tree = np.ones(len(levels[0].multi), dtype=bool)
        for level_index in range(depth + 1):
            if level_index == depth:
                size += leaf_bytes[level_index][in_tree].sum()
                break
            r = refine[level_index]
            size += block_bytes[level_index] * (in_tree & r).sum()
            size += leaf_bytes[level_index][in_tree & ~r].sum()
            q = spec.sides[level_index] ** 2
            child_in = np.repeat(in_tree & r, q)
            in_tree = child_in[levels[level_index + 1].multi]
        return refine, size

    low, high = -12.0, 3.0  # log10 of the price per byte, in ns per query per byte
    refine, _ = solve(10.0**high)
    for _ in range(40):
        middle = (low + high) / 2
        candidate, size = solve(10.0**middle)
        if size <= target_bytes:
            high, refine = middle, candidate
        else:
            low = middle
    return refine


# --- the exact counts -----------------------------------------------------------------


def descend(tree: Tree, lngs: np.ndarray, lats: np.ndarray) -> tuple[np.ndarray, ...]:
    """Each point's entry, and the reads its lookup makes: the root, plus one per level."""
    x = (lngs * F).astype(np.int64) + KX
    np.add(x, X_SPAN, out=x, where=x < 0)
    y = np.maximum((lats * F).astype(np.int64) + KY, 0)
    w = tree.w0
    v = tree.table[(y // w) * tree.columns + x // w].astype(np.int64)
    reads = np.ones(len(v), dtype=np.int64)
    todo = np.flatnonzero(v < ABSENT)
    for level, below in enumerate(tree.level_arrays):
        if tree.spec.selective and todo.size:
            entry = v[todo] <= tree.limits[level]
            v[todo[entry]] += tree.offsets[level]
            todo = todo[~entry]
        if not todo.size:
            break
        w = tree.widths[level + 1]
        k = tree.sides[level]
        m = k - 1
        v[todo] = below[
            (-2 - v[todo]) * (k * k) + ((y[todo] // w) & m) * k + ((x[todo] // w) & m)
        ]
        reads[todo] += 1
        if level < len(tree.level_arrays) - 1:
            todo = todo[v[todo] < ABSENT]
    return v, reads


class PointOracle:
    """Which polygons contain each evaluation point, found once with the kernel.

    Every configuration's counts then follow from its leaves alone: a candidate list is
    tested in order until a polygon containing the point, or its stop index. A polygon is
    ray-cast only if its bounding box holds the point; the vertices of those are the
    count the query time correlates with best (0.92, prototypes/polygon_block_encoding.py).
    """

    def __init__(
        self, finder: TimezoneFinder, points: dict[str, Sequence[tuple[float, float]]]
    ):
        b = finder.boundaries
        xmin, xmax, ymin, ymax = (
            np.asarray(a, dtype=np.int64) for a in (b.xmin, b.xmax, b.ymin, b.ymax)
        )
        self.vertices = np.asarray(b.nr_vertices, dtype=np.int64).tolist()
        self.strata = {}
        for label, pts in points.items():
            contained, boxed = [], []
            for lng, lat in pts:
                x, y = utils.query2int(lng, lat)
                hits = np.flatnonzero(
                    (xmin <= x) & (x <= xmax) & (ymin <= y) & (y <= ymax)
                ).tolist()
                boxed.append(set(hits))
                contained.append({h for h in hits if finder.inside_of_polygon(h, x, y)})
            self.strata[label] = (
                np.asarray([p[0] for p in pts], dtype=np.float64),
                np.asarray([p[1] for p in pts], dtype=np.float64),
                contained,
                boxed,
            )

    def counts(self, tree: Tree) -> dict[str, dict[str, float]]:
        result = {}
        lists: dict[int, tuple[list[int], int]] = {}
        for label, (lngs, lats, contained, boxed) in self.strata.items():
            entries, reads = descend(tree, lngs, lats)
            offered = tested = vertices = 0
            for i in np.flatnonzero(entries < ABSENT).tolist():
                entry = int(entries[i])
                found = lists.get(entry)
                if found is None:
                    found = lists[entry] = (
                        tree.candidates_of(entry).tolist(),
                        tree.stop_index_of(entry),
                    )
                candidates, stop = found
                offered += len(candidates)
                inside = contained[i]
                tests = stop
                for position in range(stop):
                    if candidates[position] in inside:
                        tests = position + 1
                        break
                tested += tests
                box = boxed[i]
                vertices += sum(
                    self.vertices[c] for c in candidates[:tests] if c in box
                )
            n = len(lngs)
            result[label] = {
                "unique_share": float((entries >= 0).sum()) / n,
                "reads_per_query": float(reads.mean()),
                "candidates_per_query": offered / n,
                "tests_per_query": tested / n,
                "vertices_per_query": vertices / n,
            }
        return result


def estimated_ns(counts: dict[str, dict[str, float]]) -> float:
    """The cost model's query time beyond the root read, averaged over the strata."""
    return sum(
        READ_NS * (counts[s]["reads_per_query"] - 1)
        + TEST_NS * counts[s]["tests_per_query"]
        for s in RANKING_STRATA
    ) / len(RANKING_STRATA)


COUNT_AXES = tuple(
    (stratum, key)
    for stratum in RANKING_STRATA
    for key in ("reads_per_query", "tests_per_query", "vertices_per_query")
)


def pareto(rows: list[dict], eps: float) -> list[dict]:
    """Rows no smaller-or-equal row matches within ``eps`` on every count axis."""
    kept: list[dict] = []
    for row in sorted(rows, key=lambda r: (r["projected_bytes"], r["estimated_ns"])):
        dominated = any(
            k["projected_bytes"] <= row["projected_bytes"]
            and all(
                k["counts"][s][a] <= row["counts"][s][a] * (1 + eps)
                for s, a in COUNT_AXES
            )
            for k in kept
        )
        if not dominated:
            kept.append(row)
    return kept


# --- shared plumbing ------------------------------------------------------------------


def data_digest() -> str:
    """One hash over every packaged data file, so stages refuse each other's mismatch."""
    digest = hashlib.sha256()
    for path in sorted(Path(DEFAULT_DATA_DIR).rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(DEFAULT_DATA_DIR).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_stage(workdir: Path, stage: str) -> dict:
    path = workdir / f"{stage}.json"
    report = json.loads(path.read_text())
    if report["data_digest"] != data_digest():
        raise SystemExit(f"{path} was taken on different data; re-run from counts")
    return report


def write_stage(workdir: Path, stage: str, report: dict) -> None:
    path = workdir / f"{stage}.json"
    path.write_text(json.dumps(report, indent=1) + "\n")
    print(f"wrote {path}", flush=True)


def stage_header(stage: str, paths: Sequence[str]) -> dict:
    return {
        "schema": 1,
        "stage": stage,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "command": f"uv run python -m {MODULE} " + " ".join(sys.argv[1:]),
        "environment": environment(paths),
        "data_digest": data_digest(),
    }


def save_tree(tree: Tree, path: Path) -> str:
    arrays = {f"level_{i}": a for i, a in enumerate(tree.level_arrays)}
    bounds = np.concatenate([tree.starts, tree.ends[-1:]])
    with path.open("wb") as handle:
        np.savez(
            handle,
            table=tree.table,
            bounds=bounds,
            payload=tree.payload,
            last_change=tree.last_change,
            **arrays,
        )
    return file_digest(path)


def load_tree(spec: TreeSpec, path: Path, digest: str) -> Tree:
    if file_digest(path) != digest:
        raise SystemExit(f"{path} is not the file counts wrote")
    with np.load(path) as stored:
        arrays = {name: stored[name] for name in stored.files}
    for array in arrays.values():
        array.flags.writeable = False
    levels = [arrays[f"level_{i}"] for i in range(spec.depth)]
    return make_tree(
        spec,
        arrays["table"],
        levels,
        arrays["bounds"],
        arrays["payload"],
        arrays["last_change"],
    )


def load_control(workdir: Path, counts_report: dict) -> ShortcutIndex:
    path = workdir / "control.bin"
    if file_digest(path) != counts_report["control"]["sha256"]:
        raise SystemExit(f"{path} is not the control counts wrote")
    return read_shortcuts_binary(path)


def load_trees(workdir: Path, counts_report: dict, names: Sequence[str]) -> dict:
    rows = {row["name"]: row for row in counts_report["selected"]}
    return {
        name: load_tree(
            TreeSpec.of_json(rows[name]["spec"]),
            workdir / f"{name}.npz",
            rows[name]["sha256"],
        )
        for name in names
    }


def ranking_fixtures(points: int, fresh_seed: int | None, reference) -> dict:
    """The ranking strata: the committed fixtures, or fresh draws by their samplers."""
    if fresh_seed is None:
        return {s: load_benchmark_points(STRATA[s])[:points] for s in RANKING_STRATA}
    from scripts.generate_benchmark_fixtures import generate_on_land_points

    rng = random.Random(fresh_seed)
    return {
        "random": [get_rnd_query_pt_area_weighted(rng) for _ in range(points)],
        "on_land": generate_on_land_points(reference, rng, points),
    }


CELLS = tuple(
    (stratum, shape) for stratum in RANKING_STRATA for shape in ("scalar", "batch_256")
)


def verdicts(result: dict) -> dict[str, str]:
    return {f"{s}/{shape}": result[s][shape]["verdict"] for s, shape in CELLS}


def majority(replicates: list[dict[str, str]]) -> dict[str, str]:
    """Per cell, the verdict most replicates gave; ``unresolved`` without a majority."""
    result = {}
    for cell in replicates[0]:
        verdict, count = Counter(r[cell] for r in replicates).most_common(1)[0]
        result[cell] = verdict if count * 2 > len(replicates) else "unresolved"
    return result


def run_pairs(
    workdir: Path,
    pairs: Sequence[str],
    *,
    path: str,
    rounds: int,
    seed: int,
    points: int,
    fresh_seed: int | None = None,
) -> dict:
    """``pairs`` in a fresh process, so replicates differ in more than their seed."""
    output = workdir / f"pairs-{path}-{seed}-{abs(hash(tuple(pairs))) % 10**8}.json"
    command = [
        sys.executable,
        "-m",
        MODULE,
        "pairs",
        "--workdir",
        str(workdir),
        "--path",
        path,
        "--rounds",
        str(rounds),
        "--seed",
        str(seed),
        "--points",
        str(points),
        "--output",
        str(output),
        "--pairs",
        *pairs,
    ]
    if fresh_seed is not None:
        command += ["--fresh-points", str(fresh_seed)]
    subprocess.run(command, check=True)
    return json.loads(output.read_text())


# --- the stages -----------------------------------------------------------------------


def counts_stage(args) -> None:
    started = time.perf_counter()
    workdir: Path = args.workdir
    workdir.mkdir(parents=True, exist_ok=True)
    reference = finder_on("clang")
    data = OrderingInput(
        reference.boundaries, reference.zone_ids, reference.zone_names.names
    )
    ocean = np.array(
        [bool(re.match(OCEAN_TIMEZONE_PREFIX, n)) for n in reference.zone_names.names]
    )
    polygons = polygons_of(reference)
    lists = ListCatalog(data, ocean)
    catalog = CellCatalog(polygons, lists)
    oracle = PointOracle(
        reference, {s: load_benchmark_points(STRATA[s]) for s in RANKING_STRATA}
    )

    shipped = reference.shortcuts
    shipped_bytes = shipped_file_size_model(shipped)
    control_path = workdir / "control.bin"
    control = build_control(shipped, data, reference.zone_ids, control_path)
    # the shipped work optimizer orders each cell's list by cost, which deduplicates
    # lists differently from the legacy order every candidate here uses
    list_ratio = entries_file_bytes(shipped) / entries_file_bytes(control)
    control_counts = oracle.counts(tree_of_shipped(control))
    print(f"control counted, {time.perf_counter() - started:.0f} s", flush=True)

    def row_of(tree: Tree, seconds: float) -> dict:
        entries = entries_file_bytes(tree)
        projected = round(tree.payload_bytes - entries + entries * list_ratio)
        counts = oracle.counts(tree)
        return {
            "name": tree.spec.name,
            "label": tree.spec.label,
            "spec": tree.spec.as_json(),
            "payload_bytes": tree.payload_bytes,
            "projected_bytes": projected,
            "level_dtypes": tree.level_dtypes,
            "reader_compatible": tree.reader_compatible,
            "blocks_per_level": tree.offsets,
            "distinct_lists": len(tree.last_change),
            "counts": counts,
            "estimated_ns": estimated_ns(counts),
            "build_seconds": round(seconds, 2),
        }

    rows: list[dict] = []
    trees: dict[str, Tree] = {}
    specs = enumerate_specs(args.finest_columns)
    if args.only:
        specs = [s for s in specs if any(o in s.name for o in args.only)] + [SHIPPED]
        specs = list(dict.fromkeys(specs))
    for spec in specs:
        built = time.perf_counter()
        levels = catalog.levels(spec.root_columns, spec.sides)
        tree = make_tree(spec, *pack(spec, levels, lists))
        rows.append(row_of(tree, time.perf_counter() - built))
        trees[spec.name] = tree
        print(
            f"{spec.name:>14}: {rows[-1]['projected_bytes']:>10,} B, "
            f"{rows[-1]['estimated_ns']:7.1f} ns, "
            f"{time.perf_counter() - started:5.0f} s",
            flush=True,
        )

    by_name = {row["name"]: row for row in rows}
    if by_name[SHIPPED.name]["counts"] != control_counts:
        raise AssertionError(
            "the rebuilt shipped shape does not count as the control does: "
            f"{by_name[SHIPPED.name]['counts']} != {control_counts}"
        )

    # selective trees, on the prefixes the cost model likes best, over the cap or not
    shrinkable = [r for r in rows if r["projected_bytes"] > min(SELECTIVE_BUDGETS)]
    prefixes = sorted(shrinkable, key=lambda r: r["estimated_ns"])[
        : args.selective_prefixes
    ]
    for prefix in prefixes:
        base = TreeSpec.of_json(prefix["spec"])
        levels = catalog.levels(base.root_columns, base.sides)
        for budget in SELECTIVE_BUDGETS:
            if budget >= prefix["projected_bytes"]:
                continue
            spec = TreeSpec(base.root_columns, base.sides, budget)
            built = time.perf_counter()
            # the selection estimates list bytes without deduplication, so its target
            # is corrected by what the exact packing misses, both ways, keeping the
            # largest tree that fits
            target = float(budget)
            best = None
            for _ in range(8):
                refine = select_refinement(spec, levels, lists, target)
                candidate = make_tree(spec, *pack(spec, levels, lists, refine))
                exact = row_of(candidate, time.perf_counter() - built)
                fits = exact["projected_bytes"] <= budget
                if fits and (
                    best is None
                    or exact["projected_bytes"] > best[1]["projected_bytes"]
                ):
                    best = (candidate, exact)
                if fits and exact["projected_bytes"] >= budget - BUDGET_SLACK:
                    break
                target += budget - exact["projected_bytes"] - (0 if fits else 1_000)
            if best is None:
                print(f"{spec.name}: nothing fits {budget:,} B", flush=True)
                continue
            tree, row = best
            rows.append(row)
            trees[spec.name] = tree
            print(
                f"{spec.name:>14}: {row['projected_bytes']:>10,} B, "
                f"{row['estimated_ns']:7.1f} ns, "
                f"{time.perf_counter() - started:5.0f} s",
                flush=True,
            )

    floor = {
        s: SELECTIVITY_FLOOR * control_counts[s]["tests_per_query"]
        for s in RANKING_STRATA
    }

    def selectivity(row: dict) -> float:
        return max(
            row["counts"][s]["tests_per_query"] / control_counts[s]["tests_per_query"]
            for s in RANKING_STRATA
        )

    for row in rows:
        row["within_cap"] = row["projected_bytes"] <= CAP_BYTES
        row["selectivity_vs_control"] = round(selectivity(row), 4)
    eligible = [r for r in rows if r["within_cap"]]
    front = pareto(eligible, EPSILON)
    for row in front:
        row["on_frontier"] = True
    selective_enough = [
        r
        for r in front
        if all(r["counts"][s]["tests_per_query"] <= floor[s] for s in RANKING_STRATA)
    ]
    ranked = sorted(selective_enough, key=lambda r: r["estimated_ns"])
    selected = ranked[: args.max_configs]
    if by_name[SHIPPED.name] not in selected:
        selected.append(by_name[SHIPPED.name])
    past_floor = [r for r in front if r not in selective_enough]
    sentinel = min(past_floor, key=selectivity) if past_floor else None
    if sentinel is not None:
        sentinel["sentinel"] = True
        selected.append(sentinel)
    for row in selected:
        row["sha256"] = save_tree(trees[row["name"]], workdir / f"{row['name']}.npz")

    report = stage_header("counts", ["clang"])
    report.update(
        {
            "cap_bytes": CAP_BYTES,
            "finest_columns": args.finest_columns,
            "cost_model": {"read_ns": READ_NS, "test_ns": TEST_NS},
            "selectivity_floor": SELECTIVITY_FLOOR,
            "epsilon": EPSILON,
            "shipped": {"file_bytes": shipped_bytes, "list_ratio": list_ratio},
            "control": {
                "sha256": file_digest(control_path),
                "payload_bytes": control_path.stat().st_size,
                "counts": control_counts,
                "estimated_ns": estimated_ns(control_counts),
            },
            "seconds_per_width": {
                str(c): round(s, 1) for c, s in catalog.seconds_per_width.items()
            },
            "configurations": len(rows),
            "within_cap": len(eligible),
            "frontier": [r["name"] for r in front],
            "selected": selected,
            "rows": rows,
            "elapsed_seconds": round(time.perf_counter() - started, 1),
        }
    )
    write_stage(workdir, "counts", report)
    print(
        f"{len(rows)} configurations, {len(eligible)} within the cap, "
        f"{len(front)} on the frontier, {len(selected)} selected "
        f"in {report['elapsed_seconds']} s"
    )
    reference.cleanup()


def screen_stage(args) -> None:
    started = time.perf_counter()
    workdir: Path = args.workdir
    counts_report = read_stage(workdir, "counts")
    names = [row["name"] for row in counts_report["selected"]]
    rows = {row["name"]: row for row in counts_report["selected"]}
    control_index = load_control(workdir, counts_report)
    trees = load_trees(workdir, counts_report, names)
    reference = finder_on("clang")
    witness = malacca_polygons(reference)
    gate_points = [p for f in STRATA.values() for p in load_benchmark_points(f)]
    fixtures = ranking_fixtures(args.points, None, reference)
    rng = np.random.default_rng(args.seed)
    shared_probes = border_probes(args.probes, rng)
    control = finder_on("clang", control_index)

    results = {}
    for name in names:
        tree = trees[name]
        gate = gate_row(
            tree,
            control_index,
            gate_points,
            edge_probes(tree, args.probes, rng),
            shared_probes,
            ("clang",),
        )
        result = {
            "projected_bytes": rows[name]["projected_bytes"],
            "malacca_witness_offered": malacca_offered(tree, reference, witness),
            "gate": gate,
        }
        if result["malacca_witness_offered"] and gate_passed(gate):
            finder = finder_on("clang", tree)
            timing = time_pair(
                ("control", control),
                (name, finder),
                fixtures,
                points=args.points,
                rounds=args.rounds,
                seed=args.seed,
            )
            finder.cleanup()
            result["timing"] = timing
            result["verdicts"] = verdicts(timing)
            result["slower_cells"] = [
                cell for cell, v in result["verdicts"].items() if v == "slower"
            ]
            result["far_slower_cells"] = [
                f"{s}/{shape}"
                for s, shape in CELLS
                if timing[s][shape]["best_challenger"]
                > timing[s][shape]["best_baseline"] * (1 + SCREEN_DROP)
            ]
            result["survives"] = (
                len(result["slower_cells"]) < 2 and not result["far_slower_cells"]
            )
        else:
            result["survives"] = False
        results[name] = result
        print(
            f"{name:>14}: {result.get('verdicts', 'gate failed')}, "
            f"{time.perf_counter() - started:5.0f} s",
            flush=True,
        )
    control.cleanup()
    reference.cleanup()

    aa = results[SHIPPED.name].get("verdicts", {})
    aa_level = bool(aa) and all(
        v in ("no difference", "unresolved") for v in aa.values()
    )
    survivors = sorted(
        (n for n, r in results.items() if r["survives"]),
        key=lambda n: (len(results[n]["slower_cells"]), rows[n]["projected_bytes"]),
    )[: args.keep]
    if SHIPPED.name not in survivors:
        survivors.append(SHIPPED.name)
    report = stage_header("screen", ["clang"])
    report.update(
        {
            "rounds": args.rounds,
            "seed": args.seed,
            "points": args.points,
            "aa_level": aa_level,
            "results": results,
            "survivors": survivors,
            "elapsed_seconds": round(time.perf_counter() - started, 1),
        }
    )
    write_stage(workdir, "screen", report)
    if not aa_level:
        raise SystemExit(f"void: the A/A pair read {aa}; re-run screen")


def decide_stage(args) -> None:
    started = time.perf_counter()
    workdir: Path = args.workdir
    counts_report = read_stage(workdir, "counts")
    screen = read_stage(workdir, "screen")
    if not screen["aa_level"]:
        raise SystemExit("the screen is void; re-run it")
    rows = {row["name"]: row for row in counts_report["selected"]}
    survivors = screen["survivors"]
    seeds = [args.seed + i for i in range(args.replicates)]
    interpreted = interpreted_path_name()

    def replicated(pairs: list[str]) -> tuple[dict[str, dict[str, str]], list[dict]]:
        runs = [
            run_pairs(
                workdir,
                pairs,
                path="clang",
                rounds=args.rounds,
                seed=seed,
                points=args.points,
            )
            for seed in seeds
        ]
        majorities = {
            pair: majority([verdicts(run["pairs"][pair]) for run in runs])
            for pair in pairs
        }
        return majorities, runs

    against_control, runs = replicated([f"control:{n}" for n in survivors])
    single = run_pairs(
        workdir,
        [f"control:{n}" for n in survivors],
        path=interpreted,
        rounds=args.interpreted_rounds,
        seed=args.seed + 1_000,
        points=args.points,
    )
    eligible = []
    table = {}
    for name in survivors:
        clang = against_control[f"control:{name}"]
        other = verdicts(single["pairs"][f"control:{name}"])
        table[name] = {"clang": clang, interpreted: other}
        if "slower" not in clang.values() and "slower" not in other.values():
            eligible.append(name)
    eligible.sort(key=lambda n: rows[n]["projected_bytes"])
    print(f"eligible, smallest first: {eligible}", flush=True)

    ladder = []
    incumbent = eligible[0] if eligible else None
    previous = None
    for challenger in eligible[1:]:
        pair = f"{incumbent}:{challenger}"
        result, step_runs = replicated([pair])
        cells = result[pair]
        displaces = "faster" in cells.values() and "slower" not in cells.values()
        ladder.append(
            {
                "incumbent": incumbent,
                "challenger": challenger,
                "verdicts": cells,
                "displaces": displaces,
                "runs": step_runs,
            }
        )
        print(f"{pair}: {cells} -> {'displaces' if displaces else 'holds'}", flush=True)
        if displaces:
            previous, incumbent = incumbent, challenger
    runner_up = previous
    if runner_up is None and len(eligible) > 1:
        runner_up = next(n for n in eligible if n != incumbent)

    winner_row = rows[incumbent] if incumbent else None
    if winner_row is None:
        outcome = "void: nothing eligible"
    elif incumbent == SHIPPED.name:
        outcome = "A"
    elif winner_row["reader_compatible"]:
        outcome = "B"
    else:
        outcome = "C"
    report = stage_header("decide", ["clang", interpreted])
    report.update(
        {
            "rounds": args.rounds,
            "seeds": seeds,
            "survivors": survivors,
            "against_control": table,
            "replicate_runs": runs,
            "interpreted_run": single,
            "eligible": eligible,
            "ladder": ladder,
            "winner": incumbent,
            "runner_up": runner_up,
            "outcome": outcome,
            "elapsed_seconds": round(time.perf_counter() - started, 1),
        }
    )
    write_stage(workdir, "decide", report)
    print(f"winner {incumbent} (outcome {outcome}), runner-up {runner_up}")


def confirm_stage(args) -> None:
    started = time.perf_counter()
    workdir: Path = args.workdir
    if args.decide is None:
        decide = read_stage(workdir, "decide")
    else:
        # a second machine re-runs counts, which is exact and deterministic, and reads
        # the first machine's committed verdicts
        decide = json.loads(args.decide.read_text())
        if decide["data_digest"] != data_digest():
            raise SystemExit(f"{args.decide} was taken on different data")
    winner, runner_up = decide["winner"], decide["runner_up"]
    pairs = [f"control:{winner}"]
    if runner_up:
        pairs += [f"control:{runner_up}", f"{runner_up}:{winner}"]
    seeds = [args.seed + i for i in range(args.replicates)]
    runs = [
        run_pairs(
            workdir,
            pairs,
            path="clang",
            rounds=args.rounds,
            seed=seed,
            points=args.points,
            fresh_seed=args.seed,
        )
        for seed in seeds
    ]
    confirmed = {
        pair: majority([verdicts(run["pairs"][pair]) for run in runs]) for pair in pairs
    }
    # what decide claimed for the winner, by the pair confirm re-times it in
    claims = {f"control:{winner}": decide["against_control"][winner]["clang"]}
    for step in decide["ladder"]:
        if step["challenger"] == winner and step["displaces"]:
            if step["incumbent"] == runner_up:
                claims[f"{runner_up}:{winner}"] = step["verdicts"]
    reversed_cells = [
        f"{pair} {cell}"
        for pair, cells in claims.items()
        for cell, verdict in cells.items()
        if verdict == "faster" and confirmed[pair][cell] == "slower"
    ]
    reproduces = (
        "slower" not in confirmed[f"control:{winner}"].values() and not reversed_cells
    )

    gates = {}
    for path in ("clang", interpreted_path_name()):
        gates[path] = gate_subprocess(
            workdir, winner, [sys.executable, "-m", MODULE], path
        )
    plain = ["uv", "run", "--isolated", "--group", "test", "python", "-m", MODULE]
    try:
        gates["python"] = gate_subprocess(workdir, winner, plain, "python")
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        gates["python"] = {"error": str(error)}

    report = stage_header("confirm", ["clang", interpreted_path_name()])
    report.update(
        {
            "decide_environment": decide["environment"],
            "rounds": args.rounds,
            "seeds": seeds,
            "fresh_points_seed": args.seed,
            "pairs": pairs,
            "confirmed": confirmed,
            "decide_claims": claims,
            "reversed_cells": reversed_cells,
            "reproduces": reproduces,
            "gates": gates,
            "runs": runs,
            "elapsed_seconds": round(time.perf_counter() - started, 1),
        }
    )
    write_stage(workdir, "confirm", report)
    print(f"{winner}: {'reproduces' if reproduces else 'does NOT reproduce'}")


def gate_subprocess(workdir: Path, name: str, python: list[str], path: str) -> dict:
    output = workdir / f"gate-{name}-{path}.json"
    subprocess.run(
        [
            *python,
            "gate",
            "--workdir",
            str(workdir),
            "--name",
            name,
            "--path",
            path,
            "--output",
            str(output),
        ],
        check=True,
    )
    return json.loads(output.read_text())


# --- the stages' helpers, run as their own processes ----------------------------------


def pairs_stage(args) -> None:
    """Time ``baseline:challenger`` pairs in this process; ``control`` names the control."""
    workdir: Path = args.workdir
    counts_report = read_stage(workdir, "counts")
    control_index = load_control(workdir, counts_report)
    names = {n for pair in args.pairs for n in pair.split(":")} - {"control"}
    trees = load_trees(workdir, counts_report, sorted(names))
    reference = finder_on("clang")
    fixtures = ranking_fixtures(args.points, args.fresh_points, reference)
    finders = {"control": finder_on(args.path, control_index)}
    finders |= {name: finder_on(args.path, tree) for name, tree in trees.items()}
    results = {}
    for pair in args.pairs:
        baseline, challenger = pair.split(":")
        results[pair] = time_pair(
            (baseline, finders[baseline]),
            (challenger, finders[challenger]),
            fixtures,
            points=args.points,
            rounds=args.rounds,
            seed=args.seed,
        )
    for finder in finders.values():
        finder.cleanup()
    reference.cleanup()
    report = stage_header("pairs", [args.path])
    report.update(
        {
            "path": args.path,
            "rounds": args.rounds,
            "seed": args.seed,
            "fresh_points": args.fresh_points,
            "pairs": results,
        }
    )
    args.output.write_text(json.dumps(report, indent=1) + "\n")


def gate_stage(args) -> None:
    """Gate one selected tree on one acceleration path, in this process."""
    workdir: Path = args.workdir
    counts_report = read_stage(workdir, "counts")
    if args.path != "clang" and args.path != interpreted_path_name():
        raise SystemExit(f"this environment cannot run the {args.path} path")
    control_index = load_control(workdir, counts_report)
    tree = load_trees(workdir, counts_report, [args.name])[args.name]
    rng = np.random.default_rng(args.seed)
    gate_points = [p for f in STRATA.values() for p in load_benchmark_points(f)]
    row = gate_row(
        tree,
        control_index,
        gate_points,
        edge_probes(tree, args.probes, rng),
        border_probes(args.probes, rng),
        (args.path,),
    )
    args.output.write_text(json.dumps({"passed": gate_passed(row), "gate": row}) + "\n")


def report_stage(args) -> None:
    """The FINDINGS tables, from whatever stages the workdir holds."""
    workdir: Path = args.workdir
    counts_report = json.loads((workdir / "counts.json").read_text())
    control = counts_report["control"]

    def ratio(row: dict, stratum: str, key: str) -> str:
        return f"{row['counts'][stratum][key] / control['counts'][stratum][key]:.2f}"

    env = counts_report["environment"]
    print(
        f"counts: {counts_report['configurations']} configurations, "
        f"{counts_report['within_cap']} within the cap, "
        f"{len(counts_report['frontier'])} on the frontier "
        f"({counts_report['elapsed_seconds']:.0f} s, {env['cpu']}, commit {env['commit']})\n"
    )
    print(
        "| configuration | bytes | reads rnd / land | tests vs control rnd / land "
        "| vertices vs control rnd / land | reader |"
    )
    print("|---|---|---|---|---|---|")
    for row in counts_report["selected"]:
        c = row["counts"]
        print(
            f"| {row['label']}{' (sentinel)' if row.get('sentinel') else ''} "
            f"| {row['projected_bytes']:,} "
            f"| {c['random']['reads_per_query']:.3f} / {c['on_land']['reads_per_query']:.3f} "
            f"| {ratio(row, 'random', 'tests_per_query')} / "
            f"{ratio(row, 'on_land', 'tests_per_query')} "
            f"| {ratio(row, 'random', 'vertices_per_query')} / "
            f"{ratio(row, 'on_land', 'vertices_per_query')} "
            f"| {'yes' if row['reader_compatible'] else 'no'} |"
        )
    for stage in ("screen", "decide", "confirm"):
        path = workdir / f"{stage}.json"
        if not path.exists():
            continue
        stored = json.loads(path.read_text())
        env = stored["environment"]
        print(f"\n{stage}: {env['cpu']}, {env['logical_cpus']} CPUs, {env['system']}")
        if stage == "screen":
            for name, result in stored["results"].items():
                print(f"- {name}: {result.get('verdicts', 'gate failed')}")
            print(f"A/A level: {stored['aa_level']}; survivors {stored['survivors']}")
        elif stage == "decide":
            for name, cells in stored["against_control"].items():
                print(f"- {name}: {cells}")
            for step in stored["ladder"]:
                print(
                    f"- {step['incumbent']} vs {step['challenger']}: {step['verdicts']}"
                )
            print(f"winner {stored['winner']}, outcome {stored['outcome']}")
        else:
            for pair, cells in stored["confirmed"].items():
                print(f"- {pair}: {cells}")
            print(f"reproduces: {stored['reproduces']}; gates {stored['gates']}")


def all_stages(args) -> None:
    """counts, screen and decide in a row, each with its own rounds and seed."""
    counts_stage(args)
    common = vars(args) | {"keep": args.keep}
    screen_stage(argparse.Namespace(**common | {"rounds": 31, "seed": 1}))
    decide_stage(argparse.Namespace(**common | {"rounds": 61, "seed": 100}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="stage", required=True)

    def stage(name: str, function, **defaults):
        p = sub.add_parser(name)
        p.set_defaults(function=function)
        p.add_argument("--workdir", type=Path, default=Path("tmp/grid-tree-sweep"))
        p.add_argument("--points", type=int, default=2_000)
        p.add_argument("--probes", type=int, default=6_000)
        p.add_argument("--seed", type=int, default=defaults.get("seed", 1))
        return p

    for name, function in (("counts", counts_stage), ("all", all_stages)):
        p = stage(name, function)
        p.add_argument("--finest-columns", type=int, default=FINEST_COLUMNS)
        p.add_argument("--max-configs", type=int, default=24)
        p.add_argument("--selective-prefixes", type=int, default=SELECTIVE_PREFIXES)
        p.add_argument("--only", nargs="*", help="substrings of configuration names")
        if name == "all":
            p.add_argument("--keep", type=int, default=6)
            p.add_argument("--replicates", type=int, default=3)
            p.add_argument("--interpreted-rounds", type=int, default=31)
    p = stage("screen", screen_stage)
    p.add_argument("--rounds", type=int, default=31)
    p.add_argument("--keep", type=int, default=6)
    p = stage("decide", decide_stage, seed=100)
    p.add_argument("--rounds", type=int, default=61)
    p.add_argument("--interpreted-rounds", type=int, default=31)
    p.add_argument("--replicates", type=int, default=3)
    p = stage("confirm", confirm_stage, seed=10_000)
    p.add_argument("--decide", type=Path, help="another machine's decide.json")
    p.add_argument("--rounds", type=int, default=61)
    p.add_argument("--replicates", type=int, default=3)
    p = stage("pairs", pairs_stage)
    p.add_argument("--pairs", nargs="+", required=True)
    p.add_argument("--path", default="clang")
    p.add_argument("--rounds", type=int, default=61)
    p.add_argument("--fresh-points", type=int, default=None)
    p.add_argument("--output", type=Path, required=True)
    p = stage("gate", gate_stage)
    p.add_argument("--name", required=True)
    p.add_argument("--path", default="clang")
    p.add_argument("--output", type=Path, required=True)
    stage("report", report_stage)
    args = parser.parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
