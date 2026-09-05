# DOC-5 — convert the remaining hand-written prose pages to semantic line breaks

- **Location:** `docs/1_usage.rst` (51 continuation lines), `docs/alternatives.rst` (40), `docs/2_use_cases.rst` (30), `docs/7_performance.rst` (17), `docs/index.rst` (9), `docs/0_getting_started.rst` (5), `docs/4_api.rst` (5) — 157 lines across seven files, counted by the method [DOC-2](doc-2-convert-the-data-format-reference-to-semantic-line-breaks.md) states, which also carries the cost, the convention and the ranking argument.
- **Defect:** the same hard wrap, spread thin. These are one slice rather than seven because no single page here is large enough to review on its own, and the conversion is the same mechanical edit in each.
- **What "remaining" excludes, so this does not have to be re-derived.** `docs/3_about.rst`, `docs/badges.rst`, `docs/5_contributing.rst` and `docs/6_changelog.rst` are hand-written and already conformant — link stubs and includes with no wrapped paragraph — so they are in scope and need no edit. Three things are genuinely out of scope: `docs/benchmark_results_*.rst` and `docs/data_report.rst` are written by `scripts/render_benchmark_reports.py` and the data report generator, so their line breaks are the generator's output and a finding there belongs against the generator; `CHANGELOG.rst` is already conformant where it is live — the unreleased section and every release back to 8.2.5 are one line per bullet — and its wrapped historical tail below that is deliberately left alone, since rewriting released history changes no reader's experience and costs the blame on it; and everything under `contributing/` is already one line per paragraph.
- **`README.rst` left this slice on 2026-09-05 and is now [DOC-7](doc-7-move-the-readme-to-markdown-with-semantic-line-breaks.md)**, which converts it to Markdown and reflows it in the same pass — a format migration rewrites the file anyway, so splitting the two would mean reviewing that one file's diff twice. Its 15 continuation lines moved with it, which is the whole of the difference between this slice's 172 lines across eight files as first filed and the 157 across seven above.
- **Fix:** one line per sentence, and per clause where a sentence's clauses are edited independently. Nothing blocks this on DOC-2; whichever slice runs first records the convention.
- **Not in the same pull request as a content change to these files.**
- **Changelog sentence it stands under:** the remaining hand-written documentation pages use semantic line breaks. Development-only, so `Internal:`.
- **Status:** open.
- **Last touched:** 2026-09-05 — sliced out of DOC-1 and re-counted per file, then narrowed by handing `README.rst` to DOC-7.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Changelog and release-note policy](../../../development/changelog-and-release-note-policy.md)
