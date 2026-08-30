# Trade-off surfacing and validation

A trade-off discovered while implementing is a rewrite; the same trade-off named during discovery is a paragraph. Surface it before writing code, and validate it before claiming it.

## Surface it during discovery

Before proposing or selecting work, state what the change trades away, in one sentence per axis, with the losing side named. The recurring axes here are query latency against resident memory and construction time, data-format compactness against decode cost, public API breadth against the compatibility contract, vectorised fast paths against the pure-Python fallback's parity, and CI coverage against the time every pull request pays. A proposal that names only its benefit has not been scoped yet.

Check each losing side against the [project purpose and non-goals](../project/project-purpose-runtime-constraints-and-non-goals.md) and the [public API contract](../project/public-api-and-compatibility-contract.md) first, because that is the cheapest step that can end the discussion: an option that gives up unsimplified boundary geometry, the memory-mapped low-memory mode, the pure-Python fallback, or a documented signature is dead on arrival regardless of how well it measures. Rule those out in the plan, not in review, and record the refusal in the matching [topic decision file](../improvements/improvement-register-rules.md) so the next pass does not re-derive it.

For the options that survive, name the one number that would decide between them and the threshold that decides it, before implementing either. Read the ceiling off [the measured baseline](../improvements/query-performance-measurement-baseline.md) rather than from intuition about what looks slow; a change whose best case removes less than the machine's own run-to-run noise cannot be demonstrated by the benchmark suite even when it is real, so it has to stand on correctness or simplicity instead, and should be argued that way from the start.

When no measurement available to a pass can separate the options, and reversal would be expensive, the choice is the maintainer's: record it as the item's single `**Decision needed:**` bullet with the options, trade-offs, recommendation and reversibility, and move down the ranking. Do not implement one branch to find out.

## Validate it during implementation

A predicted trade-off is a hypothesis until it is measured on the branch that makes it. Produce paired before/after evidence with the observed spread and the acceleration backend named, following the [benchmark rules](benchmarking-and-performance-validation.md); memory-side trade-offs appear in `make memory` and nowhere else, so a change that makes the library hold what it previously mapped is unvalidated until that runs. Compare local against local, never local against CI.

Validate the side that was traded away, not only the side that was bought. A latency win that was paid for in memory, startup, or wheel size is validated only when that cost is measured too, and a fast-path change is validated only when the fallback path is exercised as well.

If measurement contradicts the prediction, the option dies there. Revert it, keep the evidence, and record the refusal at the decision site so it stays refused; if a tracked item's proposal is what the measurement killed, follow the [register rules](../improvements/improvement-register-rules.md) for withdrawing it rather than quietly rewriting its rationale. State the predicted trade-off and the measured outcome side by side in the pull request body, including the machine the numbers came from, so a reviewer can see which claims were tested and which were reasoned.
