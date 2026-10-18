"""Whether refining the grid tree selectively, by expected work, beats refining it whole.

FINDINGS
========

Exploratory: one server class (Intel Xeon, 4 vCPUs, Linux, Python 3.13, clang), the
2026d boundaries, and no decision rule fixed beforehand, so it can refuse an idea but
not adopt one. It reads ``grid_tree_config_sweep.py``'s deciding run, committed as
``contributing/improvements/measurements/grid-tree-config-sweep-2026-10-18-*.json``;
its own ``counts`` and ``time`` output is committed beside it as
``grid-tree-selective-refinement-2026-10-18-*.json``. Ratios are to the sweep's control
(the shipped cells in legacy order) unless a row says otherwise.

1. **Under full refinement the finest cell width alone sets the polygon work**
   (``patterns``). Every refine-all tree ending at one width offers the same
   candidates and tests the same polygons; the root and the depth set only lookups and
   bytes. The 0.1875-degree trees within the cap all test 0.85x the control's polygons,
   at 1.89 (1.5-degree root, three levels of 2x2) down to 1.28 (0.75-degree root, one
   level of 4x4) lookups per on-land query.

2. **Scalar time follows polygon work; batch time follows depth.** The NumPy batch
   descent spends a fixed set of array passes per level and per selective check, which
   a 256-point batch cannot amortise. Fitted over the 23 screened trees, an extra level
   costs ~12 % and a selective check ~16 % per random batch, and nothing measurable per
   scalar call (R^2 0.69-0.91, on screen numbers, which are biased towards the
   survivors). Every multi-level or selective tree screened was slower than the
   control on random batches (1.05-1.49); the two one-level trees were not (0.94-1.01).
   The sweep's cost model has no per-level term, so it ranks scalar time well (rank
   correlation 0.74 random, 0.81 on land) and random batch time poorly (0.38).

3. **The cap picks the shape.** The finest full refinement within 800 KB is
   0.15625 degrees, and every tree reaching it needs a small root and two or three
   levels. One level of 4x4 reaches 0.1875 degrees at most (0.75-degree root, 696 KB;
   the 0.625-degree root is 889 KB), the shape the sweep's ladder kept. 8x8 blocks are
   over the cap or dominated, one level of 2x2 is too coarse for its bytes, and stacked
   2x2 blocks pay a level for the leaves one level of 4x4 reaches.

4. **Refined selectively, one level gets near that ceiling only from a 0.625-degree
   root with 4x4 blocks** (``counts``). Finer roots (0.5 and 0.46875 degrees) and 8x8
   blocks spend the budget on the root table or on blocks and test 1.1-2.2x the
   control's polygons at 700-800 KB. At 800 KB the 0.625-degree root refines about
   13,500 of its 16,523 multi-zone cells:

   ======================================================  =============  ==============
   tree (tests and vertices per random / on-land query)    tests          vertices
   ======================================================  =============  ==============
   uniform, 0.75-degree root, 696 KB                       0.85 / 0.84    0.89 / 0.84
   uniform, 0.625-degree root, 889 KB (over the cap)       0.72 / 0.74    0.80 / 0.77
   selective, the sweep's stop-index rule                  0.82 / 0.82    0.88 / 0.85
   selective, expected tests (trained)                     0.83 / 0.84    0.87 / 0.86
   selective, expected tests and vertices (trained)        0.82 / 0.82    0.83 / 0.79
   ======================================================  =============  ==============

   Counting vertices is what pays. Pricing a cell by the work its ray casts do, as
   ``scripts/shortcut_ordering.py`` prices a candidate, rather than a flat cost per
   polygon up to the stop index, cuts vertices 6-7 % below the stop-index rule at the
   same tests. Expected tests alone does no better than the stop-index rule: of the
   1,000,000 uniform training points about 110,000 reach a multi-zone root cell, single
   digits per cell, and the ordering optimiser's exact area integrals would not be that
   thin.

5. **None of it is faster than the uniform one-level tree** (``time``: three replicate
   processes of 61 paired rounds, majority per cell, against the 0.75-degree root with
   one level of 4x4). All three trees pass the sweep's gate on clang, 30,000 fixture
   points, 6,000 on their own cell edges and about 6,000 on border lines, with no
   defect.

   * selective encoding, a reader change: random scalar unresolved (0.995-1.022),
     random batch slower (1.103-1.143), on-land scalar unresolved (0.947-0.994),
     on-land batch unresolved (1.036-1.081);
   * shared uniform blocks, the shipped reader: random scalar no difference
     (0.997-1.028), random batch slower (1.029-1.048), on-land scalar unresolved
     (0.981-1.021), on-land batch slower (1.023-1.076).

   The shared encoding points every unrefined multi-zone cell at one 4x4 block per
   distinct list, so the shipped reader reads it unchanged; the 23 KB those blocks cost
   leave fewer cells refined (tests 0.88x). It runs the baseline's reader code with
   fewer lookups and is still slower per batch, most likely the 332 KB root table
   against 230 KB, which is not measured here.

6. **Better selection cannot rescue it.** The polygon loop is a minor share of a query
   (about 112 of 650 ns per random scalar call, by ``query_stage_profile.py`` as the
   sweep's cost model quotes it), so a 6 % vertex cut is worth 1-3 % of query time,
   under the 3 % a paired comparison calls faster. A selective tree of three levels
   would need about a quarter of the control's vertex work to pay its batch cost back
   by finding 2's fit, and the finest refine-all trees swept (0.0625 degrees, 2.3 MB and
   up) reach 0.43x.

**Reopen** with a compiled batch lookup, where a level costs nanoseconds rather than
array passes, so the selective trees' scalar lead (0.89 on-land scalar in the sweep's
screen) is no longer paid back per batch; then select by the ordering optimiser's exact
integrals rather than a point sample.

METHOD
======

* **patterns** reads the sweep's three committed stage files: the refine-all trees
  within the cap grouped by finest width, the screen's ratios by structure, a least
  squares of each cell's ratio on relative vertices, lookups, extra levels and
  selectivity, and the rank correlation of the sweep's ``estimated_ns`` with each cell.
* **counts** builds one-level trees with the sweep's own catalogs, packer, budget loop
  and point oracle, so its counts are exact on the committed random and on-land
  fixtures and comparable with the sweep's. ``stop`` selects with the sweep's
  ``select_refinement``. ``tests`` and ``tests+vertices`` keep its Lagrangian but take
  each multi-zone root cell's cost, left as a leaf or refined, from a training sample:
  points uniform on the sphere under ``TRAIN_SEED``, a stream the fixtures never use,
  each answered by the shipped kernel and counted as the oracle counts. Vertices are
  priced so the control's mean vertex work equals its mean test work, then averaged
  with the tests.
* **time** builds ``CANDIDATE`` in both encodings and ``BASELINE`` uniformly, gates each
  against the control with the sweep's gate, saves them, and times each candidate
  against the baseline with ``time_pair`` (one process, order-alternated, 2,000 points
  per stratum) in replicate processes, each refusing data other than the data the
  trees were built from.

USAGE
=====

::

    uv run python -m prototypes.grid_tree_selective_refinement patterns
    uv run python -m prototypes.grid_tree_selective_refinement counts
    uv run python -m prototypes.grid_tree_selective_refinement time
"""

import argparse
import json
import re
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np

import prototypes.grid_tree_config_sweep as sweep
from prototypes.latlng_index_bench import (
    KX,
    KY,
    RANKING_STRATA,
    STRATA,
    X_SPAN,
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
    polygons_of,
    time_pair,
)
from tests.auxiliaries import load_benchmark_points
from timezonefinder import utils
from timezonefinder.configs import OCEAN_TIMEZONE_PREFIX
from timezonefinder.shortcut_index import ABSENT

MODULE = "prototypes.grid_tree_selective_refinement"
#: The sweep's deciding run, committed as JSON: what ``patterns`` reads.
SWEEP_RUN = Path(
    "contributing/improvements/measurements/grid-tree-config-sweep-2026-10-18"
)
#: One-level shapes whose full refinement is over the cap: (root columns, block side).
SHAPES = ((576, 4), (720, 4), (768, 4), (288, 8), (384, 8), (480, 8))
BUDGETS = (700_000, 800_000)
#: ``stop`` is the sweep's own rule (``select_refinement``); the others replace its
#: leaf cost by the expected work a uniform training sample measures.
METRICS = ("stop", "tests", "tests+vertices")
TRAIN_POINTS = 1_000_000
TRAIN_SEED = 20_261_018
#: The shape the timing builds and the uniformly refined tree it is timed against.
CANDIDATE = (576, 4, 800_000, "tests+vertices")
BASELINE = (480, 4)


def header(stage: str) -> dict:
    return {
        "schema": 1,
        "stage": stage,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "command": f"uv run python -m {MODULE} " + " ".join(sys.argv[1:]),
        "environment": environment(["clang"]),
        "data_digest": sweep.data_digest(),
    }


# --- patterns: what the sweep's deciding run says about shape ------------------------


def patterns_stage(args) -> None:
    """The sweep's run, re-read: what sets polygon work, scalar time and batch time."""
    run = {
        s: json.loads(Path(f"{args.sweep_run}-{s}.json").read_text())
        for s in ("counts", "screen", "decide")
    }
    rows = {r["name"]: r for r in run["counts"]["rows"]}
    control = run["counts"]["control"]["counts"]

    def finest(row: dict) -> float:
        width = 360 / row["spec"]["root_columns"]
        for side in row["spec"]["sides"]:
            width /= side
        return width

    print("full refinement within the cap, grouped by finest cell width:")
    groups: dict[float, list[dict]] = {}
    for row in rows.values():
        if row["within_cap"] and not row["spec"]["budget"]:
            groups.setdefault(round(finest(row), 6), []).append(row)
    for width in sorted(groups)[:4]:
        members = sorted(groups[width], key=lambda r: r["projected_bytes"])
        tests = {r["selectivity_vs_control"] for r in members}
        listed = ", ".join(
            f"{r['name']} {r['projected_bytes'] // 1000} KB "
            f"{r['counts']['on_land']['reads_per_query']:.2f} reads"
            for r in members
        )
        print(f"  {width:.5f} deg, tests x{sorted(tests)}: {listed}")

    cells = [f"{s}/{shape}" for s, shape in sweep.CELLS]
    results = run["screen"]["results"]

    def ratio(name: str, cell: str) -> float:
        stratum, shape = cell.split("/")
        c = results[name]["timing"][stratum][shape]
        return c["best_challenger"] / c["best_baseline"]

    def kind(row: dict) -> str:
        if row["spec"]["budget"]:
            return "selective"
        return f"{len(row['spec']['sides'])} level(s)"

    print("\nscreen, ratio to the control by structure (biased to survivors):")
    for k in sorted({kind(rows[n]) for n in results}):
        names = [n for n in results if kind(rows[n]) == k]
        spans = "  ".join(
            f"{c} {min(ratio(n, c) for n in names):.2f}-{max(ratio(n, c) for n in names):.2f}"
            for c in cells
        )
        print(f"  {k:11} ({len(names):2}): {spans}")

    print(
        "\nleast squares, ratio - 1 ~ vertices/control - 1, lookups - control's,"
        " extra levels, selective:"
    )
    for cell in cells:
        stratum = cell.split("/")[0]
        x, y = [], []
        for name in results:
            row = rows[name]
            c = row["counts"][stratum]
            x.append(
                [
                    c["vertices_per_query"] / control[stratum]["vertices_per_query"]
                    - 1,
                    c["reads_per_query"] - control[stratum]["reads_per_query"],
                    len(row["spec"]["sides"]) - 1,
                    1.0 if row["spec"]["budget"] else 0.0,
                ]
            )
            y.append(ratio(name, cell) - 1)
        a, b = np.array(x), np.array(y)
        fit, *_ = np.linalg.lstsq(a, b, rcond=None)
        r2 = 1 - ((b - a @ fit) ** 2).sum() / ((b - b.mean()) ** 2).sum()
        print(
            f"  {cell:18} vertices {fit[0]:+.3f}  per lookup {fit[1]:+.3f}  "
            f"per extra level {fit[2]:+.3f}  selective {fit[3]:+.3f}  R2 {r2:.2f}"
        )

    def rank(values: Sequence[float]) -> np.ndarray:
        return np.argsort(np.argsort(values))

    estimate = [rows[n]["estimated_ns"] for n in results]
    spearman = "  ".join(
        f"{c} {np.corrcoef(rank(estimate), rank([ratio(n, c) for n in results]))[0, 1]:+.2f}"
        for c in cells
    )
    print(f"\nrank correlation of the sweep's cost model with the screen: {spearman}")
    decide = run["decide"]
    for step in decide["ladder"]:
        print(
            f"ladder {step['incumbent']} -> {step['challenger']}: {step['verdicts']}"
            f" -> {'displaces' if step['displaces'] else 'holds'}"
        )
    print(f"winner {decide['winner']}, outcome {decide['outcome']}")


# --- the trees -------------------------------------------------------------------------


class Bench:
    """The sweep's building blocks, set up once: catalogs, the point oracle, the control."""

    def __init__(self, workdir: Path):
        workdir.mkdir(parents=True, exist_ok=True)
        self.reference = finder_on("clang")
        r = self.reference
        self.data = OrderingInput(r.boundaries, r.zone_ids, r.zone_names.names)
        ocean = np.array(
            [bool(re.match(OCEAN_TIMEZONE_PREFIX, n)) for n in r.zone_names.names]
        )
        self.lists = sweep.ListCatalog(self.data, ocean)
        self.catalog = sweep.CellCatalog(polygons_of(r), self.lists)
        self.oracle = sweep.PointOracle(
            r, {s: load_benchmark_points(STRATA[s]) for s in RANKING_STRATA}
        )
        self.control = build_control(
            r.shortcuts, self.data, r.zone_ids, workdir / "control.bin"
        )
        self.list_ratio = entries_file_bytes(r.shortcuts) / entries_file_bytes(
            self.control
        )
        self.control_counts = self.oracle.counts(sweep.tree_of_shipped(self.control))
        self.sample = TrainingSample(r, TRAIN_POINTS, TRAIN_SEED)

    def projected_bytes(self, tree: sweep.Tree) -> int:
        """The sweep's projection: exact bytes, lists scaled as the converter packs them."""
        entries = entries_file_bytes(tree)
        return round(tree.payload_bytes - entries + entries * self.list_ratio)

    def row(self, name: str, tree: sweep.Tree, **extra) -> dict:
        counts = self.oracle.counts(tree)
        row = {
            "name": name,
            "projected_bytes": self.projected_bytes(tree),
            "reader_compatible": tree.reader_compatible,
            "counts": counts,
            "relative": {
                s: {
                    k: counts[s][k] / self.control_counts[s][k]
                    for k in ("tests_per_query", "vertices_per_query")
                }
                for s in RANKING_STRATA
            },
            "estimated_ns": sweep.estimated_ns(counts),
            **extra,
        }
        rel = row["relative"]
        print(
            f"{name:34} {row['projected_bytes']:>9,} B  lookups "
            f"{counts['random']['reads_per_query']:.3f}/{counts['on_land']['reads_per_query']:.3f}"
            f"  tests x{rel['random']['tests_per_query']:.3f}/x{rel['on_land']['tests_per_query']:.3f}"
            f"  vertices x{rel['random']['vertices_per_query']:.3f}/x{rel['on_land']['vertices_per_query']:.3f}",
            flush=True,
        )
        return row

    def fit(
        self,
        budget: int,
        select: Callable[[float], list[np.ndarray]],
        build: Callable[[list[np.ndarray]], sweep.Tree],
    ) -> tuple[sweep.Tree, list[np.ndarray]] | None:
        """The sweep's budget loop: the largest tree whose projected bytes fit."""
        target = float(budget)
        best = None
        for _ in range(12):
            refine = select(target)
            tree = build(refine)
            size = self.projected_bytes(tree)
            fits = size <= budget
            if fits and (best is None or size > best[0]):
                best = (size, tree, refine)
            if fits and size >= budget - sweep.BUDGET_SLACK:
                break
            target += budget - size - (0 if fits else 1_000)
        return None if best is None else (best[1], best[2])

    def selector(
        self, spec: sweep.TreeSpec, metric: str
    ) -> Callable[[float], list[np.ndarray]]:
        levels = self.catalog.levels(spec.root_columns, spec.sides)
        if metric == "stop":
            return lambda target: sweep.select_refinement(
                spec, levels, self.lists, target
            )
        return self.trained_selector(spec, levels, metric)

    def trained_selector(
        self, spec: sweep.TreeSpec, levels: list[sweep.Level], metric: str
    ) -> Callable[[float], list[np.ndarray]]:
        """``select_refinement`` at depth 1, with each cell's leaf cost and its children's
        costs replaced by the expected work per query the training sample measures."""
        root, child = levels
        k = spec.sides[0]
        sample = self.sample
        x, y = sample.xy
        w0, w1 = spec.widths[0], spec.widths[1]
        cell = (y // w0) * spec.root_columns + x // w0
        inside = np.flatnonzero(root.values[cell] <= sweep.MULTI_LIMIT)
        rank = np.searchsorted(root.multi, cell[inside])
        child_at = (
            rank * k * k
            + ((y[inside] // w1) & (k - 1)) * k
            + ((x[inside] // w1) & (k - 1))
        )
        full_spec = sweep.TreeSpec(spec.root_columns, spec.sides)
        full = sweep.make_tree(full_spec, *sweep.pack(full_spec, levels, self.lists))
        unrefined = sweep.make_tree(
            spec,
            *sweep.pack(
                spec, levels, self.lists, [np.zeros(len(root.multi), dtype=bool)]
            ),
        )
        tests_leaf, vertices_leaf = sample.work(unrefined, inside)
        tests_refined, vertices_refined = sample.work(full, inside)
        if metric == "tests":
            leaf, refined = sweep.TEST_NS * tests_leaf, sweep.TEST_NS * tests_refined
        else:
            # vertices priced so the control's mean vertex work equals its mean test work
            c = self.control_counts["random"]
            per_vertex = sweep.TEST_NS * c["tests_per_query"] / c["vertices_per_query"]
            leaf = 0.5 * (sweep.TEST_NS * tests_leaf + per_vertex * vertices_leaf)
            refined = 0.5 * (
                sweep.TEST_NS * tests_refined + per_vertex * vertices_refined
            )
        n = len(sample.lngs)
        leaf_ns = np.bincount(rank, weights=leaf, minlength=len(root.multi)) / n
        share = np.bincount(rank, minlength=len(root.multi)) / n
        child_ns = np.bincount(child_at, weights=refined, minlength=len(child.values))
        children_ns = (child_ns / n).reshape(-1, k * k).sum(axis=1)

        def list_bytes(level: sweep.Level) -> np.ndarray:
            sets = (-2 - level.values[level.multi]).tolist()
            return np.array(
                [2 * len(self.lists.sets[s]) + 5 for s in sets], dtype=np.float64
            )

        leaf_bytes = list_bytes(root)
        child_bytes = np.zeros(len(child.values))
        child_bytes[child.multi] = list_bytes(child)
        children_bytes = child_bytes.reshape(-1, k * k).sum(axis=1)
        block = 2.0 * k * k

        def solve(lam: float) -> tuple[np.ndarray, float]:
            refine = (
                share * sweep.READ_NS + lam * (block + children_bytes) + children_ns
                < leaf_ns + lam * leaf_bytes
            )
            size = (
                float(spec.root_columns**2)
                + (block + children_bytes)[refine].sum()
                + leaf_bytes[~refine].sum()
            )
            return refine, size

        def select(target: float) -> list[np.ndarray]:
            low, high = -12.0, 3.0
            refine, _ = solve(10.0**high)
            for _ in range(40):
                middle = (low + high) / 2
                candidate, size = solve(10.0**middle)
                if size <= target:
                    high, refine = middle, candidate
                else:
                    low = middle
            return [refine]

        return select

    def selective(self, spec: sweep.TreeSpec, metric: str):
        levels = self.catalog.levels(spec.root_columns, spec.sides)
        return self.fit(
            spec.budget,
            self.selector(spec, metric),
            lambda refine: sweep.make_tree(
                spec, *sweep.pack(spec, levels, self.lists, refine)
            ),
        )

    def shared(self, spec: sweep.TreeSpec, metric: str):
        """The same selection, encoded so the shipped reader reads it unchanged."""
        levels = self.catalog.levels(spec.root_columns, spec.sides)
        full = sweep.TreeSpec(spec.root_columns, spec.sides)
        return self.fit(
            spec.budget,
            self.selector(spec, metric),
            lambda refine: sweep.make_tree(
                full, *pack_shared(full, levels, self.lists, refine[0])
            ),
        )


class TrainingSample:
    """Points uniform on the sphere, drawn under a seed the fixtures never use, and which
    polygons hold each - found lazily, only for points that reach a candidate list."""

    def __init__(self, reference, count: int, seed: int):
        rng = np.random.default_rng(seed)
        self.lngs = rng.uniform(-180.0, 180.0, count)
        self.lats = np.degrees(np.arcsin(rng.uniform(-1.0, 1.0, count)))
        x = (self.lngs * F).astype(np.int64) + KX
        np.add(x, X_SPAN, out=x, where=x < 0)
        self.xy = x, np.maximum((self.lats * F).astype(np.int64) + KY, 0)
        self.reference = reference
        b = reference.boundaries
        self.boxes = [
            np.asarray(a, dtype=np.int64) for a in (b.xmin, b.xmax, b.ymin, b.ymax)
        ]
        self.vertices = np.asarray(b.nr_vertices, dtype=np.int64).tolist()
        self._truth: dict[int, tuple[set[int], set[int]]] = {}

    def truth(self, i: int) -> tuple[set[int], set[int]]:
        found = self._truth.get(i)
        if found is None:
            x, y = utils.query2int(float(self.lngs[i]), float(self.lats[i]))
            xmin, xmax, ymin, ymax = self.boxes
            hits = np.flatnonzero(
                (xmin <= x) & (x <= xmax) & (ymin <= y) & (y <= ymax)
            ).tolist()
            found = self._truth[i] = (
                {h for h in hits if self.reference.inside_of_polygon(h, x, y)},
                set(hits),
            )
        return found

    def work(
        self, tree: sweep.Tree, points: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Per point, as ``PointOracle.counts`` counts: polygons tested, and the vertices of
        those whose bounding box holds the point."""
        entries, _ = sweep.descend(tree, self.lngs[points], self.lats[points])
        tests = np.zeros(len(points))
        vertices = np.zeros(len(points))
        lists: dict[int, tuple[list[int], int]] = {}
        for j in np.flatnonzero(entries < ABSENT).tolist():
            entry = int(entries[j])
            found = lists.get(entry)
            if found is None:
                found = lists[entry] = (
                    tree.candidates_of(entry).tolist(),
                    tree.stop_index_of(entry),
                )
            candidates, stop = found
            inside, boxed = self.truth(int(points[j]))
            tested = stop
            for position in range(stop):
                if candidates[position] in inside:
                    tested = position + 1
                    break
            tests[j] = tested
            vertices[j] = sum(
                self.vertices[c] for c in candidates[:tested] if c in boxed
            )
        return tests, vertices


def pack_shared(
    spec: sweep.TreeSpec,
    levels: list[sweep.Level],
    lists: sweep.ListCatalog,
    refine: np.ndarray,
):
    """One level in the shipped format: a refined multi-zone root cell holds its own
    block, an unrefined one the uniform block every unrefined cell with its list shares.

    Selective refinement the shipped reader reads unchanged, at one block per distinct
    unrefined list and one more read for the queries landing in those cells.
    """
    root, child = levels
    q = spec.sides[0] ** 2
    packer = sweep.ListPacker(lists)
    values = root.values.astype(np.int64)
    sets = (-2 - values[root.multi]).tolist()
    blocks = []
    for i in np.flatnonzero(refine).tolist():
        children = child.values[i * q : (i + 1) * q].astype(np.int64)
        for j in np.flatnonzero(children <= sweep.MULTI_LIMIT).tolist():
            children[j] = -(packer.entry(int(-2 - children[j])) + 2)
        blocks.append(children)
    block_of = np.empty(len(sets), dtype=np.int64)
    block_of[refine] = np.arange(len(blocks))
    uniform: dict[int, int] = {}
    for rank in np.flatnonzero(~refine).tolist():
        s = sets[rank]
        if s not in uniform:
            uniform[s] = len(blocks)
            blocks.append(np.full(q, -(packer.entry(s) + 2), dtype=np.int64))
        block_of[rank] = uniform[s]
    values[root.multi] = -(block_of + 2)
    bounds, payload, last_change = packer.arrays()
    return (
        sweep.narrow(values),
        [sweep.narrow(np.concatenate(blocks))],
        bounds,
        payload,
        last_change,
    )


# --- counts and timing -----------------------------------------------------------------


def counts_stage(args) -> None:
    started = time.perf_counter()
    bench = Bench(args.workdir)
    rows = []
    print("uniformly refined, for reference:")
    for root_columns, side in (
        (sweep.SHIPPED.root_columns, sweep.SHIPPED.sides[0]),
        BASELINE,
    ):
        spec = sweep.TreeSpec(root_columns, (side,))
        levels = bench.catalog.levels(root_columns, (side,))
        tree = sweep.make_tree(spec, *sweep.pack(spec, levels, bench.lists))
        rows.append(bench.row(spec.name, tree))
    print("\none level, refined selectively:")
    for metric in METRICS:
        for root_columns, side in SHAPES:
            for budget in BUDGETS:
                spec = sweep.TreeSpec(root_columns, (side,), budget)
                found = bench.selective(spec, metric)
                if found is None:
                    print(f"{spec.name} [{metric}]: nothing fits", flush=True)
                    continue
                tree, refine = found
                root = bench.catalog.levels(root_columns, (side,))[0]
                unrefined = set((-2 - root.values[root.multi[~refine[0]]]).tolist())
                rows.append(
                    bench.row(
                        f"{spec.name} [{metric}]",
                        tree,
                        refined=int(refine[0].sum()),
                        multi_zone_root_cells=len(refine[0]),
                        shared_block_bytes=len(unrefined) * 2 * side * side,
                    )
                )
    report = header("counts")
    report.update(
        {
            "train": {"points": TRAIN_POINTS, "seed": TRAIN_SEED},
            "control": bench.control_counts,
            "rows": rows,
            "elapsed_seconds": round(time.perf_counter() - started, 1),
        }
    )
    (args.workdir / "counts.json").write_text(json.dumps(report, indent=1) + "\n")
    print(f"\nwrote {args.workdir / 'counts.json'} in {report['elapsed_seconds']} s")
    bench.reference.cleanup()


def time_stage(args) -> None:
    """Build, gate and save the candidates, then time them in replicate processes."""
    started = time.perf_counter()
    bench = Bench(args.workdir)
    root_columns, side, budget, metric = CANDIDATE
    spec = sweep.TreeSpec(root_columns, (side,), budget)
    baseline_spec = sweep.TreeSpec(BASELINE[0], (BASELINE[1],))
    levels = bench.catalog.levels(BASELINE[0], (BASELINE[1],))
    trees = {
        baseline_spec.name: (
            baseline_spec,
            sweep.make_tree(
                baseline_spec, *sweep.pack(baseline_spec, levels, bench.lists)
            ),
        ),
        f"{spec.name}_selective": (spec, bench.selective(spec, metric)[0]),
        f"{spec.name}_shared": (
            sweep.TreeSpec(root_columns, (side,)),
            bench.shared(spec, metric)[0],
        ),
    }
    rng = np.random.default_rng(args.seed)
    gate_points = [p for f in STRATA.values() for p in load_benchmark_points(f)]
    saved = {}
    for name, (tree_spec, tree) in trees.items():
        row = bench.row(name, tree)
        gate = gate_row(
            tree,
            bench.control,
            gate_points,
            edge_probes(tree, args.probes, rng),
            border_probes(args.probes, rng),
            ("clang",),
        )
        if not gate_passed(gate):
            raise SystemExit(f"{name} fails the gate: {gate}")
        saved[name] = {
            "spec": tree_spec.as_json(),
            "sha256": sweep.save_tree(tree, args.workdir / f"{name}.npz"),
            "row": row,
            "gate": gate,
        }
    report = header("time")
    report.update({"baseline": baseline_spec.name, "candidates": saved})
    (args.workdir / "candidates.json").write_text(json.dumps(report, indent=1) + "\n")

    replicates = []
    for seed in range(args.seed_base, args.seed_base + args.replicates):
        output = args.workdir / f"pairs-{seed}.json"
        subprocess.run(
            [
                sys.executable,
                "-m",
                MODULE,
                "pairs",
                "--workdir",
                str(args.workdir),
                "--seed",
                str(seed),
                "--rounds",
                str(args.rounds),
                "--points",
                str(args.points),
                "--output",
                str(output),
            ],
            check=True,
        )
        replicates.append(json.loads(output.read_text()))
    verdicts = {}
    for pair in replicates[0]["pairs"]:
        runs = [r["pairs"][pair] for r in replicates]
        verdicts[pair] = sweep.majority([sweep.verdicts(run) for run in runs])
        print(f"\n{pair}: majority of {len(runs)} replicates")
        for stratum, shape in sweep.CELLS:
            ratios = [
                run[stratum][shape]["best_challenger"]
                / run[stratum][shape]["best_baseline"]
                for run in runs
            ]
            print(
                f"  {stratum}/{shape}: {verdicts[pair][f'{stratum}/{shape}']}"
                f" (ratios {min(ratios):.3f}-{max(ratios):.3f})"
            )
    report.update(
        {
            "rounds": args.rounds,
            "seeds": [r["seed"] for r in replicates],
            "replicate_runs": replicates,
            "verdicts": verdicts,
            "elapsed_seconds": round(time.perf_counter() - started, 1),
        }
    )
    (args.workdir / "time.json").write_text(json.dumps(report, indent=1) + "\n")
    print(f"\nwrote {args.workdir / 'time.json'} in {report['elapsed_seconds']} s")
    bench.reference.cleanup()


def pairs_stage(args) -> None:
    """Time each saved candidate against the baseline, in this process."""
    saved = json.loads((args.workdir / "candidates.json").read_text())
    if saved["data_digest"] != sweep.data_digest():
        raise SystemExit("the packaged data changed since the candidates were built")
    finders = {
        name: finder_on(
            "clang",
            sweep.load_tree(
                sweep.TreeSpec.of_json(c["spec"]),
                args.workdir / f"{name}.npz",
                c["sha256"],
            ),
        )
        for name, c in saved["candidates"].items()
    }
    reference = finder_on("clang")
    fixtures = sweep.ranking_fixtures(args.points, None, reference)
    baseline = saved["baseline"]
    pairs = {}
    for name in finders:
        if name == baseline:
            continue
        pairs[f"{baseline}:{name}"] = time_pair(
            (baseline, finders[baseline]),
            (name, finders[name]),
            fixtures,
            points=args.points,
            rounds=args.rounds,
            seed=args.seed,
        )
    for finder in [*finders.values(), reference]:
        finder.cleanup()
    report = header("pairs")
    report.update({"seed": args.seed, "rounds": args.rounds, "pairs": pairs})
    args.output.write_text(json.dumps(report, indent=1) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("patterns")
    p.set_defaults(function=patterns_stage)
    p.add_argument("--sweep-run", default=str(SWEEP_RUN))
    for name, function in (
        ("counts", counts_stage),
        ("time", time_stage),
        ("pairs", pairs_stage),
    ):
        p = sub.add_parser(name)
        p.set_defaults(function=function)
        p.add_argument("--workdir", type=Path, default=Path("tmp/grid-tree-selective"))
        p.add_argument("--points", type=int, default=2_000)
        p.add_argument("--rounds", type=int, default=61)
        p.add_argument("--seed", type=int, default=1)
        if name == "time":
            p.add_argument("--probes", type=int, default=6_000)
            p.add_argument("--replicates", type=int, default=3)
            p.add_argument("--seed-base", type=int, default=100)
        if name == "pairs":
            p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
