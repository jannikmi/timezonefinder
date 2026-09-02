# Run one improvement pass

Deliver one reviewable pull request against `master`. A pass starts with the highest-ranked eligible item, then batches further eligible small items when they fit in the same focused, releasable pull request. Status-only requests use the triage mode below and change nothing.

Read the [register rules](../improvements/improvement-register-rules.md), the [priority ranking](../improvements/improvement-priority-ranking.md), and only the selected items. Follow each item's links when sequencing, measurements, or recorded decisions apply.

## Hard boundaries

- Never merge, enable auto-merge, push to `master`, or tag.
- Never ask a maintainer question during the pass. Record a briefed decision question in the item, leave it ineligible, and continue down the ranking.
- Do not change dependencies, the lockfile, supported Python versions, or the `timezonefinder` release version. Generated data, bindings, and benchmark fixtures may be regenerated through their generators when the selected item requires it; the data distribution's version follows a format or upstream-data change. Do not edit generated artifacts by hand. Keep `prototypes/` out of scope except that a query-path change updates the profiler's committed `FINDINGS`.
- Preserve the lookup fast path. A performance claim requires paired evidence, measured noise, and the acceleration backend named; an unresolved regression is reverted and recorded.

## Re-verify and rank

Fetch and prune `origin`, list open pull requests, remote branches, and `origin/improvement-claims/*`, and inspect any claim, branch, or pull request associated with an item or issue before selecting it. Pruning is required before treating a remote-tracking claim as authoritative because another pass may have released its remote ref. A current claim ref is authoritative even when its feature branch or pull request is not visible yet. Check every `GH-*` item under `contributing/improvements/items/` against the issue state. An item already implemented is deleted with its ranking row; a wrong, rejected, withdrawn, or out-of-scope item normally keeps its evidence and moves to `Closed`, but the register's redundant-route exception deletes it when the narrow canonical decision record already retains its refusal and decision evidence. Blocked, parked, and conditional work remains live.

Treat entries as evidence, not gospel. Re-find locations by symbol rather than line and correct stale reasoning. Update only the affected surface record linked by the [coverage map](../improvements/improvement-discovery-coverage-map.md), and only when a deliberate audit expands coverage, invalidates a coverage claim, or materially changes the next useful gap. Implementing a selected item and reviewing code in order to change it do not by themselves change discovery coverage. Do not re-propose anything in the linked decision or checked-and-sound memory without new evidence.

Surface each candidate's trade-off while ranking, following the [trade-off rules](../development/trade-off-surfacing-and-validation.md): an option whose losing side is forbidden by a project constraint or the API contract is ruled out before it is ranked, and a trade-off no available measurement can settle becomes a briefed decision rather than an implementation attempt.

Rank expected value first: likely defects, then unblockers, drift-prone duplication, then readability; size only breaks ties. A performance item is ranked on measured removable workload share, never intuition. Use the [measurement baseline](../improvements/query-performance-measurement-baseline.md); an unmeasured hypothesis becomes a measurement item.

An item is eligible only when it is unclaimed, its [preconditions](../improvements/improvement-sequencing-and-preconditions.md) hold, and every maintainer-owned choice is recorded. Resume existing work instead of racing it.

Take the first eligible item in ranking order. Then add as many subsequent eligible small items as fit in the same focused, releasable pull request. Favor items with overlapping files, tests, documentation, or release context; independent small maintenance items may still share the pull request when their combined diff and verification remain easy to review. Do not batch an item that adds a new maintainer decision, materially broadens risk or verification, obscures the behavior of another item, or makes the pull request no longer releasable on its own. A larger item remains its own slice unless it is already part of the selected work's coherent deliverable.

## Decisions

A choice belongs to the maintainer only when reasonable answers produce materially different work and reversal is expensive. Naming, formatting, file placement, test structure, and small reversible implementation choices belong to the contributor.

For a missing maintainer decision, change the item's status to start with `needs` and add exactly one `**Decision needed:**` bullet containing the question, consequences, two to four options, trade-offs, recommendation, reversibility, and unpriced uncertainty. Update the ranking eligibility cell. Do not answer it or wait; the [maintainer-decision workflow](record-maintainer-decisions.md) owns that interaction.

Recorded decisions are binding. New contrary evidence creates a new briefed question; it never silently reverses the earlier decision.

## Isolate and claim

Preserve the shared checkout. Survey first:

```bash
git fetch --prune origin
git branch -r
gh pr list --state open
```

Finalize the proposed slice or batch before creating a worktree, installing, or running baselines. Atomically claim every selected item through its canonical remote ref, `refs/heads/improvement-claims/<ITEM-ID>`:

1. Create one unique claim commit without adding it to the implementation branch. It uses the `origin/master` tree and parent, and its message records the selected item IDs, a unique run token, the planned feature branch, the base commit, and the creation time. Do not point a new claim ref directly at `origin/master`: concurrent pushes of the same commit can both appear successful.
2. Push all selected claim refs in one `git push --atomic`. Guard each ref with `--force-with-lease=<claim-ref>:` so the push succeeds only when every canonical ref is absent. A rejected push acquires nothing; fetch again, inspect the winning claims and concurrent work, then re-rank rather than retrying the same selection blindly.
3. Fetch the claim refs immediately after a successful push and verify that every ref points to this run's unique claim commit. Until that verification succeeds, the items are not claimed and no implementation work may begin.

Never overwrite, delete, or steal another run's claim. Treat a foreign or orphaned claim as blocking, report its recorded metadata, and continue down the ranking. A maintainer may remove a confirmed orphan separately.

After ownership is verified, create a uniquely named worktree and feature branch from the recorded `origin/master` commit. Do not base an independent pass on another open pull request merely to absorb its contributor-memory edits; an item that truly depends on unmerged work is ineligible until that precondition lands. Include the first item ID in the feature-branch name and push the branch immediately so the work behind the claim is inspectable. Then install and record untouched `make test` and `make hook` baselines. Do not add another item after implementation begins; release the current claims and form a newly ranked batch if the scope must change.

Keep each claim until its pull request is open and visible. Then delete only this run's claim refs, guarding each deletion with a force-with-lease that expects this run's claim commit; the open pull request becomes the durable claim. Release claims the same way when explicitly abandoning or yielding the work. If verification fails and findings are pushed without a pull request, retain the claims so another pass resumes rather than races that branch. Stage explicit paths, never `git add -A`.

## Deliverable

Valid outcomes are one or more implemented items; briefed questions only; a design decomposed into releasable slices; or triage proving nothing is eligible. The latter three still produce a register-only pull request. Never manufacture cosmetic code to make a pass look productive.

A slice is releasable when one true standalone changelog sentence describes it without promising a follow-up. Prefer additive before subtractive changes. An atomic data-format migration is prototyped and measured rather than half-landed. While an unreleased `DATA_FORMAT_VERSION` bump is pending, take compatible format changes consecutively so they share one ordered data/code release.

Implement only the selected slice or batch, and add a test for each changed seam. Commit each item using its ID, or use all batched IDs when one cohesive change implements them together. If an item ships, delete its item file and ranking row in a separate register-only commit; a single register-only commit may remove every shipped batched item. If work remains, rewrite the item to describe only the remainder. Rejections normally keep their item and move to `Closed`; apply the register's redundant-route deletion exception when the canonical decision record already retains the refusal and decision evidence.

## Final gate and pull request

Rebase onto `origin/master` before verification and repeat the gate if the base moves. Run `make hook`, `make test`, scope-specific integration or slow tests, and `make testall` once as the final gate. Apply the [testing rules](../development/testing-strategy-and-change-scope.md), the [benchmark rules](../development/benchmarking-and-performance-validation.md), and the [changelog policy](../development/changelog-and-release-note-policy.md), and validate every trade-off predicted during selection, measuring the side that was traded away as well as the side that was bought.

Confirm packaged data is untouched unless regeneration was the selected item's subject; if it was, the data diff must list only intended binaries. Confirm the overall diff contains only intended paths, the register invariants pass, all discoveries are recorded, and no shipped ID remains. If a required gate cannot be fixed, push the findings but do not open a pull request.

Open the pull request without merging or adding automation. Its body states what changed, why the first item outranked or skipped higher work, why each additional item belonged in the batch, recorded decisions, exact behavior impact, real verification, judgment calls, concurrent work yielded to, and the next eligible item.

## Automated Codex review

Opening the pull request is not the end of the pass. Record its head commit and watch the Codex review that repository configuration starts, if one arrives. **Never request or re-trigger a review:** do not comment `@codex review` or invoke an equivalent action. Inspect formal reviews, inline pull-request review comments, and reactions on the pull request; `gh pr view --comments` alone misses inline findings. Record which commit a review covered, because a review whose commit is older than the current head is evidence about that commit only. Silence is reported as silence, not treated as permission to spend another review.

Assess every Codex finding against the current code rather than accepting it mechanically. Fix every confirmed problem introduced or exposed by the pull request, add or strengthen the regression test where behavior changes, and run the narrow verification plus `make hook` before committing and pushing the fixes. Answer each finding on its own thread in one or two sentences - the commit that fixed it, or the evidence showing it is stale - then resolve the thread. A genuine unrelated improvement becomes a new register item instead of silently broadening the pull request. If a confirmed finding cannot be fixed without violating a hard boundary or obtaining a maintainer decision, leave the pull request unmerged, record the blocker through the normal register rules, and report it rather than declaring the pass complete.

After pushing review fixes, inspect any comments already in flight and address them, but do not request another review. A corrective push makes an earlier disposition stale; record the reviewed commit and the final head instead of manufacturing a current-head disposition. When follow-up edits materially change behavior or risk, the final report may suggest that the maintainer re-trigger Codex review; routine conflict resolution, documentation, test, and review-fix edits do not justify that suggestion, and the agent never acts on it. Review fixes still invalidate the earlier final gate: fetch and rebase if `origin/master` moved, then repeat the full gate. The pass is complete when that head is current with `origin/master`, passes the required gate, and every finding that actually arrived has been addressed or declined with evidence.

## Triage-only mode

For `triage`, `status`, `dry-run`, “what is next,” or “what blocks this,” re-verify and report only. Create no worktree, branch, commit, register edit, push, or pull request.

## Final report

Report the selected items and why higher rows were ineligible or eligible small items were not batched; decisions used or questions recorded; claims acquired, released, or left for resumable work; the pull request URL or why no code was correct; Codex review findings fixed or declined with evidence, the reviewed commit and whether the final head differs, plus any maintainer re-review suggestion justified by substantial edits; deferred work; register changes; exact verification results; concurrent passes; and any worktree left behind.
