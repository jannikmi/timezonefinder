# IDX-2 — replace the H3 shortcut index with a longitude/latitude-aligned grid tree

## Related memory

- [Longitude/latitude-aligned index decisions](../../decisions/longitude-latitude-aligned-index-decisions.md) — the measurement behind this item, the chosen shape's figures, what it trades away and leaves unpriced, and the refused variants.
- [Data-format version-marker and release-batching decisions](../../decisions/data-format-version-marker-and-release-batching-decisions.md) — the held tie-order rebuild and PERF-10's costs ride this item's format bump.
- [Benchmarking, tooling and dependency decisions](../../decisions/benchmarking-tooling-and-dependency-decisions.md) — `h3` is the one runtime dependency reopened for removal.
- [Data pipeline and release order](../../../development/data-pipeline-format-versioning-and-release-order.md)

## Decision

- **Decided 2026-10-12 by the maintainer: replace the resolution-4 H3 index with a grid tree — a dense 0.9375° grid aligned with longitude and latitude whose cells several zones can own refine into one level of 4×4 blocks.** It was the only option ahead of H3 on every measured axis below H3's footprint, polygon-test counts included, and counts are what survive a change of machine. **Refused:** a flat aligned grid, the simplest format but slower per call and less selective; a deeper tree (1.875° root, two levels of 4×4), which spends 55 % more disk than H3 because "replace, never add" is not read as a memory bound; and keeping H3.

## What adopting it changes

- **Runtime:** `timezonefinder/shortcut_index.py` reads the tree — a root table and one block array — instead of the H3 slot table, and every `h3.latlng_to_cell` call in `timezonefinder/timezonefinder.py` becomes the tree's integer arithmetic, scalar and vectorised. `GridTree1` in `prototypes/latlng_index_bench.py` is the reference lookup, unrolled because a generic loop over the levels lost to a flat grid. `timezonefinder/_data_integrity.py` stops checking H3's bit layout.
- **Converter:** `scripts/shortcuts.py` and `scripts/hex_utils.py` compute candidates as the prototype's `build_grid_tree` and `owned_pairs` do, and the work optimizer in `scripts/shortcut_ordering.py` takes a rectangle where it takes an H3 cell (`cell_region`, `cell_cap`).
- **Format and release:** a new shortcut layout, `DATA_FORMAT_VERSION` 4 and the ordered two-distribution release, carrying the held tie-order rebuild and PERF-10's costs with it.
- **Dependencies:** `h3` leaves the runtime dependencies once nothing above imports it, which changes the published metadata.
- **A test pinning the kernel's edge convention**, because the tree's exactness rests on it: a polygon owns a point on its east or north boundary, never its west or south.
- **Answers that move:** `TimezoneFinderL` answers move cell by cell. Overlap answers follow per-cell legacy precedence and can move where a cell regroups an overlap's polygons, which PREC-1 would end.
- **Decide, within this item, what a lookup answers on the −180° meridian and the −90° parallel.** No polygon owns a point exactly there, since the kernel never puts a point on a polygon's west or south boundary inside it, so both indexes answer a cell's untested last zone and the answer depends on the index: under the chosen tree 146 of 200 sampled points at exactly −180° change, mostly from `Etc/GMT-12` to `Etc/GMT+12` and three Chukotka points from `Asia/Anadyr` to the ocean, while none of 200 at −90° do. The options to price: keep that fallback, so answers follow the index; look −180° up as +180°, which the polygon west of the antimeridian owns, so both spellings of one meridian agree and land keeps its land zone; and for −90°, keep the fallback or answer the zone owning the point one unit north. Each moves answers, so the pass implementing the reader measures them on the tree and puts the choice to the maintainer before that slice lands, then records it here.
- **Elsewhere:** GH-657 closes as moot; GEOM-3 is re-scoped to rectangle predicates; half of PERF-7's reopening condition is met; FT-3 is moot once `h3` is gone; LITE-1 is phrased in H3 cells and needs rephrasing; `docs/data_format.rst` and every page describing the H3 index change.
- **To measure while implementing**, unpriced by the decision: loading and construction time, `make memory`, mapped page residency, a second machine class, and the rectangle port of the work optimizer.

- **Size:** L — refine into slices when taken; the format change itself is one atomic migration.
- **Status:** open — decided 2026-10-12; implementing it is the work.
