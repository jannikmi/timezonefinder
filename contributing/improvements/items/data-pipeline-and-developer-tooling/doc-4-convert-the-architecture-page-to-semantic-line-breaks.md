# DOC-4 — convert `docs/architecture.rst` to semantic line breaks

- **Location:** `docs/architecture.rst`.
- **Defect:** 135 continuation lines, counted by the method [DOC-2](doc-2-convert-the-data-format-reference-to-semantic-line-breaks.md) states, which also carries the cost and the convention. **This page was first filed at 195 and re-counted down**, because the looser count treated indented directive and literal-block lines as prose; that is also why it is the smallest of the three large slices rather than the middle one.
- **Watch the diagrams and directives.** A third of this page's non-blank lines are indented — literal blocks, directive bodies, list continuations — and their line breaks are content. Only top-level prose paragraphs are reflowed, and the converted page must render identically: `make docs` building without new warnings is the check that says so, and `rstcheck` does not stand in for it.
- **Fix:** one line per sentence, and per clause where a sentence's clauses are edited independently. Nothing blocks this on DOC-2; whichever slice runs first records the convention.
- **Not in the same pull request as a content change to this file.**
- **Changelog sentence it stands under:** the architecture page uses semantic line breaks. Development-only, so `Internal:`.
- **Withdrawn 2026-09-06, superseded by [DOC-9](doc-9-migrate-the-documentation-from-sphinx-to-mkdocs.md).** The maintainer chose to move `docs/` off Sphinx to MkDocs, which rewrites `docs/architecture.rst` wholesale into Markdown — so the line breaks are set while the new file is written and cost nothing extra, exactly as this slice's own rule against mixing a reflow with a content change would demand. The counts and the method above are kept because DOC-9 checks its converted output against them. **Reopen this entry if DOC-9 is abandoned**; the hard wrap and its merge-conflict cost are unchanged until one of the two lands.
- **Status:** withdrawn — superseded by DOC-9.
- **Last touched:** 2026-09-06 — withdrawn into DOC-9. Filed 2026-09-05 — sliced out of DOC-1 and re-counted, downwards.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Changelog and release-note policy](../../../development/changelog-and-release-note-policy.md)
