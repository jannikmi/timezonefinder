# DOC-5 — convert the remaining hand-written prose pages to semantic line breaks

- **Location:** `docs/1_usage.rst` (65 continuation lines), `docs/alternatives.rst` (47), `docs/2_use_cases.rst` (37), `README.rst` (34), `docs/index.rst` (17), `docs/7_performance.rst` (17), `docs/0_getting_started.rst` (9), `docs/3_about.rst` (5), `docs/4_api.rst` (5), `docs/badges.rst` (2) — 238 lines across ten files.
- **Defect:** the same hard wrap [DOC-2](doc-2-convert-the-data-format-reference-to-semantic-line-breaks.md) describes, spread thin. These are one slice rather than ten because no single page here is large enough to review on its own, and the conversion is the same mechanical edit in each.
- **`README.rst` is rendered by PyPI as well as by Sphinx**, which is the one place to check the rendering rather than assume it: PyPI's reStructuredText renderer is not Sphinx. It folds a single newline into a space as well, but confirm the rendered page rather than taking that from here.
- **Fix:** one line per sentence, and per clause where a sentence's clauses are edited independently. Take it after DOC-2, which records the convention; it needs nothing else from that slice.
- **Not in the same pull request as a content change to these files.**
- **Changelog sentence it stands under:** the remaining hand-written documentation pages use semantic line breaks. Development-only, so `Internal:`.
- **Status:** open.
- **Last touched:** 2026-09-05 — sliced out of DOC-1; counted per file.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Changelog and release-note policy](../../../development/changelog-and-release-note-policy.md)
