---
name: code-quality-pass
description: Runs one autonomous internal-code-quality pass over this repository — triage, then the highest-priority findings fixed one at a time with no behaviour change until a diff budget of ~400 changed lines is spent, full verification, and a pull request opened against master — coordinated through a persistent findings ledger (potential-improvements.md) so repeated passes build on each other instead of rediscovering the same candidates. Use this whenever the user asks for a code-quality pass, a cleanup or refactoring pass, wants technical debt found or paid down, says something like "improve the code quality", "tidy up the codebase", "find what's worth refactoring", or asks to run/continue/repeat the quality pass. Use it also when they ask what improvements are still outstanding, want the next item from the ledger picked up, or want a quality PR prepared for review — even if they never say the word "skill".
---

# Autonomous code-quality pass

Deliver one **code-quality improvement pass** on `timezonefinder` (Python library for offline
timezone lookup by coordinates), ending in a pull request opened against `master` for the
repository owner to review, plus an updated findings ledger.

The pass works the ledger down rather than sideways: rank every candidate, fix the highest-priority
one, come back to the ranking for the next, and stop once the accumulated diff reaches the ~400
changed-line budget of §6.

Work to completion without stopping to ask questions. Where something is ambiguous, apply §8 and
record the call you made in the PR description.

This pass is designed to be run many times, **and several may be in flight at once**. Most of its
value comes from §4: the ledger is what turns a series of one-off passes into cumulative progress,
so treat reading and updating it as part of the deliverable, not bookkeeping. §2.1 is what keeps
concurrent passes off each other's ground — read it before you pick anything to work on.

## 1. Ground rules

`CLAUDE.md` is auto-loaded. Read `CONTRIBUTING.md` too — it is not auto-loaded and it owns the
benchmarking, testing-scope and PR conventions this pass needs. Both are authoritative and override
any general habit; nothing here repeats them.

Two of their rules outrank everything else for *this* task, so treat them as hard gates rather than
guidance: the changelog entry is mandatory (yours belongs in the `Internal:` sub-list), and the
lookup fast path is not to be traded away for elegance (§5).

## 2. Isolate before you edit

Two things to stay clear of: the maintainer's uncommitted work (below) and any pass already
running (§2.1).

The checkout may contain unrelated uncommitted work. **Your PR must not contain any of it.**

1. `git status --short`, and the survey in §2.1.
2. Work in an isolated worktree branched from the pushed baseline, and do everything from there:
   ```
   git fetch origin
   git worktree add ../tzf-<slug> -b quality/<slug> origin/master
   ```
   A worktree rather than `git checkout -b` even on a clean tree: the checkout may sit on someone
   else's branch, and switching it out from under a concurrent session breaks that session. **Both
   names must be unique to this pass** — a fixed path collides the moment a second pass runs. The
   ground you will take is not settled until §5, so a provisional slug is fine here; rename the
   branch with `git branch -m quality/<theme-slug>` when you claim it, before the first push.
3. Install into that worktree.
4. Record a baseline **before** editing: run `make test` and `make hook` on the untouched branch.
   Anything already failing there is pre-existing — note it, do not fix it in this pass, do not let
   it block you.

Also note: `make hook` runs pre-commit across **all** files, so it can reformat files unrelated to
your change. Stage only what belongs to your change; `git checkout --` the rest.

The checkout may also hold untracked scratch material — notes, plans, working directories — that
`.gitignore` does not cover, so a blanket `git add -A` would sweep it into your PR. Stage paths
explicitly; never `git add -A`. The findings ledger is the deliberate exception: it is a tracked
file at the repository root that you do commit (§4).

### 2.1 Isolate from the other passes

Several passes may run at once. They share one repository, one ledger and one changelog, so assume
a sibling exists. There is no lock — the remote branch list is the whole coordination mechanism, so
it only works if every pass both reads it and writes to it, at the right two moments.

**Survey, before you create your worktree:**

```
git fetch origin
git branch -r --list 'origin/quality/*'
gh pr list --state open
```

For each live branch, `git log origin/master..origin/<branch> --stat` shows the ground it has
already taken, and `git show origin/<branch>:potential-improvements.md` its ledger (§4).

**Claim, the moment you pick your first item in §5** — before you edit a single file:

```
git branch -m quality/<theme-slug>      # if you branched under a provisional name
git push -u origin quality/<theme-slug>
```

Pushing a branch that still points at `master` costs nothing and is instantly visible to every
sibling. The slug *is* the claim, so make it name the ground you are taking
(`quality/docstring-contracts`, not `quality/pass-4`). A pass that works for an hour and pushes at
the end has claimed nothing.

Because this pass takes several items in sequence, the branch only ever claims what it already
holds. Push after each item you finish (§6), and re-run the fetch and branch list above before you
start the next one — it costs seconds, and it is the only thing standing between two passes and the
same entry.

**Resolving a collision.** If a sibling's branch already covers an item you were about to take, or
the files it touches, it wins — it pushed first. Take the next candidate off your ranking rather
than racing it, and say in your PR which item you yielded and to whom. Two passes converging on one
entry is the expensive failure here: both do the work, only one PR can land, and the ledger entry
gets closed twice.

**What will conflict anyway, and how to resolve it.** These are expected, not mistakes:

- `CHANGELOG.rst` — every pass appends a bullet to the end of the same `Internal:` sub-list, so
  two passes always conflict there. **Keep both bullets**, in the order the PRs merged. Never drop
  a sibling's bullet to make the conflict go away.
- `potential-improvements.md` — mostly avoided by §4's rules (delete what shipped, append new
  entries at the end of their section, never renumber). What remains is usually one entry both
  passes re-verified: take the later, more specific note.
- Source files — should not happen if you honoured the claim above. If it does, rebase and re-read
  the sibling's change before resolving; it may have already fixed what you were about to.

Rebase onto `master` and re-run the gate (§7) whenever a sibling lands ahead of you.

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

Because it travels through `master`, a pass starting while a sibling's PR is still open will read a
ledger missing that PR's updates. From the survey you already ran in §2.1, read each live branch's
copy (`git show origin/<branch>:potential-improvements.md`) and fold its entries into yours. Do not
branch off the sibling — branch off `master` as in §2 and reconcile the content.

**The ledger is a to-do list, not a history.** An entry you ship is **deleted** in the same PR, not
kept with a `shipped` status. The code is the evidence it is done, the changelog says what changed,
and `git log -- potential-improvements.md` still has the text if anyone wants it. Left in, they are
dead weight every later pass reads past, interleaved with the live entries — and the ledger's
largest source of conflict between concurrent passes.

The deletion rule is **only** for shipped work. Entries you *rejected*, ruled *out of scope* or
*withdrew* stay, with their one line of reason: they encode a dead end, and re-discovering one
costs a whole pass. So does the "deliberately checked and found sound" list.

### 4.1 Reading it

Entries from earlier passes are evidence, not gospel — the code has moved since they were written.

- Treat every open entry as a candidate that has already paid its discovery cost. Re-verify it
  against the current code before spending time on it, and re-locate it by content rather than by
  the recorded line number.
- If an entry no longer describes reality, work out which case it is. **Already fixed** — by you,
  by a sibling pass, or by unrelated work: delete it. **Wrong, or a dead end**: keep it, marked
  `withdrawn` with one line of reason, so it is not rediscovered at full price.
- Entries marked rejected, out of scope or withdrawn are **closed**. Do not re-litigate them, and
  do not re-add them under a new name. (Anything shipped is gone from the file entirely; if you
  find yourself about to re-raise something, `git log -S'<id>' -- potential-improvements.md`
  tells you whether a past pass already dealt with it.)
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
- status: `open`, `rejected (reason)`, `out of scope (reason)`, or `withdrawn (reason)` — there is
  no `shipped`, because shipped entries are deleted;
- the pass that last touched the entry (date + short note).

Also keep a short section recording the sweep itself: which areas or modules this pass examined,
and which it did not reach. Coverage notes are what make the next pass cheap.

Write so a sibling pass's edits merge cleanly beside yours: **append** new entries at the end of
their section rather than interleaving, **never renumber** an existing id, and leave the wording of
entries you did not act on alone. Reflowing a paragraph you did not change turns a clean merge into
a conflict for no gain.

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

**Rank the whole list, then work down it.** The ranking, not a theme, is what this pass ships: take
the top candidate, fix it (§6), come back for the next, and stop at the budget. So rank everything
and not just the winner — a candidate lost to a sibling (§2.1) or found already fixed should then
cost you the next line of the ranking rather than a fresh triage.

Prefer: defects that will cause a real bug later > duplication that will drift > readability. Size
breaks ties only: at equal value the smaller fix goes first, since it leaves more budget for what
follows. Do not otherwise let size reorder the list — a pass that takes the cheap items first
because they are cheap spends 400 lines on the least important things in the repository.

**Claim by pushing your branch (§2.1) the moment you have picked the first item** — that is the
step that makes running several passes at once safe, and it is worthless done later.

A cosmetic-only PR is not worth the owner's review time; if triage genuinely finds nothing above
that bar, do not invent a change to justify the pass — open a **ledger-only PR** instead, carrying
just the updated `potential-improvements.md`, and say so in your final report. The findings are
that pass's deliverable; losing them is the one outcome worse than shipping no code.

**If a candidate you take sits on the lookup fast path**, `CONTRIBUTING.md`'s benchmarking section
applies in full — measure before and after on the same machine and report the noise spread
alongside, since one pair of numbers cannot separate a regression from scheduler noise. If the
result is not clearly neutral or better, revert, and record the measurement in the ledger entry so
the next pass does not retry it blind.

## 6. Working loop and the diff budget

Take the ranked candidates one at a time, highest first. Per item:

1. **Re-verify** it against the current code (§4.1). Already fixed, or wrong? Resolve the entry as
   §4.1 says and move to the next candidate without spending a commit on it.
2. **Implement it, and only it.** Test scope per change follows `CLAUDE.md`'s Testing section — in
   particular, do not run the `slow` suites reflexively. A refactor with no test exercising the new
   seam is not finished.
3. **Commit it on its own**, message naming the ledger id, so a reviewer can read one fix at a time
   and reject one without unpicking the rest.
4. **Delete its ledger entry** and **push** (§2.1). Ledger edits stay in their own commits, apart
   from the code (§4) — one per item or one at the end, as long as they are not mixed in.
5. **Measure the diff and decide whether to continue.**

**The budget is ~400 changed lines**, measured against the merge base with the ledger excluded,
since ledger churn is bookkeeping rather than review load:

```
git diff origin/master --shortstat -- . ':(exclude)potential-improvements.md'
```

Check it **between items, never mid-item**: finish and commit the one in hand first, then go to §7
as soon as the total has reached 400 — or as soon as the next candidate's estimated size would
carry it well past 400, since a fix half-applied to stay under the line is worse than one not
started. Everything unreached stays `open` in the ledger for the next pass.

400 is a stopping rule, not a quota. If the ranking runs dry first, or every remaining candidate is
too large to start, conclude at whatever the diff is — do not pad the pass to fill the budget. One
item and a report is a valid outcome; so is a single item that is worth 400 lines by itself.

The items need no common theme — the ranking is the story — but each must stand alone and be
explicable without the others, so that the owner can take part of the PR.

## 7. Gate before opening the PR

All of these, with output you have actually read:

- [ ] `git fetch origin && git rebase origin/master` **first** — a sibling pass may have landed
      while you worked, and `CLAUDE.md` is explicit that a rebase after the gate invalidates it.
      Resolve per §2.1 and start the list again if the rebase moved your base.
- [ ] `make hook` clean, modulo the pre-existing failures recorded in §2.
- [ ] `make test` green.
- [ ] Whichever `slow` / `integration` suites your change maps to — green.
- [ ] `make testall` once, as a final gate.
- [ ] Benchmark evidence, if the fast path was touched.
- [ ] `git diff origin/master --stat` shows only files you intended to touch — no stray scratch
      files, and `potential-improvements.md` present.
- [ ] The changed-line total sits at or just past the §6 budget, or the ranking ran dry first —
      and you can say which of the two stopped the pass.
- [ ] `CHANGELOG.rst` entry present.
- [ ] `potential-improvements.md` updated and committed: this pass's findings recorded, the entries
      you shipped **deleted**, the ones you rejected or withdrew kept with a reason, coverage noted.

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
- **An item outgrows its estimate?** Cut it back to what you can finish and verify; the remainder
  goes back into the ledger as a new `open` entry. If it has eaten the budget, it ends the pass.
- **Budget nearly spent and the next item is large?** Stop there. 400 finished lines beat 600 with
  the last fix rushed, and the item keeps its place in the ranking for the next pass.
- **A comment contradicts the code?** The code is the truth for behaviour; fix the comment. Never
  change code to match a comment.
- **An old ledger entry contradicts what you see?** The code wins. Correct the entry.
- **A sibling pass holds an item you were about to take?** It pushed first, so it keeps it (§2.1).
  Take the next candidate on your ranking; do not open a competing PR on the same ground.
- **A sibling landed while you worked and your change is now partly redundant?** Rebase, keep only
  what is still a defect, and say in the PR what its change already covered. A shrunken PR is fine;
  a PR that re-applies what is already on `master` is not.

## 9. Open the PR

`gh` is authenticated as the repository owner, so the branch goes to `origin`, not a fork. The
branch is already pushed — you claimed it in §2.1 — so this is a second push and the PR:

```
git push origin quality/<short-slug>
gh pr create --base master --title "<title>" --body "<body>"
```

Do not merge, do not enable auto-merge, do not add reviewers or labels, do not push to `master`, do
not tag a release. The PR is the deliverable; the owner reviews it.

Title: imperative, and about what was paid down rather than the mechanics. Name the common thread
if the items happen to share one; otherwise name the ground they cover. Body:

```markdown
## What
One paragraph on what this pass paid down, then one line per item shipped — ledger id, the defect,
the end state — in the order they were committed. Close with the changed-line total against the
400-line budget, and whether the budget or an exhausted ranking stopped the pass.

## Why
Why this was worth a reviewer's time. What breaks or drifts if it stays as is.

## Behaviour impact
None — internal quality only. (Or: name the exact observable difference, if any survived.)

## Verification
Commands run and their outcome. Benchmark before/after plus noise spread, if the fast path
was touched.

## Judgement calls
Anything ambiguous you decided yourself, and what you decided. Name any sibling pass you yielded
to, or whose landed change shrank this one.

## Deferred
Everything the ranking still holds: candidates deliberately left out, and the ones the budget
stopped the pass before reaching — one line of reason each, in ranked order, so the next pass's
starting point is visible. Full detail is in `potential-improvements.md`, updated in this PR.
```

## 10. Final report

In chat: the PR URL; the items shipped in the order they were taken, one line each, with the
changed-line total and what stopped the pass — budget reached, or ranking exhausted; the exact
verification commands and their results — failures stated plainly, including anything skipped and
why; what changed in the ledger this pass (new entries, entries deleted as shipped, closures, areas
swept); which sibling passes were in flight and how you stayed clear of them; and whether you left
a `git worktree` behind, with its path.

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
