# DOC-6 — price a check that rejects a newly hard-wrapped paragraph

- **Location:** `.pre-commit-config.yaml`, or `tests/`; the pages [DOC-2](doc-2-convert-the-data-format-reference-to-semantic-line-breaks.md) to [DOC-5](doc-5-convert-the-remaining-prose-pages-to-semantic-line-breaks.md) convert.
- **What it is.** The conversion buys one clean tree; the convention recorded in DOC-2 is what is meant to keep it. A check is the cheaper insurance if it can be written without false positives — re-doing the conversion costs far more than the check does.
- **Price it before writing it, and the price is the false-positive rate.** The heuristic is "a prose line whose predecessor is a prose line that did not end a sentence", and it has to not fire on tables, directives, literal and code blocks, field lists, section underlines, or a deliberately broken long link. Measuring that is the work: run the candidate over the converted tree and over `contributing/`, which is already conformant, and count what it flags. A check that fires on correct prose gets `# noqa`-ed into uselessness or disabled, which is worse than no check — so if the rate is not near zero, record that and close this rather than shipping it.
- **It cannot be taken before DOC-2 to DOC-5 have all landed**, because it fails on every unconverted page. That is the whole of its sequencing.
- **Generated pages are outside it.** `benchmark_results_*.rst` and `data_report.rst` are written by `scripts/render_benchmark_reports.py` and the data report generator, so their line breaks are the generator's output; the check must skip them or a regeneration turns red. `CHANGELOG.rst`'s historical tail below 8.2.5 is wrapped and is deliberately left that way — rewriting released history changes no reader's experience and costs the blame on it.
- **Status:** blocked on DOC-2, DOC-3, DOC-4 and DOC-5.
- **Last touched:** 2026-09-05 — sliced out of DOC-1, which raised the check as worth pricing without pricing it.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Changelog and release-note policy](../../../development/changelog-and-release-note-policy.md)
