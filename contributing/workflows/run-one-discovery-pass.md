# Run one discovery pass

Find improvement candidates that are not yet in the register, and leave the discovery memory cheaper than it was found. This workflow records; it never implements, and it ends in a register-only pull request.

Read the [coverage map](../improvements/improvement-discovery-coverage-map.md) and the [priority ranking](../improvements/improvement-priority-ranking.md) first, then only the surface record the chosen lane names. Read the [register rules](../improvements/improvement-register-rules.md) and the [ranking and eligibility rules](../improvements/improvement-ranking-and-eligibility.md) before writing an entry, not before choosing a lane.

## Hard boundaries

- Never implement, fix, refactor, merge, push to `master`, or tag. The diff contains `contributing/improvements/` and nothing else, and therefore carries no changelog entry.
- Never ask the maintainer a question during the pass. A maintainer-owned choice becomes an item with a `needs` status and exactly one `**Decision needed:**` bullet, which [the decision workflow](record-maintainer-decisions.md) owns.
- Never re-raise a candidate already held under `checked-and-found-sound/`, in a `decisions/` file, or in a `Closed` row, without new evidence that disproves its premise.
- Never manufacture findings. A lane that yields nothing above the bar is a result: record the coverage it advanced and stop.

## Spend the pass on the core

The core is correctness at borders, the query fast path with its memory profile, the binary format and the pipeline that produces the packaged payload, the documented public API, and the release path that ships them. Developer tooling, benchmark and report plumbing, prose documentation, and prototypes are periphery.

A pass reads the core deliberately and reaches periphery only through a signal that already points there — a measured contradiction, a check that cannot fail, a claim the code disproves. Sweeping periphery for its own sake is how a pass fills with findings nobody will ever take, which then cost re-verification in every later pass. Covering everything is not the goal; the core being right is.

## Choose one lane

Take one lane and a stated budget, never the whole map. In yield order:

1. **Evidence-led probes**, which carry their own evidence so a finding arrives half-verified: the [measured baseline](../improvements/query-performance-measurement-baseline.md) and the profiler's committed `FINDINGS` against where query time actually goes; tests that cannot fail — skipped, `xfail`, assertion-free, or tautological — and uncovered branches on the query path; drift between docstrings, `:raises:` and `:return:` claims, public documentation, and behavior; tool signal from a `ruff --select ALL` delta, mypy over the excluded directories, or `check-manifest`; open issues with no register entry; and churn, `git log --format= --name-only <since> | sort | uniq -c | sort -rn`, because repeated fixes concentrate where a design is wrong.
2. **Delta sweep**: what changed since a surface's recorded delta anchor, via `git diff --stat <anchor>..origin/master -- <paths>`. This is the lane that keeps coverage current, and it is bounded by the diff rather than by the tree.
3. **Named gap**: the `Next useful gap` a previous pass left on a surface record. It is a pointer, not an obligation — re-verify that it still names the best remaining gap before spending the pass on it.
4. **Method replay**: a [reusable method](../improvements/discovery-coverage/reusable-discovery-methods.md) whose trigger has fired since it last ran. Triggers, never a schedule.

Re-reading a surface the coverage record already claims covered is not a lane.

## The bar for recording anything

The ranking prices work; this bar prices the record. An entry costs a file, a ranking row, a reviewer's attention, and re-verification by every later pass, so a finding cheaper to forget than to carry is not written down.

Record a candidate only when it names a location and anchor a later pass can re-verify, and it does at least one of these:

- produces a wrong answer, a silently empty one, or a corrupt artifact on a path real usage reaches;
- blocks or cheapens other ranked work;
- removes a measured share of the query workload, the resident memory, or the shipped payload, stated as that share with where it was measured;
- removes duplication that has already drifted once, or that two edits must now keep in step;
- corrects a claim a user can act on and be wrong — public documentation, a docstring, an error message.

Everything else is a preference. Naming, formatting, placement, and structure that no measurement and no contract distinguishes are preferences however many of them a sweep finds; they are not recorded, not ranked, and not fixed here. Leave them to whichever pass is already editing that code.

Rank every surviving candidate against the current ranking before writing it down, because that comparison is what keeps a cheap finding from displacing real work. How many survive one pass is not capped yet: report the count, so a cap can be set from what passes actually produce rather than guessed at now.

## Dispose of every candidate exactly once

- An actionable finding becomes one item file and one ranking row, with a fresh id in the matching family.
- A suspected defect is a measurement, not a defect. Confirm it inside the pass with one command or one focused test, or record the measurement as the item.
- Something checked and found sound, or refused on its merits, goes to the narrowest file under `checked-and-found-sound/` **with its reason**: the reason is the filter, and a refusal without one gets re-raised.
- A settled choice whose consequences reach past one item goes to the matching file under `decisions/`, keeping the refused options.
- A preference goes nowhere.

## Leave the next pass cheaper

The write-back is as much the deliverable as the findings, and it is what stops the next run repeating this one.

- Advance the delta anchor of every surface actually swept, and say in the record which audit justifies the new boundary. An anchor moved without that is a coverage claim nobody made.
- Rewrite that surface's `Known uncovered deltas` and `Next useful gap`. A gap still describing what this pass just closed costs the next pass its whole budget.
- Add or amend the reusable method a probe used, with the trigger that should bring it back.
- Rewrite superseded coverage claims in place rather than appending beneath them, and record no chronology: which pass found what is in Git.

Before writing any candidate down, grep it against `checked-and-found-sound/`, `decisions/`, the `Closed` table, and the open items. An already-refused candidate is dropped; a refusal this pass can disprove is rewritten, never appended to.

## Deliverable and report

Survey `origin` and open pull requests first, since every discovery pass writes to the same ranking file; work in a dedicated worktree on a branch from current `origin/master`, stage explicit paths under `contributing/improvements/`, and rebase before the final gate. Run `make hook` plus the contributor-memory and improvement-ledger tests. Open the pull request without merging, and settle its review per the [review-settlement rules](settle-pull-request-review.md).

Report the lane and budget, what was swept, each recorded candidate with where it ranks and why, candidates dropped and against which existing refusal, every coverage record advanced with the audit justifying its anchor, decision questions recorded, exact verification, the pull request URL, and the lane the next pass should take.
