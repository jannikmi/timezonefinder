# Improvement register rules

The contributor-memory graph of what is worth doing next to `timezonefinder`, kept in the open: one [ranking](improvement-priority-ranking.md) across every finding, ordered by the [ranking and eligibility rules](improvement-ranking-and-eligibility.md), with linked item files, [sequencing rules](improvement-sequencing-and-preconditions.md), and topic decision files retaining the options considered and refused. This file holds what an entry is made of, how it is maintained, and how it is retired.

**Anything that improves the package belongs here**, whatever its area and however large: a correctness defect, a slow path, an awkward API, a docs page that lies, a release step that can fail silently, a test that cannot fail, duplication that will drift, a data encoding that wastes half its bytes. There is one list because there is one reviewer's attention to spend, and sorting candidates into kinds first is how the cheap ones get taken because they are cheap. Item files are grouped into area directories under `items/` purely so they can be scanned; the grouping decides nothing, because the ranking table is the only statement of order.

**The division of labour with an issue, where an entry has one.** This file's graph holds what a *pass* needs in order to choose: where the item ranks and why, what blocks it, the decision taken and the options refused. The issue holds the item's **detail** — the measurements, the design tables, the implementation notes, the reproduction. An entry names its issue and says what is on it, rather than restating it, because two copies of a measurement drift and only one of them is ever re-read. **An entry with no issue is the complete record**, and most are: the detail stays here, because there is nowhere else for it. What never moves to an issue in either case is the *ranking*, the *sequencing* and the *recorded decisions* — those are the point, and the next section says why.

**Why here and not on the tracker.** The ranking, the sequencing and the recorded decisions used to live in a roadmap issue. Reasoning that sits outside the repository goes stale silently: nothing references it, no check reads it, and a reviewer never sees it in a diff. Here an entry is reviewed in the pull request that changes it, and every change to the ranking arrives as a diff. Issues remain the place a single item is worked out and where outside contributors comment — which is exactly why an item's detail belongs there and its *rank* does not. A stale measurement on an issue is one wrong number; a stale ranking outside the repository silently misdirects every pass that reads it.

## Entry conventions

An id is a stable handle and nothing more — `GH-<n>` means the item is also tracked by issue `<n>`, the other prefixes are mnemonics, and neither says how a pass should treat the entry. Locations are given by file plus a code anchor (a function or symbol name), never a line number, so they survive reformatting. `Size` is a rough count of changed lines.

An entry belongs here if it names something a pass could act on and later re-verify — code that exists, a file that is built, a decision that can be taken. A finding with no such anchor can never be resolved by the pass that reads it, so it stays open for ever.

`Status` opens with one of `open`, `needs …`, `blocked …`, `conditional …`, `parked …`, `rejected …`, `out of scope …` or `withdrawn …`, and `tests/test_improvement_ledger.py` rejects anything else. **There is deliberately no status meaning "done"** — everything written down here is unfinished or declined, and work that landed is *deleted* rather than marked. Do not re-litigate a closed entry and do not re-add it under a new id.

**A `needs …` entry names the one piece of work nobody can do by reading harder.** It carries exactly one `**Decision needed:**` bullet holding the question, the options with their trade-offs and a recommendation — and its row in the ranking says so too, so the queue is visible from the table. `tests/test_improvement_ledger.py` asserts the pairing in both directions: a `needs` status without the bullet is an entry that says it is waiting without saying what for, and the bullet without the status is a question no pass looking at statuses will find. Answering one turns it back into `open` and the bullet into the decision and its rationale, with the refused options kept.

Every entry has exactly one row in the ranking and every row has exactly one entry; `tests/test_improvement_ledger.py` fails otherwise.

## How it is maintained

Three provider-neutral workflows, split by what they are allowed to do. [Run one discovery pass](../workflows/run-one-discovery-pass.md) adds entries: it sweeps one surface, records only what clears its bar, and never implements. [Run one improvement pass](../workflows/run-one-improvement-pass.md) retires them, and asks nothing — it runs unattended, so a choice that is genuinely the maintainer's is written down as a `**Decision needed:**` question and the item is left for later rather than stalling the pass and everything ranked below it. [Record maintainer decisions](../workflows/record-maintainer-decisions.md) is the other half of that — it collects those questions, re-verifies each against the current code, briefs them, puts them to the maintainer and records the answers here.

Everything is committed so that all of it reaches the next pass through `master`: every pass reads it before touching a source file, re-verifies the entries it is considering against the current code, and writes back what it found.

## Retirement and retention

**It is a to-do list, not a history.** Work that landed is *deleted* — the item file and its ranking row, in the same pull request that ships it — because the code is the evidence it is done, the changelog says what changed, and `git log -- contributing/improvements` still has the text. Nothing renumbers and nothing else moves.

Deleting the item file and ranking row is not enough: grep the id across `contributing/improvements/`. Rewrite blocker, sequencing, measurement, and decision references to describe the lasting fact rather than leaving a dangling item handle. Recorded decisions remain and therefore get rewritten rather than deleted.

**Closing an entry moves its row into *Closed*.** Changing only the eligibility column leaves a dead item holding a live rank, and since the list is walked top-down that costs every later pass the reading it takes to discover there is nothing to take. Entries that were *rejected*, ruled *out of scope* or *withdrawn* normally stay closed rather than being deleted: they encode a dead end, and re-discovering one costs a whole pass. Remove one only when its refusal and decision evidence already live in the narrow canonical decision record; delete its Closed row and rewrite references to the lasting fact. Git retains its narrative and status.

Recorded decisions live in `decisions/`, one file per subject and named for it, split rather than grown once a file reaches its word budget. Checked findings are retained for [runtime and data](checked-and-found-sound/runtime-geometry-and-data-checks.md), [tests and benchmarks](checked-and-found-sound/testing-and-benchmarking-checks.md), and [tooling and packaging](checked-and-found-sound/developer-tooling-and-packaging-checks.md).

Recorded decisions are **kept, never deleted** — including the rejected options, which is most of their value. The next pass re-proposes whatever is not written down as already refused. When a premise moves, rewrite the claim and keep the superseded measurement beneath it, dated. A reversal is still never silent.

## Scope notes

`prototypes/` is excluded throughout — it carries its own crop of ruff findings (`RUF012` mutable class defaults, `RUF034` useless `if`/`else`, `B905` unstrict `zip`) that are appropriate to leave in exploratory code.

`packages/timezonefinder-data/timezonefinder_data/data/` and `timezonefinder/flatbuf/generated/` are generated and are never edited directly; findings there belong against the generator or the schema instead. The first is not in the repository at all — `make bootstrap` obtains it — so nothing there can be read from a diff.

The `timezonefinder-data` distribution is deliberately thin — one `DATA_DIR` constant and a version in `packages/timezonefinder-data/timezonefinder_data/__init__.py`, plus the payload. The package has been reviewed and contains no code that can carry meaningful debt; the [data-distribution decisions](decisions/data-distribution-packaging-and-release-decisions.md) refuse moving the binary-format reader into it.
