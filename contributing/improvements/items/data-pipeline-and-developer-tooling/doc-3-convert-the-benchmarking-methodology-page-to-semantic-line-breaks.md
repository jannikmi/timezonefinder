# DOC-3 — convert `docs/benchmarking_methodology.rst` to semantic line breaks

- **Location:** `docs/benchmarking_methodology.rst`.
- **Defect:** 215 continuation lines. [DOC-2](doc-2-convert-the-data-format-reference-to-semantic-line-breaks.md) states the cost this shares and the convention that fixes it; it is not restated here.
- **Why this page is worth its own slice:** it is the page a measurement result is argued against, so it is edited a clause at a time — which is precisely the edit the hard wrap makes unreadable in review.
- **Fix:** one line per sentence, and per clause where a sentence's clauses are edited independently. Rendered output is unchanged. Take it after DOC-2, which records the convention; it needs nothing else from that slice.
- **Not in the same pull request as a content change to this file.**
- **Changelog sentence it stands under:** the benchmarking methodology page uses semantic line breaks. Development-only, so `Internal:`.
- **Status:** open.
- **Last touched:** 2026-09-05 — sliced out of DOC-1; counted at 215 continuation lines.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Changelog and release-note policy](../../../development/changelog-and-release-note-policy.md)
