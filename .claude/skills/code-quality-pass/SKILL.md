---
name: code-quality-pass
description: Runs one autonomous internal-code-quality pass over this repository — triage, a single-theme refactor with no behaviour change, full verification, and a pull request opened against master — coordinated through a persistent findings ledger (potential-improvements.md) so repeated passes build on each other instead of rediscovering the same candidates. Use this whenever the user asks for a code-quality pass, a cleanup or refactoring pass, wants technical debt found or paid down, says something like "improve the code quality", "tidy up the codebase", "find what's worth refactoring", or asks to run/continue/repeat the quality pass. Use it also when they ask what improvements are still outstanding, want the next item from the ledger picked up, or want a quality PR prepared for review — even if they never say the word "skill".
---

# Autonomous code-quality pass

Deliver one **code-quality improvement pass** on `timezonefinder` (Python library for offline
timezone lookup by coordinates), ending in a pull request opened against `master` for the
repository owner to review, plus an updated findings ledger.

Work to completion without stopping to ask questions. Where something is ambiguous, apply §8 and
record the call you made in the PR description.

This pass is designed to be run many times. Most of its value comes from §4: the ledger is what
turns a series of one-off passes into cumulative progress, so treat reading and updating it as part
of the deliverable, not bookkeeping.

## 1. Ground rules

`CLAUDE.md` is auto-loaded. Read `CONTRIBUTING.md` too — it is not auto-loaded and it owns the
benchmarking, testing-scope and PR conventions this pass needs. Both are authoritative and override
any general habit; nothing here repeats them.

Two of their rules outrank everything else for *this* task, so treat them as hard gates rather than
guidance: the changelog entry is mandatory (yours belongs in the `Internal:` sub-list), and the
lookup fast path is not to be traded away for elegance (§5).

## 2. Isolate from the maintainer's working tree

The checkout may contain unrelated uncommitted work. **Your PR must not contain any of it.**

1. `git status --short`.
2. Clean tree: `git fetch origin && git checkout -b quality/<short-slug> origin/master`.
3. Dirty tree: do **not** stash, reset, or commit the maintainer's changes. Work in an isolated
   worktree branched from the pushed baseline, and do everything from there:
   ```
   git fetch origin
   git worktree add ../tzf-quality -b quality/<short-slug> origin/master
   ```
4. Install into whichever tree you are working in.
5. Record a baseline **before** editing: run `make test` and `make hook` on the untouched branch.
   Anything already failing there is pre-existing — note it, do not fix it in this pass, do not let
   it block you.

Also note: `make hook` runs pre-commit across **all** files, so it can reformat files unrelated to
your change. Stage only what belongs to your change; `git checkout --` the rest.

The checkout may also hold untracked scratch material — notes, plans, working directories — that
`.gitignore` does not cover, so a blanket `git add -A` would sweep it into your PR. Stage paths
explicitly; never `git add -A`. The findings ledger is the deliberate exception: it is a tracked
file at the repository root that you do commit (§4).

## 3. Scope: what "code quality" means here

You are improving the internal quality of code that already works. **Observable behaviour must not
change** — same results, same public API, same binary formats, same exception types for the same
inputs.

In scope:

- Duplication that has drifted or will drift.
- Functions doing several unrelated things; deep nesting; parameter lists that have outgrown the
  function.
- Missing, wrong, or `Any`-shaped type hints.
- Error handling that swallows failures, raises the wrong type, or fails without naming the
  offending input or file.
- Dead code, unreachable branches, comments that contradict the code, docstrings describing an
  older signature.
- Test quality: assertions that assert nothing, over-mocking, an uncovered error path the code
  clearly cares about.
- Names that mislead about what a thing holds or does.

Out of scope for this task — the repo docs describe these procedures neutrally because they cannot
know your boundary, so treat them as prohibitions here:

- Behaviour changes, bug fixes, features, API additions or removals.
- Regenerating timezone data, benchmark fixtures or FlatBuffers bindings; editing
  `timezonefinder/data/` or `timezonefinder/flatbuf/generated/`.
- Dependency, lockfile, Python-version or release-version changes.
- Whole-file reformatting or "modernisation" for style alone — churn a reviewer cannot tie to a
  concrete defect.
- `prototypes/`.

## 4. The findings ledger

`potential-improvements.md` at the repository root is the shared memory across passes. **Read it
before you read any source file**, and write it back before you finish. If it does not exist yet,
this is the first pass — create it there.

It is a **tracked file, committed as part of your PR.** That is what carries it between passes: it
arrives with the checkout or worktree, and it reaches the next pass through `master`. It also means
the ledger is public and the owner reads it — write it for a contributor who has never seen this
skill.

Because it travels through `master`, a pass starting while an earlier quality PR is still open will
read a ledger missing that PR's updates. Before triaging, check for unmerged work
(`git branch -r --list 'origin/quality/*'`, `gh pr list --state open`); if a newer ledger exists on
one of those branches, read it (`git show origin/<branch>:potential-improvements.md`) and fold its
entries into yours. Do not branch off the open PR — branch off `master` as in §2 and reconcile the
content.

### 4.1 Reading it

Entries from earlier passes are evidence, not gospel — the code has moved since they were written.

- Treat every open entry as a candidate that has already paid its discovery cost. Re-verify it
  against the current code before spending time on it, and re-locate it by content rather than by
  the recorded line number.
- If an entry no longer describes reality — already fixed, refactored away, or simply wrong — mark
  it resolved or withdrawn with one line of reason. Do not silently delete it; a rediscovered dead
  end costs a whole pass.
- Entries marked shipped, rejected or out of scope are **closed**. Do not re-litigate them, and do
  not re-add them under a new name.
- Spend your fresh discovery effort on parts of the repo the ledger shows no coverage of yet.
  Record which areas you swept, so the next pass knows where not to start.

### 4.2 Writing it

Every candidate you find goes in — including the ones you will not implement, the ones you reject,
and the bugs you must not fix here (§8). The ledger is the complete picture; the PR is one slice of
it.

One entry per finding, with at least:

- a stable short id, and a one-line title;
- location (file, and a code anchor durable enough to survive reformatting);
- the concrete defect — what is actually wrong, not a style opinion;
- the proposed fix and a rough size in changed lines;
- value: what breaks, drifts or misleads if it stays;
- status: `open`, `shipped (PR #N)`, `rejected (reason)`, `out of scope (reason)`, or
  `withdrawn (reason)`;
- the pass that last touched the entry (date + short note).

Also keep a short section recording the sweep itself: which areas or modules this pass examined,
and which it did not reach. Coverage notes are what make the next pass cheap.

Keep it terse and scannable. It is a working ledger, not a report — no narration of your process,
no restating the repo rules.

Commit it in its own commit, separate from the code change, so a reviewer can read the refactor
without the ledger churn in the way. It needs no changelog bullet of its own — the ledger mechanism
is already recorded in the changelog, and a per-pass entry for "updated the ledger" would bury the
bullets users actually read.

## 5. Triage before you edit

Read first, write second. Merge the ledger's still-valid open entries with whatever this pass turns
up, and rank the combined list by *reviewer value per line of diff*.

Discovery is yours to direct: read the code and let the candidates come from what is there, rather
than grepping for a defect you decided on in advance. Ad-hoc static-analysis runs beyond what the
pre-commit hook configures can surface things CI never will. When a construct looks suspicious,
`git log -S` on it tells you whether it is load-bearing or leftover.

**Then pick one coherent theme and stop expanding.** A reviewable PR here is roughly ≤400 changed
lines with a single story. If triage surfaces several good themes, implement the best one and leave
the rest in the ledger as `open` — do not open several PRs, do not bundle unrelated themes.

Prefer: defects that will cause a real bug later > duplication that will drift > readability. A
cosmetic-only PR is not worth the owner's review time; if triage genuinely finds nothing above that
bar, do not invent a change to justify the pass — open a **ledger-only PR** instead, carrying just
the updated `potential-improvements.md`, and say so in your final report. The findings are that
pass's deliverable; losing them is the one outcome worse than shipping no code.

**If the best candidate sits on the lookup fast path**, `CONTRIBUTING.md`'s benchmarking section
applies in full — measure before and after on the same machine and report the noise spread
alongside, since one pair of numbers cannot separate a regression from scheduler noise. If the
result is not clearly neutral or better, revert, and record the measurement in the ledger entry so
the next pass does not retry it blind.

## 6. Working loop

Small, self-contained commits, each independently explicable. Test scope per change follows
`CLAUDE.md`'s Testing section — in particular, do not run the `slow` suites reflexively. A refactor
with no test exercising the new seam is not finished.

## 7. Gate before opening the PR

All of these, with output you have actually read:

- [ ] `make hook` clean, modulo the pre-existing failures recorded in §2.
- [ ] `make test` green.
- [ ] Whichever `slow` / `integration` suites your change maps to — green.
- [ ] `make testall` once, as a final gate.
- [ ] Benchmark evidence, if the fast path was touched.
- [ ] `git diff origin/master --stat` shows only files you intended to touch — no stray scratch
      files, and `potential-improvements.md` present.
- [ ] `CHANGELOG.rst` entry present.
- [ ] `potential-improvements.md` updated and committed: this pass's findings recorded, statuses of
      the entries you acted on changed, coverage noted.

If a gate fails and you cannot fix it, do not open the PR — report what failed and stop. Still
commit the ledger and push the branch, and name that branch in your report: the findings outlive
the failed change, and a branch left unpushed loses them.

## 8. Deciding alone

- **Is this a behaviour change?** If you cannot prove it is not, treat it as one and drop it — into
  the ledger, `out of scope`.
- **Two defensible refactors?** Take the smaller diff.
- **A bug spotted in passing?** Do not fix it here. Record it in the ledger and list it under
  "Deferred" in the PR.
- **A pre-existing test failure?** Not yours. Note it, work around it, record it.
- **The change keeps growing?** Cut back to what you can finish and verify; the remainder stays
  `open` in the ledger.
- **A comment contradicts the code?** The code is the truth for behaviour; fix the comment. Never
  change code to match a comment.
- **An old ledger entry contradicts what you see?** The code wins. Correct the entry.

## 9. Open the PR

`gh` is authenticated as the repository owner, so the branch goes to `origin`, not a fork:

```
git push -u origin quality/<short-slug>
gh pr create --base master --title "<title>" --body "<body>"
```

Do not merge, do not enable auto-merge, do not add reviewers or labels, do not push to `master`, do
not tag a release. The PR is the deliverable; the owner reviews it.

Title: imperative, names the theme rather than the mechanics. Body:

```markdown
## What
One paragraph: the defect, and the end state.

## Why
Why this was worth a reviewer's time. What breaks or drifts if it stays as is.

## Behaviour impact
None — internal quality only. (Or: name the exact observable difference, if any survived.)

## Verification
Commands run and their outcome. Benchmark before/after plus noise spread, if the fast path
was touched.

## Judgement calls
Anything ambiguous you decided yourself, and what you decided.

## Deferred
Candidates found during triage and deliberately left out, one line of reason each. Full detail is
in `potential-improvements.md`, updated in this PR.
```

## 10. Final report

In chat: the PR URL; the theme in one sentence and why it beat the alternatives; the exact
verification commands and their results — failures stated plainly, including anything skipped and
why; what changed in the ledger this pass (new entries, statuses moved, areas swept); and whether
you left a `git worktree` behind, with its path.

A small, verified, correctly-scoped PR is the goal. A large one that "probably works" is a failure.
A pass that ships nothing but leaves the ledger better than it found it is still worth something.

---

## Maintaining this skill

Two things are deliberately absent, and should stay absent when editing this file.

**Repo rules already written down elsewhere.** `CLAUDE.md` is auto-loaded and `CONTRIBUTING.md` is
one read away. A second copy here would drift, and the copy that drifts is the one an agent obeys.

**Named files, patterns or suspected defects.** Any example anchors the pass on it, and every run
then rediscovers the same handful of things instead of looking with fresh eyes. Concrete findings
belong in `potential-improvements.md` — that file is evidence from an actual pass, and it carries
the status and history that keep a finding from being re-raised forever. This file is instructions.
