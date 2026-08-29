# Run one improvement pass

Deliver one reviewable improvement and one pull request against `master`. A pass takes the
highest-ranked eligible item, not a theme or batch. Status-only requests use the triage mode below
and change nothing.

Read the [register rules](../improvements/improvement-register-rules.md), the
[priority ranking](../improvements/improvement-priority-ranking.md), and only the selected item.
Follow that item's links when sequencing, measurements, or recorded decisions apply.

## Hard boundaries

- Never merge, enable auto-merge, push to `master`, or tag.
- Never ask a maintainer question during the pass. Record a briefed decision question in the item,
  leave it ineligible, and continue down the ranking.
- Do not change dependencies, the lockfile, supported Python versions, or the `timezonefinder`
  release version. Generated data, bindings, and benchmark fixtures may be regenerated through
  their generators when the selected item requires it; the data distribution's version follows a
  format or upstream-data change. Do not edit generated artifacts by hand. Keep `prototypes/` out
  of scope except that a query-path change updates the profiler's committed `FINDINGS`.
- Preserve the lookup fast path. A performance claim requires paired evidence, measured noise, and
  the acceleration backend named; an unresolved regression is reverted and recorded.

## Re-verify and rank

Fetch `origin`, list open pull requests and remote branches, and inspect any branch mentioning an
item or issue before claiming it. Check every `GH-*` item under
`contributing/improvements/items/` against the issue state. An item already implemented is deleted
with its ranking row; a wrong, rejected, withdrawn, or out-of-scope item keeps its evidence but its
row moves to `Closed`. Blocked, parked, and conditional work remains live.

Treat entries as evidence, not gospel. Re-find locations by symbol rather than line, correct stale
reasoning, and record newly swept areas in the
[coverage log](../improvements/improvement-discovery-coverage-log.md). Do not re-propose anything
in the linked decision or checked-and-sound memory without new evidence.

Rank expected value first: likely defects, then unblockers, drift-prone duplication, then
readability; size only breaks ties. A performance item is ranked on measured removable workload
share, never intuition. Use the [measurement baseline](../improvements/query-performance-measurement-baseline.md);
an unmeasured hypothesis becomes a measurement item.

An item is eligible only when it is unclaimed, its
[preconditions](../improvements/improvement-sequencing-and-preconditions.md) hold, every
maintainer-owned choice is recorded, and it fits one releasable pull request. Resume existing work
instead of racing it.

## Decisions

A choice belongs to the maintainer only when reasonable answers produce materially different work
and reversal is expensive. Naming, formatting, file placement, test structure, and small reversible
implementation choices belong to the contributor.

For a missing maintainer decision, change the item's status to start with `needs` and add exactly
one `**Decision needed:**` bullet containing the question, consequences, two to four options,
trade-offs, recommendation, reversibility, and unpriced uncertainty. Update the ranking eligibility
cell. Do not answer it or wait; the
[maintainer-decision workflow](record-maintainer-decisions.md) owns that interaction.

Recorded decisions are binding. New contrary evidence creates a new briefed question; it never
silently reverses the earlier decision.

## Isolate and claim

Preserve the shared checkout. Survey first:

```bash
git fetch origin
git branch -r
gh pr list --state open
```

Create a uniquely named worktree and branch from `origin/master`, install, and record untouched
`make test` and `make hook` baselines. Push the branch immediately after selecting the item so it
acts as the claim. Stage explicit paths, never `git add -A`.

## Deliverable

Valid outcomes are one implemented item; briefed questions only; a design decomposed into releasable
slices; or triage proving nothing is eligible. The latter three still produce a register-only pull
request. Never manufacture cosmetic code to make a pass look productive.

A slice is releasable when one true standalone changelog sentence describes it without promising a
follow-up. Prefer additive before subtractive changes. An atomic data-format migration is
prototyped and measured rather than half-landed. While an unreleased `DATA_FORMAT_VERSION` bump is
pending, take compatible format changes consecutively so they share one ordered data/code release.

Implement only the selected slice, add a test for its seam, and commit it using the item ID. If it
ships, delete its item file and ranking row in a separate commit. If work remains, rewrite the item
to describe only the remainder. Rejections keep their item and move to `Closed`.

## Final gate and pull request

Rebase onto `origin/master` before verification and repeat the gate if the base moves. Run
`make hook`, `make test`, scope-specific integration or slow tests, and `make testall` once as
the final gate. Apply the [testing rules](../development/testing-strategy-and-change-scope.md), the
[benchmark rules](../development/benchmarking-and-performance-validation.md), and the
[changelog policy](../development/changelog-and-release-note-policy.md).

Confirm packaged data is untouched unless regeneration was the selected item's subject; if it was,
the data diff must list only intended binaries. Confirm the overall diff contains only intended
paths, the register invariants pass, all discoveries are recorded, and no shipped ID remains. If a
required gate cannot be fixed, push the findings but do not open a pull request.

Open the pull request without merging or adding automation. Its body states what changed, why the
item outranked or skipped higher work, recorded decisions, exact behavior impact, real verification,
judgment calls, concurrent work yielded to, and the next eligible item.

## Triage-only mode

For `triage`, `status`, `dry-run`, “what is next,” or “what blocks this,” re-verify and report
only. Create no worktree, branch, commit, register edit, push, or pull request.

## Final report

Report the item and why higher rows were ineligible; decisions used or questions recorded; the pull
request URL or why no code was correct; deferred work; register changes; exact verification results;
concurrent passes; and any worktree left behind.
