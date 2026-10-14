# DOC-11 — cut the historical illustrations that carry no rule

- **Location:** every canonical file under `contributing/`, the item files in `improvements/items/` included, and the long-form comments in `.github/workflows/`. `tests/test_contributor_memory.py::test_memory_names_depth_and_size_budgets` holds the budget the sweep buys back.
- **What it is.** This tree argues from incidents in places, and the narration costs the same words as a rule while carrying none: which release first exercised a credential, how many runs preceded it, what a draft once got wrong, the date something was discovered. A reader acts on the rule, not on how it was arrived at.
- **The criterion is a sentence the rule cannot be stated without.** Cut an incident unless the rule is unstatable without it — which is rare, because what the incident shows is almost always a *mechanism*, and a mechanism states in the present tense: not "this bit four pages after one loader change" but "a figure quoted in prose is typically quoted in three more places before anyone re-measures". Where the mechanism is written down, the anecdote is provenance, and provenance is what `git log` and the pull request hold; they are read once, where this tree is read before every pass.
- **Delete, never rephrase.** Every file here is read by every pass, so a rewording diff costs the review of a tree-wide change and buys nothing a deletion does not; a bullet whose only content is provenance goes whole. A pass that finds itself arguing about a sentence's wording has left the item.
- **What it buys is reading time rather than room.** Every pass reads this tree, so a cut anecdote is saved on every pass; no file in scope is near its word budget, so the budget is not what forces the cut. Report the words recovered per file rather than the sentences removed.
- **Preventing the regression is a rule, not a check.** Its home is the [documentation maintenance rules](../../../development/documentation-maintenance-rules.md), beside the existing preference for describing *why* a choice was made over restating *what* a file says. No mechanical signal separates the two cases: the only shape a checker could key on is a date, and decision records are required to carry one, so such a check would fire on precisely the files it must not. Do not write one; if a pass is tempted, record the measurement and refuse, the way [DOC-6](doc-6-price-a-check-that-rejects-a-new-hard-wrapped-paragraph.md) prices its heuristic before building it.
- **Changelog:** none. The contributor-memory layer is exempt under the [changelog policy](../../../development/changelog-and-release-note-policy.md), and the rule this item adds belongs to that layer too.
- **Status:** open — the [documentation maintenance rules](../../../development/documentation-maintenance-rules.md), the geometry/data-format decisions and the public-API decisions are done; the rest of the tree is not swept.
- **Last touched:** 2026-10-14.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Improvement register rules](../../improvement-register-rules.md)
