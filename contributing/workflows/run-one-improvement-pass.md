# Run one improvement pass

Deliver one reviewable pull request against `master`. A pass starts with the highest-ranked eligible item, then batches further eligible small items when they fit in the same focused, releasable pull request.

Read the [register rules](../improvements/improvement-register-rules.md), the [priority ranking](../improvements/improvement-priority-ranking.md), and only the selected items. Follow each item's links when sequencing, measurements, or recorded decisions apply.

## Hard boundaries

- Never merge, enable auto-merge, push to `master`, or tag.
- Never ask a maintainer question during the pass. Record a briefed decision question in the item, leave it ineligible, and continue down the ranking.
- Do not change dependencies, the lockfile, supported Python versions, or the `timezonefinder` release version. Generated data, bindings, and benchmark fixtures may be regenerated through their generators when the selected item requires it; the data distribution's version follows a format or upstream-data change. Never edit a generated artifact by hand. `prototypes/` is out of scope, except that a query-path change updates the profiler's committed `FINDINGS`.
- Preserve the lookup fast path. A performance claim requires paired evidence, measured noise, and the acceleration backend named; an unresolved regression is reverted and recorded.

## Re-verify and rank

Fetch and prune `origin`, then list open pull requests, remote branches and `origin/improvement-claims/*`, and inspect whatever is associated with an item or issue before selecting it. Prune first: another pass may have released a claim ref, and a stale remote-tracking ref reads as a live claim. A current claim ref is authoritative even when its branch or pull request is not visible yet. Check every `GH-*` item under `contributing/improvements/items/` against its issue state. An implemented item is deleted with its ranking row; a wrong, rejected, withdrawn, or out-of-scope item keeps its evidence and moves to `Closed`, unless the register's redundant-route exception deletes it. Blocked, parked, and conditional work stays live.

Treat entries as evidence, not gospel. Re-find locations by symbol rather than line and correct stale reasoning. Update the affected surface record linked by the [coverage map](../improvements/improvement-discovery-coverage-map.md) only when a deliberate audit expands coverage, invalidates a claim, or changes the next useful gap - implementing an item, or reading code in order to change it, does neither. Do not re-propose anything in the linked decision or checked-and-sound memory without new evidence.

Surface each candidate's trade-off while ranking, per the [trade-off rules](../development/trade-off-surfacing-and-validation.md): an option whose losing side a project constraint or the API contract forbids is ruled out before it is ranked, and a trade-off no available measurement can settle becomes a briefed decision rather than an implementation attempt.

Rank expected value first: likely defects, then unblockers, drift-prone duplication, then readability; size only breaks ties. A performance item is ranked on measured removable workload share, never intuition. Use the [measurement baseline](../improvements/query-performance-measurement-baseline.md); an unmeasured hypothesis becomes a measurement item.

An item is eligible only when it is unclaimed, its [preconditions](../improvements/improvement-sequencing-and-preconditions.md) hold, and every maintainer-owned choice is recorded. Resume existing work instead of racing it.

Take the first eligible item, then add as many subsequent eligible small items as fit one focused, releasable pull request. Favor overlapping files, tests, documentation, or release context; independent small maintenance items may share it when the combined diff and verification stay easy to review. Do not batch an item that adds a maintainer decision, materially broadens risk or verification, obscures another item's behavior, or makes the pull request no longer releasable alone. A larger item stays its own slice unless it already belongs to the selected work's deliverable.

## Decisions

A choice belongs to the maintainer only when reasonable answers produce materially different work and reversal is expensive. Naming, formatting, file placement, test structure, and small reversible implementation choices belong to the contributor.

For a missing maintainer decision, change the item's status to start with `needs` and add exactly one `**Decision needed:**` bullet holding the question, consequences, two to four options, trade-offs, recommendation, reversibility, and unpriced uncertainty. Update the ranking eligibility cell. Do not answer it or wait; the [maintainer-decision workflow](record-maintainer-decisions.md) owns that interaction.

Recorded decisions are binding. New contrary evidence creates a new briefed question; it never silently reverses the earlier decision.

## Isolate and claim

Preserve the shared checkout. Survey first:

```bash
git fetch --prune origin
git branch -r
gh pr list --state open
```

Finalize the slice or batch before creating a worktree, installing, or running baselines. Atomically claim every selected item through its canonical remote ref, `refs/heads/improvement-claims/<ITEM-ID>`:

1. Create one unique claim commit on the `origin/master` tree and parent, without adding it to the implementation branch. Its message records the selected item IDs, a unique run token, the planned feature branch, the base commit, and the creation time. Never point a claim ref straight at `origin/master`: concurrent pushes of one commit can both report success.
2. Push all claim refs in one `git push --atomic`, guarding each with `--force-with-lease=<claim-ref>:` so it succeeds only when every ref is absent. A rejected push acquires nothing: fetch again, inspect the winning claims and concurrent work, then re-rank rather than retrying blindly.
3. Fetch the refs immediately afterwards and verify each points at this run's claim commit. Until that succeeds nothing is claimed and no implementation may begin.

Never overwrite, delete, or steal another run's claim. Treat a foreign or orphaned claim as blocking, report its recorded metadata, and continue down the ranking. A maintainer may remove a confirmed orphan separately.

After ownership is verified, create a uniquely named worktree and feature branch from the recorded `origin/master` commit. Do not base a pass on another open pull request merely to absorb its contributor-memory edits; an item that truly depends on unmerged work is ineligible until that lands. Name the branch after the first item ID and push it immediately, so the work behind the claim is inspectable. Then install and record untouched `make test` and `make hook` baselines. Do not add an item after implementation begins: release the claims and form a newly ranked batch if the scope must change.

Keep each claim until its pull request is open and visible, then delete only this run's refs, guarding each deletion with a force-with-lease expecting this run's claim commit; the open pull request becomes the durable claim. Release claims the same way when abandoning or yielding work. If verification fails and findings are pushed without a pull request, retain the claims so another pass resumes rather than races that branch. Stage explicit paths, never `git add -A`.

## Deliverable

Valid outcomes are one or more implemented items; briefed questions only; a design decomposed into releasable slices; or triage proving nothing is eligible. The latter three still produce a register-only pull request. Never manufacture cosmetic code to make a pass look productive.

A slice is releasable when one true standalone changelog sentence describes it without promising a follow-up. Prefer additive before subtractive changes. An atomic data-format migration is prototyped and measured rather than half-landed. While an unreleased `DATA_FORMAT_VERSION` bump is pending, take compatible format changes consecutively so they share one ordered data/code release.

Implement only the selected slice, and add a test for each changed seam. Commit each item under its ID, or under all batched IDs when one cohesive change implements them together. A shipped item's file and ranking row are deleted in a separate register-only commit, which may remove every shipped batched item at once. If work remains, rewrite the item to describe only the remainder. A rejection keeps its item and moves to `Closed`, unless the register's redundant-route exception applies.

## Final gate and pull request

Rebase onto `origin/master` before verification and repeat the gate if the base moves. Run `make hook`, `make test`, scope-specific integration or slow tests, and `make testall` once as the final gate. Apply the [testing rules](../development/testing-strategy-and-change-scope.md), the [benchmark rules](../development/benchmarking-and-performance-validation.md), and the [changelog policy](../development/changelog-and-release-note-policy.md), and validate every trade-off predicted during selection, measuring the side traded away as well as the side bought.

Confirm packaged data is untouched unless regeneration was the item's subject; if it was, the data diff must list only intended binaries. Confirm the diff contains only intended paths, the register invariants pass, all discoveries are recorded, and no shipped ID remains. If a required gate cannot be fixed, push the findings but open no pull request.

Open the pull request without merging or adding automation. Its body states what changed, why the first item outranked or skipped higher work, why each additional item belonged in the batch, recorded decisions, behavior impact, real verification, judgment calls, concurrent work yielded to, and the next eligible item.

## Automated Codex review

Opening the pull request is not the end of the pass. Record its head commit and watch for the Codex review repository configuration starts. Inspect formal reviews, inline review comments, and reactions; `gh pr view --comments` alone misses inline findings. Record which commit a review covered, because a review older than the current head is evidence about that commit only. Silence is reported as silence, not treated as permission to spend another review.

Assess every finding against the current code rather than accepting it mechanically. Fix every confirmed problem the pull request introduced or exposed, strengthen the regression test where behavior changes, and run the narrow verification plus `make hook` before pushing. Answer each finding on its thread in one or two sentences - the commit that fixed it, or the evidence it is stale - then resolve it once settled. A genuine unrelated improvement becomes a new register item instead of silently broadening the pull request. If a confirmed finding cannot be fixed without violating a hard boundary or obtaining a maintainer decision, leave its thread open and the pull request unmerged, record the blocker, and report it rather than declaring the pass complete.

After pushing fixes, address any comments already in flight. A corrective push makes an earlier disposition stale; record the reviewed commit and the final head rather than manufacturing a current-head disposition. Review fixes invalidate the earlier final gate: fetch and rebase if `origin/master` moved, then repeat it - in full when code changed, narrowed to `make hook` and the affected tests when only documentation or tests did. Re-trigger with `@codex review` only on that gated head, and only when the fixes materially changed behavior or risk - a new enforced gate, a changed seam, a fix no review has seen. Documentation, test, and conflict-resolution edits earn no round. **Stop on a usage limit:** report it, leave the pull request unmerged, and neither wait it out nor retry. The pass is complete when that head is current with `origin/master`, passes its gate, and every finding that arrived has been addressed or declined with evidence.

## Triage-only mode

For `triage`, `status`, `dry-run`, “what is next,” or “what blocks this,” re-verify and report only. Create no worktree, branch, commit, register edit, push, or pull request.

## Final report

Report the selected items and why higher rows were ineligible or eligible small items were not batched; decisions used or questions recorded; claims acquired, released, or left for resumable work; the pull request URL or why no code was correct; findings fixed or declined with evidence, the reviewed commit and whether the final head differs; deferred work; register changes; exact verification results; concurrent passes; and any worktree left behind.
