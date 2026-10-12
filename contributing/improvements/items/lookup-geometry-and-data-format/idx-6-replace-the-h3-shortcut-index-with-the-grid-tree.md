# IDX-6 — replace the H3 shortcut index with the grid tree

## Related memory

- [Longitude/latitude-aligned index decisions](../../decisions/longitude-latitude-aligned-index-decisions.md) — the measurement behind this item, the chosen shape's figures, what it trades away and leaves unpriced, and the refused variants.
- [Data-format version-marker and release-batching decisions](../../decisions/data-format-version-marker-and-release-batching-decisions.md) — the held tie-order rebuild and PERF-10's costs ride this item's format bump.
- [Data pipeline and release order](../../../development/data-pipeline-format-versioning-and-release-order.md)

## Decision

- **Decided 2026-10-12 by the maintainer: replace the resolution-4 H3 index with a grid tree — a dense 0.9375° grid aligned with longitude and latitude whose cells several zones can own refine into one level of 4×4 blocks.** It was the only option ahead of H3 on every measured axis below H3's footprint, polygon-test counts included, and counts are what survive a change of machine. **Refused:** a flat aligned grid, the simplest format but slower per call and less selective; a deeper tree (1.875° root, two levels of 4×4), which spends 55 % more disk than H3 because "replace, never add" is not read as a memory bound; and keeping H3.
- **Refined into slices on 2026-10-12**, since the whole replacement is not one reviewable pull request. The kernel's boundary rule the tree's exactness rests on is already pinned, by `tests/test_point_in_polygon_boundary_convention.py`; the answers no polygon owns as spelled are decided and already shipped on H3, the cell computation already sits behind the index, this item is the format migration itself, and [IDX-7](idx-7-drop-h3-from-the-runtime-dependencies.md) drops the dependency.

## What it changes

- **Runtime:** `timezonefinder/shortcut_index.py` reads the tree — a root table and one block array — instead of the H3 slot table, and its point-to-entry lookup, `entry_at` and `entries_at`, becomes the tree's integer arithmetic, scalar and vectorised; no lookup method in `timezonefinder/timezonefinder.py` computes a cell. `GridTree1` in `prototypes/latlng_index_bench.py` is the reference lookup, unrolled because a generic loop over the levels lost to a flat grid. Cells are computed from the truncated integer coordinates the kernel reads. `timezonefinder/_data_integrity.py` checks the tree instead of H3's bit layout.
- **Converter:** `scripts/shortcuts.py` and `scripts/hex_utils.py` compute candidates as the prototype's `build_grid_tree` and `owned_pairs` do, and the work optimizer in `scripts/shortcut_ordering.py` takes a rectangle where it takes an H3 cell (`cell_region`, `cell_cap`, `safe_to_reorder`). Reporting, fixture classification and the calibration tooling follow the index.
- **Format and release:** a new shortcut layout, `DATA_FORMAT_VERSION` 4 and the ordered two-distribution release, carrying the held tie-order rebuild and PERF-10's costs with it. The data is compiled by `compile_data.yml` and recorded in `DATA_BUILD_RUN`.
- **Answers that move:** `TimezoneFinderL` answers move cell by cell. Overlap answers follow per-cell legacy precedence and can move where a cell regroups an overlap's polygons, which PREC-1 would end. The answers no polygon owns as spelled must not move, as the [fallback-semantics decisions](../../decisions/shortcut-ordering-and-fallback-semantics.md) require: −180° reads as +180°, so the tree's prologue wraps a negative column to the last cell rather than clamping it to the first, and −90° as the point one unit north, which clamping a negative row to the first already gives. `tests/test_minus_180_meridian_and_minus_90_parallel.py` fails on a clamp.
- **Dependencies:** [IDX-7](idx-7-drop-h3-from-the-runtime-dependencies.md) ships in this item's pull request, removing `h3` from the runtime dependencies under the one-off exception that item states by artifact, and the changelog fragment says `h3` is no longer installed.
- **Documentation:** `docs/data_format.rst`, the *How it works* passage in `README.rst`, `docs/index.rst` and `docs/architecture.rst`, and every other page describing the H3 index; the generated data report and benchmark pages are regenerated.
- **Elsewhere:** GH-657 closes as moot; GEOM-3 is re-scoped to rectangle predicates; half of PERF-7's reopening condition is met; LITE-1 is phrased in H3 cells and needs rephrasing.
- **To measure while implementing**, unpriced by the decision: loading and construction time, `make memory`, mapped page residency, a second machine class, and the rectangle port of the work optimizer.
- **Size:** L — the format change is one atomic migration.
- **Status:** open — decided; the slices it was sequenced after have shipped.
