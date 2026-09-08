# PERF-7 — answer a fully covered ambiguous cell without geometry


## Related memory

- [Query performance and shortcut index decisions](../../decisions/query-performance-and-shortcut-index-decisions.md) — why *re-ordering* a cell's candidates is refused; this item removes the loop instead of re-ordering it, so that refusal does not cover it.
- [Geometry data format and validation decisions](../../decisions/geometry-data-format-and-validation-decisions.md) — the 2026-08-21 decision that a correctness property is never expressed in terms of the H3 shortcut index, and the 2026-09-02 refusal of a zone-precedence *engine*. The rule below is bound by both: it is a zone-level relation derived from geometry, evaluated once, not a per-cell rule and not maintained configuration.
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- `prototypes/shortcut_ordering_optimum.py` — the study that produced the counts below; its `areas` stage prints them, and re-running it after a dataset or resolution change re-derives them. Landing separately.

## The observation

Some ambiguous cells are covered **entirely** by the polygons of a single zone. No query point in such a cell can fall outside that zone, so the cell needs no point-in-polygon test at all: the shortcut index could store it as a unique-zone cell, which the reader already supports and which costs one table read.

Measured over 2026c at H3 resolution 4: **826 of 31,368 ambiguous cells (2.63 %) are fully covered by one zone**, and 1,124 to within 1e-4 of full.

## What it is worth

An ambiguous query is ~5,150 ns and a unique one ~1,000 ns, so converting those cells moves ~2.63 % of ambiguous queries onto a path ~4,150 ns cheaper — **~109 ns, or 2.12 % of an ambiguous query**, and ~0.85 % of a mixed workload if queries are uniform over cells. That is about **three times what the provably optimal candidate ordering was worth** (0.27 %, refused), because it removes the geometry rather than reordering it — and it is not bounded by the candidate loop's 14.7 % share the way any ordering change is. The index does not grow, and does not measurably shrink either: converting 743 cells left the binary the same size, because the table is fixed and the candidate lists deduplicate.

The per-cell count is not a query share. Weighting by real traffic needs the fixtures rather than the cell count; `count` in the prototype is the instrument.

## The precedence rule, decided

**Decided 2026-09-08.** Precedence is set by a documented heuristic, and it is used **only in shortcut cells that one polygon covers entirely** — the scope is what makes it tractable. Within that scope the rule is *containment*: of two overlapping zones, the one for which the shared area is the larger share of **itself** is the enclave and takes precedence. It is a property of the two zones, computed once from their full geometry, so it is the same in every cell and does not express a correctness property in terms of the H3 index.

Refused along the way, and kept so they are not re-proposed:

- **Smaller total zone area wins.** Reproduces containment's answers on this dataset (0 of 118 pairs disagree) but proxies "more specific" by size rather than deriving it, is latitude-distorted in the planar coordinates the package works in, and can flip on a boundary redraw. GH-513 records the size-derived rule failing on 20 of 216 edges of the *hole* relation, systematically on the ocean zones.
- **Lower polygon or zone id wins.** Ids follow upstream GeoJSON feature order — the packaged zone names are not sorted — so a zone added upstream shifts them and flips a winner with no geometry change.
- **Deciding per cell** (the smaller polygon beside a covering one). Not consistent: of the 7 zone pairs it rules on, 2 get opposite winners in different cells, because "covers *this* cell" is a property of the cell. Two points in one overlap region either side of a cell boundary would be answered differently.

## What the rule has to decide, and what it costs

Scoping to covered cells is what removes the tie-break problem. Across the whole index 118 zone pairs overlap, most of them coastal slivers where both containments round to zero — but **none of those occur in a covered cell**. What the conversion actually has to order is:

| | pairs |
|---|---:|
| among the covering zones of a covered cell | **2** — `Asia/Urumqi` over `Asia/Shanghai` (100.0 % vs 17.7 %), `Africa/Juba` over `Africa/Khartoum` (3.6 % vs 1.2 %) |
| a coverer against a smaller overlapping candidate | 7, margins 1.1x to 281x |

Every one has a clear winner; none is a near-tie. **The relation over all 118 pairs is acyclic**, checked by topological sort, so a global order exists — which is the feasibility question GH-513 left open when the *hole* relation turned out cyclic.

**What it moves.** Converting the 826 cells to their containment winner: **743 convert, 0 unresolved**. Over the committed fixtures the answers move on **2 of 5,000 ambiguous points, and none of the 10,000 random or 10,000 on-land ones**. That is a count over one sample, not a property: the rule *decides* precedence, so wherever it differs from the ordering today happens to produce, the answer changes by design. The fixtures bound how often a real workload reaches such a point; they do not establish that none does, and the item does not need them to. Point-in-polygon tests fall **2.6 % on ambiguous, 2.1 % on random and 4.4 % on on-land**, and the index does not grow.

**The whole-query effect is not resolvable.** Paired and order-alternated on the C-extension backend, 61 rounds x 2,500 points: no difference on ambiguous (31 of 61) and random (32 of 61), `unresolved` on on-land (best round −3.1 %, 29 of 61), control clean. That is what the ceiling predicts — 2.12 % of an ambiguous query is under the 3–9 % noise floor — and it is the same result every candidate reordering got, for the same reason: the loop is overhead-bound. The count is the evidence here, not the clock.

- **Size:** M — a converter change in `scripts/shortcuts.py` plus a coverage computation needing `shapely` at build time, the regenerated index, and the moved-answer diff.
- **Status:** open — the precedence question is decided (above) and the route is measured; what is left is the converter change, the regenerated index and the moved-answer diff. Found 2026-09-07 while measuring polygon overlap for the candidate-ordering work; nothing has been implemented.
