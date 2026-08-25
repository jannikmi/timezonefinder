---
name: improvement-pass
description: "Advances timezonefinder by one improvement pass — read the ranked register in potential-improvements.md, re-verify and re-rank it, take the highest-ranked item that is eligible, implement one reviewable slice, and end in a single pull request against master plus an updated register. It runs unattended and asks nothing: a design choice that belongs to the maintainer is recorded as a briefed question and the item is left for a later pass, rather than stalling this one. One pass, one item, one pull request. Any improvement is in scope, whatever its area: correctness, performance, public API, data format, docs, packaging, release and CI, tests, developer tooling, internal structure. Use this whenever the user asks for an improvement, quality, cleanup, refactoring or roadmap pass, wants technical debt found or paid down, says improve the code quality or tidy up the codebase or find what is worth refactoring, asks to work on or continue the roadmap, wants the next item picked up, asks what improvements are still outstanding or what the next pass would do or what is blocking an item, or wants a pull request prepared for review — even if they never say the word skill."
---

# Improvement pass

Deliver **one improvement** to `timezonefinder` (offline timezone lookup by coordinates), ending in **one pull request** against `master` plus an updated register.
Not a theme, not a batch: the point of maintaining a ranking is that the top of it is what gets reviewed next.

`potential-improvements.md` at the repository root is the register — every finding, one ranking across all of them, the sequencing rules, the decisions already taken.
It is what turns one-off passes into cumulative progress, so reading it and writing it back is the deliverable, not bookkeeping.

## 0. What counts as an improvement

Anything that leaves the package better than you found it and that a reviewer can act on: a correctness defect, a slow path, an API that is awkward to call, a docs page that lies, a release step that can fail silently, a test that cannot fail, a name that misleads, a data encoding that wastes half its bytes.
**Whatever a pass discovers is welcome in the register**, whatever its area — §4 ranks it, §5 names the few things out of bounds.

Do not sort candidates into categories that then decide how the pass behaves.
Two questions do that, and both belong to the individual change:

- **Does it change observable behaviour?** Same results, same public API, same binary formats, same exception types for the same inputs — or not.
  If you cannot prove it does not, it does (§5).
- **Does it carry a choice that belongs to the maintainer?** One that outlives the pass and is expensive to reverse — what a batch call returns, whether a dependency is hard, which thresholds block a release.
  If so and the choice is not already on record, the item is **not eligible this pass**: record the question as §6 says and walk on down the ranking.
  If not, decide and proceed, since stopping to ask would be declining to make a routine call.

Ask both per item, not per category: a rename that looks like tidying can change an exception type, and a month-sized item whose design was settled two passes ago needs no question at all.

## 1. Ground rules

`CLAUDE.md` is auto-loaded; read `CONTRIBUTING.md` too, which is not, and which owns the benchmarking, testing-scope and PR conventions.
Both are authoritative and nothing here repeats them.

- **Never merge, never enable auto-merge, never push to `master`, never tag.** Open the pull request and stop.
- **Never put a question to the maintainer.** A pass runs unattended and ends without them, so a question asked mid-run reaches nobody and stalls the item behind it; §6 says what to do with one instead.
- **Regenerating the packaged data is allowed** when the item needs it — do not park an item for that reason alone. Say in the pull request which binaries changed and why, and check that `git status --short packages/timezonefinder-data/timezonefinder_data/data` lists only files the change should have moved.
  Two things to hold: it rewrites up to ~64 MB, so never regenerate incidentally; and the weekly data-update workflow opens *and auto-merges* its own pull requests, so rebase before the final gate and expect to redo it if that pipeline lands meanwhile.
- **The changelog entry is mandatory**, shaped as `CLAUDE.md` says; amend the item's existing bullet rather than appending a second.
- **The lookup fast path is not traded for elegance.** If the item touches it, `CONTRIBUTING.md`'s benchmarking section applies in full — before/after on one machine, the noise spread alongside, the acceleration backend named.
  Not clearly neutral or better ⇒ revert and record the measurement.

## 2. The register

A tracked file, committed as part of your pull request — that is how it reaches the next pass, through `master`.
It is public and the owner reads it, so write for a contributor who has never seen this skill.
The ranking, the sequencing and the decisions live there rather than on the issue tracker, because reasoning outside the repository goes stale silently: no check reads it and a reviewer never sees it in a diff.
An issue is still where one item is worked out in detail; an entry names it as a pointer.
Anything a pass learns that a later pass needs lands there before the pass ends — an answer that exists only in a chat session is lost.

**Reading it.** Entries are evidence, not gospel: the code has moved since they were written.

- Re-verify an entry against the current code before spending time on it, and re-locate it by content, not by a recorded line number.
- If it no longer describes reality: **already done** ⇒ delete it, row and all, and say so in the pull request; **wrong or a dead end** ⇒ keep it, marked `withdrawn` with one line of reason, and **move its ranking row into the `Closed` table**.
  Same for anything you reject or rule out of scope. The entry stays because the argument against it is what stops the next pass re-proposing it; the *row* goes, because the ranking orders work and a closed item has none.
  Leave `blocked`, `parked` and `conditional` rows in the ranking - they can become live without the entry changing. `tests/test_improvement_ledger.py` checks the placement both ways.
- **Check every issue the register names before you rank** — a `GH-<n>` whose issue closed either shipped or was dropped, and both mean the entry is resolved:
  ```
  grep -o 'GH-[0-9]*' potential-improvements.md | sort -u | cut -d- -f2 |
    xargs -I{} gh issue view {} --json number,state --jq '"\(.number) \(.state)"'
  ```
- **Correct the reasoning, not just the status.** An entry whose conclusion survived on a premise since disproved reads as settled and sends the next pass down a path already ruled out.
- Rejected, out-of-scope and withdrawn entries are **closed**; so are recorded decisions.
  Do not re-litigate one or re-add it under a new name.
  New evidence against a decision is itself a question for the maintainer (§6) — never reverse one silently.
- Spend fresh discovery on areas the coverage log shows no coverage of, and record what you swept.

**Writing it.** Every candidate goes in, including the ones you will not implement, the ones you reject, and the ones waiting on a decision.
One entry per finding: a stable id and one-line title; location by file plus a code anchor, or the issue it tracks; the defect; the fix and a rough size; what breaks or drifts if it stays; a status; and the pass that last touched it, dated.

- **It is a to-do list, not a history.** An entry whose work landed is **deleted with its ranking row, in the pull request that ships it** — the code is the evidence and `git log` still has the text.
  Left in, it reads exactly like an open one and the next pass pays full price to rediscover there is nothing to do.
  `tests/test_improvement_ledger.py` rejects any status meaning done, and asserts every entry has exactly one ranking row and vice versa.
- **Write so a sibling pass's edits merge beside yours:** append new entries at the end of their section, never renumber an id, and leave entries you did not act on alone — reflowing a paragraph you did not change turns a clean merge into a conflict for no gain.
- Keep it terse and scannable.
  Commit it separately from the code change, so a reviewer can read the change without register churn in the way; it needs no changelog bullet of its own.

## 3. Isolate and claim

Stay clear of two things: the maintainer's uncommitted work, and any pass already running.
The checkout may hold unrelated work and untracked scratch material, and **none of it may reach your pull request** — stage paths explicitly, never `git add -A`.

**Survey first**, because the remote branch list is the whole coordination mechanism — there is no lock:

```
git fetch origin
git branch -r --list 'origin/improve/*'
gh pr list --state open
```

Branch names are not uniform (`improve/*` here, `quality/*` and `roadmap/*` from earlier passes, `<issue>-<slug>` from GitHub's button), so match on the item and its issue number, not on a prefix.
`git log origin/master..origin/<branch> --stat` shows the ground a branch has taken.

Then work in a worktree of your own — never `git checkout -b`, since the checkout may sit on a concurrent session's branch:

```
git worktree add ../tzf-<slug> -b improve/<slug> origin/master
```

Both names must be unique to this pass, and the slug should name the ground (`improve/499-batch-api`, not `improve/pass-4`).
Install into it, then record a baseline **before editing**: `make test` and `make hook` on the untouched branch.
Anything already failing is pre-existing — note it, do not fix it here.
`make hook` runs pre-commit over all files, so stage only what belongs to your change and `git checkout --` the rest.

**Claim the moment §4 picks your item**, before editing anything:

```
git push -u origin improve/<slug>
```

A branch still pointing at `master` costs nothing and is instantly visible; a pass that pushes only at the end has claimed nothing.
If a sibling's branch already covers your item, it wins — take the next eligible candidate rather than racing it, and say in your pull request which item you yielded.

Expected conflicts, which are not mistakes: `CHANGELOG.rst`, where every pass appends to the same `Internal:` list — **keep both bullets**, never drop a sibling's.
In the register, usually one entry both passes re-verified: take the later, more specific note, and merge ranking rows rather than taking one side.
Source-file conflicts should not happen if you honoured the claim; if one does, read the sibling's change before resolving — it may already have fixed what you were about to.
Rebase and re-run the gate (§9) whenever a sibling lands ahead of you.

## 4. Triage and select

Read first, write second: merge the register's still-valid entries with what this pass turns up, re-rank, then **walk the ranking from the top and take the first eligible item**.
Let discovery come from reading the code rather than grepping for a defect you decided on in advance; `git log -S` on a suspicious construct tells you whether it is load-bearing or leftover.

Rank by **expected value** — defects that will cause a real bug later > work that unblocks other work > duplication that will drift > readability.
Size breaks ties only: a pass that takes the cheap item because it is cheap ships the least important thing in the repository.
An item sits **below its own blocker**, since the ranking is walked top-down.

**A performance item is ranked on a measured share, never on an intuition about what looks slow.**
`prototypes/query_stage_profile.py` attributes a `timezone_at` query to its stages; the register's *The measured baseline* carries the denominators, the commit they were taken at, the freshness check, and how far those figures travel off the machine that took them.
Follow it: benefit is the **ceiling** a change removes, stated as a count before a time and as a workload share rather than a stratum share; cost is size plus decisions plus whether it forces a data-format change.
A ceiling under the machine's own run-to-run noise cannot be shown by the benchmark suite — rank that item on correctness or simplicity and say so, rather than selling it as a speed-up.
Unmeasured is not a third case: the item *is* a measurement, one profiler run.

An item is **eligible** when all of these hold:

- **Unclaimed** (§3) — an open pull request or live branch means it is taken.
  A branch with no pull request means a previous pass started it: **resume that branch**.
- **Its preconditions are met**, checked explicitly against the register's sequencing rules.
  Unmet ⇒ not eligible this pass; take the next item, or the prerequisite itself if it is free.
- **Its maintainer-owned decisions are already recorded** (§6).
  Not recorded means not eligible: record the question and move down the ranking, which is what stops one blocked item stalling every pass behind it.
  Do not wait for an answer, and do not supply your own.
- **It fits one reviewable pull request**, or can be sliced into one (§7); if neither, the decomposition is the deliverable.

Prefer resuming an item a previous pass started — half-advanced items are the ones that go stale.
Re-rank and re-verify *before* picking: an entry's premise goes stale faster than its location.

## 5. Scope

**In scope: any change a reviewer can act on** — library code, scripts, tests, docs, packaging, workflows, tooling.
What may be improved is deliberately not enumerated: an enumeration reads as exhaustive, and then a real defect goes unrecorded for fitting no heading.

Out of bounds for every pass — the repository docs describe some of these neutrally because they cannot know your boundary, so treat them as prohibitions here:

- Editing the packaged data or the generated bindings *by hand*. Regenerating them through their generators is in scope, and so is the `DATA_FORMAT_VERSION` bump that follows — see §7 on why an unreleased bump costs nothing extra.
- Dependency, lockfile or Python-version changes, and the `timezonefinder` release version. The *data* distribution's version is not a release version in this sense: it tracks the format and the upstream dataset, and a format change is obliged to move it.
- Whole-file reformatting or "modernisation" for style alone — churn a reviewer cannot tie to a defect.
- `prototypes/` — **except** the `FINDINGS` block of `prototypes/query_stage_profile.py`, which the pass that invalidates it updates (§9).
- A behaviour change with no recorded decision behind it (§6), and an item whose design is already decided being implemented as anything other than **exactly what its decisions say**.

## 6. Decisions that belong to the maintainer

**A pass never asks one.**
It records the question, leaves the item, and takes the next eligible one.
`.claude/skills/maintainer-decisions/SKILL.md` is where the accumulated questions are put to the maintainer — briefed, discussed and settled one at a time, in a session they invoked and are present for.

Two things follow from a pass running unattended, and they are the whole reason the asking lives elsewhere.
A question asked mid-run reaches nobody, so the item stalls and every item behind it waits with it.
And an answer given in a chat session and used in that same session is never written down: the pass that finally implements the item cannot read it, so it either re-asks and gets a different answer or guesses.
Recording the question costs one bullet, and is the only form in which an answer reaches the code.

**Read before you record.**
A question the repository already answers is the agent failing to read: the register's recorded decisions, the entry and its issue body, `CLAUDE.md`, `CONTRIBUTING.md`, `docs/architecture.rst`, `docs/data_format.rst`.
Never record one about naming, formatting, file placement, test structure, or anything reversible in five minutes — decide it, state it in the pull request, move on.

> **The bar: would two reasonable answers lead to materially different work, and is the choice expensive to reverse?**

Both halves, or it is yours to make.
Recording a question that fails the bar is not caution: it hands routine work back to the maintainer and buries the questions that do matter among ones that never needed asking.

**Recording one.**
An entry that is waiting is marked in two places, and `tests/test_improvement_ledger.py` fails if they disagree:

- its `Status` opens with `needs`, and
- it carries exactly one `**Decision needed:**` bullet — the question, what turns on it, the options with their trade-offs, and **your recommendation with the reasoning that picks it out from the others**.

Its row in the ranking says the same in the eligibility column, so a pass walking the ranking sees it without opening the entry.

Write the recommendation even though you are not the one asking, and especially when you found the choice close.
You have just read the code the question is about, and that reading is what goes stale first — the skill that asks will re-verify it, but it should be checking your reasoning rather than starting without any.
A brief with no recommendation hands over the whole problem instead of the last step of it.

**A recorded decision is binding.**
Implement exactly what it says, and never reverse one silently.
New evidence against a decision is itself a question for the maintainer — record it as one, leading with what changed.

## 7. What one pass delivers

Four outcomes are all successes — say which you are aiming at, and do not manufacture code to make a pass feel productive:

1. **One item implemented** — the ordinary case.
2. **Questions surfaced and briefed, no code** — *"these are the four decisions blocking this item, the trade-off in each, and my recommendation"*, written into the register where the sibling skill that asks them will find them.
   That unblocks every later pass, and is a success rather than a pass that failed to produce code.
3. **A design written up and the item decomposed, no code**, when it cannot be cut into releasable slices by inspection.
4. **Nothing eligible**, triage recorded.

Outcomes 2–4 still open a **register-only pull request**: the findings are the deliverable, and losing them is worse than shipping no code.
A cosmetic pull request invented to justify a pass is not worth the owner's review time.

**The releasable-slice rule: a slice must leave `master` releasable on its own.**

> Can it be described by one true sentence in `CHANGELOG.rst` that stands without promising a follow-up?

"Added `timezone_at_many`, returning zone ids" passes; "migrated the reader to the new encoding, writer to follow" fails — nothing can read the shipped data until the second half lands.
In practice:

- **Additive before subtractive**: add the new path, keep the old one working and tested, remove it in a later slice.
- **Decompose first, implement second** (outcome 3), recording the slices as ranked entries.
- **A genuinely atomic migration is prototyped, not sliced** — a binary format change cannot half-land, so the deliverable is a prototype and its measurements under `prototypes/`, with the numbers in the entry.
- **An unreleased `DATA_FORMAT_VERSION` bump is free to reuse, so format changes want to be consecutive.** The version numbers a *release*, not a change: while a bump is sitting unreleased on `master`, the next format change that lands rides the same number at no extra cost, and the two-distribution ordered release is paid once for both. So the moment one format change lands, every other format change is temporarily cheaper than the ranking says — take them one after another and let them go out together, rather than spacing them across releases and paying the ordered release each time. State in the pull request whether a bump is already pending, so a reviewer can see which release the change is joining.
- **One story per slice, and no line count.** A slice is the right size when it carries one story, passes the sentence test, and can be reviewed in one sitting — never because it came in under a threshold.
  A number decides nothing a reviewer cares about, and invites both padding up to it and cutting an item mid-thought to stay beneath it.
  If an item outgrows what you can finish and verify, cut it back and put the remainder in the register as a new ranked entry.

## 8. Working loop

1. **Re-verify** the item against the current code (§2).
   Already done or wrong ⇒ resolve the entry and go back to §4 without spending a commit on it.
2. **Confirm every decision it needs is already on record** (§6), and build exactly what those decisions say.
   A missing one means the item was never eligible — record the question and go back to §4.
3. **Implement it, and only it.** Test scope follows `CLAUDE.md`'s *Testing* section — do not run the `slow` suites reflexively, do run the ones your change maps to.
   A change with no test exercising the new seam is not finished.
4. **Commit the code**, message naming the entry id.
5. **Delete the entry and its ranking row** in a commit of their own — or, if the slice left a remainder, rewrite the entry to describe only what is left, keeping its id and row.
   If the slice ended in a rejection rather than a shipped change, the entry stays and its row moves to `Closed` instead (§5).
6. **Push** (§3), then go to the gate.

## 9. Gate before opening the pull request

All of these, with output you have actually read:

- [ ] `git fetch origin && git rebase origin/master` **first** — a rebase after the gate invalidates it.
      Start the list again if the rebase moved your base, and re-check preconditions a sibling may have satisfied or invalidated.
- [ ] `make hook` clean, modulo the pre-existing failures recorded in §3.
- [ ] `make test` green, plus whichever `slow` / `integration` suites your change maps to, plus `make testall` once as a final gate.
- [ ] Benchmark evidence naming its backend, if the fast path was touched or any performance claim is made.
- [ ] If anything under `timezonefinder/` or the packaged data moved: the register's freshness check run, and **either** the profiler re-run on both backends with `FINDINGS`, the baseline anchor and every share it moved updated here, **or** one line in the register classifying the change as inert for timings.
      A stale share does not announce itself — the next pass ranks on it.
- [ ] The slice passes §7's changelog sentence test, and `CHANGELOG.rst` carries its entry.
- [ ] `git status --short packages/timezonefinder-data/timezonefinder_data/data` lists **only** binaries this item had to move — empty if it regenerated nothing. A file the change had no reason to touch means the generator was run wider than intended.
- [ ] If a per-file layout version moved: `DATA_FORMAT_VERSION` moved with it, and the pull request says whether an unreleased bump is already pending, so the two stack into one rather than reading as two.
- [ ] `git diff origin/master --stat` shows only files you intended to touch, with `potential-improvements.md` among them.
- [ ] The register is committed: findings recorded, decisions recorded, coverage noted, and the shipped entry **deleted with its ranking row** — grep its id in the diff and confirm nothing survives.

If a gate fails and you cannot fix it, do not open the pull request: report what failed and stop.
Still commit the register and push the branch, and name it in your report — the findings outlive the failed change, and an unpushed branch loses them.

## 10. Open the pull request

`gh` is authenticated as the repository owner, so the branch goes to `origin`, not a fork.
The branch is already pushed (§3), so this is a second push and the pull request:

```
git push origin improve/<slug>
gh pr create --base master --title "<title>" --body "<body>"
```

Do not merge, enable auto-merge, add reviewers or labels, push to `master`, or tag.
Reference an issue as `Refs #<issue>` — **not** `Closes`, unless the slice genuinely finishes the whole issue.
Title: imperative, about what changed rather than the mechanics.
Body:

```markdown
## What
The item, what it changes, and the end state after this pull request.

## Why
What breaks, drifts or misleads if it stays as is. If the item was not the top of the ranking,
say what stood above it and why that was not eligible.

## Decisions this implements
The recorded decisions it is built on, and who decided them. Omit if it needed none.

## Behaviour impact
None, and why you are sure. Or: the exact observable difference, and the decision behind it.

## Verification
Commands run and their outcome. Benchmark before/after with the backend named and the noise
spread, if any performance claim is made.

## Judgement calls
Anything ambiguous decided without asking. Name any sibling pass you yielded to, or whose landed
change shrank this one.

## Next
What the following pass should pick up, and anything still awaiting a decision.
```

## 11. Triage-only mode

When invoked for status — *"what would the next pass pick"*, *"what is blocking this item"*, `triage`, `status`, `dry-run` — run §1, §2 and §4 and **report only**.
**Change nothing**: no worktree, no branch, no push, no register edit, no pull request.
That absolute prohibition is what makes the skill safe to run for a status check; if a triage run turns up something worth writing down, say so and let the user ask for a full pass.

## 12. Deciding alone

- **Two defensible implementations?** Take the smaller diff.
- **A bug spotted in passing?** Do not fix it here — record it, and list it under *Next*.
- **A pre-existing test failure?** Not yours: note it, work around it, record it.
- **A comment contradicts the code?** The code is the truth for behaviour; fix the comment, never the reverse.
- **An old entry contradicts what you see?** The code wins — correct the entry, reasoning included.
- **A sibling landed while you worked and your change is now partly redundant?** Rebase and keep only what is still a defect, saying what their change already covered.
  A shrunken pull request is fine; one that re-applies what is on `master` is not.

## 13. Final report

In chat, in this order: **the item taken** and why it beat everything above it, including which higher entries were ineligible;
**decisions** — the recorded ones this built on, and any question it recorded instead of taking an item, naming `maintainer-decisions` as how those get answered;
**what shipped** — the pull request URL, or plainly "no code, and why that was the right outcome" — with §7's one sentence;
**what was deferred**, one line of reason each;
**what changed in the register**;
and **verification** — exact commands and results, failures stated plainly, anything skipped and why, which sibling passes were in flight, and whether you left a worktree behind, with its path.

A small, verified, correctly-scoped pull request is the goal; a large one that "probably works" is a failure.
A pass that ships no code but leaves the register better than it found it has done real work.
A pass that guessed a design decision and implemented it has done damage that is expensive to undo.

---

## Maintaining this skill

**One skill, one register, one ranking, and no item categories that gate behaviour.**
§0's two questions are asked of each change; that is the whole of what varies between passes.
Splitting this file by kind of work — or splitting the ranking — puts the decision back on a category, which is what makes an agent ask a routine question or skip a consequential one.
**Autonomy, and where it stops.** §6 used to put its questions to the maintainer mid-pass, and a pass could wait for the answer.
That stop is gone — a pass now runs start to finish without one, and `.claude/skills/maintainer-decisions/SKILL.md` asks the accumulated questions in a session the maintainer themselves invoked.
It went not because the questions stopped mattering: collapsing §6 away so that every item is decided by the agent is the opposite failure and the more expensive one, and it must not happen either.
It went because a pass runs unattended, so the question reached nobody, the item stalled behind it, and an answer given in chat and consumed in the same session was never written down anywhere a later pass could read it.
Do not restore it.
If a wrong design is ever implemented, the fix is a sharper bar in §6 and a better brief, not a stop in a run that has no audience.

Three things are deliberately absent and should stay absent: **repo rules written down elsewhere**, since the copy that drifts is the one an agent obeys;
**a ranked worklist**, which would give two rankings and no way to tell which is current;
and **named files, patterns or suspected defects**, since any example anchors every future pass on it.
Concrete findings belong in the register — that file is evidence, this one is instructions.
