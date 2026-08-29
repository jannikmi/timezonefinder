# Improvement priority ranking

| Id | What | Area | Size | Eligibility |
|---|---|---|---|---|
| [DATA-BINARIES](items/packaging-distribution-and-release/data-binaries-stop-committing-the-packaged-data-binaries.md) | Stop committing the packaged data binaries | packaging | L | blocked until a `timezonefinder-data` 2.x is on PyPI |
| [GH-542](items/lookup-geometry-and-data-format/gh-542-establish-what-coordinate-precision-is-worth.md) | Establish what coordinate precision is worth | data format | M | free — the source-precision half is settled, the rest needs a regeneration a pass may now do |
| [GH-449](items/lookup-geometry-and-data-format/gh-449-polygon-encoding-delta-varint.md) | Polygon encoding: delta + varint | data format | L | blocked by GH-542 + DATA-BINARIES |
| [DOC-3](items/documentation/doc-3-the-zoneinfo-snippets-never-say-that-windows-needs-tzdata.md) | The `zoneinfo` snippets never say Windows needs `tzdata` | docs | ~3 | free |
| [BENCH-1](items/packaging-distribution-and-release/bench-1-the-pull-request-benchmark-comparison-cannot-resolve-the-changes-worth-reviewing.md) | The pull request benchmark comparison cannot resolve the changes worth reviewing | tooling | M | free |
| [BATCH-2](items/packaging-distribution-and-release/batch-2-the-batch-lookups-are-measured-by-nothing-the-ci-tracks.md) | The batch lookups are measured by nothing the CI tracks | tooling | S–M | free |
| [GH-501](items/packaging-distribution-and-release/gh-501-guardrails-on-the-automated-data-update-pipeline.md) | Guardrails on the automated data update pipeline | release | M | free — decided |
| [GH-500](items/data-pipeline-and-developer-tooling/gh-500-validate-a-data-directory-s-cross-file-invariants.md) | Validate a data directory's cross-file invariants | data integrity | M | free — decided |
| [GH-428](items/data-pipeline-and-developer-tooling/gh-428-data-parsing-ux-and-the-cli-shape-it-shares-with-gh-500.md) | Data parsing UX, and the CLI shape it shares with GH-500 | CLI / UX | M | free — decided |
| [BIG-1](items/lookup-geometry-and-data-format/big-1-iter-boundary-ids-of-zone-re-opens-zone-positions-npy-on-every-call.md) | `_iter_boundary_ids_of_zone` re-opens `zone_positions.npy` on every call | performance | ~10 | free — decided |
| [GH-364](items/lookup-geometry-and-data-format/gh-364-free-threaded-python-via-a-native-candidate-loop.md) | Free-threaded Python, via a native candidate loop | performance | L | blocked on an h3 release |
| [GH-502](items/public-api-and-behavior/gh-502-first-class-zoneinfo-utc-offset-helpers.md) | First-class `zoneinfo` / UTC-offset helpers | public API | S–M | free — decided |
| [GH-332](items/packaging-distribution-and-release/gh-332-reduced-timezone-dataset-as-a-second-distribution.md) | Reduced timezone dataset as a second distribution | packaging | M | parked until GH-334 |
| [TOOL-7](items/packaging-distribution-and-release/tool-7-the-data-dependency-guard-checks-one-wheel-of-however-many-it-finds.md) | The data-dependency guard checks one wheel of however many it finds | release | ~10 | free — decided |
| [TOOL-6](items/data-pipeline-and-developer-tooling/tool-6-parse-data-rewrites-the-committed-data-report-whatever-out-it-was-given.md) | `parse_data` rewrites the committed data report whatever `-out` it was given | tooling | ~150 | free — decided |
| [API-2](items/public-api-and-behavior/api-2-every-submodule-is-reachable-as-a-package-attribute-so-the-public-api-is-wider-than-all-says.md) | Every submodule is reachable as a package attribute | public API | ~20 | decided — held for the next major |
| [API-1](items/public-api-and-behavior/api-1-abstracttimezonefinder-init-takes-an-in-memory-it-never-uses.md) | `AbstractTimezoneFinder.__init__` takes an `in_memory` it never uses | public API | ~10 | decided — held for the next major |
| [BIG-4](items/data-pipeline-and-developer-tooling/big-4-load-binary-data-s-hole-branch-silently-yields-empty-lists-when-a-file-is-missing.md) | `load_binary_data`'s hole branch silently yields empty lists | diagnostics | ~8 | free — decided |
| [BUG-5](items/public-api-and-behavior/bug-5-the-exact-poles-lie-on-a-polygon-boundary.md) | The exact poles lie on a polygon boundary, so `certain_timezone_at` is `None` there | correctness | ~5 | free |
| [PYPI-1](items/packaging-distribution-and-release/pypi-1-the-pypi-project-holds-11-37-gb-of-pre-split-releases.md) | The PyPI project holds 11.37 GB of pre-split releases | packaging | S | free — maintainer action |
| [GH-524](items/packaging-distribution-and-release/gh-524-move-timezonefinder-under-packages-for-a-symmetric-workspace-layout.md) | Move `timezonefinder` under `packages/` | repo layout | M | free |
| [GH-362](items/data-pipeline-and-developer-tooling/gh-362-reuse-the-polygonarray-binaries-in-file-conversion.md) | Reuse the `PolygonArray` binaries in file conversion | internal | M | free |
| [BIG-3](items/data-pipeline-and-developer-tooling/big-3-the-geojson-parser-threads-nine-accumulator-lists-through-three-call-levels.md) | The GeoJSON parser threads nine accumulator lists through three call levels | internal | ~120 | verification is the expensive part |
| [PERF-1](items/lookup-geometry-and-data-format/perf-1-is-ocean-timezone-runs-a-regex-on-the-timezone-at-land-path.md) | `is_ocean_timezone` runs a regex on the `timezone_at_land` path | performance | ~2 | free — decided |
| [BATCH-1](items/public-api-and-behavior/batch-1-timezone-at-land-has-no-batch-form.md) | `timezone_at_land` has no batch form | public API | ~30 | below PERF-1 |
| [PERF-2](items/lookup-geometry-and-data-format/perf-2-zone-ids-of-is-a-numpy-fancy-index-over-a-handful-of-candidates.md) | `zone_ids_of` is a numpy fancy-index over a handful of candidates | performance | ~25 | free — ranked on simplicity, not on the timing |
| [PERF-6](items/lookup-geometry-and-data-format/perf-6-scalar-njit-helpers-on-the-query-path-cost-more-to-call-than-to-compute.md) | Scalar `njit` helpers on the query path cost more to call than to compute | performance | ~20 | free — measured |
| [DUP-1](items/lookup-geometry-and-data-format/dup-1-the-coordinate-bounds-are-declared-three-times.md) | The coordinate bounds are declared three times | internal | ~8 | free — decided |
| [BIG-2](items/data-pipeline-and-developer-tooling/big-2-calculate-shortcut-index-stats-computes-four-unrelated-things-in-one-pass.md) | `calculate_shortcut_index_stats` computes four unrelated things in one pass | internal | ~80 | free |
| [TOOL-1](items/data-pipeline-and-developer-tooling/tool-1-ruff-runs-close-to-its-default-rule-set.md) | ruff runs close to its default rule set | tooling | M | free |
| [GH-543](items/data-pipeline-and-developer-tooling/gh-543-the-numba-group-s-numpy-2-4-pin-is-stale-and-redundant.md) | The numba group's `numpy<2.4` pin is stale and redundant | tooling | ~4 | free |
| [DEAD-5](items/data-pipeline-and-developer-tooling/dead-5-reduced-timezone-mapping-has-no-consumer.md) | `REDUCED_TIMEZONE_MAPPING` has no consumer | internal | ~20 | free — decided |
| [DEAD-6](items/data-pipeline-and-developer-tooling/dead-6-iter-boundaries-in-shortcut-has-no-caller-outside-the-test-suite.md) | `_iter_boundaries_in_shortcut` has no caller outside the test suite | internal | ~20 | free |
| [GH-522](items/packaging-distribution-and-release/gh-522-shrink-the-repository-history-by-dropping-the-committed-coordinate-binaries.md) | Shrink the repository history by dropping the committed binaries | repo history | L | blocked by DATA-BINARIES |
| [GH-513](items/lookup-geometry-and-data-format/gh-513-drop-hole-polygons-entirely.md) | Drop hole polygons entirely | data format | L | blocked by GH-500 |
| [GH-505](items/lookup-geometry-and-data-format/gh-505-distance-to-the-nearest-timezone-border.md) | Distance to the nearest timezone border | public API | L | conditional — never implement unprompted |
| [GH-334](items/packaging-distribution-and-release/gh-334-official-mapping-for-the-reduced-timezone-set.md) | Official mapping for the reduced set | data | S | parked upstream |
| [GH-318](items/adjacent-projects/gh-318-improve-the-timezonefinder-gui.md) | Improve the timezonefinder GUI | adjacent | M | parked — different repository |

### Closed

Kept so the dead end is not re-proposed on its merits, and out of the ranking above because no pass will take them: there is no work to order. No `Size` column, for the same reason — it prices work, and there is none. The one line here is a handle; the reasoning is in the entry, because a row cannot refuse a re-proposal and only the argument can.

| Id | What | Area | Why it is closed |
|---|---|---|---|
| [GH-301](items/lookup-geometry-and-data-format/gh-301-sort-shortcut-polygons-by-overlap-area.md) | Sort shortcut polygons by overlap area | performance | rejected — 2.90 % headroom, bounded by enumeration over the packaged index |
| [PERF-4](items/lookup-geometry-and-data-format/perf-4-the-mapped-fetch-re-acquires-the-mmap-s-buffer-on-every-candidate.md) | The mapped fetch re-acquires the mmap buffer per candidate | performance | rejected — measured inside the query, below the noise floor |
| [GH-317](items/packaging-distribution-and-release/gh-317-reduce-the-release-artifact-count.md) | Reduce the release artifact count | packaging | withdrawn — superseded by the distribution split |

---
