# DOC-3 — convert `docs/benchmarking_methodology.rst` to semantic line breaks

- **Location:** `docs/benchmarking_methodology.rst`.
- **Defect:** 208 continuation lines, counted by the method [DOC-2](doc-2-convert-the-data-format-reference-to-semantic-line-breaks.md) states. DOC-2 also carries the cost this shares, the convention that fixes it, and why the family ranks where it does; none of that is restated here.
- **Why this page is worth its own slice:** it is the page a measurement result is argued against, so it is edited a clause at a time — which is precisely the edit the hard wrap makes unreadable in review.
- **Fix:** one line per sentence, and per clause where a sentence's clauses are edited independently. Rendered output is unchanged. Nothing blocks this on DOC-2; whichever of the two runs first records the convention.
- **Not in the same pull request as a content change to this file.**
- **Changelog sentence it stands under:** the benchmarking methodology page uses semantic line breaks. Development-only, so `Internal:`.
- **Withdrawn 2026-09-06, superseded by [DOC-9](doc-9-migrate-the-documentation-from-sphinx-to-mkdocs.md).** The maintainer chose to move `docs/` off Sphinx to MkDocs, which rewrites `docs/benchmarking_methodology.rst` wholesale into Markdown — so the line breaks are set while the new file is written and cost nothing extra, exactly as this slice's own rule against mixing a reflow with a content change would demand. The counts and the method above are kept because DOC-9 checks its converted output against them. **Reopen this entry if DOC-9 is abandoned**; the hard wrap and its merge-conflict cost are unchanged until one of the two lands.
- **Status:** withdrawn — superseded by DOC-9.
- **Last touched:** 2026-09-06 — withdrawn into DOC-9. Filed 2026-09-05 — sliced out of DOC-1 and re-counted.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Changelog and release-note policy](../../../development/changelog-and-release-note-policy.md)
