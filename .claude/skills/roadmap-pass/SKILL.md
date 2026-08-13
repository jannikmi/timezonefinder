---
name: roadmap-pass
description: "Advances the structural work tracked by roadmap issue #506 by one pass — select an eligible item, check its sequencing preconditions, put the maintainer's open design decisions to them as concrete choices, and only then implement one releasable slice, ending in a single pull request against master. State lives in the tracker (issues, branches, PRs) rather than a progress file, so passes are idempotent and can run concurrently. Use this whenever the user asks to work on the roadmap, advance or continue it, pick up the next roadmap item, run/repeat a roadmap pass, make progress on an issue from #506, or asks what the roadmap would do next or what is blocking an item — even if they never say the word 'skill'. For internal code quality with no structural change, use `code-quality-pass` instead."
---

# Roadmap pass

Advance the work tracked by **roadmap issue #506** on `jannikmi/timezonefinder` by **one pass**,
ending in at most one pull request opened against `master` for the repository owner to review.

The roadmap is a list of L-sized structural items — a batch API, a data format, a separate data
distribution. None of them is finished in one pass, and none of them has one obvious correct
design. Both facts shape everything below: §3 is how a pass gets the maintainer's decisions instead
of inventing them, and §6 is how it lands a slice that is complete on its own.

## 0. This skill asks questions. Its sibling does not. That is deliberate.

`.claude/skills/code-quality-pass/SKILL.md` runs to completion without stopping, and is right to:
an internal refactor with no behaviour change has an obvious correct answer, so a question there
would just be the agent declining to make a routine call.

**Roadmap items are the opposite.** Every one of them carries choices that belong to the
maintainer — whether the data package is a hard dependency, what a batch call returns, whether
precision reduction is on the table, which thresholds block an automated release. Those decisions
outlive the pass, are expensive to reverse, and several issues carry an explicit *open design
questions* section listing them. **A month-sized item built on a guessed design choice is worse
than one not started.**

So do not make this file consistent with its sibling by removing the question protocol. The two
skills differ here on purpose. What *does* transfer is the sibling's machinery — worktree
isolation, claim-by-push, the verification gate, the fixed PR body, the final report — and this
file references it rather than restating it.

## 1. Ground rules

`CLAUDE.md` is auto-loaded. Read `CONTRIBUTING.md` too — it is not auto-loaded and owns the
benchmarking, testing-scope and PR conventions. Both are authoritative; nothing here repeats them.

Read **#506 in full** (`gh issue view 506`) at the start of every pass, and the body of every issue
you are considering. #506 owns the ranking, the sequencing rules and the recorded decisions. Where
this file summarises #506 (§4, §5), **#506 is the authority and this file is a stale copy** — see
*Maintaining this skill*.

Four hard gates, above everything else:

- **Never merge a pull request, never enable auto-merge, never push to `master`, never tag.** Open
  the PR and stop.
- **Never regenerate the packaged timezone data as a side effect.** It rewrites ~64 MB into git
  history, and a weekly workflow (`check_data_updates.yml` → `release_data_update.yml`) already
  opens *and auto-merges* data-update PRs. Colliding with it is how an unrelated change ends up in
  a release. Regeneration happens only when an item's whole point is the data format, only under
  §5's `#458` rule, and only with the maintainer's explicit go-ahead in this session.
- **Every non-trivial change gets a `CHANGELOG.rst` entry**, including tooling and internal ones
  (`Internal:` sub-list). Amend the existing bullet for an item rather than appending a second one.
- **The working tree is shared** with other agent sessions and worktrees. Verify file state on disk
  before trusting it, stage explicit paths, never `git add -A`.

## 2. State lives in the tracker

There is no progress file, and do not create one. A hand-maintained parallel record drifts from
reality and then quietly misdirects every later pass. The source of truth is:

| Question | Answered by |
|---|---|
| what is still open | `gh issue list --state open` and `gh issue view <n>` |
| what is claimed | remote branches and open PRs (§4.1) |
| what has been decided | `gh issue view <n> --comments` (§3.2) and #506 §5 |
| what earlier passes did | the roadmap-pass log comment on #506 (§9) |

Everything a pass learns that a later pass needs must land in one of those places before the pass
ends. An answer that exists only in this chat session is lost.

**Consequence for concurrency and repetition:** running this skill twice in a row, or in two
sessions at once, must not duplicate work, PRs or issues. Every step below derives eligibility from
the four rows above, which is what makes that true — there is nothing else to keep in sync.

## 3. Surface the decisions before writing any code

### 3.1 Read first, then ask

**Before asking anything**, check that the answer is not already written down. A question the
repository already answers is the agent failing to read:

1. recorded decisions on the item's own issue (§3.2), and #506 §5;
2. the issue body — most name their own open questions and several already state the trade-offs;
3. `CLAUDE.md`, `CONTRIBUTING.md`, `docs/architecture.rst`, `docs/data_format.rst`.

Also do not ask about naming, formatting, file placement, test structure, or anything reversible in
five minutes. Make the call, state it in the PR, move on.

**The bar for asking: would two reasonable answers lead to materially different work?** If yes, ask.
If no, decide.

### 3.2 How to ask

Use structured multiple-choice questions — the alternatives are usually already named with their
trade-offs in the issue. **Lead with a recommendation.** A question presented without one hands the
work back to the maintainer instead of reducing it; state which option you would take and why in
one line, then let them override it.

Batch every blocking question for the item into as few rounds as possible. Ask the ones that block
*this* pass and the ones that would be expensive to reverse later; leave the rest for the pass that
reaches them.

Examples of the class, so the shape is unambiguous — these are illustrations, not a worklist:
#499 (what a batch call returns, and what happens to element 999,999 when it is invalid), #446
(data package hard-required or optional with a helpful error), #449 (pure varint vs int16-delta +
escape; whether precision reduction is on the table at all), #501 (which thresholds block an
automated release and what happens when one trips), #500 (which invariants, and whether validation
ever runs on construction).

### 3.3 Record every answer on the issue

An answer given in chat dies with the session, and the next pass would re-ask and might get a
different answer. **Post the answers as a comment on the item's own issue** — durable, public,
reviewable, and already on the source of truth this skill reads:

```markdown
<!-- roadmap-pass-decisions -->
## Recorded decisions (roadmap pass, YYYY-MM-DD)

| # | Question | Decision | Rationale |
|---|---|---|---|
| 1 | Return type of `timezone_at_many` | … | … |
```

Post it **before** implementing against it, so a crash mid-pass does not lose the decision. Extend
the existing comment on later passes rather than posting a second one. A recorded decision is
closed: do not re-litigate it. If new evidence contradicts one, that is itself a question for the
maintainer — say what changed and ask whether to revisit; never reverse it silently.

### 3.4 When the maintainer does not answer

**Do not guess and proceed.** Post the unanswered questions on the issue under the same marker,
headed `## Open questions awaiting a decision`, note the state in the log comment (§9), and end the
pass there. That pass delivered the questions; the next one starts by checking whether they were
answered.

## 4. Select an item

Rank the open issues by #506 §1 and §4, then walk the ranking and take the first item that is both
**unclaimed** (§4.1) and **eligible** (§5). Prefer resuming an item a previous pass started over
opening a new front — half-advanced items are the ones that go stale.

### 4.1 Claimed, resumable, or free

```
git fetch origin
git branch -r | grep -E 'origin/(roadmap/)?(497|499|446|449|...)[-/]'   # the numbers you are ranking
gh pr list --state open
gh issue view <n> --comments
```

Branch names are not uniform — this skill uses `roadmap/<issue>-<slug>`, GitHub's *create branch
from issue* button produces `<issue>-<slug>`, and earlier work used both. Match on the issue
number, not on a prefix.

- **An open PR references the item** → claimed and in review. Not eligible. Do not push to it and
  do not open a competing PR. Take the next item.
- **A remote branch exists with no open PR** → a previous pass started it. **Resume that branch**:
  check it out into a fresh worktree, rebase onto `origin/master`, read its commits and the issue's
  recorded decisions, and continue on it. One branch per item is what keeps the claim readable, so
  never open a second branch for the same issue.
- **Neither** → free. Claim it (§7) before you edit anything.

### 4.2 Nothing eligible

A legitimate outcome, but it must leave a durable trace or the next pass repeats the triage. Record
what you evaluated and why nothing was picked in the log comment on #506 (§9), and stop. No branch,
no PR.

## 5. Preconditions — refuse and say which one blocked

Copied from #506 §4 and §5, which are the authority. Check them explicitly and name the blocking
one in your report when you skip an item.

- **#497 (profiling) gates #499, #301 and the native-candidate-loop work under #364.** All three
  are justified by an assumption about where query time goes, and #477 already demonstrated one
  such assumption was wrong. Do not start any of them before #497 has landed results.
- **Any change that regenerates the packaged data must carry #458** (the shortcut-file format
  guard), deferred precisely until something else regenerates that data. Applies to #449, #301,
  #350, and to #477 if the shortcut file must be written sorted.
- **#446 sequences before #449.** Once the data is its own distribution, regeneration stops adding
  ~64 MB to this repository's history, which is what makes the rest of the data work cheap.
- **#505 (border proximity) is gated on publicly voiced user interest.** A demand-signal issue.
  Never implement it; only report whether interest has appeared.
- **Do not re-propose anything in #506 §5** — in particular the dropped raster fast-path index and
  the parked runtime-dependency-surface idea. They were considered and closed.

A precondition is unmet ⇒ the item is **not eligible this pass**. Not "eligible with a caveat", not
"eligible if I also do the prerequisite". Take the next item, or pick up the prerequisite itself if
it is free.

## 6. What one pass delivers

**One pass = one item, and at most one PR.** Four outcomes are all successes — say which one you
are aiming at, and do not manufacture code to make a pass feel productive:

1. **Decisions surfaced and recorded, no code.** *"These are the four decisions blocking #446, the
   trade-off in each, and my recommendation"* is a complete, valuable pass. It unblocks every
   later one.
2. **A design written up and sub-issues opened, no code.** The decomposition (§6.1) is the
   deliverable; the sub-issues are what make the item shippable in slices.
3. **One releasable slice implemented**, behind decisions already taken.
4. **Nothing eligible**, triage recorded (§4.2).

### 6.1 The releasable-slice rule

Roadmap items are month-sized, so the question that decides whether this skill helps or harms is:
*how does a pass deliver a reviewable slice without leaving the tree half-migrated?*

**The rule: a slice must leave `master` releasable on its own.** The test is concrete —

> Can the slice be described by one true sentence in `CHANGELOG.rst` that stands without promising
> a follow-up? If not, it is not a slice; it is half a change.

"Added `timezone_at_many`, returning zone ids" passes. "Migrated the reader to the new encoding,
writer to follow" fails: nothing can read the shipped data until the second half lands.

What that implies in practice:

- **Additive before subtractive.** Add the new path, keep the old one working, remove it in a later
  slice once the new one is proven. Both live at once and both are tested.
- **Decompose first, implement second.** When an item cannot be cut into releasable slices by
  inspection, that decomposition *is* this pass's deliverable (outcome 2): open sub-issues, link
  them from the parent, stop.
- **A genuinely atomic migration is not sliced — it is prototyped.** A binary format change cannot
  half-land. The pass's deliverable is then the prototype plus its measurements in `prototypes/`
  (as #497 specifies for itself: not shipped, not a benchmark, no CI, no committed figures), and
  the numbers posted to the issue. The migration lands later, in one piece, once the numbers have
  settled the design.
- **Keep the slice reviewable** — roughly ≤400 changed lines with a single story, as in the sibling
  skill. If it grows past that, cut it and leave the rest as a sub-issue.

### 6.2 Constraints on the work itself

- **Test scope follows the change**, per `CLAUDE.md`'s *Testing* section. Do not run the `slow`
  suites reflexively; do run the ones your change maps to. Remember the matrix: a local `uv run`
  binds Numba, so it never exercises the C extension.
- **Any performance claim goes through the `benchmarks/` harness**, per
  `docs/benchmarking_methodology.rst` and `CONTRIBUTING.md`, **and must name the acceleration
  backend it was measured on** (`scripts/assert_acceleration_path.py` pins it). A local Numba
  measurement does not describe what a plain `pip install timezonefinder` runs. Report the noise
  spread (`make benchmark-noise`) alongside any before/after pair — one pair of numbers cannot
  separate a regression from scheduler noise. **A pass that asserts a speedup without this is
  wrong**, however plausible the number.
- **Respect the ledger/roadmap boundary.** Structural work is the tracker's; internal quality is
  `potential-improvements.md`'s. Its scope note is the test: an entry belongs there only if it
  names code that exists *and* could be closed by editing that code. An internal-quality finding
  turned up in passing is **recorded in the ledger, not fixed inline** — fixing it inline is how a
  reviewable slice turns into an unreviewable one.

## 7. Isolate and claim

Mechanics as in `.claude/skills/code-quality-pass/SKILL.md` §2 and §2.1 — read them; they are not
repeated here. Two deltas:

- The branch is **`roadmap/<issue>-<slug>`** (`roadmap/446-data-distribution`), because the issue
  number is what §4.1 matches on.
- **Claim by pushing that branch the moment §4 selects the item** — before editing, and before
  asking the questions in §3, since a question round can take a while and an unclaimed item is
  fair game for a sibling pass the whole time. Pushing a branch that still points at `master` costs
  nothing and is instantly visible.

```
git worktree add ../tzf-roadmap-<issue> -b roadmap/<issue>-<slug> origin/master
git push -u origin roadmap/<issue>-<slug>
```

If a sibling claimed the item while you were reading, it wins — it pushed first. Take the next
item and say in your report which one you yielded.

## 8. Triage-only mode

When invoked for status — *"what would the next pass pick"*, *"what is blocking #449"*, `triage`,
`status`, `dry-run` — run §1, §2, §4 and §5 and **report only**.

**Change nothing at all**: no worktree, no branch, no push, no issue comment (including the log
comment), no PR, no questions. This is what makes the skill safe to run for a status check, so the
prohibition is absolute — if a triage run turns up something worth writing down, say so in the
report and let the user ask for a full pass.

## 9. Keep #506 current without hand-syncing it

#506's body is a ranking and a set of decisions, not a status board — the issue says itself it is
not a commitment. Closing a sub-issue is already the durable record that work landed, so **do not
rewrite the body for every slice.**

Edit the body (`gh issue edit 506 --body-file …`) only when a **sequencing fact** changed:

- a precondition is now satisfied (#497 landed ⇒ the gate over #499 / #301 / #364 opens);
- an item was closed, superseded or re-scoped, so its row or verdict is now wrong;
- a new decision belongs in §5, so it is never re-proposed.

Everything else goes in **one log comment on #506, edited in place** — the durable trace for every
pass, including the ones that shipped nothing:

```bash
# find it
gh api repos/jannikmi/timezonefinder/issues/506/comments \
  --jq '.[] | select(.body | startswith("<!-- roadmap-pass-log -->")) | .id'
# update it (create with `gh issue comment 506 --body-file` if absent)
gh api --method PATCH repos/jannikmi/timezonefinder/issues/comments/<id> -F body=@log.md
```

One row per pass: date · item · outcome · PR or "no code" · what the next pass should pick up.
**Editing one comment rather than appending is what keeps repeated passes idempotent** — ten
no-op passes leave one comment with ten short rows, not ten comments.

## 10. Gate before opening the PR

The sibling's §7 checklist applies unchanged — `git fetch && git rebase origin/master` **first**,
`make hook`, the test scope your change maps to, `make testall` as the final gate, a clean
`git diff origin/master --stat`, the changelog entry. Additionally:

- [ ] Decisions recorded on the issue (§3.3), and the implementation matches them.
- [ ] Preconditions (§5) re-checked after the rebase — a sibling may have landed one, or #506 may
      have moved.
- [ ] The slice passes §6.1's changelog sentence test.
- [ ] Benchmark evidence names its backend, if any performance claim is made.
- [ ] `git status --short timezonefinder/data` is **empty** unless data regeneration was the
      explicit, agreed subject of this pass.

If a gate fails and you cannot fix it, do not open the PR. Push the branch, record the state in the
log comment, and report what failed — the recorded decisions and the branch outlive the failure.

## 11. Open the PR

`gh` is authenticated as the repository owner, so the branch goes to `origin`, not a fork.

```
gh pr create --base master --title "<title>" --body "<body>"
```

Do not merge, do not enable auto-merge, do not add reviewers or labels. Reference the item as
`Refs #<issue>` — **not** `Closes`, unless the slice genuinely finishes the whole issue, which is
rare.

```markdown
## What
The item, the slice, and the end state after this PR.

## Decisions this implements
The recorded decisions it is built on, linked to the issue comment. Say who decided them.

## Why this slice
Why it is releasable on its own (§6.1), and what deliberately stayed out.

## Verification
Commands run and their outcome. Benchmark before/after with the backend named and the noise
spread, if any performance claim is made.

## Judgement calls
Anything ambiguous decided without asking, and what was decided.

## Next
What the following pass should pick up, and anything still awaiting a decision.
```

## 12. Final report

In chat, in this order:

1. **Item selected**, and why it beat the alternatives in the ranking.
2. **Precondition check** — which gates were tested, which passed, and the one that blocked
   anything skipped.
3. **Decisions** — asked and answered (with the answers), or asked and still outstanding.
4. **What shipped** — the PR URL, or plainly "no code, and why that was the right outcome".
5. **What was deferred**, one line of reason each; sub-issues opened, with numbers.
6. **What the next pass should pick up.**
7. Verification commands and results — failures stated plainly, including anything skipped and why;
   sibling branches in flight and how you stayed clear; and any `git worktree` left behind, with
   its path.

A small, verified, correctly-scoped slice is the goal. A pass that only records four decisions and
opens two sub-issues has done real work. A pass that guessed a design decision and implemented it
has done damage that is expensive to undo.

---

## Maintaining this skill

**The question protocol in §0 and §3 is the point of this skill, not an inconsistency with its
sibling.** Do not remove it to make the two files match.

**#506 is the authority for §4 and §5; this file holds a copy that will go stale.** The copy exists
because a pass has to know the gates before it has read anything, but #506 §1, §4 and §5 override
it whenever they disagree. Every pass re-reads #506 (§1) and therefore detects divergence for free:
a row that no longer exists, a precondition satisfied by work that has landed, a new decision in
§5. **When a pass finds a divergence it corrects this file** — in the PR it was opening anyway, or
in a skill-only PR if it had none. A stale precondition here is worse than a missing one: it blocks
eligible work or waves through work that should have been blocked, and it does so silently.

**Two things stay absent**, for the same reasons as in the sibling skill:

- *Repo rules written down elsewhere.* `CLAUDE.md` is auto-loaded and `CONTRIBUTING.md` is one read
  away. A second copy drifts, and the copy that drifts is the one an agent obeys.
- *A ranked worklist.* The ranking lives in #506, which is edited as work lands. Duplicating it
  here would produce two rankings and no way to tell which is current. The issue numbers in §3.2
  and §5 are illustrations of a *rule*, not the list of what to do next.
