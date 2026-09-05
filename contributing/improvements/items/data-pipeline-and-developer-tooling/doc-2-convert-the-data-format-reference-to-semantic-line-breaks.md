# DOC-2 — convert `docs/data_format.rst` to semantic line breaks, and record the convention

- **Location:** `docs/data_format.rst`; `contributing/development/documentation-maintenance-rules.md`.
- **Defect:** 249 continuation lines, the most of any page in the tree — a paragraph is hard-wrapped at a fixed column, so a line break falls where the column ran out rather than where the sentence turns. Changing one word reflows every following line of its paragraph, which makes the diff of a one-word correction indistinguishable from a rewrite: a reviewer cannot see what changed, `git blame` attributes the whole block to whoever last touched any of it, and two passes editing different sentences of the same paragraph conflict on lines neither of them meant to change. That last cost is not hypothetical — concurrent sessions edit this tree, and a reflowed paragraph is a conflict with no semantic content to resolve.
- **Fix:** one line per sentence, and per clause where a sentence is long enough that its clauses are edited independently. Rendered output is identical, since reStructuredText folds a single newline into a space, so no published page changes.
- **This slice also records the convention, and it is why it goes first.** `contributing/development/documentation-maintenance-rules.md` states no wrapping convention at all, which is why the tree has both styles: everything under `contributing/` is already one line per paragraph or bullet, and `docs/` is hard-wrapped. Converting without recording the rule buys one clean pass and then re-accumulates — so the rule lands here, before the other pages are converted against it. [DOC-3](doc-3-convert-the-benchmarking-methodology-page-to-semantic-line-breaks.md), [DOC-4](doc-4-convert-the-architecture-page-to-semantic-line-breaks.md) and [DOC-5](doc-5-convert-the-remaining-prose-pages-to-semantic-line-breaks.md) are the remaining pages and are ordered after this one for that reason alone; they touch disjoint files and are otherwise independent of each other.
- **Not in the same pull request as a content change to this file.** A reflow diff and an edit diff in one review are exactly the reviewing problem this work exists to remove.
- **Changelog sentence it stands under:** the data format reference uses semantic line breaks, so a correction to it diffs as the lines it changed. Development-only, so `Internal:`.
- **Status:** open.
- **Last touched:** 2026-09-05 — sliced out of DOC-1; counted at 249 continuation lines.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Changelog and release-note policy](../../../development/changelog-and-release-note-policy.md)
