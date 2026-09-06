# Improvement priority ranking

| Id | What | Area | Size | Eligibility |
|---|---|---|---|---|
| [GH-364](items/lookup-geometry-and-data-format/gh-364-free-threaded-python-via-a-native-candidate-loop.md) | Free-threaded Python, via a native candidate loop | performance | L | blocked on an h3 release |
| [GH-332](items/packaging-distribution-and-release/gh-332-reduced-timezone-dataset-as-a-second-distribution.md) | Reduced timezone dataset as a second distribution | packaging | M | parked — decided 2026-09-05 to publish nothing; resume only on evidenced user demand for an installable reduced dataset |
| [BUG-6](items/lookup-geometry-and-data-format/bug-6-timezonefinder-cleanup-releases-nothing-in-the-mapped-mode.md) | `TimezoneFinder.cleanup()` releases nothing in the mapped mode | resource lifetime | ~40 | free — the accessor half is already correct; this is the missing route from the finder to it, and it enforces a documented contract that has never bitten |
| [GH-524](items/packaging-distribution-and-release/gh-524-move-timezonefinder-under-packages-for-a-symmetric-workspace-layout.md) | Move `timezonefinder` under `packages/` | repo layout | M | needs a decision — move it now, park it on a third distribution, or refuse it |
| [GH-362](items/data-pipeline-and-developer-tooling/gh-362-reuse-the-polygonarray-binaries-in-file-conversion.md) | Reuse the `PolygonArray` binaries in file conversion | internal | M | free — ranked on clarity; the read-back-per-access implementation is ruled out by measurement |
| [GH-301](items/lookup-geometry-and-data-format/gh-301-sort-shortcut-polygons-by-overlap-area.md) | Sort shortcut polygons by overlap area | performance | M | free — 2.90 % fewer point-in-polygon tests by enumeration; last of the performance items on size, not on the instrument |
| [TOOL-4](items/data-pipeline-and-developer-tooling/tool-4-three-small-lint-families-are-not-selected-at-all.md) | Three small lint families are not selected at all | tooling | ~15 | free — 7 sites; the item is the adopt-or-refuse judgement |
| [TOOL-5](items/data-pipeline-and-developer-tooling/tool-5-the-pylint-complexity-limits-are-a-threshold-argument.md) | The pylint complexity limits are a threshold argument | tooling | M | needs a decision — refuse `PLR09xx`, ratchet it above the tree, or adopt its defaults |
| [TOOL-6](items/data-pipeline-and-developer-tooling/tool-6-the-ruff-version-is-pinned-below-0-16.md) | The ruff version is pinned below 0.16 | tooling | L | needs a decision — a pass may not change a dependency pin or the lockfile |
| [DOC-7](items/data-pipeline-and-developer-tooling/doc-7-move-the-readme-to-markdown-with-semantic-line-breaks.md) | Move `README.rst` to Markdown, reflowing it in the same pass | docs | ~200 | free — decided 2026-09-05; changes the published PyPI page, and is the one Markdown move DOC-9 does not cover |
| [DOC-8](items/data-pipeline-and-developer-tooling/doc-8-move-the-changelog-and-its-fragments-to-markdown.md) | Move `CHANGELOG.rst` and the `changelog.d/` fragments to Markdown | docs | M | free — decided 2026-09-05; narrow code coupling, but not while a release is in flight |
| [DOC-10](items/data-pipeline-and-developer-tooling/doc-10-plan-the-mkdocs-migration-for-maintainer-review.md) | Plan the MkDocs migration for maintainer review | docs | M | free — produces a plan and a losslessness contract; DOC-9 cannot start without it |
| [DOC-9](items/data-pipeline-and-developer-tooling/doc-9-migrate-the-documentation-from-sphinx-to-mkdocs.md) | Migrate `docs/` from Sphinx to MkDocs, converting the prose in the same pass | docs | L | blocked on DOC-10 — the plan and its approval; big-bang, 5,332 lines, and it absorbs DOC-2 to DOC-5 |
| [DOC-6](items/data-pipeline-and-developer-tooling/doc-6-price-a-check-that-rejects-a-new-hard-wrapped-paragraph.md) | Price a check that rejects a newly hard-wrapped paragraph | docs tooling | S | blocked on DOC-9 and DOC-7 — and may close with a measurement rather than a check |
| [GH-522](items/packaging-distribution-and-release/gh-522-shrink-the-repository-history-by-dropping-the-committed-coordinate-binaries.md) | Shrink the repository history by dropping the committed binaries | repo history | L | parked — resume only for a concrete repository-history size need |
| [PYPI-1](items/packaging-distribution-and-release/pypi-1-the-pypi-project-holds-11-37-gb-of-pre-split-releases.md) | The PyPI project holds 11.37 GB of pre-split releases | packaging | S | conditional — only if PyPI storage is exhausted |
| [GH-505](items/lookup-geometry-and-data-format/gh-505-distance-to-the-nearest-timezone-border.md) | Distance to the nearest timezone border | public API | L | conditional — never implement unprompted |
| [GH-318](items/adjacent-projects/gh-318-improve-the-timezonefinder-gui.md) | Improve the timezonefinder GUI | adjacent | M | parked — different repository |

### Closed

Kept so the dead end is not re-proposed on its merits, and out of the ranking above because no pass will take them: there is no work to order. No `Size` column, for the same reason — it prices work, and there is none. The one line here is a handle; the reasoning is in the entry, because a row cannot refuse a re-proposal and only the argument can.

| Id | What | Area | Why it is closed |
|---|---|---|---|
| [GH-513](items/lookup-geometry-and-data-format/gh-513-drop-hole-polygons-entirely.md) | Drop hole polygons entirely | data format | rejected — the zone precedence relation it needs is cyclic, so no candidate ordering satisfies it |
| [GH-317](items/packaging-distribution-and-release/gh-317-reduce-the-release-artifact-count.md) | Reduce the release artifact count | packaging | withdrawn — superseded by the distribution split |
| [DOC-2](items/data-pipeline-and-developer-tooling/doc-2-convert-the-data-format-reference-to-semantic-line-breaks.md) | Convert `docs/data_format.rst` to semantic line breaks, and record the convention | docs | withdrawn — superseded by DOC-9, which rewrites `docs/data_format.rst` into Markdown and sets its line breaks in the same pass |
| [DOC-3](items/data-pipeline-and-developer-tooling/doc-3-convert-the-benchmarking-methodology-page-to-semantic-line-breaks.md) | Convert `docs/benchmarking_methodology.rst` to semantic line breaks | docs | withdrawn — superseded by DOC-9, which rewrites `docs/benchmarking_methodology.rst` into Markdown and sets its line breaks in the same pass |
| [DOC-4](items/data-pipeline-and-developer-tooling/doc-4-convert-the-architecture-page-to-semantic-line-breaks.md) | Convert `docs/architecture.rst` to semantic line breaks | docs | withdrawn — superseded by DOC-9; kept for the diagram and directive caveats the conversion of that page still has to respect |
| [DOC-5](items/data-pipeline-and-developer-tooling/doc-5-convert-the-remaining-prose-pages-to-semantic-line-breaks.md) | Convert the remaining prose pages to semantic line breaks | docs | withdrawn — superseded by DOC-9; kept for the per-file counts and the exclusion list DOC-6 reads |

---
