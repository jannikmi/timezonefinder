---
name: improvement-pass
description: "Advances timezonefinder by one improvement pass — read the ranked register in potential-improvements.md, re-verify and re-rank it, take the highest-ranked item that is eligible, put any maintainer-owned design choice to them as concrete options, implement one reviewable slice, and end in a single pull request against master plus an updated register. One pass, one item, one pull request. Any improvement is in scope, whatever its area: correctness, performance, public API, data format, docs, packaging, release and CI, tests, developer tooling, internal structure. The register holds every finding, the ranking, the sequencing rules and the decisions already taken, so repeated and concurrent passes build on each other instead of rediscovering the same candidates. Use this whenever the user asks for an improvement, quality, cleanup, refactoring or roadmap pass, wants technical debt found or paid down, says improve the code quality or tidy up the codebase or find what is worth refactoring, asks to work on or continue the roadmap, wants the next item picked up, asks what improvements are still outstanding or what the next pass would do or what is blocking an item, or wants a pull request prepared for review — even if they never say the word skill."
---

# Improvement pass

Deliver **one improvement** to `timezonefinder` (Python library for offline timezone lookup by
coordinates), ending in **one pull request** opened against `master` for the repository owner to
review, plus an updated register.

**One pass = one item = one pull request**, and the item is the most important one the ranking
holds that this pass can actually take. Not a theme, not a batch: the whole point of maintaining a
ranking is that the top of it is what gets reviewed next.

The register — `potential-improvements.md` at the repository root — is what turns a series of
one-off passes into cumulative progress. It holds every finding, the single ranking across all of
them, the sequencing rules and the decisions already taken. Reading it and writing it back is part
of the deliverable, not bookkeeping. §3 is what keeps concurrent passes off each other's ground;
read it before you pick anything to work on.

## 0. What counts as an improvement

Anything that leaves the package better than you found it and that a reviewer can act on. A
correctness defect, a slow path, an API that is awkward to call, a docs page that lies, a release
step that can fail silently, a test that cannot fail, a name that misleads, a build slower than it
needs to be, a data encoding that wastes half its bytes. **Whatever a pass discovers is welcome in
the register**, whatever its area and whoever would do the work — §4 ranks it and §5 names the few
things that are out of bounds.

Resist the pull to sort candidates into categories that then decide how the pass behaves. Two
properties do that, and both belong to the individual change rather than to any class you could put
it in:

- **Does it change observable behaviour?** Same results, same public API, same binary formats, same
  exception types for the same inputs — or not. If you cannot prove it does not, it does (§5).
- **Does it carry a choice that belongs to the maintainer?** One that outlives the pass and is
  expensive to reverse: what a batch call returns, whether a dependency is hard, which thresholds
  block a release. If so, §6 applies **before any code is written** — an item built on a guessed
  design choice is worse than one not started. If not, decide and proceed; stopping to ask would
  be the agent declining to make a routine call.

Read both per item, not per category. A rename that looks like pure tidying changes an exception
type and is a behaviour change; a month-sized item whose design was settled two passes ago needs no
question at all.

## 1. Ground rules

`CLAUDE.md` is auto-loaded. Read `CONTRIBUTING.md` too — it is not auto-loaded and it owns the
benchmarking, testing-scope and PR conventions this pass needs. Both are authoritative and override
any general habit; nothing here repeats them.

Four hard gates, above everything else:

- **Never merge a pull request, never enable auto-merge, never push to `master`, never tag.** Open
  the pull request and stop.
- **Never regenerate the packaged timezone data as a side effect.** It rewrites ~64 MB, and a
  weekly workflow already opens *and auto-merges* data-update pull requests; colliding with it is
  how an unrelated change ends up in a release. Regeneration happens only when an item's whole
  point is the data format, only with its precondition carried, and only with the maintainer's
  explicit go-ahead in this session.
- **The changelog entry is mandatory** — `CLAUDE.md`'s *Changelog* section owns its shape; internal
  work goes in the `Internal:` sub-list. Amend the existing bullet for an item rather than
  appending a second one.
- **The lookup fast path is not traded away for elegance.** If the item touches it,
  `CONTRIBUTING.md`'s benchmarking section applies in full — before/after on the same machine, the
  noise spread alongside, and the acceleration backend named, since one pair of numbers cannot
  separate a regression from scheduler noise and a local `uv run` binds Numba rather than the C
  extension. If the result is not clearly neutral or better, revert and record the measurement.

## 2. The register is the source of truth

`potential-improvements.md` is a **tracked file, committed as part of your pull request.** That is
what carries it between passes: it arrives with the checkout, and it reaches the next pass through
`master`. It is public and the owner reads it — write it for a contributor who has never seen this
skill.

It replaced a roadmap issue on the tracker, deliberately. Reasoning that lives outside the
repository goes stale silently: nothing references it, no check reads it, and a reviewer never sees
it in a diff. In the register, an entry is reviewed in the pull request that changes it.

Issues still exist and are still useful — an issue is where one item is worked out in detail and
where outside contributors comment. But **the ranking, the sequencing and the decisions live
here**, and an entry names its issue as a pointer rather than delegating its reasoning to it.

| Question | Answered by |
|---|---|
| what is worth doing next | the ranking in the register |
| why an option was refused | the register's recorded decisions |
| what is claimed right now | remote branches and open pull requests (§3.1) |
| what one item's detail is | its issue, where it has one |

Anything a pass learns that a later pass needs must land in the register before the pass ends. An
answer that exists only in a chat session is lost.

### 2.1 Reading it

Entries from earlier passes are evidence, not gospel — the code has moved since they were written.

- Treat every open entry as a candidate that has already paid its discovery cost. Re-verify it
  against the current code before spending time on it, and re-locate it by content rather than by
  a recorded line number.
- If an entry no longer describes reality, work out which case it is. **Already done** — by you, by
  a sibling pass, or by unrelated work: delete it, row and all, and say so in the pull request.
  **Wrong, or a dead end**: keep it, marked `withdrawn` with one line of reason, so it is not
  rediscovered at full price.
- **Check the state of every issue the register names before you rank.** A `GH-<n>` entry whose
  issue has closed either shipped or was dropped; both mean the entry is resolved. It is one
  command over the whole file and it is the only staleness signal that needs no reading:
  ```
  grep -o 'GH-[0-9]*' potential-improvements.md | sort -u | cut -d- -f2 |
    xargs -I{} gh issue view {} --json number,state --jq '"\(.number) \(.state)"'
  ```
- **Correct the reasoning, not just the status.** An entry whose conclusion survived on a premise
  since disproved is the failure worth catching: it reads as settled and sends the next pass down a
  path already ruled out. Say what moved.
- Entries marked rejected, out of scope or withdrawn are **closed**. Do not re-litigate them and do
  not re-add them under a new name. Recorded decisions are closed the same way; if new evidence
  contradicts one, that is itself a question for the maintainer (§6) — never reverse one silently.
- Spend fresh discovery effort on parts of the repository the coverage log shows no coverage of
  yet, and record which areas you swept.

### 2.2 Writing it

Every candidate you find goes in — including the ones you will not implement, the ones you reject,
and the ones that need a decision you did not get. The register is the complete picture; the pull
request is one slice of it.

One entry per finding, with at least: a stable short id and a one-line title; location (file plus a
code anchor durable enough to survive reformatting) or the issue it tracks; the concrete defect or
the change proposed; the fix and a rough size in changed lines; the value — what breaks, drifts or
misleads if it stays; a status; and the pass that last touched it, dated.

**The register is a to-do list, not a history.** An entry whose work landed is **deleted — the
entry and its ranking row — in the same pull request that ships it**, never kept with a status
saying it is done. The code is the evidence, the changelog says what changed, and
`git log -- potential-improvements.md` still has the text. Left in, a finished entry reads exactly
like an open one, so the next pass pays full price to rediscover that there is nothing to do; it is
also the largest source of conflict between concurrent passes. There is no status meaning done, and
`tests/test_improvement_ledger.py` rejects one — if you are tempted to write `shipped`, the entry
should be gone instead. The deletion rule is **only** for work that landed. Rejected, out-of-scope and
withdrawn entries stay with their one line of reason, as does the *deliberately checked and found
sound* list: each encodes a dead end, and re-discovering one costs a whole pass.

Two rules the file depends on:

- **The ranking table and the entries are one list, kept in step.** Every entry has exactly one row
  and every row has exactly one entry; `tests/test_improvement_ledger.py` fails otherwise. The
  table is the only statement of order — do not re-sort the entry sections to match it.
- **Write so a sibling pass's edits merge beside yours:** append new entries at the end of their
  section rather than interleaving, never renumber an existing id, and leave the wording of entries
  you did not act on alone. Reflowing a paragraph you did not change turns a clean merge into a
  conflict for no gain.

Keep it terse and scannable — a working register, not a report. Commit it separately from the code
change so a reviewer can read the change without the register churn in the way. It needs no
changelog bullet of its own.

## 3. Isolate and claim

Two things to stay clear of: the maintainer's uncommitted work, and any pass already running.

The checkout may contain unrelated uncommitted work, and untracked scratch material `.gitignore`
does not cover. **Your pull request must not contain any of it.** Stage paths explicitly; never
`git add -A`. The register is the deliberate exception — a tracked root file you do commit.

1. `git status --short`, and the survey in §3.1.
2. Work in an isolated worktree branched from the pushed baseline, and do everything from there:
   ```
   git fetch origin
   git worktree add ../tzf-<slug> -b improve/<slug> origin/master
   ```
   A worktree rather than `git checkout -b` even on a clean tree: the checkout may sit on someone
   else's branch, and switching it out from under a concurrent session breaks that session. **Both
   names must be unique to this pass** — a fixed path collides the moment a second pass runs. Where
   the item has an issue, put its number in the slug (`improve/499-batch-api`), since that is what
   a sibling's survey matches on.
3. Install into that worktree.
4. Record a baseline **before** editing: run `make test` and `make hook` on the untouched branch.
   Anything already failing there is pre-existing — note it, do not fix it in this pass, do not let
   it block you. Note also that `make hook` runs pre-commit across **all** files, so it can
   reformat files unrelated to your change; stage only what belongs to yours and `git checkout --`
   the rest.

### 3.1 Isolate from the other passes

Several passes may run at once. They share one repository, one register and one changelog, so
assume a sibling exists. There is no lock — the remote branch list is the whole coordination
mechanism, so it only works if every pass both reads it and writes to it, at the right two moments.

**Survey, before you create your worktree:**

```
git fetch origin
git branch -r --list 'origin/improve/*'
gh pr list --state open
```

Branch names are not uniform: this skill uses `improve/<slug>`, earlier passes used `quality/*` and
`roadmap/*`, and GitHub's *create branch from issue* button produces `<issue>-<slug>`. Match on the
item — its id and its issue number — not on a prefix. For each live branch,
`git log origin/master..origin/<branch> --stat` shows the ground it has taken and
`git show origin/<branch>:potential-improvements.md` its register.

**Claim, the moment §4 picks your item** — before you edit a file, and before you ask the questions
in §6, since a question round can take a while and an unclaimed item is fair game the whole time:

```
git push -u origin improve/<slug>
```

Pushing a branch that still points at `master` costs nothing and is instantly visible to every
sibling. The slug *is* the claim, so make it name the ground you are taking
(`improve/docstring-contracts`, not `improve/pass-4`). A pass that works for an hour and pushes at
the end has claimed nothing.

**Resolving a collision.** If a sibling's branch already covers your item, or the files it touches,
it wins — it pushed first. Take the next eligible candidate rather than racing it, and say in your
pull request which item you yielded and to whom. Two passes converging on one entry is the
expensive failure here: both do the work, only one pull request can land.

**What will conflict anyway, and how to resolve it.** These are expected, not mistakes:

- `CHANGELOG.rst` — every pass appends a bullet to the end of the same `Internal:` sub-list, so
  two passes always conflict there. **Keep both bullets**, in the order the pull requests merged.
  Never drop a sibling's bullet to make the conflict go away.
- `potential-improvements.md` — mostly avoided by §2.2's rules. What remains is usually one entry
  both passes re-verified: take the later, more specific note. If both changed the ranking table,
  merge the rows rather than taking one side wholesale.
- Source files — should not happen if you honoured the claim above. If it does, rebase and re-read
  the sibling's change before resolving; it may already have fixed what you were about to.

Rebase onto `master` and re-run the gate (§9) whenever a sibling lands ahead of you.

## 4. Triage and select

Read first, write second. Merge the register's still-valid entries with whatever this pass turns
up, re-rank the combined list, then **walk the ranking from the top and take the first eligible
item**.

Discovery is yours to direct: read the code and let the candidates come from what is there, rather
than grepping for a defect you decided on in advance. Ad-hoc static-analysis runs beyond what the
pre-commit hook configures can surface things CI never will. When a construct looks suspicious,
`git log -S` on it tells you whether it is load-bearing or leftover.

Rank by **expected value**: defects that will cause a real bug later > work that unblocks other
work > duplication that will drift > readability. Size breaks ties only — at equal value the
smaller item goes first. Do not otherwise let size reorder the list; a pass that takes the cheap
item because it is cheap ships the least important thing in the repository. An item sits **below
its own blocker**, because the ranking is walked top-down and a blocked item at the top is noise.

**A performance item needs a measured share before it can be ranked as one.**
`prototypes/query_stage_profile.py` attributes a `timezone_at` query to its stages, per backend
and per coordinate-access mode, off the committed fixtures; the register's *The measured
baseline* carries the denominators, the commit they were taken at, and a one-command freshness
check. Benefit is the **ceiling** — the share the change removes at best — and cost is size plus
the decisions it needs plus whether it forces a data-format change. A ceiling under the
machine's own 3–9 % run-to-run noise cannot be shown by the benchmark suite even when the change
is real: rank that item on correctness or simplicity and say so, rather than selling it as a
speed-up. If nobody has measured it, the item *is* a measurement — one profiler run, a few
minutes per backend, and the numbers go in the entry.

Those numbers came off one development machine, so state a benefit in the form that survives
leaving it: **the count a change removes** (hit counts do not depend on hardware) before the
time it removes, read from the **`clang` / `in_memory=False`** column rather than the dev
checkout's numba one, and converted from a stratum share to a **workload** share — the register
carries the conversion. Then apply the 2x rule: act on a difference only if it survives any one
stage turning out twice as cheap or twice as expensive on someone else's hardware.

An item is **eligible** when all of these hold:

- **Unclaimed** (§3.1). An open pull request referencing it, or a live branch, means it is taken.
  A branch with no pull request means a previous pass started it: **resume that branch** rather
  than opening a second one for the same item.
- **Its preconditions are met** — the register's sequencing rules, checked explicitly. A
  precondition is unmet ⇒ the item is not eligible this pass. Not "eligible with a caveat", not
  "eligible if I also do the prerequisite". Take the next item, or pick up the prerequisite itself
  if it is free.
- **Its maintainer-owned decisions are already recorded**, or you can get them this session (§6).
  If not, record the questions and move down the ranking — that is what keeps a large item awaiting
  a decision from stalling every pass behind it.
- **It fits one reviewable pull request**, or can be sliced into one (§7.1). If neither, the
  decomposition is the deliverable.

Prefer resuming an item a previous pass started over opening a new front — half-advanced items are
the ones that go stale. Re-rank and re-verify *before* picking, not after: an entry's premise goes
stale faster than its location.

## 5. Scope: what a pass may change

**In scope: any change to this repository a reviewer can act on** — library code, scripts, tests,
docs, packaging, workflows, developer tooling. The list of what a pass may improve is not enumerated
anywhere on purpose; an enumeration is read as exhaustive, and then a real defect goes unrecorded
because it did not fit a heading.

Two conditions attach to the change rather than to its area, and both are §0's questions applied:

- A change that alters observable behaviour needs a **recorded decision** behind it (§6). If you
  cannot prove a change is behaviour-preserving, treat it as one.
- An item whose design is already decided is implemented as decided — **exactly what its recorded
  decisions say, and no more.**

Out of bounds for every pass — the repository docs describe some of these procedures neutrally
because they cannot know your boundary, so treat them as prohibitions here:

- Regenerating timezone data, benchmark fixtures or FlatBuffers bindings; editing the packaged data
  directory or the generated FlatBuffers bindings.
- Dependency, lockfile, Python-version or release-version changes.
- Whole-file reformatting or "modernisation" for style alone — churn a reviewer cannot tie to a
  concrete defect.
- `prototypes/` — **except** the `FINDINGS` block of `prototypes/query_stage_profile.py`, which
  the pass that invalidates it updates (§9).
- A behaviour change with no recorded decision behind it. If you cannot prove a change is
  behaviour-preserving, treat it as a behaviour change: it needs §6 first.

## 6. Decisions that belong to the maintainer

### 6.1 Read first, then ask

**Before asking anything**, check that the answer is not already written down. A question the
repository already answers is the agent failing to read: the register's recorded decisions; the
entry itself and the issue body, most of which name their own open questions; `CLAUDE.md`,
`CONTRIBUTING.md`, `docs/architecture.rst`, `docs/data_format.rst`.

Do not ask about naming, formatting, file placement, test structure, or anything reversible in five
minutes. Make the call, state it in the pull request, move on.

**The bar for asking: would two reasonable answers lead to materially different work?** If yes,
ask. If no, decide.

### 6.2 How to ask

Use structured multiple-choice questions — the alternatives are usually already named with their
trade-offs. **Lead with a recommendation**: a question presented without one hands the work back to
the maintainer instead of reducing it. State which option you would take and why in one line, then
let them override it. Batch every blocking question for the item into as few rounds as possible —
the ones that block *this* pass, and the ones that would be expensive to reverse later.

### 6.3 Record every answer in the register

An answer given in chat dies with the session, and the next pass would re-ask and might get a
different answer. Write each answer into the item's entry — question, decision, one line of
rationale, dated — **commit and push it before implementing against it**, so a crash mid-pass does
not lose it. A decision with consequences beyond its own item goes in the register's *recorded
decisions* section instead, which is the part that is never deleted.

### 6.4 When the maintainer does not answer

**Do not guess and proceed.** Record the unanswered questions in the entry, marked as awaiting a
decision, and move down the ranking to the next eligible item (§4). If nothing below it is eligible
either, the questions are this pass's deliverable: ship them as a register-only pull request (§7).

## 7. What one pass delivers

Four outcomes are all successes. Say which one you are aiming at, and do not manufacture code to
make a pass feel productive:

1. **One item implemented** — the ordinary case: one reviewable slice, behind decisions already
   taken.
2. **Decisions surfaced and recorded, no code.** *"These are the four decisions blocking this item,
   the trade-off in each, and my recommendation"* is a complete pass. It unblocks every later one.
3. **A design written up and the item decomposed, no code.** When an item cannot be cut into
   releasable slices by inspection, that decomposition is the deliverable.
4. **Nothing eligible**, triage recorded.

Outcomes 2–4 still open a **register-only pull request** carrying just
`potential-improvements.md`. The findings are that pass's deliverable, and losing them is the one
outcome worse than shipping no code. The same applies when triage genuinely finds nothing above the
bar: a cosmetic-only pull request is not worth the owner's review time, so do not invent a change
to justify the pass.

### 7.1 The releasable-slice rule

Some items are month-sized, so the question that decides whether this skill helps or harms is:
*how does a pass deliver a reviewable slice without leaving the tree half-migrated?*

**The rule: a slice must leave `master` releasable on its own.** The test is concrete —

> Can the slice be described by one true sentence in `CHANGELOG.rst` that stands without promising
> a follow-up? If not, it is not a slice; it is half a change.

"Added `timezone_at_many`, returning zone ids" passes. "Migrated the reader to the new encoding,
writer to follow" fails: nothing can read the shipped data until the second half lands.

What that implies in practice:

- **Additive before subtractive.** Add the new path, keep the old one working, remove it in a later
  slice once the new one is proven. Both live at once and both are tested.
- **Decompose first, implement second** (outcome 3). Record the slices as entries in the register,
  ranked, so the next pass takes the first of them.
- **A genuinely atomic migration is not sliced — it is prototyped.** A binary format change cannot
  half-land. The deliverable is then the prototype plus its measurements in `prototypes/` — not
  shipped, not a benchmark, no CI, no committed figures — and the numbers recorded in the entry.
  The migration lands later, in one piece, once the numbers have settled the design.
- **Keep the slice reviewable: roughly ≤400 changed lines with a single story**, measured against
  the merge base with the register excluded, since register churn is bookkeeping rather than review
  load:
  ```
  git diff origin/master --shortstat -- . ':(exclude)potential-improvements.md'
  ```
  400 is a ceiling that forces slicing, **not a budget to spend**: an item worth 40 lines ends the
  pass at 40. If the item outgrows the ceiling mid-flight, cut it back to what you can finish and
  verify, and put the remainder back in the register as a new ranked entry.

## 8. Working loop

1. **Re-verify** the item against the current code (§2.1). Already done, or wrong? Resolve the
   entry as §2.1 says and go back to §4 for the next candidate without spending a commit on it.
2. **Get and record any decision it needs** (§6), pushed before you implement against it.
3. **Implement it, and only it.** Test scope follows `CLAUDE.md`'s *Testing* section — in
   particular, do not run the `slow` suites reflexively; do run the ones your change maps to. A
   change with no test exercising the new seam is not finished.
4. **Commit the code**, message naming the entry id.
5. **Delete the entry and its ranking row**, in one commit of their own. If the slice left a
   remainder, the entry stays instead — rewritten to describe only what is left, keeping its id and
   its row, so the next pass reads the remainder and not the original scope.
6. **Push** (§3.1), then go to the gate.

## 9. Gate before opening the pull request

All of these, with output you have actually read:

- [ ] `git fetch origin && git rebase origin/master` **first** — a sibling pass may have landed
      while you worked, and `CLAUDE.md` is explicit that a rebase after the gate invalidates it.
      Resolve per §3.1 and start the list again if the rebase moved your base.
- [ ] Preconditions re-checked after the rebase — a sibling may have satisfied or invalidated one.
- [ ] `make hook` clean, modulo the pre-existing failures recorded in §3.
- [ ] `make test` green.
- [ ] Whichever `slow` / `integration` suites your change maps to — green.
- [ ] `make testall` once, as a final gate.
- [ ] Benchmark evidence naming its backend, if the fast path was touched or any performance claim
      is made.
- [ ] If anything under `timezonefinder/` or the packaged data moved: the register's freshness
      check run, and **either** the profiler re-run on both backends with `FINDINGS`, the
      baseline anchor and every share it moved updated in this pull request, **or** one line in
      the register classifying the change as inert for timings. A stale share does not announce
      itself — the next pass ranks on it.
- [ ] The slice passes §7.1's changelog sentence test.
- [ ] `git status --short packages/timezonefinder-data/timezonefinder_data/data` is **empty**,
      unless data regeneration was the explicit, agreed subject of this pass.
- [ ] `git diff origin/master --stat` shows only files you intended to touch — no stray scratch
      files, and `potential-improvements.md` present.
- [ ] `CHANGELOG.rst` entry present.
- [ ] `potential-improvements.md` updated and committed: this pass's findings recorded; the entry
      whose work landed **deleted, with its ranking row** — grep the id in the diff and confirm no
      occurrence survives; rejected or withdrawn entries kept with a reason; decisions recorded;
      coverage noted.

If a gate fails and you cannot fix it, do not open the pull request — report what failed and stop.
Still commit the register and push the branch, and name that branch in your report: the findings
and the recorded decisions outlive the failed change, and a branch left unpushed loses them.

## 10. Open the pull request

`gh` is authenticated as the repository owner, so the branch goes to `origin`, not a fork. The
branch is already pushed — you claimed it in §3.1 — so this is a second push and the pull request:

```
git push origin improve/<slug>
gh pr create --base master --title "<title>" --body "<body>"
```

Do not merge, do not enable auto-merge, do not add reviewers or labels, do not push to `master`, do
not tag a release. The pull request is the deliverable; the owner reviews it. Reference an issue as
`Refs #<issue>` — **not** `Closes`, unless the slice genuinely finishes the whole issue.

Title: imperative, and about what changed rather than the mechanics. Body:

```markdown
## What
The item, what it changes, and the end state after this pull request. Close with the changed-line
total.

## Why
Why this was worth a reviewer's time — what breaks, drifts or misleads if it stays as is. If the
item was not the top of the ranking, say what stood above it and why that was not eligible.

## Decisions this implements
The recorded decisions it is built on, and who decided them. Omit for an item that needed none.

## Behaviour impact
None, and why you are sure. Or: the exact observable difference, and the decision behind it.

## Verification
Commands run and their outcome. Benchmark before/after with the backend named and the noise
spread, if any performance claim is made.

## Judgement calls
Anything ambiguous decided without asking, and what was decided. Name any sibling pass you yielded
to, or whose landed change shrank this one.

## Next
What the following pass should pick up, and anything still awaiting a decision. Full detail is in
`potential-improvements.md`, updated in this pull request.
```

## 11. Triage-only mode

When invoked for status — *"what would the next pass pick"*, *"what is blocking this item"*,
`triage`, `status`, `dry-run` — run §1, §2 and §4 and **report only**.

**Change nothing at all**: no worktree, no branch, no push, no register edit, no pull request, no
questions. This is what makes the skill safe to run for a status check, so the prohibition is
absolute — if a triage run turns up something worth writing down, say so in the report and let the
user ask for a full pass.

## 12. Deciding alone

- **Is this a behaviour change?** If you cannot prove it is not, treat it as one: it needs a
  recorded decision (§6), or it goes back in the register.
- **Two defensible implementations?** Take the smaller diff.
- **A bug spotted in passing?** Do not fix it here — that is how a reviewable slice becomes an
  unreviewable one. Record it in the register and list it under *Next* in the pull request.
- **A pre-existing test failure?** Not yours. Note it, work around it, record it.
- **The item outgrows its estimate?** Cut it back to what you can finish and verify; the remainder
  goes back into the register as a new ranked entry.
- **A comment contradicts the code?** The code is the truth for behaviour; fix the comment. Never
  change code to match a comment.
- **An old entry contradicts what you see?** The code wins. Correct the entry, reasoning included.
- **A sibling pass holds your item?** It pushed first, so it keeps it (§3.1). Take the next
  eligible candidate; do not open a competing pull request on the same ground.
- **A sibling landed while you worked and your change is now partly redundant?** Rebase, keep only
  what is still a defect, and say in the pull request what its change already covered. A shrunken
  pull request is fine; one that re-applies what is already on `master` is not.

## 13. Final report

In chat, in this order:

1. **The item taken**, and why it beat everything above it in the ranking — including which higher
   entries were ineligible and what made them so.
2. **Decisions** — asked and answered, with the answers, or asked and still outstanding.
3. **What shipped** — the pull request URL, or plainly "no code, and why that was the right
   outcome". The changed-line total against the §7.1 ceiling.
4. **What was deferred**, one line of reason each, and what the next pass should pick up.
5. **What changed in the register** — new entries, the entry deleted as shipped, closures, areas
   swept.
6. **Verification** — the exact commands and their results, failures stated plainly, including
   anything skipped and why; which sibling passes were in flight and how you stayed clear of them;
   and whether you left a `git worktree` behind, with its path.

A small, verified, correctly-scoped pull request is the goal. A large one that "probably works" is
a failure. A pass that ships no code but leaves the register better than it found it — four
decisions recorded, an item decomposed — has done real work. A pass that guessed a design decision
and implemented it has done damage that is expensive to undo.

---

## Maintaining this skill

**One skill, one register, one ranking, and no item categories that gate behaviour.** §0's two
questions are asked of each change; that is the whole of what varies between passes. Splitting this
file by kind of work — or splitting the register's ranking — puts the decision back on a category,
which is what makes an agent ask a routine question or skip a consequential one. Equally, do not
collapse §6 away so that every item is decided by the agent.

Three things are deliberately absent, and should stay absent.

**Repo rules already written down elsewhere.** `CLAUDE.md` is auto-loaded and `CONTRIBUTING.md` is
one read away. A second copy here would drift, and the copy that drifts is the one an agent obeys.

**A ranked worklist.** The ranking lives in `potential-improvements.md`, which is edited as work
lands. Duplicating it here would produce two rankings and no way to tell which is current.

**Named files, patterns or suspected defects.** Any example anchors the pass on it, and every run
then rediscovers the same handful of things instead of looking with fresh eyes. Concrete findings
belong in the register — that file is evidence from an actual pass, and it carries the status and
history that keep a finding from being re-raised forever. This file is instructions.
