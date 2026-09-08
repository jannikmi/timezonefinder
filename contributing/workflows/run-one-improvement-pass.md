# Run one improvement pass

Deliver one pull request per item, against `master`. A pass takes the highest-ranked eligible item and finishes it before selecting the next. An item too large for one reviewable pull request is refined into slices — each its own item and pull request — and the refinement itself delivers the first slice.

Read the [register rules](../improvements/improvement-register-rules.md), the [ranking and eligibility rules](../improvements/improvement-ranking-and-eligibility.md), the [priority ranking](../improvements/improvement-priority-ranking.md), and only the selected items. Follow each item's links when sequencing, measurements, or recorded decisions apply.

## Hard boundaries

- Never merge, enable auto-merge, push to `master`, or tag.
- Never ask a maintainer question during the pass. Record a briefed decision question in the item, move its now-ineligible row below the eligible ones, and continue down the ranking.
- Do not change runtime or build dependencies, the lockfile, supported Python versions, or the `timezonefinder` release version. **One exception** ([TOOL-6](../improvements/items/data-pipeline-and-developer-tooling/tool-6-the-ruff-version-is-pinned-below-0-16.md)): a pass may raise a lint or formatter pin with its `.pre-commit-config.yaml` rev and the lockfile lines that bump alone produces; a bump resolving anything further stops. Generated data, bindings, and benchmark fixtures may be regenerated through their generators when the item requires it, per the [generated-file rules](../development/generated-file-regeneration-rules.md) and the [data-pipeline rules](../development/data-pipeline-format-versioning-and-release-order.md). `prototypes/` is out of scope **as a source of work** — a pass does not go looking for findings in exploratory code — but its records are not exempt from the obligations a pass already carries: a query-path change updates the profiler's committed `FINDINGS`, a retirement grep reaches the item ids cited there, and the [documentation pairing](../development/documentation-maintenance-rules.md) reaches `prototypes/README.md`. The [register rules](../improvements/improvement-register-rules.md) state that split and why.
- Preserve the lookup fast path. A performance claim requires paired evidence, measured noise, and the acceleration backend named; an unresolved regression is reverted and recorded.

## Re-verify and rank

Fetch and prune `origin`, then list open pull requests, remote branches and `origin/improvement-claims/*`, and inspect whatever is associated with an item or issue before selecting it. Prune first: another pass may have released a claim ref, and a stale remote-tracking ref reads as a live claim. A current claim ref is authoritative even when its branch or pull request is not visible yet. Check every `GH-*` item under `contributing/improvements/items/` against its issue state. An implemented item is deleted with its ranking row; a wrong, rejected, withdrawn, or out-of-scope item keeps its evidence and moves to `Closed`, unless the register's redundant-route exception deletes it. Blocked, parked, and conditional work stays live.

Treat entries as evidence, not gospel. Re-find locations by symbol rather than line and correct stale reasoning. Update the affected surface record linked by the [coverage map](../improvements/improvement-discovery-coverage-map.md) only when a deliberate audit expands coverage, invalidates a claim, or changes the next useful gap - implementing an item, or reading code in order to change it, does neither. Do not re-propose anything in the linked decision or checked-and-sound memory without new evidence.

Surface each candidate's trade-off while ranking, per the [trade-off rules](../development/trade-off-surfacing-and-validation.md): an option whose losing side a project constraint or the API contract forbids is ruled out before it is ranked, and a trade-off no available measurement can settle becomes a briefed decision rather than an implementation attempt.

Rank expected value first: likely defects, then unblockers, drift-prone duplication, then readability; size only breaks ties. The row order is what a pass walks, so it obeys the [ordering invariant](../improvements/improvement-ranking-and-eligibility.md): an item above every item it blocks, and every ineligible row below every eligible one. Whenever a pass changes a row's eligibility it moves the row too. A performance item is ranked on measured removable workload share, never intuition. Use the [measurement baseline](../improvements/query-performance-measurement-baseline.md); an unmeasured hypothesis becomes a measurement item.

An item is eligible only when it is unclaimed, its [preconditions](../improvements/improvement-sequencing-and-preconditions.md) hold, and every maintainer-owned choice is recorded. Resume existing work instead of racing it.

Take the first eligible item and only that one; never plan a session's item list in advance. The next is selected after the current one is finished, against a re-verified ranking, because merged work and concurrent passes change what ranks first.

Once its pull request is open and its review is settled, ask whether to continue in this session or stop and let a new pass rank from scratch. Continue while the loaded context still pays: another small item, an item of the same shape, or one reading the same code, tests, documentation, or release context. Stop when the next eligible item needs a maintainer decision, depends on unmerged work, reads an unrelated part of the codebase, or when this session's remaining budget cannot carry it through its own final gate; a half-verified second item is worse than a fresh pass. The final report says why the session stopped where it did.

One pull request holds two items only when a single cohesive change implements both and neither can be described without the other; touching the same file is not that.

An item that cannot be delivered as one focused, releasable pull request is refined rather than rewritten in place: slices that each stand alone under one true standalone changelog sentence, recorded as ordinary register items with fresh IDs in the same family (`DOC-1`, `DOC-2`, ...) and the sequencing that orders them. `tests/test_improvement_ledger.py` reads `<prefix>-<number>`, so `DOC-1-2` is not an item ID. The original item is deleted with its ranking row; never keep its ID alive by narrowing it into one of the slices, so that a reader of the shipped pull request cannot mistake a slice for the whole item that was ranked.

Discovering the oversize mid-implementation does not change this: abandon the in-place edit, record the slices, and deliver the first, so the pass leaves working code rather than register churn. The later slices stay live, unclaimed, and ranked for a following item or pass. Only when the first slice itself needs a maintainer decision is the refinement a register-only deliverable.

## Decisions

A choice belongs to the maintainer only when reasonable answers produce materially different work and reversal is expensive. Naming, formatting, file placement, test structure, and small reversible implementation choices belong to the contributor.

For a missing maintainer decision, change the item's status to start with `needs` and add exactly one `**Decision needed:**` bullet holding the question, consequences, two to four options, trade-offs, recommendation, reversibility, and unpriced uncertainty. Update the ranking eligibility cell and move the row below the eligible ones. Do not answer it or wait; the [maintainer-decision workflow](record-maintainer-decisions.md) owns that interaction.

Recorded decisions are binding. New contrary evidence creates a new briefed question; it never silently reverses the earlier decision.

## Isolate and claim

Preserve the shared checkout, take the item's claim ref, and work in a dedicated worktree and branch, per the [claim and isolation protocol](claim-an-improvement-item.md). Nothing is claimed until the pushed ref is fetched back and verified, and no implementation may begin before that.

## Deliverable

Valid outcomes are one or more implemented items, each in its own pull request; an oversized item refined into recorded slices with the first slice implemented; briefed questions only; or triage proving nothing is eligible. The last two still produce a register-only pull request, as does a refinement whose first slice is itself blocked on a decision. Never manufacture cosmetic code to make a pass look productive.

A slice is releasable when one true standalone changelog sentence describes it without promising a follow-up. Prefer additive before subtractive changes. An atomic data-format migration is prototyped and measured rather than half-landed. While an unreleased `DATA_FORMAT_VERSION` bump is pending, take compatible format changes consecutively so they share one ordered data/code release.

Implement one item per branch, and add a test for each changed seam. Commit under that item's ID. Its item file and ranking row are deleted in a separate register-only commit on the same branch, so each pull request retires exactly the item it ships; resolve register-file overlap between sibling branches on the later branch, never by re-basing the earlier one. If work remains, rewrite the item to describe only the remainder. A rejection keeps its item and moves to `Closed`, unless the register's redundant-route exception applies.

## Final gate and pull request

Each pull request is gated on its own: a sibling passing is not evidence about this one. Rebase onto `origin/master` before verification and repeat the gate if the base moves. Run `make hook`, `make test`, scope-specific integration or slow tests, and `make testall` once as the final gate. Apply the [testing rules](../development/testing-strategy-and-change-scope.md), the [benchmark rules](../development/benchmarking-and-performance-validation.md), and the [changelog policy](../development/changelog-and-release-note-policy.md), and validate every trade-off predicted during selection, measuring the side traded away as well as the side bought.

Confirm packaged data is untouched unless regeneration was the item's subject; if it was, the data diff must list only intended binaries. Confirm the diff contains only intended paths, the register invariants pass, all discoveries are recorded, and no shipped ID remains. If a required gate cannot be fixed, push the findings but open no pull request.

Open the pull request without merging or adding automation. Its body states what changed, why this item outranked or skipped higher work, which items this session already delivered and where, the slices a refinement recorded and which one this ships, recorded decisions, behavior impact, real verification, judgment calls, concurrent work yielded to, and the next eligible item.

## Independent review

Each pull request is reviewed and settled per the [review-settlement rules](settle-pull-request-review.md), before it is opened and after: the pass is not over while a finding is unanswered.

## Triage-only mode

For `triage`, `status`, `dry-run`, “what is next,” or “what blocks this,” re-verify and report only. Create no worktree, branch, commit, register edit, push, or pull request.

## Final report

Report the items taken in order, why higher rows were ineligible, and why the session stopped rather than taking one more item; each item's pull request URL, and the slices an oversized item was refined into with the one that shipped; decisions used or questions recorded; claims acquired, released, or left for resumable work; why no code was correct where none was written; findings fixed or declined with evidence, the reviewed commit and whether the final head differs; deferred work; register changes; exact verification results; concurrent passes; and any worktree left behind.
