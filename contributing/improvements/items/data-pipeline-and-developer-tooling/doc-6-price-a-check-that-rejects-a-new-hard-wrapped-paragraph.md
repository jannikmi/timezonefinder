# DOC-6 — price a check that rejects a newly hard-wrapped paragraph

- **Location:** `.pre-commit-config.yaml`, or `tests/`; the pages [DOC-2](doc-2-convert-the-data-format-reference-to-semantic-line-breaks.md) to [DOC-5](doc-5-convert-the-remaining-prose-pages-to-semantic-line-breaks.md) convert, plus the README that [DOC-7](doc-7-move-the-readme-to-markdown-with-semantic-line-breaks.md) does.
- **What it is.** Those slices buy one clean tree; the convention recorded with the first of them is what is meant to keep it. A check is the cheaper insurance if it can be written without false positives — re-doing the conversion costs far more than the check does.
- **Price it before writing it, and the price is the false-positive rate.** The heuristic is "an unindented prose line whose unindented prose predecessor did not end a sentence" — the one DOC-2 states, which is already a measuring instrument and not yet a gate. It has to not fire on tables, directives, literal and code blocks, field lists, section underlines, list item starts, or a deliberately broken long link. Measuring that is the work: run the candidate over the converted tree and over `contributing/`, which is already conformant, and count what it flags. A check that fires on correct prose gets `# noqa`-ed into uselessness or disabled, which is worse than no check.
- **This item may legitimately ship no code**, and that is not a failure: if the false-positive rate is not near zero, the outcome is to record the measurement and close this as rejected, keeping the numbers so the next pass does not re-run them. It therefore carries no changelog sentence in advance — a shipped check gets one under `Internal:`, and a refusal gets none.
- **It cannot be taken before DOC-2 to DOC-5 and DOC-7 have all landed**, because it fails on every unconverted page, and the README is one of them until DOC-7 reflows it. That is the only real precondition anywhere in this family, and the whole of its sequencing. [DOC-8](doc-8-move-the-changelog-and-its-fragments-to-markdown.md) is not a precondition: it renames the changelog without reflowing it, and the tail this check skips is skipped under either name.
- **What the check must skip** is listed in DOC-5: the generated report pages, and `CHANGELOG.rst`'s historical tail.
- **Status:** blocked on DOC-2, DOC-3, DOC-4, DOC-5 and DOC-7.
- **Last touched:** 2026-09-05 — sliced out of DOC-1, which raised the check as worth pricing without pricing it; DOC-7 added to the blockers when the README left DOC-5.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Changelog and release-note policy](../../../development/changelog-and-release-note-policy.md)
