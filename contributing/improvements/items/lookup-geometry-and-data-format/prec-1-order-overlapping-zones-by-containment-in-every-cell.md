# PREC-1 — order overlapping zones by containment in every cell

## Related memory

- [PERF-7](perf-7-answer-a-fully-covered-ambiguous-cell-without-geometry.md) (withdrawn) — where this rule was decided, and the measurement showing it cannot be scoped to some cells: applied only in covered cells it split Abyei by H3 cell.
- [Geometry decisions](../../decisions/geometry-data-format-and-validation-decisions.md) — answers never depend on the H3 index; the hole-dropping precedence relation is cyclic (GH-513), which is a different relation; a precedence *engine* of maintained political rules is refused.
- `scripts/shortcut_ordering.py` — the ordering optimizer, which keeps the input zone order wherever candidates of different zones overlap. The [committed calibration](../../../../docs/benchmarking_methodology.rst#calibrating-the-shortcut-ordering-model) validates that optimizer's *cost model*; this item changes the *constraint* it keeps, so the two are independent.

## The problem

Where two zones' polygons overlap, `timezone_at` answers whichever zone the candidate order tests first, and `timezones_at` puts that zone first by contract. The ordering optimizer (`ShortcutOrderer.order`) reorders freely only where `safe_to_reorder` proves different zones' candidates disjoint in the cell; where they overlap it keeps the zone-block order `optimise_shortcut_ordering` produced, whose docstring calls it **legacy zone precedence**: zones sorted by the vertex count of *their candidates in that cell*, fewest first.

So the answer in an overlap is decided by which zone has fewer vertices among a cell's candidates — a proxy chosen for query cost that says nothing about the zones. It can move whenever a data update changes a vertex count, and because the key is a property of the cell, two cells of one overlap holding different subsets of a zone's polygons can rank the pair oppositely: the per-cell split PERF-7 was withdrawn for, reachable here by construction even though none of the regions sampled below shows it. The overlaps are real: 28 of 10,000 random, 98 of 10,000 on-land and 163 of 5,000 ambiguous fixture points lie in two zones (API-1's measurement, 2026c), most of them `Asia/Urumqi` inside `Asia/Shanghai`, the rest disputed or dual-administered areas.

## The rule

**Decided 2026-09-08, for covered cells, as part of PERF-7.** Of two overlapping zones, the one for which the shared area is the larger share of *itself* is the enclave and takes precedence. The two ratios share the shared area as their numerator, so this is exactly *smaller spherical zone area wins*, needs no polygon clipping, and is computed once per zone pair from the geometry alone. Because it is a comparison of one scalar per zone, it is acyclic by construction and one global order always satisfies it; the only hazard is an exact area tie, which the recorded overlap tie rule settles by timezone identifier, as the legacy key's ties already are. Areas must be spherical: a planar sum over the stored coordinates lets latitude decide.

Refused along the way, kept so they are not re-proposed:

- **Lower polygon or zone id wins.** Ids follow upstream GeoJSON feature order, so a zone added upstream shifts them and flips a winner with no geometry change.
- **Deciding per cell**, by whichever polygon covers that cell. Of the 7 zone pairs it rules on, 2 get opposite winners in different cells; PERF-7's withdrawal measured the consequence, one overlap answered two ways by H3 cell.

## The route, measured

Change the key `optimise_shortcut_ordering` sorts zone blocks by, from the per-cell vertex count to spherical zone area. It binds only in the cells where the optimizer is restricted; everywhere else the optimizer reorders freely and the key only seeds it. No reader change, no format change, no coverage proof — a regenerated `shortcuts.bin` through the data pipeline, and `scripts/shortcut_ordering.py`'s `spherical_area` already computes the areas.

Measured by compiling 2026c twice with the converter on `master`, the only difference being that key:

- `shortcuts.bin` is the only binary that moves.
- **Cost: none resolvable.** Point-in-polygon tests go **−0.18 %** random, **−0.56 %** on-land and **+0.02 %** ambiguous.
- **Answers:** 1 of 10,000 random, 1 of 10,000 on-land and 5 of 5,000 ambiguous fixture points move, every one a two-zone overlap point whose `timezones_at` set is unchanged and whose order swaps.
- **Whole regions move, not points.** Sampling the points that lie in two zones: Abyei goes entirely from `Africa/Khartoum` to `Africa/Juba` (5,718 of 5,718); **the West Bank overlap goes entirely from `Asia/Jerusalem` to `Asia/Hebron` (7,851 of 7,851)**; `Asia/Urumqi` in Xinjiang and `Asia/Tbilisi` in northern Georgia already won and stay. Legacy precedence is consistent within each region too; what changes is *who* wins, and why.

## Decision

- **Decided 2026-10-19 by the maintainer: (a) containment everywhere.** `optimise_shortcut_ordering` sorts zone blocks by spherical zone area, smaller first, with the timezone identifier breaking exact ties, so `timezone_at`'s answer in an overlap is the zone that is the enclave, in every cell. The answer becomes a property of the geometry: stable under data updates that only redraw vertex counts, and independent of the index and of the ordering's cost model. Ship it with a changelog entry and a data release note that both name the zones that flip with the release.
  - **Owner:** the maintainer decided; implementation is an ordinary improvement-pass item.
  - **Refused: keeping legacy fewest-vertices precedence.** It costs no work and moves nothing now, but leaves the pick a per-cell cost proxy that a data update or an index change can flip for whole regions without announcement — a worse property for a lookup whose answers users store. A maintained per-pair list stays refused as the precedence engine.
  - **Both release notes name the change and the zones that flip against the last published release.** Users hold answers from the release they installed, not from `master`, and the aligned grid tree has not shipped, so the baseline is `timezonefinder-data` `3.2026.4` (upstream 2026d, H3 index) or whatever data release is newest on PyPI when this ships. Measure on the dataset the release ships, compiled with this key, against that published release, and list every zone pair whose overlap answer flips in two places: the `CHANGELOG.rst` entry, with `timezones_at` named for anyone who needs both zones, and the data release's entry under *Releases* in `packages/timezonefinder-data/README.md`, which must name the overlap-precedence change itself and not only the boundary release. Abyei (`Africa/Khartoum` → `Africa/Juba`) and the West Bank overlap (`Asia/Jerusalem` → `Asia/Hebron`) are the flips measured on 2026c and must be confirmed, not copied.
  - **What would reopen it:** evidence that users rely on the legacy winner in a disputed overlap region, weighed against the instability above.
- **Size:** S — the sort key, a zone-area helper and the identifier tie-break in `scripts/shortcuts.py`, a test pinning an overlap's winner independently of the index, a rewrite of `docs/result_stability.rst`'s channel 2 to name the rule, a changelog entry, and the regenerated index through the data pipeline.
- **Status:** open.
