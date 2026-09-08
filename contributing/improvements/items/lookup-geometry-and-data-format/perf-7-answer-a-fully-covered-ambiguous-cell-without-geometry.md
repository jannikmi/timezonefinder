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

So essentially the whole gain is a precedence decision. Today's answer on those points is already arbitrary — it falls out of a vertex-count sort, and any reordering moves it — and the recorded decision of 2026-08-21 forbids expressing a correctness property in terms of the H3 index, which is what a per-cell precedence rule does.

## The proposed heuristic, and what it leaves open

**Proposed 2026-09-08:** use a documented heuristic — where one smaller polygon A sits beside a polygon B covering the whole cell, A takes precedence; where several polygons cover the whole cell, the lower id wins.

The intuition is the right one: the more specific zone winning over the one enclosing it is the standard enclave rule, and it is what today's ordering already does by accident. Measured against the packaged index, it does not yet close the decision.

| | cells |
|---|---:|
| exactly one covering polygon — the clause's own case | **98** |
| several covering polygons — falls to the id tie-break | **728** |
| overlapping candidates but no coverer — heuristic silent | **266** |
| two *non-covering* candidates overlapping each other | **0** |

Four things follow.

- **The first clause decides 98 of the 826 cells.** The dominant case is several coverers at once, which the proposal itself marks as the ambiguous half. `Asia/Urumqi` and `Asia/Shanghai` are one such pair — both cover their shared cell entirely — so the case most often cited for this item is decided by the tie-break rather than by the size rule.
- **The id tie-break is not stable.** Polygon and zone ids are assigned in upstream GeoJSON feature order, and the packaged zone names are not in sorted order, so ids track that file rather than any property of the zones. A zone added or moved upstream shifts them, and the winner flips on a data update with no geometry change. A tie-break on identity should key on something stable — the zone name — rather than on an id.
- **266 cells are left where they are**: candidates overlap, nothing covers the cell, and today's arbitrary ordering still decides. The heuristic neither fixes nor documents those.
- **It is not consistent between cells, and that is the blocking objection.** Of the 7 zone pairs the first clause rules on, **2 receive opposite winners in different cells** — `Asia/Tbilisi` vs `Europe/Moscow`, and `Africa/Juba` vs `Africa/Khartoum` — because whether a zone covers *this* cell is a property of the cell, not of the zones. Two points inside the same overlap region, either side of a cell boundary, would then be answered differently. That is exactly the failure the 2026-08-21 decision was taken to prevent, now demonstrated rather than predicted.

**What would close it.** Decide precedence at the *zone* level, from a property of the zones evaluated once rather than per cell — smaller total area wins, ties broken by name. That is a total order, so it is acyclic by construction, it assigns every overlapping pair one winner everywhere, it reproduces the heuristic's intent in the cases the heuristic does decide, and it covers the 266 cells the heuristic does not reach. The covering-cell conversion then becomes a pure speed change that provably cannot move an answer, and the H3-independence decision is respected rather than spent. GH-513 found the equivalent relation over *holes* to be cyclic; the overlap relation is a different and much smaller one, so its acyclicity is a question this item can answer cheaply rather than an assumption.

- **Decision needed:** should zone precedence for overlapping boundaries be defined **globally, at the zone level**, so that the covering-cell optimisation cannot change an answer? **Consequences:** a global rule closes all 1,092 overlap-or-coverage cells at once, keeps precedence out of the H3 index as the 2026-08-21 decision requires, and unblocks this item as a pure speed change worth 2.12 % of an ambiguous query; the per-cell heuristic as proposed decides 98 of 826, hands 728 to an id tie-break that a data update can flip, leaves 266 untouched, and gives 2 of 7 zone pairs different answers in different cells. **Options:** (a) **global rule — smaller total zone area wins, ties by name**, then apply the conversion; (b) the **per-cell heuristic as proposed**, accepting the inconsistency and the unstable tie-break, documented as such; (c) the per-cell heuristic with the tie-break changed to **zone name** rather than id, which removes the instability but not the inconsistency; (d) **refuse the item** and leave precedence implicit in the ordering. **Trade-offs:** (a) is the only one that makes the answer a function of the point rather than of the cell, and it costs a feasibility check plus a review of every moved answer; (b) and (c) are cheaper and buy the same 2.12 %, at a rule that is documented but wrong at cell boundaries; (d) keeps the status quo, in which the same answers are already arbitrary but nothing claims otherwise. **Recommendation:** (a). The measurements above were all taken to price it, the relation is small, and it is the only option whose gain does not have to be re-litigated the next time the index resolution changes. **Reversibility:** the converter change is one release to undo, but every answer it moves is user-visible, so reversing it moves them back. **Unpriced:** whether the overlap relation is acyclic (very likely — it is far smaller than GH-513's hole relation, and any rule derived from a single total quantity is acyclic by construction), and whether `tzfpy` and other implementations agree with the smaller zone or the larger one on these points.

- **Size:** M — a converter change in `scripts/shortcuts.py` plus a coverage computation needing `shapely` at build time, the regenerated index, and the moved-answer diff.
- **Status:** needs a decision — narrowed 2026-09-08 by the proposed heuristic and the measurements above, which showed it decides 98 of 826 cells and is inconsistent between cells on 2 of 7 zone pairs. Found 2026-09-07 while measuring polygon overlap for GH-301; nothing has been implemented.
