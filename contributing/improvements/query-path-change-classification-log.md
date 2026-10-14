# Query-path change-classification log

This log classifies changes to the query path that landed **since** the anchor in the [query performance measurement baseline](query-performance-measurement-baseline.md), so a later pass does not have to re-derive whether the recorded denominators still apply. The changes from before the anchor bear on freshness only through the rules they state, and are in [query-path changes before the measurement anchor](query-path-changes-before-the-measurement-anchor.md).

**It is empty, because the anchor was re-measured with the current tree.** The baseline's freshness command reports empty, and that is the state this file exists to make legible.

## How to add an entry

Add new entries at the top of a list below, and give each one three things:

- **Which class the change is in.** *Inert* means the query path executes the same statements - establish that with a count (`sys.settrace` opcode events over fixture points, or the hit counts in `prototypes/query_stage_profile.py`), never with a clock, because no timing on one machine resolves a few bytecodes. *Not inert* means a denominator or a share may have moved, and the change owes a paired A/B inside one process with the arms alternated.
- **What it does to the baseline:** whether the anchor stands, and which shares were re-taken. A change that moves the critical path re-anchors and re-measures in its own pull request - that rule is in the baseline, and this file is where a pass finds out whether it was followed.
- **The generalisable half**, which is the part that outlives the bookkeeping: what the next change of this shape should do differently. An entry with no such half is bookkeeping Git already has, and belongs in the pull request rather than here.
