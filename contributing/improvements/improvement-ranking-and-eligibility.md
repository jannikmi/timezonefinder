# Improvement ranking and eligibility

How the order in the [priority ranking](improvement-priority-ranking.md) is decided, and what makes a row eligible for a pass to take. The table itself is that file; the [register rules](improvement-register-rules.md) hold what an entry is made of and how it is retired.

**The order is the ranking's point.** Listing everything that could be improved is easy and worth little; what costs something is deciding which findings earn a reviewer's attention, and writing down why the rest do not. Rows are ordered by expected value — *defects that will cause a real bug later > work that unblocks other work > duplication that will drift > readability* — with size breaking ties only.

**The ranking has no numbers**, because the row order is the ranking. A number column would have to be re-flowed on every insertion and deletion — churn on the one operation the file exists to make cheap, and a conflict between any two passes that both ship something.

## What outranks what

**A confirmed defect outranks everything that is not one.** Decided 2026-08-29 by the maintainer: a correctness defect goes to the top the moment it is confirmed, and a pass takes it before any improvement, whatever its size or expected value. The expected-value ordering above governs what sits *below* the defects. Three boundaries keep it honest. **What counts is a wrong or silently-empty answer on a path real usage reaches** — not the `**Defect:**` label, which entries also use for docs and unreachable code. A **suspected** defect is a measurement rather than a defect, so confirm it before it displaces anything. And a confirmed defect that is genuinely blocked still sits below its blocker.

Stated as an absolute because a narrow defect prices low on any honest expected-value reading, which is how real wrong answers end up ranked beneath refactors.

**A performance item is ranked on a measured share, never on an intuition about what looks slow.** Benefit is the fraction of a query the change removes *at best* — its ceiling, read off [the measured baseline](query-performance-measurement-baseline.md) — and cost is size, plus the decisions it needs, plus whether it forces a data-format change (which is a two-distribution ordered release, the expensive category). A ceiling below the machine's own run-to-run noise, 3–9 %, cannot be demonstrated by the benchmark suite even when the change is real: such an item has to stand on correctness or simplicity instead, and is ranked on that. Unmeasured is not a third case — it means the item is a measurement, and the measurement is one profiler run.

State the ceiling as a **workload** share, not a stratum share, and prefer the count a change removes to the time it removes: the counts are machine-independent and the shares are not. The [measured baseline](query-performance-measurement-baseline.md) carries the conversion and the rest of what one machine's numbers can and cannot be asked.

An item sits **below its own blocker**, because the list is walked top-down.

## Eligibility

A pass takes the highest-ranked item that is *eligible*: unclaimed, [preconditions](improvement-sequencing-and-preconditions.md) met, its maintainer-owned decisions already recorded or obtainable, and small enough to review. That is what lets a cheap item proceed while a large one waits on a decision.

**`needs …` means a person has to decide something** and the row is ineligible until they have. The [maintainer-decision workflow](../workflows/record-maintainer-decisions.md) collects those questions; answering one turns the entry back to `open` and makes the row eligible again.

**Blocked is not closed.** A blocked item is live work waiting on a blocker and stays in the ranking below it, as do *parked* and *conditional*, which can become live without the entry changing. Only *rejected*, *withdrawn* and *out of scope* leave the ranking, because no pass will ever take them as they stand; the [register rules](improvement-register-rules.md) say where they go.

Both tables sit under one heading in the ranking file on purpose: `tests/test_improvement_ledger.py` reads the section rather than a single table, so every entry still has exactly one row and the two halves cannot drift.

## Re-verify before ranking

Treat every entry as evidence, not gospel: re-find its location by symbol, and check its premise against the current code before giving it a rank. An entry left in after its work shipped is the failure the register cannot detect on its own — it reads exactly like an open one, and the next pass pays full price to rediscover that there is nothing to do.

**A `GH-<n>` entry whose issue has closed is the cheapest staleness signal there is**: either the work landed or the item was dropped, and both mean the entry is resolved rather than open. `gh issue view <n> --json state` over the ids costs seconds, and it is what caught the one entry the register arrived with that had shipped the day before.
