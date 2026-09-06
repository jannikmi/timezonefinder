# Improvement ranking and eligibility

How the order in the [priority ranking](improvement-priority-ranking.md) is decided, and what makes a row eligible for a pass to take. The table itself is that file; the [register rules](improvement-register-rules.md) hold what an entry is made of and how it is retired.

**The order is the ranking's point.** Listing everything that could be improved is easy and worth little; what costs something is deciding which findings earn a reviewer's attention, and writing down why the rest do not. Rows are ordered by expected value — *defects that will cause a real bug later > work that unblocks other work > duplication that will drift > readability* — with size breaking ties only.

**The row order is the order a pass considers the items in, and nothing else.** A pass walks the table top-down and takes the first eligible row, so the table is read correctly only if walking it reproduces what a pass actually does. Two consequences, and they outrank the expected-value ordering wherever they collide, because that ordering decides which of two *takeable* items is worth more and says nothing about an item nobody can take. **An item appears above every item it blocks**, without exception — a blocker read after the work waiting on it is a row the pass has already skipped for a reason it had not yet seen. And **an ineligible row sorts below every eligible one**: `needs`, `blocked`, `parked` and `conditional` entries are live work, but no pass can take them as they stand, so leading with them puts the reading cost of the whole ineligible set in front of the first item anyone can start. Expected value then orders each of the two groups internally, and the eligibility cell keeps the rank the entry would hold if it were takeable, so nothing is lost by moving it down.

This is why the ranking does not double as a statement of what matters most. GH-364 and GH-332 sat at the top for months on expected value while being unreachable the whole time; what that bought was that every pass re-read them first. An entry that becomes eligible moves up in the same change that clears it.

**The ranking has no numbers**, because the row order is the ranking. A number column would have to be re-flowed on every insertion and deletion — churn on the one operation the file exists to make cheap, and a conflict between any two passes that both ship something.

## What outranks what

**A confirmed defect outranks everything that is not one.** Decided 2026-08-29 by the maintainer: a correctness defect goes to the top the moment it is confirmed, and a pass takes it before any improvement, whatever its size or expected value. The expected-value ordering above governs what sits *below* the defects. Three boundaries keep it honest. **What counts is a wrong or silently-empty answer on a path real usage reaches** — not the `**Defect:**` label, which entries also use for docs and unreachable code. A **suspected** defect is a measurement rather than a defect, so confirm it before it displaces anything. And a confirmed defect that is genuinely blocked still sits below its blocker.

Stated as an absolute because a narrow defect prices low on any honest expected-value reading, which is how real wrong answers end up ranked beneath refactors.

**A performance item is ranked on a measured share, never on an intuition about what looks slow.** Benefit is the fraction of a query the change removes *at best* — its ceiling, read off [the measured baseline](query-performance-measurement-baseline.md) — and cost is size, plus the decisions it needs, plus whether it forces a data-format change (which is a two-distribution ordered release, the expensive category). **A ceiling below the benchmark suite's noise floor, 3–9 %, is not a reason to refuse the item.** That floor is a property of the instrument and of the workload it averages over, not of the change: a real saving that is smaller than the spread of a random-workload batch is still a real saving, and several of them land on the same query and compose. Refuse a performance item when the gain **cannot be measured at all** — when no instrument the repository has shows a non-noise effect — not when the coarsest instrument cannot resolve it. Sufficient evidence, in the order the [measured baseline](query-performance-measurement-baseline.md) prefers: a **count** a change removes (exact and machine-independent, and a share only when the things counted cost the same — GH-301 removed 2.8 % of the point-in-polygon tests on the ambiguous stratum and cost 24.8 % of an ambiguous query, because it removed the cheap ones), a non-noise effect in a **line or stage profile**, or a win rate outside a coin flip in an **in-query alternating A/B** (`benchmarks/candidate_comparison.py`). Any one of those clears the bar; none of them has to reach 3 %. **A count clears it only once the cost of the counted things is established** — otherwise it sizes the work removed and not the work, and GH-301 is what that costs.

Two things this does not license. A sub-noise item still **must not be written up as a suite-visible speed-up** — state the increment as what it is, and claim the composite figure only once the siblings it composes with have actually shipped, re-measured against the tree they landed on. And an isolated per-call microbenchmark is still **not** a workload share: converting one into the other is how the mapped candidate fetch was once written up as "~3 % of a mixed workload" on the strength of ~370 ns per fetch in isolation, where inside the query it measured ~0.8 %. Measure inside the query; then rank on what that measurement says rather than on whether it reaches the suite's threshold.

Unmeasured is not a third case — it means the item is a measurement, and the measurement is one profiler run.

State the ceiling as a **workload** share, not a stratum share, and prefer the count a change removes to the time it removes: the counts are machine-independent and the shares are not. The [measured baseline](query-performance-measurement-baseline.md) carries the conversion and the rest of what one machine's numbers can and cannot be asked.

An item sits **below its own blocker**, because the list is walked top-down; that is the ordering invariant above, restated where a rank is being argued.

## Eligibility

A pass takes the highest-ranked item that is *eligible*: unclaimed, [preconditions](improvement-sequencing-and-preconditions.md) met, its maintainer-owned decisions already recorded or obtainable, and small enough to review. That is what lets a cheap item proceed while a large one waits on a decision.

**`needs …` means a person has to decide something** and the row is ineligible until they have. The [maintainer-decision workflow](../workflows/record-maintainer-decisions.md) collects those questions; answering one turns the entry back to `open` and makes the row eligible again.

**Blocked is not closed.** A blocked item is live work waiting on a blocker and stays in the ranking below it — and, by the ordering rule above, below every eligible row too, as do *needs*, *parked* and *conditional*, which can become live without the entry changing. Only *rejected*, *withdrawn* and *out of scope* leave the ranking, because no pass will ever take them as they stand; the [register rules](improvement-register-rules.md) say where they go.

Both tables sit under one heading in the ranking file on purpose: `tests/test_improvement_ledger.py` reads the section rather than a single table, so every entry still has exactly one row and the two halves cannot drift.

## Re-verify before ranking

Treat every entry as evidence, not gospel: re-find its location by symbol, and check its premise against the current code before giving it a rank. An entry left in after its work shipped is the failure the register cannot detect on its own — it reads exactly like an open one, and the next pass pays full price to rediscover that there is nothing to do.

**A `GH-<n>` entry whose issue has closed is the cheapest staleness signal there is**: either the work landed or the item was dropped, and both mean the entry is resolved rather than open. `gh issue view <n> --json state` over the ids costs seconds, and it is what caught the one entry the register arrived with that had shipped the day before.
