# Improvement discovery coverage map

This stable index routes improvement passes to the current discovery coverage, durable methods, and remaining gaps. Routine passes edit one narrow record linked below, not this index.

## Update contract

Update a surface record only when one of these events occurs:

- a deliberate audit broadens the recorded coverage;
- new evidence invalidates an existing coverage claim; or
- the surface's next useful discovery gap materially changes.

Implementing an already-ranked item, reading code in order to change it, or reviewing code as its author is not by itself a discovery-coverage change. Put an actionable finding in its own item file, a durable non-finding in the narrowest file under `checked-and-found-sound/`, and a settled choice in the matching file under `decisions/`. Shipped behavior belongs in code, tests, public documentation, or the changelog rather than in coverage memory.

Each surface record owns its own delta anchor. The anchor identifies the tree the snapshot describes; it does not claim that every file in that tree received an independent review. Advance it only when the record says what audit justifies the new boundary. Keep one fact or instruction per bullet, link durable evidence instead of copying it, and leave pass chronology to Git history.

## Repository surfaces

- [Runtime package](discovery-coverage/surfaces/runtime-package.md)
- [Data and conversion scripts](discovery-coverage/surfaces/data-and-conversion-scripts.md)
- [Tests](discovery-coverage/surfaces/tests.md)
- [Benchmarks and reports](discovery-coverage/surfaces/benchmarks-and-reports.md)
- [Workflows and packaging](discovery-coverage/surfaces/workflows-and-packaging.md)
- [Documentation](discovery-coverage/surfaces/documentation.md)
- [Prototype code](discovery-coverage/surfaces/prototype-code.md)
- [Generated and data-package code](discovery-coverage/surfaces/generated-and-data-package-code.md)
- [Improvement ledger](discovery-coverage/surfaces/improvement-ledger.md)

## Reusable methods

- [Reusable discovery methods](discovery-coverage/reusable-discovery-methods.md)

## Where discovery starts

Start with the [priority ranking](improvement-priority-ranking.md), because known work normally outranks another broad sweep. A pass that does look for new candidates follows the [discovery-pass workflow](../workflows/run-one-discovery-pass.md), which selects one lane and states the bar a candidate must clear to be recorded. For fresh discovery, compare the surface records' `Next useful gap` sections. The coverage map does not maintain a second global ordering that can drift from the ranking.

---
