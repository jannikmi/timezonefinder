---
name: maintainer-decisions
description: "Puts the design decisions that are blocking `timezonefinder`'s improvement register to the maintainer, one round at a time — find every entry waiting on a decision, re-verify each against the current code, prepare a brief per question (what turns on it, the options, what each one costs, a recommendation and the justification for it), then take the questions one at a time: present the brief, discuss it for as long as the maintainer wants to, answering from the code and pricing any option they raise, and only then settle it as structured multiple choice, recording each answer in `potential-improvements.md` as a decision with its rationale and the options it refused before the next question goes up. Ends in a register-only pull request, and never implements what it asks about. Use this whenever the user asks what decisions you need from them, wants the open questions or blocked items decided, asks to unblock the register or the roadmap, says ask me what you need to know or bring me the decisions or let us talk through or settle the open design questions, wants to discuss a specific open question or a recommendation on one, or asks why an item is waiting — even if they never say the word skill."
---

# Maintainer decisions

Turn the questions blocking `timezonefinder`'s improvement register into **recorded decisions**, in one round, ending in a register-only pull request against `master`.

`potential-improvements.md` at the repository root is the register.
It holds the ranking, the sequencing rules and the decisions already taken — including the options that were refused, which is most of their value.

## 0. What this skill is for, and why it is separate

`.claude/skills/improvement-pass/SKILL.md` runs start to finish without asking anything.
That is deliberate: a pass runs unattended, and a pass that blocks on a question nobody is present to answer has converted an autonomous run into a stalled one.
So when a pass meets a choice that is genuinely the maintainer's, it does not ask — it writes the question into the entry and takes the next eligible item.

The questions therefore accumulate, and this skill is where they are spent.
It is invoked by the maintainer, so the maintainer is present by construction; the asking is the whole job rather than an interruption to some other job.
That presence is also what makes §5 a conversation rather than a form: there is somebody there to argue with, and a decision that survives being argued with is worth more than one that was merely selected.

Which gives each skill one thing it must not do:

- **A pass never asks.** It records the question and moves on.
- **This skill never implements.** It ends with decisions recorded and pushed, and the next pass builds against them.
  Answering a question and immediately writing the code puts an unreviewed design and its implementation in one diff, and there is nobody left to catch the design.

The split also fixes what neither half could fix alone: an answer given in a chat session and used there is lost the moment the session ends.
Here the answer is written to a tracked file and pushed *before* anything is built on it.

## 1. Hard gates

`CLAUDE.md` is auto-loaded; read `CONTRIBUTING.md` too, which is not.
Both are authoritative and nothing here repeats them.

- **Never implement, and never start.** No source file changes in this run — the register is the only file this skill edits.
- **Never treat silence, a shrug or "you decide" as an answer to a question that reached the bar in §4.**
  If it is genuinely the maintainer's and they did not make it, it stays open — record the brief (§7) and say so.
  A question they hand back is a different case: it did not belong to them, so decide it, say what you decided, and record why it was demoted.
- **The discussion changes the brief; it never sells it.** Pushback is evidence, not an objection to be handled — re-check it against the code and rewrite the recommendation if it moved.
  An agent that argues its way back to the option it opened with has run a form with extra steps.
- **Never re-open a recorded decision** to see whether the maintainer still means it.
  New *evidence* against one is a question worth asking, and then the brief leads with what changed; nothing else is.
- **Never ask what the repository already answers** (§4). That is not caution, it is the agent failing to read.
- **Never merge, never enable auto-merge, never push to `master`, never tag.**
- **The working tree is shared** with other agent sessions and may hold unrelated edits. Verify state on disk, stage explicit paths, never `git add -A`.

## 2. Set up, then find the questions

Cut the branch before anything else, in a worktree of your own — never `git checkout -b` in the shared checkout.
§6 records each answer as it is given rather than batching them at the end, so there has to be somewhere to write from the first decision on:

```bash
git fetch origin
git worktree add ../tzf-decisions-<slug> -b decisions/<slug> origin/master
```

Fetching first is not bookkeeping.
§4 re-verifies every question against the current code, and a question already answered by a merge you have not pulled is the one kind of question this skill must never ask.

The register is the queue, and an entry waiting on a decision is marked in two places that must agree — its `Status` opens with `needs`, and it carries exactly one `**Decision needed:**` bullet stating the question.
`tests/test_improvement_ledger.py` enforces the pairing, so neither can rot alone:

```bash
grep -n '\*\*Decision needed:\*\*' potential-improvements.md
grep -n '^- \*\*Status:\*\* needs' potential-improvements.md
```

Read the ranking table alongside them: an entry's row says where it sits and what else waits behind it, and that is what §3 ranks on.

Two other sources count as questions even though they carry no marker:

- **The invocation itself.** "Should the batch API take an array or an iterable?" is a question whether or not the register holds it. Take it, and record the answer in the register like any other.
- **A recorded decision whose premise has since been disproved.** Rare, and the one legitimate way a settled question comes back. The brief has to open with the new evidence, not with the question.

If nothing is waiting, say so and stop.
Manufacturing a question to justify the round spends the one thing this skill exists to conserve.

## 3. Which questions this round takes

**Rank by what the answer releases**, not by how interesting it is: an answer that unblocks the top of the ranking, or several entries at once, beats one that unblocks a single low-ranked item.
An entry whose *other* preconditions are unmet is worth little now — its answer would sit unused while it waits on a blocker.

**Take at most four.** Four briefed decisions with their evidence is a sitting's worth of attention, and a round of nine gets skimmed, which is worse than not asking.
Nothing technical binds the number — §5 asks one question per dialog, so the four-per-call limit no longer applies — it is simply the point at which a round stops being read.
If more than four are waiting, take the four with the highest release and leave the rest — they keep.

**Four is a ceiling, not a quota.** The round ends when the maintainer's attention does, on whichever question that lands.
Everything settled by then is already recorded and pushed, and everything unsettled keeps its brief (§7), so a round that settles two of four has done its job rather than half of it.

Then drop, before writing any brief, whatever fails §4's bar.

## 4. Prepare the brief

This is the work. The asking is a formality once the brief is right.

**Read before you write.** A question the repository already answers must not reach the maintainer: the register's *Recorded decisions*, the entry itself and the issue it names, `CLAUDE.md`, `CONTRIBUTING.md`, `docs/architecture.rst`, `docs/data_format.rst`.
Then apply the bar, both halves:

> **Would two reasonable answers lead to materially different work, and is the choice expensive to reverse?**

Naming, formatting, file placement, test structure, which of two equivalent implementations to write — all fail it.
Decide those and say so.
What passes: what a public function returns, whether a dependency becomes hard, what a threshold blocks, which of two binary layouts ships, whether a feature is wanted at all.

**Re-verify the question against the current code before pricing it.**
The pass that recorded it may be several merges old, and an entry's premise goes stale faster than its location.
Three outcomes and only one of them is a question: the code has moved and the question is *answered* — record that and drop it; the code has moved and the question is *different* — rewrite it; the question stands — price it.

**Measure rather than speculate where a measurement is one command.**
A performance question priced by intuition is exactly the failure the register's *The measured baseline* exists to prevent, and a maintainer cannot correct a number they were never shown.
If pricing it properly needs a prototype rather than a command, that is not this round's work: say the option is unpriced and let the recommendation account for the uncertainty.

Each brief carries all of this, in this order:

```markdown
### <entry id> — <the question in one line>

**What is blocked:** which entries wait on this, and where they sit in the ranking.

**Context:** what a reader needs to answer it, and no more. State it fresh — do not
send them to the issue to find out what is being asked.

**Options:** two to four. A bold label each, then what it **costs**, what it **buys** and what
it **forecloses**, one line apiece — so the options can be compared down the column instead of
read as three paragraphs. Include the option of not doing the thing at all whenever that is real.

**Recommendation:** one option, named, with the reasoning that picks it out from the
others — not its merits in isolation. Say what would change your mind.

**Reversibility:** what it costs to undo if it turns out wrong — a later refactor, a
major version, a rewritten 63 MB binary, or nothing.

**Confidence, and what is unpriced:** where the evidence is thin, and what nobody has measured.
End on the one thing you would most like challenged: §5 opens the discussion from it.
```

**A recommendation is mandatory in every brief**, including the ones you find close.
A question presented without one hands the work back instead of reducing it, and "both are defensible" is not a finding — it is the moment to say which you would take and why the other one loses.
Where the options are genuinely balanced, that *is* the recommendation: say the choice is close, name the tiebreaker you used, and note that the cost of being wrong is low.

Form the recommendation now, from what you just verified.
If the entry already records one, treat it as evidence and check it — it was formed against older code and may be arguing from a premise that has moved.

**Write it to be read in a terminal**, since that is where it will be: bold labels rather than long prose, no nesting past one level, no tables wide enough to wrap.
A brief that runs past a couple of screens has stopped being a brief — either the question is really two questions, or the evidence has not been reduced yet — and what gets skimmed is exactly the part you most needed read.

## 5. Present, discuss, then settle — one question at a time

The maintainer is at the keyboard, which is this skill's whole premise, so use them: **a decision is settled in conversation, not collected in a form.**
A single dialog carrying the whole round asks for four answers at once from someone who has just read four briefs at once, and it leaves nowhere to push back before the answer is final.

### Open with the round, not with a brief

Post one compact overview before any evidence — a line per question: the entry id, the question, what it unblocks, and the option you will recommend.

That is a menu, not a decision.
It lets the maintainer reorder the round, drop a question they consider settled, or add one of their own, all of which cost far less now than after four briefs have gone up.

### Then take them one at a time

For each question, in whatever order the overview settled on:

1. **Post the brief in full** (§4), in chat. It does not go in the dialog — the dialog holds a short label and a sentence per option, and the evidence must not be compressed into that.
2. **Say what you would most like pushed on**, from the brief's last line. "The failure mode I cannot price is X" opens a useful reply; "let me know what you think" opens nothing.
3. **Discuss it for as long as they want to.** This is not a detour on the way to the decision. It is where the decision is made.
4. **Settle it** (below), then **record it** (§6) before the next brief goes up.

### What the discussion is for

- **Answer from the code, not from the brief.** A challenged premise gets re-checked against the tree in the moment — the file, a `grep`, the test — and the answer is whatever the check said, including when it costs you the recommendation.
- **Measure what one command can measure**, on §4's rule. A number asked for and estimated out loud is worse than one not asked for: it enters the decision with the authority of a measurement and none of the evidence. If it genuinely needs a prototype, say that instead.
- **An option the maintainer raises is a real option.** Price it on the same three axes as the others and put it in the dialog. Talking it down without pricing it is how a brief's framing quietly decides a question the maintainer believed they were deciding.
- **Update the recommendation when the discussion moves it, and say that it moved.** Which option you now hold, and what moved you, is the single most useful thing you can say in the conversation.
- **Disagreement is worth one plain statement, then their call.** If their reasoning has a hole you can name, name it once — that is what they invoked an agent that has read the code for. Repeating it is not diligence; nor is silently recording a decision you believe is wrong, then hedging it in the register's rationale (§6 records what they decided, not what you would have preferred).
- **Do not re-brief.** Once the discussion has produced the answer, go straight to the dialog with the options as discussed.

### Settling

One `AskUserQuestion` call carrying **that question alone**, at the point the discussion has converged:

- Options **mutually exclusive**, exhaustive enough that the answer is actionable, and reflecting the discussion rather than the brief wherever the two now differ.
- **The recommended option goes first and is labelled `(Recommended)`** — the one you hold now, not the one you opened with.
- Offer a real "leave it open for now" option where deferring is legitimate; otherwise the dialog forces a decision that §7 handles better.

Two shortcuts, both of which respect the maintainer's time better than the ritual does:

- **An answer given in chat is an answer.** Read it back in one line to confirm the reading, record it, and skip the dialog. Making somebody re-enter a decision they have just stated is friction dressed as rigour.
- **A brief answered immediately gets no manufactured discussion.** The conversation is offered, not imposed.

### Each answer changes what is left

Before the next brief goes up, check the remaining questions against the decision that just landed.
One of them may now be answered outright, or have become a different question — say so and re-brief it, rather than presenting the version you wrote before.

## 6. Record the answer

**As each one is given, before the next brief goes up**, and pushed.
An answer that exists only in this session is the failure mode this skill was built to remove, and a round interrupted after its third discussion should lose the fourth question and nothing else.

For each answered question:

- **Rewrite the entry.** Delete the `**Decision needed:**` bullet, replace it with what was decided and why, and open the `Status` line with `open` (the register documents the vocabulary; `needs` no longer applies).
- **Update the entry's row in the ranking** so its eligibility column stops advertising a question that has been answered.
  **If the answer was “no”, the row moves to the `Closed` table instead** - a rejected or withdrawn entry keeps its entry and loses its rank, since the ranking orders work and there is none left to order.
  An eligibility column reading `rejected` in the live table is the failure this prevents: the item is dead and every later pass still reads its row before finding out.
  `tests/test_improvement_ledger.py` checks the placement, so a miss fails the gate below rather than reaching `master`.
- **Record the options that were refused, and why.** They are what stops the next pass re-proposing them on their merits, and they are never deleted.
  An option the *discussion* produced and rejected counts: it was not in the brief, so nothing else records that it was considered.
- **A decision with consequences beyond its own entry goes in *Recorded decisions*** as well, dated, with one line of rationale. That section is never deleted either.
- **Say who decided it.** A decision recorded without an owner reads like one an agent made up, and the next pass cannot tell whether it may be revisited.

Write what was decided and why — not the round it happened in, nor the options in the order they were presented.
The register is read by contributors who have never seen this skill.

```bash
git add potential-improvements.md
git commit -m "Record the decision on <id>: <what was decided>"
git push -u origin decisions/<slug>   # -u on the first push, plain `git push` after
```

One commit per decision, so a reviewer can read the round as it happened and see which entry each discussion produced.

## 7. What the unanswered questions get

**The brief, written into the entry.** This is the half that pays even when nothing is answered.

Keep the `needs` status and the `**Decision needed:**` bullet, and expand the bullet to carry the question, the options, the recommendation and its justification.
The next round then starts from a brief instead of re-deriving one, and a pass that reads the entry can at least see what it is waiting for.

Where a discussion happened but produced no decision, the brief is written **as the discussion left it** — the options it added, the premises it disproved, the recommendation as it now stands.
Re-recording the version the round opened with throws away the only work an unanswered question produced.

A question that this round *demoted* — one that turned out not to reach §4's bar, or that the maintainer handed back — is not left open.
Decide it, record the decision as yours, and say in the pull request that you took it.

## 8. Gate, then the pull request

The branch was cut in §2, so there is a worktree already and every decision is committed to it.
Then, with output you have actually read:

- [ ] `git fetch origin && git rebase origin/master` — a round takes a sitting, and another pass may have shipped an entry it asked about in the meantime. If so, say so: that question was answered by the code and did not need the maintainer.
      A rebase that actually moves the branch has rewritten commits §6 already pushed, so the next push is `git push --force-with-lease` — never a plain `--force`, which would discard a decision another session had pushed to the same branch.
- [ ] `uv run pytest tests/test_improvement_ledger.py` green: every entry still has exactly one ranking row, closed entries hold none, no status claims the work is done, and every `needs` status still pairs with a `**Decision needed:**` bullet.
- [ ] `make hook` clean, modulo pre-existing failures.
- [ ] `git diff origin/master --stat` lists `potential-improvements.md` and **nothing else** — no `CHANGELOG.rst`, per the rule above.
- [ ] Every answer given in this session appears in the diff. Grep each entry id and read what it now says.

`make test` and `make testall` are not run here: no code changed, and the one test that covers this file is named above.
**No changelog bullet, ever.** A round writes to the register and nothing else, and the register is a list of work *not* done — a decision to change the public API later is not a change a user can observe today. `CLAUDE.md` states the exception; do not reach for `Internal:` either, which is still the user's changelog.

```bash
gh pr create --base master --title "<title>" --body "<body>"
```

Do not merge, enable auto-merge, add reviewers, push to `master`, or tag.
Body:

```markdown
## What
The questions this round put to the maintainer, and what was decided on each.

## Decisions recorded
One line per answer: the question, the option taken, the options refused, and who decided it.
Where the discussion changed the answer, say what moved it — that reasoning is the review's
subject and it is not visible in the register's final wording.

## Still open
The questions asked and not answered, and the ones not asked this round, with the brief now
recorded against each so the next round starts from it.

## Decided without asking
Anything demoted below the bar and taken here instead, with the reason it did not need the
maintainer.

## Next
What the next improvement pass can now take that it could not before.
```

## 9. Final report

In chat, in this order: **what was asked** and why those questions and not others;
**what was decided**, one line each, including the options refused;
**where the discussion moved the answer** — any recommendation that changed and what changed it, and any option the maintainer introduced;
**what is still open**, and whether a brief now exists for it;
**what this unblocks** — the entries that became eligible, named;
and the **pull request URL**, with the verification commands and their real outcomes.

A round that records two well-argued decisions has done more for the register than a pass that ships code against a design nobody chose.
A round that asks nine questions, or asks one the register already answered, has spent the maintainer's attention on the agent's failure to read.

---

## Maintaining this skill

**One stop, and it is this whole skill.** The reason improvement-pass has no `AskUserQuestion` in it is that the two jobs want opposite things from the maintainer's presence: a pass wants none, this wants them at the keyboard. Do not restore an asking step to the pass, and do not let this skill start implementing what it just asked about — each change would recreate the failure the split removed.

**Rejected: a queue file of open questions.** The obvious shape is a `questions/` directory, or a section of its own in the register, so the queue is trivially greppable. Refused because the question would then live somewhere other than the entry it blocks, and the two would drift exactly as the roadmap issue drifted from the code — a question outliving its item, or an item whose entry no longer mentions that it is waiting. The `Status: needs …` and `**Decision needed:**` pairing keeps the question where its context is, and a test enforces the pair, which is what a separate file could not have.

**Rejected: one question per invocation.** A whole round for a single question reads as more careful and is worse: the fixed cost is the maintainer's context switch, not the reading, and four briefed questions in one sitting cost barely more than one. What §5 made sequential is the *asking*, not the round — the batch is still found, ranked and re-verified in one pass, and only then presented a question at a time.

**Rejected: collecting the whole round in one dialog**, which is what §5 replaced. It is the same mistake in the other direction: four briefs go up as a wall, the maintainer answers all four at once from a form, and there is no point at which they can put a fifth option on the table or disprove a premise while it still matters. The round is a batch; the conversation is not.

**Rejected: publishing the round outside chat** — a rendered page, a document, an artifact. It presents better and settles worse, because the reading leaves the conversation the answering happens in: a question raised while reading has nowhere to go, and the round degenerates into the form above. The briefs are written to be read in a terminal, which is why §4 bounds their length and §5 sends them up one at a time.

**Absent on purpose:** repository rules that live in `CLAUDE.md` or `CONTRIBUTING.md`, since the copy that drifts is the one an agent obeys; and any list of what the currently-open questions are, since the register holds those and a copy here would be stale within a pass. This file is instructions; that file is evidence.
