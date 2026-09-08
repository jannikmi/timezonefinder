# PERF-7 — answer a fully covered ambiguous cell without geometry


## Related memory

- [Query performance and shortcut index decisions](../../decisions/query-performance-and-shortcut-index-decisions.md) — why *re-ordering* a cell's candidates is refused; this item removes the loop instead of re-ordering it, so that refusal does not cover it.
- [Geometry data format and validation decisions](../../decisions/geometry-data-format-and-validation-decisions.md) — the 2026-08-21 decision that a correctness property is never expressed in terms of the H3 shortcut index. That is what this item runs into.
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- `prototypes/shortcut_ordering_optimum.py` — the study that produced the counts below; its `areas` stage prints them, and re-running it after a dataset or resolution change re-derives them. Landing separately.

## The observation

Some ambiguous cells are covered **entirely** by the polygons of a single zone. No query point in such a cell can fall outside that zone, so the cell needs no point-in-polygon test at all: the shortcut index could store it as a unique-zone cell, which the reader already supports and which costs one table read.

Measured over 2026c at H3 resolution 4: **826 of 31,368 ambiguous cells (2.63 %) are fully covered by one zone**, and 1,124 to within 1e-4 of full.

## What it is worth

An ambiguous query is ~5,150 ns and a unique one ~1,000 ns, so converting those cells moves ~2.63 % of ambiguous queries onto a path ~4,150 ns cheaper — **~109 ns, or 2.12 % of an ambiguous query**, and ~0.85 % of a mixed workload if queries are uniform over cells. That is about **three times what the provably optimal candidate ordering was worth** (0.27 %, refused), because it removes the geometry rather than reordering it — and it is not bounded by the candidate loop's 14.7 % share the way any ordering change is. It also *shrinks* the index: a unique cell stores one zone id instead of a candidate list.

The per-cell count is not a query share. Weighting by real traffic needs the fixtures rather than the cell count; `count` in the prototype is the instrument.

## Why it is not simply free

Where a zone covers the whole cell, every other candidate in that cell necessarily overlaps it — so choosing the covering zone is choosing which of two overlapping zones answers. Splitting the 826:

- **2 cells** where every other candidate has zero area inside the cell. Converting those is answer-preserving, and worth 0.01 % of an ambiguous query — nothing.
- **824 cells** where another zone genuinely overlaps. Converting those **changes the answer** for points in the overlap, from whatever today's ordering happens to reach first to the covering zone always.

So essentially the whole gain is a precedence decision. Two things make it a real question rather than an obvious yes. Today's answer on those points is already arbitrary — it falls out of a vertex-count sort, and any reordering moves it (up to 158 of 5,000 ambiguous fixture points; see the ordering decisions). And the recorded decision of 2026-08-21 forbids expressing a correctness property in terms of the H3 index: "fully covered" is a property of a *cell*, so this makes which zone answers depend on the index's resolution, and a later resolution change would silently move those answers rather than only performance.

- **Decision needed:** may the converter answer an ambiguous cell that one zone covers entirely with that zone, changing which of two overlapping upstream zones wins on ~824 cells? **Consequences:** ~2.12 % of an ambiguous query and a slightly smaller index, against making zone precedence depend on the shortcut index's resolution — the thing the 2026-08-21 decision was taken to prevent — so a future resolution change would move answers, not just timings. **Options:** (a) **adopt it as stated** — largest gain, and it makes an already-arbitrary precedence explicit and stable rather than a side effect of a sort key; (b) **adopt only the answer-preserving subset** — zero risk, and worth nothing (2 cells); (c) **refuse it** and keep precedence out of the index entirely; (d) **derive precedence at the zone level first** (which zone wins wherever two overlap, globally) and then apply this as a pure optimisation that cannot change an answer — principled, but GH-513 established that the zone-level precedence relation over holes is cyclic, so this needs its own feasibility study for the overlap case. **Trade-offs:** (a) buys the most and spends the recorded decision; (c) costs the gain but keeps one rule intact; (d) is correct-by-construction and much larger. **Recommendation:** (d) if the zone-level relation turns out acyclic for overlaps, otherwise (a) with the answer diff reviewed as a data-update-style artifact, since the answers it changes are ones no rule currently pins. **Reversibility:** the converter change is one release to undo, but the answers it moves are user-visible, so reversing it moves them back. **Unpriced:** how many of the 824 are real upstream overlaps like `Asia/Urumqi` inside `Asia/Shanghai` versus artefacts of the boundary data, and whether `tzfpy` and other implementations agree with the covering zone on them.

- **Size:** M — a converter change in `scripts/shortcuts.py` plus a coverage computation needing `shapely` at build time, the regenerated index, and the moved-answer diff.
- **Status:** needs a decision — the precedence question above. Found 2026-09-07 while measuring polygon overlap for GH-301; nothing was implemented.
