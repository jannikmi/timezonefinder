# Record maintainer decisions

Turn at most four blocking design questions into recorded decisions, ending in a register-only pull
request. This workflow asks and records; it never implements.

Read the [priority ranking](../improvements/improvement-priority-ranking.md), then open only item
files whose status starts with `needs`. A valid item also has exactly one
`**Decision needed:**` bullet.

## Hard boundaries

- Never edit source, tests, changelog, or implementation files.
- Never implement an answer, merge, enable auto-merge, push to `master`, or tag.
- Never ask what repository memory, current code, documentation, or an existing decision answers.
- Never treat silence or “you decide” as a maintainer answer. If the question fails the maintainer
  bar, decide it as a contributor and record why it was demoted.
- Never reopen a recorded decision without new evidence that disproves its premise.

## Select and verify questions

Include explicit questions from the invocation and recorded decisions invalidated by new evidence.
Rank questions by what their answer releases: one unblocking the top item or several items outranks
an isolated low item. Skip questions whose other preconditions remain unmet. Take at most four.

Before briefing, re-read the item, applicable topic decisions, current code,
`docs/architecture.rst`, and `docs/data_format.rst`. Re-verify whether the question is already
answered, has changed, or still stands. Measure facts obtainable with one command; if measurement
needs a prototype, mark the option unpriced.

A maintainer question must have at least two reasonable answers that create materially different
work and be expensive to reverse. Routine naming, formatting, placement, testing, and equivalent
implementation choices fail this bar.

Create the dedicated worktree and branch from current `origin/master` before asking anything, so
each answer can be committed and pushed immediately.

## Brief, discuss, and ask

Prepare each brief before asking:

1. Question and item ID.
2. What it blocks and ranking position.
3. Fresh context sufficient to answer without visiting an issue.
4. Two to four mutually exclusive options, including “do not do it” when real.
5. Cost, benefit, and foreclosed choices for each option.
6. A named recommendation, why alternatives lose, and what would change it.
7. Reversibility, confidence, and unpriced uncertainty.

Handle one question at a time: present its brief in full, then discuss it for as long as the
maintainer wants. Re-check challenged premises against the tree, measure facts one command can
measure, price options the maintainer introduces on the same axes, and update the recommendation
when the evidence moves it. State a concrete disagreement once, then leave the choice to the
maintainer. Do not re-brief after the discussion converges.

Use the provider's structured question interface for that question alone when available. Put the
current recommended option first and offer deferral only when it is genuinely actionable. An answer
already given in chat needs only a one-line read-back, not a second entry in a dialog. A brief
answered immediately needs no manufactured discussion.

Before presenting the next brief, compare every remaining question with the decision just taken.
Revise or remove any that it answered or materially changed.

## Record immediately

For each answer, before presenting the next question, rewrite the item: remove the decision-needed bullet, record the chosen option,
rationale, owner, and refused alternatives, and return the status to `open`. Update the ranking
eligibility cell. A “do not do it” answer makes the item rejected or withdrawn and moves its row to
`Closed`; the item remains as the argument against re-proposal.

If the choice affects other items, add it to the applicable topic decision module and link those
items to it. Preserve earlier decisions and corrections. Unanswered questions keep `needs` and gain
the complete brief as the discussion left it so the next round does not re-derive or forget it.

Commit and push each decision separately before moving on. Rebase before the final gate; after a
rebase of already-pushed commits, use `--force-with-lease`, never plain `--force`. Stage only the
ranking, affected items, and any applicable decision module. Run the contributor-memory and
improvement-ledger tests plus `make hook`. The diff must contain no changelog or implementation.

Open a pull request without merging. Report what was
asked, answers and refused options, unanswered questions, contributor-owned decisions demoted from
the maintainer bar, options or recommendations changed by discussion, newly eligible items,
verification, and the pull request URL.
