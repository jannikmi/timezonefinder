# Improvement priority ranking

| Id | What | Area | Size | Eligibility |
|---|---|---|---|---|
| [GH-364](items/lookup-geometry-and-data-format/gh-364-free-threaded-python-via-a-native-candidate-loop.md) | Free-threaded Python, via a native candidate loop | performance | L | blocked on an h3 release |
| [GH-332](items/packaging-distribution-and-release/gh-332-reduced-timezone-dataset-as-a-second-distribution.md) | Reduced timezone dataset as a second distribution | packaging | M | parked — decided 2026-09-05 to publish nothing; resume only on evidenced user demand for an installable reduced dataset |
| [PROF-1](items/data-pipeline-and-developer-tooling/prof-1-the-stage-ladder-measures-the-checked-public-accessors.md) | The stage ladder measures the checked public accessors | tooling | ~25 | free — repairs the instrument every performance rank is read off |
| [PERF-9](items/lookup-geometry-and-data-format/perf-9-the-candidate-loop-reads-numpy-scalars-where-a-memoryview-yields-an-int.md) | The candidate loop reads numpy scalars where a memoryview yields an `int` | performance | ~25 | free — measured -12.7 % of an ambiguous query |
| [PERF-2](items/lookup-geometry-and-data-format/perf-2-the-candidate-loop-builds-a-zone-id-array-to-read-one-element.md) | The candidate loop builds a zone id array to read one element | performance | ~20 | free — measured -10.1 % of an ambiguous query, and it deletes code |
| [PERF-8](items/lookup-geometry-and-data-format/perf-8-the-hole-registry-is-probed-with-an-exception-per-candidate.md) | The hole check raises a `KeyError` on most candidates | performance | ~10 | free — measured -4.9 % of an ambiguous query |
| [GH-524](items/packaging-distribution-and-release/gh-524-move-timezonefinder-under-packages-for-a-symmetric-workspace-layout.md) | Move `timezonefinder` under `packages/` | repo layout | M | needs a decision — move it now, park it on a third distribution, or refuse it |
| [GH-362](items/data-pipeline-and-developer-tooling/gh-362-reuse-the-polygonarray-binaries-in-file-conversion.md) | Reuse the `PolygonArray` binaries in file conversion | internal | M | free |
| [BIG-3](items/data-pipeline-and-developer-tooling/big-3-the-geojson-parser-threads-nine-accumulator-lists-through-three-call-levels.md) | The GeoJSON parser threads nine accumulator lists through three call levels | internal | ~120 | verification is the expensive part |
| [PERF-6](items/lookup-geometry-and-data-format/perf-6-scalar-njit-helpers-on-the-query-path-cost-more-to-call-than-to-compute.md) | Scalar `njit` helpers on the query path cost more to call than to compute | performance | ~20 | free — measured |
| [BIG-2](items/data-pipeline-and-developer-tooling/big-2-calculate-shortcut-index-stats-computes-four-unrelated-things-in-one-pass.md) | `calculate_shortcut_index_stats` computes four unrelated things in one pass | internal | ~80 | free |
| [TOOL-1](items/data-pipeline-and-developer-tooling/tool-1-ruff-runs-close-to-its-default-rule-set.md) | ruff runs close to its default rule set, and holds `ruff` at 0.15.x | tooling | M | free — ~97 findings measured on 0.16.5 |
| [DOC-2](items/data-pipeline-and-developer-tooling/doc-2-convert-the-data-format-reference-to-semantic-line-breaks.md) | Convert `docs/data_format.rst` to semantic line breaks, and record the convention | docs | ~205 | free — take when nothing else is queued; DOC-2 states the family's whole argument |
| [DOC-3](items/data-pipeline-and-developer-tooling/doc-3-convert-the-benchmarking-methodology-page-to-semantic-line-breaks.md) | Convert `docs/benchmarking_methodology.rst` to semantic line breaks | docs | ~210 | free — take when nothing else is queued |
| [DOC-4](items/data-pipeline-and-developer-tooling/doc-4-convert-the-architecture-page-to-semantic-line-breaks.md) | Convert `docs/architecture.rst` to semantic line breaks | docs | ~135 | free — take when nothing else is queued; a third of the page is directives and literal blocks |
| [DOC-5](items/data-pipeline-and-developer-tooling/doc-5-convert-the-remaining-prose-pages-to-semantic-line-breaks.md) | Convert the remaining prose pages to semantic line breaks | docs | ~170 | free — take when nothing else is queued; eight small files including `README.rst` |
| [DOC-6](items/data-pipeline-and-developer-tooling/doc-6-price-a-check-that-rejects-a-new-hard-wrapped-paragraph.md) | Price a check that rejects a newly hard-wrapped paragraph | docs tooling | S | blocked on DOC-2 to DOC-5 — and may close with a measurement rather than a check |
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
