# Improvement priority ranking

| Id | What | Area | Size | Eligibility |
|---|---|---|---|---|
| [BENCH-1](items/packaging-distribution-and-release/bench-1-comparing-two-candidate-implementations-hand-rolls-a-harness-every-time.md) | Comparing two candidate implementations hand-rolls a harness every time | tooling | M | free |
| [BENCH-2](items/packaging-distribution-and-release/bench-2-the-committed-benchmark-pages-are-measured-on-whichever-machine-happens-to-render-them.md) | The committed benchmark pages are measured on whichever machine happens to render them | benchmarking | M | free — decided: render in CI and publish the runner's numbers |
| [BENCH-3](items/packaging-distribution-and-release/bench-3-the-tracked-measurement-and-the-published-pages-describe-different-experiments.md) | The tracked measurement and the published pages describe different experiments | benchmarking | S–M | free — the acceleration-path assertion is independent of BENCH-2's decision |
| [CHANGELOG-1](items/packaging-distribution-and-release/changelog-1-changelog-fragments-keep-concurrent-pull-requests-out-of-one-unreleased-section.md) | Changelog fragments keep concurrent pull requests out of one unreleased section | release tooling | M | free — removes the remaining routine shared append point |
| [BATCH-2](items/packaging-distribution-and-release/batch-2-the-batch-lookups-are-measured-by-nothing-the-ci-tracks.md) | The batch lookups are measured by nothing the CI tracks | tooling | S–M | free — the comparator compatibility it waited on merged in #566; measure the expanded core set's noise first |
| [GH-501](items/packaging-distribution-and-release/gh-501-guardrails-on-the-automated-data-update-pipeline.md) | Guardrails on the automated data update pipeline | release | M | free — decided |
| [BIG-1](items/lookup-geometry-and-data-format/big-1-iter-boundary-ids-of-zone-re-opens-zone-positions-npy-on-every-call.md) | `_iter_boundary_ids_of_zone` re-opens `zone_positions.npy` on every call | performance | ~10 | free — decided |
| [GH-364](items/lookup-geometry-and-data-format/gh-364-free-threaded-python-via-a-native-candidate-loop.md) | Free-threaded Python, via a native candidate loop | performance | L | blocked on an h3 release |
| [GH-334](items/packaging-distribution-and-release/gh-334-official-mapping-for-the-reduced-timezone-set.md) | Official mapping for the reduced set | data | S | free — upstream shipped the mapping in the 2026c release |
| [GH-332](items/packaging-distribution-and-release/gh-332-reduced-timezone-dataset-as-a-second-distribution.md) | Reduced timezone dataset as a second distribution | packaging | M | sequenced after GH-334 |
| [TOOL-6](items/data-pipeline-and-developer-tooling/tool-6-parse-data-rewrites-the-committed-data-report-whatever-out-it-was-given.md) | `parse_data` rewrites the committed data report whatever `-out` it was given | tooling | ~150 | free — decided |
| [GH-524](items/packaging-distribution-and-release/gh-524-move-timezonefinder-under-packages-for-a-symmetric-workspace-layout.md) | Move `timezonefinder` under `packages/` | repo layout | M | free |
| [GH-362](items/data-pipeline-and-developer-tooling/gh-362-reuse-the-polygonarray-binaries-in-file-conversion.md) | Reuse the `PolygonArray` binaries in file conversion | internal | M | free |
| [BIG-3](items/data-pipeline-and-developer-tooling/big-3-the-geojson-parser-threads-nine-accumulator-lists-through-three-call-levels.md) | The GeoJSON parser threads nine accumulator lists through three call levels | internal | ~120 | verification is the expensive part |
| [PERF-2](items/lookup-geometry-and-data-format/perf-2-zone-ids-of-is-a-numpy-fancy-index-over-a-handful-of-candidates.md) | `zone_ids_of` is a numpy fancy-index over a handful of candidates | performance | ~25 | free — ranked on simplicity, not on the timing |
| [PERF-6](items/lookup-geometry-and-data-format/perf-6-scalar-njit-helpers-on-the-query-path-cost-more-to-call-than-to-compute.md) | Scalar `njit` helpers on the query path cost more to call than to compute | performance | ~20 | free — measured |
| [PERF-7](items/lookup-geometry-and-data-format/perf-7-a-single-block-ring-pays-for-an-index-it-cannot-use.md) | The blocked point-in-polygon kernel's per-call and per-edge overheads | performance | ~25 | free — ranked on a count, below the noise floor |
| [DUP-1](items/lookup-geometry-and-data-format/dup-1-the-coordinate-bounds-are-declared-three-times.md) | The coordinate bounds are declared three times | internal | ~8 | free — decided |
| [BIG-2](items/data-pipeline-and-developer-tooling/big-2-calculate-shortcut-index-stats-computes-four-unrelated-things-in-one-pass.md) | `calculate_shortcut_index_stats` computes four unrelated things in one pass | internal | ~80 | free |
| [TOOL-1](items/data-pipeline-and-developer-tooling/tool-1-ruff-runs-close-to-its-default-rule-set.md) | ruff runs close to its default rule set, and holds `ruff` at 0.15.x | tooling | M | free — ~97 findings measured on 0.16.5 |
| [DEAD-5](items/data-pipeline-and-developer-tooling/dead-5-reduced-timezone-mapping-has-no-consumer.md) | `REDUCED_TIMEZONE_MAPPING` has no consumer | internal | ~20 | free — decided |
| [DEAD-6](items/data-pipeline-and-developer-tooling/dead-6-iter-boundaries-in-shortcut-has-no-caller-outside-the-test-suite.md) | `_iter_boundaries_in_shortcut` has no caller outside the test suite | internal | ~20 | free |
| [DOC-1](items/data-pipeline-and-developer-tooling/doc-1-the-prose-documentation-is-hard-wrapped-so-every-small-edit-reflows-a-block.md) | The prose documentation is hard-wrapped, so every small edit reflows a block | docs | L | free — splittable per file; 628 lines across 11 |
| [GH-522](items/packaging-distribution-and-release/gh-522-shrink-the-repository-history-by-dropping-the-committed-coordinate-binaries.md) | Shrink the repository history by dropping the committed binaries | repo history | L | parked — resume only for a concrete repository-history size need |
| [GH-301](items/lookup-geometry-and-data-format/gh-301-sort-shortcut-polygons-by-overlap-area.md) | Sort shortcut polygons by overlap area | performance | M | parked — 2.90 % headroom by enumeration; resume only if the packaged index changes that bound |
| [PERF-4](items/lookup-geometry-and-data-format/perf-4-the-mapped-fetch-re-acquires-the-mmap-s-buffer-on-every-candidate.md) | The mapped fetch re-acquires the mmap buffer per candidate | performance | ~30 | parked — measured below the noise floor in-query; resume only on a measurement that clears it |
| [PYPI-1](items/packaging-distribution-and-release/pypi-1-the-pypi-project-holds-11-37-gb-of-pre-split-releases.md) | The PyPI project holds 11.37 GB of pre-split releases | packaging | S | conditional — only if PyPI storage is exhausted |
| [GH-505](items/lookup-geometry-and-data-format/gh-505-distance-to-the-nearest-timezone-border.md) | Distance to the nearest timezone border | public API | L | conditional — never implement unprompted |
| [GH-318](items/adjacent-projects/gh-318-improve-the-timezonefinder-gui.md) | Improve the timezonefinder GUI | adjacent | M | parked — different repository |

### Closed

Kept so the dead end is not re-proposed on its merits, and out of the ranking above because no pass will take them: there is no work to order. No `Size` column, for the same reason — it prices work, and there is none. The one line here is a handle; the reasoning is in the entry, because a row cannot refuse a re-proposal and only the argument can.

| Id | What | Area | Why it is closed |
|---|---|---|---|
| [GH-513](items/lookup-geometry-and-data-format/gh-513-drop-hole-polygons-entirely.md) | Drop hole polygons entirely | data format | rejected — the zone precedence relation it needs is cyclic, so no candidate ordering satisfies it |
| [GH-317](items/packaging-distribution-and-release/gh-317-reduce-the-release-artifact-count.md) | Reduce the release artifact count | packaging | withdrawn — superseded by the distribution split |

---
