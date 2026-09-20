# DOC-11 — cut the historical illustrations that carry no rule

- **Location:** every canonical file under `contributing/`, the item files in `improvements/items/` included, and the long-form comments in `.github/workflows/`. `tests/test_contributor_memory.py::test_memory_names_depth_and_size_budgets` holds the budget the sweep buys back.
- **What it is.** This tree argues from incidents deliberately, and most of them earn their place: "that is how `'Europe/Paris'` once annotated eleven snippets" is the evidence its rule rests on, and a reader inclined to skip the rule is talked out of it by the story. What does not earn its place is narration that changes nothing a reader does — which release first exercised a credential, how many runs preceded it, the date something was discovered. It reads like evidence, costs the same words, and carries no rule.
- **The criterion is the whole item.** Keep an incident when the rule is one a competent contributor would otherwise reasonably break and the incident is what shows the cost. Cut it when the rule stands without it and the anecdote is only provenance: provenance is what `git log` and the pull request hold, and they are read once, where this tree is read before every pass.
- **Delete, never rephrase.** Every file here is read by every pass, so a rewording diff costs the review of a tree-wide change and buys nothing a deletion does not; a bullet whose only content is provenance goes whole. A pass that finds itself arguing about a sentence's wording has left the item.
- **What it buys is measurable.** `documentation-maintenance-rules.md` stands at 1,839 words against the 2,000-word canonical limit, so the next rule that file owes does not fit. Report the words recovered per file rather than the sentences removed.
- **Preventing the regression is a rule, not a check.** Its home is the [documentation maintenance rules](../../../development/documentation-maintenance-rules.md), beside the existing preference for describing *why* a choice was made over restating *what* a file says. No mechanical signal separates the two cases: the only shape a checker could key on is a date, and decision records are required to carry one, so such a check would fire on precisely the files it must not. Do not write one; if a pass is tempted, record the measurement and refuse, the way [DOC-6](doc-6-price-a-check-that-rejects-a-new-hard-wrapped-paragraph.md) prices its heuristic before building it.
- **Changelog:** none. The contributor-memory layer is exempt under the [changelog policy](../../../development/changelog-and-release-note-policy.md), and the rule this item adds belongs to that layer too.
- **Status:** open.
- **Last touched:** 2026-09-20 — raised by the maintainer while reviewing the data-updater credential preflight, whose first draft grew four sentences of provenance on the data-pipeline entry and had them cut.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Improvement register rules](../../improvement-register-rules.md)
