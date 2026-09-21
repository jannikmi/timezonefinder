# PERF-7 — answer a fully covered ambiguous cell without geometry


## Related memory

- [Query performance and shortcut index decisions](../../decisions/query-performance-and-shortcut-index-decisions.md) — why *re-ordering* a cell's candidates is refused; this item removes the loop instead of re-ordering it, so that refusal does not cover it.
- [Geometry data format and validation decisions](../../decisions/geometry-data-format-and-validation-decisions.md) — the 2026-08-21 decision that a correctness property is never expressed in terms of the H3 shortcut index, and the 2026-09-02 refusal of a zone-precedence *engine*. The rule below is bound by both: it is a zone-level relation derived from geometry, evaluated once, not a per-cell rule and not maintained configuration.
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- Draft PR #652 — the converter half, implemented and measured before GEOM-3 blocked it: `Hex.covers_cell`, `scripts/zone_precedence.py`, and two full 2026c compiles diffed against each other. It discards the candidates `timezones_at` reads, so it is evidence for the route below rather than something to rebase; the counts in *What it moves* are its. The study the first counts came from, `prototypes/shortcut_ordering_optimum.py`, never landed.

## The observation

Some ambiguous cells are covered **entirely** by the polygons of a single zone. No query point in such a cell can fall outside that zone, so the cell needs no point-in-polygon test at all: the shortcut index could store it as a unique-zone cell, which the reader already supports and which costs one table read.

Measured over 2026c at H3 resolution 4: **826 of 31,368 ambiguous cells (2.63 %) are fully covered by one zone**, and 1,124 to within 1e-4 of full.

## What it is worth

An ambiguous query is ~5,150 ns and a unique one ~1,000 ns, so converting those cells moves ~2.63 % of ambiguous queries onto a path ~4,150 ns cheaper — **~109 ns, or 2.12 % of an ambiguous query**, and ~0.85 % of a mixed workload if queries are uniform over cells. That is about **three times what the provably optimal candidate ordering was worth** (0.27 %, refused), because it removes the geometry rather than reordering it — and it is not bounded by the candidate loop's 14.7 % share the way any ordering change is. The index does not grow, and does not measurably shrink either: converting 742 cells left the binary the same size, because the table is fixed and the candidate lists deduplicate.

The per-cell count is not a query share. Weighting by real traffic needs the fixtures rather than the cell count; `count` in the prototype is the instrument.

## The precedence rule, decided

**Decided 2026-09-08.** Precedence is set by a documented heuristic, and it is used **only in shortcut cells that one polygon covers entirely** — the scope is what makes it tractable. Within that scope the rule is *containment*: of two overlapping zones, the one for which the shared area is the larger share of **itself** is the enclave and takes precedence. It is a property of the two zones, computed once from their full geometry, so it is the same in every cell and does not express a correctness property in terms of the H3 index.

Refused along the way, and kept so they are not re-proposed:

- **Smaller total zone area wins** is not a separate option, and no longer a refused one: within this scope it *is* containment. The two ratios containment compares share the shared area as their numerator, so `shared/area(A) > shared/area(B)` holds exactly when `area(A) < area(B)` — which is why they disagreed on 0 of 118 pairs, and why the rule needs no polygon clipping. Measure the areas on the sphere, not by a shoelace sum over the stored plate-carrée coordinates, or latitude decides precedence. GH-513's size-derived rule failing on 20 of 216 edges, systematically on the ocean zones, is a different relation: those edges answer points inside a *hole*, and a hole reaching the cell already disqualifies it from coverage.
- **Lower polygon or zone id wins.** Ids follow upstream GeoJSON feature order — the packaged zone names are not sorted — so a zone added upstream shifts them and flips a winner with no geometry change.
- **Deciding per cell** (the smaller polygon beside a covering one). Not consistent: of the 7 zone pairs it rules on, 2 get opposite winners in different cells, because "covers *this* cell" is a property of the cell. Two points in one overlap region either side of a cell boundary would be answered differently.

## What the rule has to decide, and what it costs

Scoping to covered cells is what removes the tie-break problem. Across the whole index 118 zone pairs overlap, most of them coastal slivers where both containments round to zero — but **none of those occur in a covered cell**. What the conversion actually has to order is:

| | pairs |
|---|---:|
| among the covering zones of a covered cell | **2** — `Asia/Urumqi` over `Asia/Shanghai` (100.0 % vs 17.7 %), `Africa/Juba` over `Africa/Khartoum` (3.6 % vs 1.2 %) |
| a coverer against a smaller overlapping candidate | 7, margins 1.1x to 281x |

Every one has a clear winner; none is a near-tie. **The relation over all 118 pairs is acyclic**, checked by topological sort, so a global order exists — which is the feasibility question GH-513 left open when the *hole* relation turned out cyclic.

**What it moves.** Of the 826 covered cells, **742 convert and 84 stay ambiguous** — the 743/0 first recorded here did not reproduce. The 84 are cells a larger zone covers while a *smaller* zone reaches in without covering them, mostly along Xinjiang's boundary: the smaller zone takes the part it reaches, so no single zone answers the whole cell, and converting one would be a wrong answer. Over the committed fixtures the answers move on **2 of 5,000 ambiguous points, and none of the 10,000 random or 10,000 on-land ones**. That is a count over one sample, not a property: the rule *decides* precedence, so wherever it differs from the ordering today happens to produce, the answer changes by design. The fixtures bound how often a real workload reaches such a point; they do not establish that none does, and the item does not need them to. Point-in-polygon tests fall **2.6 % on ambiguous, 2.1 % on random and 4.4 % on on-land**, and the index does not grow.

**The whole-query effect is not resolvable.** Paired and order-alternated on the C-extension backend, 61 rounds x 2,500 points: no difference on ambiguous (31 of 61) and random (32 of 61), `unresolved` on on-land (best round −3.1 %, 29 of 61), control clean. That is what the ceiling predicts — 2.12 % of an ambiguous query is under the 3–9 % noise floor — and it is the same result every candidate reordering got, for the same reason: the loop is overhead-bound. The count is the evidence here, not the clock.

## Keeping the candidates `timezones_at` reads

`timezones_at` walks an ambiguous cell's whole candidate list and reports every zone containing the point. In a covered cell every other-zone candidate lies inside the covering polygon, so every point it reaches is in two zones: each converted cell is one where that method needs both, and collapsing it to a zone id makes it answer one — plausibly, so review will not catch it. A green suite will not either, because the full-scan reference in `tests/test_overlapping_zones.py` reads the same index; that file's `DOCUMENTED_OVERLAPS`, six hard-coded coordinates asserted as exact lists, are the regression surface, `Asia/Urumqi` over `Asia/Shanghai` first among them. Converting only the cells whose other candidates are spurious keeps nothing worth having, so the conversion has to keep the list.

**The route: give a covered cell its own entry, not a zone id.** Entries are deduplicated on *(candidate list, covering zone)* instead of the list alone and placed in a reserved index range, with a per-entry column holding the covering zone. `timezone_at`'s ambiguous branch tests the range and returns that zone with no geometry; `timezones_at` ignores it and walks the list as today; the unique-zone path is untouched. It ships with a test that reads coverage independently of the index, since only such a test can see a converted cell losing a zone. **Priced on 2026c: 7 entries on top of today's 2,994** — the 742 cells share seven (list, zone) pairs — and the payload does not grow, since equal offsets already share it. What it costs instead is one integer comparison on every ambiguous query, unmeasured and to be settled by an in-query A/B against the ~109 ns it saves on average, and **a format change: `SHORTCUT_LAYOUT_VERSION` 3 and `DATA_FORMAT_VERSION` 4**, an ordered two-distribution release this item pays for alone, since format 3 has published. That release is the item's dominant cost now, and it is why PERF-7 should ride with the next format change rather than open one.

**No `shapely`.** Coverage is `fully_contained_in_hole(cell, polygon)`, already in `scripts/utils_numba.py`, plus no hole of the covering polygon meeting the cell; precedence reduces to comparing spherical areas, above. Neither needs a dependency — but neither answers GEOM-3, whose question is whether the cell's stored ring stands for every point H3 assigns to it.

- **Size:** M-L — the converter change (done on #652), the new shortcut column and reader dispatch, the regenerated index, the moved-answer diff, and the format-4 release.
- **Status:** blocked on GEOM-3 — the precedence question is decided (above), but the planar ring through `h3.cell_to_boundary` vertices does not cover every point H3 assigns to the cell. A conservative full-cell predicate must be established before the converter can answer a cell with an unconditional zone; keeping the candidates does not relax that, because `timezone_at` still skips them. Once unblocked it is a format-4 change and belongs with the next one. Found 2026-09-07 while measuring polygon overlap for the candidate-ordering work; the converter half exists on draft #652 and is not mergeable as it stands.
