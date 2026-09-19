# IDX-1 — price a longitude/latitude-aligned index in place of H3

## Related memory

- [Shortcut index and query performance decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Benchmarking, tooling and dependency decisions](../../decisions/benchmarking-tooling-and-dependency-decisions.md)
- [Candidate audit and geometry authority](../../decisions/shortcut-candidate-audit-and-geometry-authority.md)
- [Cell-local geometry findings](../../decisions/cell-local-geometry-findings.md)
- [Measured baseline](../../query-performance-measurement-baseline.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)

## Why it is recorded

Raised by the maintainer on 2026-09-18. The dependency decision had parked shrinking the runtime dependency surface "unless import time or cold start is ever measured to be a real problem"; the case for H3 specifically no longer rests on import time, so this reopens that bullet for `h3` alone, on three premises the parking did not weigh:

- **H3 is most of a unique query.** `h3.latlng_to_cell` in `TimezoneFinder.timezone_at` is ~51 % of a unique-shortcut query and, with validation, ~54-64 % of the uniformly random stratum ([measured baseline](../../query-performance-measurement-baseline.md)). The batch lookups hoist everything else and still pay one scalar `latlng_to_cell` per point, which is why they saturate at ~1.6x. Re-measured 2026-09-18 on an M1 Pro, free-threaded 3.14: 0.52 µs of a 1.16 µs `timezone_at` over `random_points`. A cell in an index aligned to longitude and latitude is a few integer operations on coordinates the query already converts.
- **H3 blocks other items.** FT-3 waits on an h3 release to stop h3 re-enabling the GIL; GH-657 waits on the merge and release of uber/h3#1178; GEOM-3's proof burden — and through it PERF-7's — exists because H3 cells are spherical while the source edges are planar in longitude/latitude, so, in GEOM-3's words, "released planar modes are not a correctness authority for spherical cells". Cells bounded by lines of constant longitude and latitude live in the same planar space as the source polygons: exclusion and full coverage become exact rectangle-against-polygon tests in the stored int32 coordinates, the construction the cell-local findings already call viable.
- **H3 is the only compiled runtime dependency whose job is this small.** `h3` 4.5.0 installs ~2.4 MB and costs ~27 ms to import; the package uses one function of it at query time. `timezonefinder/shortcut_index.py` derives its table slots from H3's cell bit layout, and `timezonefinder/_data_integrity.py` and the converter's `scripts/hex_utils.py` use `h3` too.

## What the item is

**A measurement, not a migration.** Build a prototype under `prototypes/` that compiles the 2026c boundaries into each candidate index below, and price it against the resolution-4 H3 index on the axes the resolution decision used: resident and payload bytes, candidate polygons per query per stratum, the share of queries answered without geometry, and an in-query alternating A/B of `timezone_at` and the batch lookup on both acceleration paths. Record the verdict in the shortcut-index decisions; adoption, if the numbers support it, is a separate decided item.

Candidates, all aligned to longitude and latitude, so all inherit the exact planar cell predicates above:

- **A single-level equal-angle grid.** The H3 table is `122 * 8**4` ≈ 500k slots at resolution 4. An equal-angle grid has `(360/s) * (180/s)` slots — ≈ 259k at 0.5°, ≈ 500k at 0.36° — but its cells shrink by `cos(latitude)`, over-resolving the polar ocean and Antarctica and under-resolving the equator relative to H3's near-equal areas. A latitude-dependent column count (equal-area bands) is the variant to price beside it.
- **A multi-level index of exactly nesting cells — `tzfpy`'s scheme, read from `ringsaturn/tzf` 2026-09-19.** Its fast path is a preindex of Web Mercator slippy tiles (`z/x/y`, key `z<<56 | x<<28 | y`), generated at zoom 13, merged upward to zoom 3, and kept only down to zoom 10; a tile is kept only if it lies inside one zone's polygon (edge tiles dropped), stored as a hash map from tile to zone. A query computes its zoom-13 tile once and derives each coarser tile by a shift, probing zoom 3 → 13 until a hit — ~100-200 ns for most queries in Rust/Go. A miss falls through to a dense 1° × 1° grid (64,800 cells) listing the zones whose bounding boxes overlap the cell, then point-in-polygon with a per-polygon y-stripe edge index. Mercator tiles nest exactly, so the objection that sank the multi-resolution H3 prototype — parents kept beside children — does not carry over, and a quadtree stores large uniform regions as one coarse cell rather than as many slots. Two things to check rather than copy: `tzf` builds its preindex from the simplified polygons, so tile containment must be re-established against the source polygons; and a hash map per level is not the dense-table layout the shortcut decisions chose, so price a layout that keeps mapped mode working. Node `geo-tz`'s quadtree over equal-angle quadrants is the same family and can be priced in the same harness.
- **The two-tier split itself**, independent of cell shape: an exact "one zone" tile layer for the common case in front of a coarse candidate grid for the rest, against today's single table that serves both.

Constraints already decided that still apply:

- **Replace, never add.** The raster fast-path in front of H3 was dropped for spending storage; a candidate is only viable if it replaces the H3 table at no larger footprint in total.
- **The edge-crossing check.** Any new cell shape must re-run the edge-crossing class that caught the Strait of Malacca defect at resolution 4 before being timed.

If adopted later, the consequences to carry: a `DATA_FORMAT_VERSION` bump and the ordered two-distribution release; `TimezoneFinderL` shares the index; GH-657 closes as moot, GEOM-3 and PERF-7 are re-scoped to rectangle predicates, and FT-3 ceases to depend on an upstream release; LITE-1 is phrased in H3 cells and would need rephrasing.

- **Size:** M for the prototype and its recorded verdict; the migration it may justify is L and is not this item.
- **Status:** open — the measurement is the item; nothing in `timezonefinder/` changes.
