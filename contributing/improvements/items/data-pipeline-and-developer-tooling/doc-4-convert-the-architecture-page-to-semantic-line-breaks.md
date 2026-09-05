# DOC-4 — convert `docs/architecture.rst` to semantic line breaks

- **Location:** `docs/architecture.rst`.
- **Defect:** 195 continuation lines. [DOC-2](doc-2-convert-the-data-format-reference-to-semantic-line-breaks.md) states the cost and the convention.
- **Watch the diagrams and directives.** This page carries more literal blocks and directives than the other two large ones, and their line breaks are content: only prose paragraphs are reflowed, and a converted page must render identically. `make docs` building without new warnings is the check that says so; `rstcheck` alone does not.
- **Fix:** one line per sentence, and per clause where a sentence's clauses are edited independently. Take it after DOC-2, which records the convention; it needs nothing else from that slice.
- **Not in the same pull request as a content change to this file.**
- **Changelog sentence it stands under:** the architecture page uses semantic line breaks. Development-only, so `Internal:`.
- **Status:** open.
- **Last touched:** 2026-09-05 — sliced out of DOC-1; counted at 195 continuation lines.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Changelog and release-note policy](../../../development/changelog-and-release-note-policy.md)
