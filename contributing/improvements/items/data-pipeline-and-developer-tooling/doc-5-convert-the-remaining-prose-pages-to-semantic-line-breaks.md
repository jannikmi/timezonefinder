# DOC-5 — convert the remaining hand-written prose pages to semantic line breaks

- **Location:** `docs/1_usage.rst` (51 continuation lines), `docs/alternatives.rst` (40), `docs/2_use_cases.rst` (30), `docs/7_performance.rst` (17), `README.rst` (15), `docs/index.rst` (9), `docs/0_getting_started.rst` (5), `docs/4_api.rst` (5) — 172 lines across eight files, counted by the method [DOC-2](doc-2-convert-the-data-format-reference-to-semantic-line-breaks.md) states, which also carries the cost, the convention and the ranking argument.
- **Defect:** the same hard wrap, spread thin. These are one slice rather than eight because no single page here is large enough to review on its own, and the conversion is the same mechanical edit in each.
- **What "remaining" excludes, so this does not have to be re-derived.** `docs/3_about.rst`, `docs/badges.rst`, `docs/5_contributing.rst` and `docs/6_changelog.rst` are hand-written and already conformant — link stubs and includes with no wrapped paragraph — so they are in scope and need no edit. Three things are genuinely out of scope: `docs/benchmark_results_*.rst` and `docs/data_report.rst` are written by `scripts/render_benchmark_reports.py` and the data report generator, so their line breaks are the generator's output and a finding there belongs against the generator; `CHANGELOG.rst` is already conformant where it is live — the unreleased section and every release back to 8.2.5 are one line per bullet — and its wrapped historical tail below that is deliberately left alone, since rewriting released history changes no reader's experience and costs the blame on it; and everything under `contributing/` is already one line per paragraph.
- **`README.rst` is rendered by PyPI as well as by Sphinx**, which is the one place to check the rendering rather than assume it: PyPI's reStructuredText renderer is not Sphinx. It folds a single newline into a space as well, but confirm the rendered page rather than taking that from here.
- **Fix:** one line per sentence, and per clause where a sentence's clauses are edited independently. Nothing blocks this on DOC-2; whichever slice runs first records the convention.
- **Not in the same pull request as a content change to these files.**
- **Changelog sentence it stands under:** the remaining hand-written documentation pages use semantic line breaks. Development-only, so `Internal:`.
- **Status:** open.
- **Last touched:** 2026-09-05 — sliced out of DOC-1 and re-counted per file.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Changelog and release-note policy](../../../development/changelog-and-release-note-policy.md)
