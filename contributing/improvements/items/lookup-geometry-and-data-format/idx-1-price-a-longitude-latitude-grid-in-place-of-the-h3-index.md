# IDX-1 — price a longitude/latitude grid in place of the H3 index

## Related memory

- [Shortcut index and query performance decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Benchmarking, tooling and dependency decisions](../../decisions/benchmarking-tooling-and-dependency-decisions.md)
- [Candidate audit and geometry authority](../../decisions/shortcut-candidate-audit-and-geometry-authority.md)
- [Cell-local geometry findings](../../decisions/cell-local-geometry-findings.md)
- [Measured baseline](../../query-performance-measurement-baseline.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)

## Why it is recorded

Raised by the maintainer on 2026-09-18. The dependency decision had parked shrinking the runtime dependency surface "unless import time or cold start is ever measured to be a real problem"; the case for H3 specifically no longer rests on import time, so this reopens that bullet for `h3` alone, on three premises the parking did not weigh:

- **H3 is most of a unique query.** `h3.latlng_to_cell` in `TimezoneFinder.timezone_at` is ~51 % of a unique-shortcut query and, with validation, ~54-64 % of the uniformly random stratum ([measured baseline](../../query-performance-measurement-baseline.md)). The batch lookups hoist everything else and still pay one scalar `latlng_to_cell` per point, which is why they saturate at ~1.6x. Re-measured 2026-09-18 on an M1 Pro, free-threaded 3.14: 0.52 µs of a 1.16 µs `timezone_at` over `random_points`. A lng/lat grid cell is two floor-divisions on coordinates the query already converts.
- **H3 blocks other items.** FT-3 waits on an h3 release to stop h3 re-enabling the GIL; GH-657 waits on the merge and release of uber/h3#1178; GEOM-3's proof burden — and through it PERF-7's — exists because H3 cells are spherical while the source edges are planar in longitude/latitude, so, in GEOM-3's words, "released planar modes are not a correctness authority for spherical cells". A grid whose cell edges are lines of constant longitude and latitude lives in the same planar space as the source polygons: exclusion and full coverage become exact rectangle-against-polygon tests in the stored int32 coordinates, the construction the cell-local findings already call viable.
- **H3 is the only compiled runtime dependency whose job is this small.** `h3` 4.5.0 installs ~2.4 MB and costs ~27 ms to import; the package uses one function of it at query time. `timezonefinder/shortcut_index.py` derives its table slots from H3's cell bit layout, and `timezonefinder/_data_integrity.py` and the converter's `scripts/hex_utils.py` use `h3` too.

## What the item is

**A measurement, not a migration.** Build a prototype under `prototypes/` that compiles the 2026c boundaries into a single-level lng/lat grid index in the shipped shortcut layout, and price it against the resolution-4 H3 index on the axes the resolution decision used: resident and payload bytes, candidate polygons per query per stratum, the unique-cell share, and an in-query alternating A/B of `timezone_at` and the batch lookup on both acceleration paths. Record the verdict in the shortcut-index decisions; adoption, if the numbers support it, is a separate decided item.

Constraints the prototype must respect, each already decided:

- **Single level.** A hierarchical index over several resolutions is refused; a quadtree like node `geo-tz`'s is that refusal in another shape.
- **Replace, never add.** The raster fast-path in front of H3 was dropped for spending storage; a grid is only a candidate if it replaces the H3 table at no larger footprint.
- **The exchange rate is the number to beat.** The H3 table is `122 * 8**4` ≈ 500k slots at resolution 4. An equal-angle grid has `(360/s) * (180/s)` slots — ≈ 259k at 0.5°, ≈ 500k at 0.36° — but its cells shrink by `cos(latitude)`, over-resolving the polar ocean and Antarctica and under-resolving the equator relative to H3's near-equal areas. Whether that is paid for by cheaper cell computation and exact planar coverage is exactly the question; do not assume it. A latitude-dependent column count (equal-area bands) is the obvious variant to price alongside.
- **The edge-crossing check.** Any new cell shape must re-run the edge-crossing class that caught the Strait of Malacca defect at resolution 4 before being timed.

If adopted later, the consequences to carry: a `DATA_FORMAT_VERSION` bump and the ordered two-distribution release; `TimezoneFinderL` shares the index; GH-657 closes as moot, GEOM-3 and PERF-7 are re-scoped to rectangle predicates, and FT-3 ceases to depend on an upstream release; LITE-1 is phrased in H3 cells and would need rephrasing.

- **Size:** M for the prototype and its recorded verdict; the migration it may justify is L and is not this item.
- **Status:** open — the measurement is the item; nothing in `timezonefinder/` changes.
