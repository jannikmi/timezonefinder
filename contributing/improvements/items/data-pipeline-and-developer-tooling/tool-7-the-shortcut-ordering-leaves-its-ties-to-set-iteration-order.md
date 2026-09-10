# TOOL-7 — the shortcut ordering leaves its ties to set iteration order


## Related memory

- [Shortcut index and query performance decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Generated-file rules](../../../development/generated-file-regeneration-rules.md)
- **Defect (build reproducibility, not answers):** `scripts/shortcuts.py`'s `process_single_hex` takes `list(cell.polys_in_cell)` — a `set` — and `optimise_shortcut_ordering` sorts it with two stable `sorted` calls. Where the sort key ties, the output order is therefore whatever order the set happened to iterate in, which is a CPython implementation detail of the insertion history rather than a property of the data.
- **Observed, 2026-09-06:** recompiling the shipped 2026c index from the same source with the candidate sets in sorted order reproduces `shortcuts.bin` to **29 differing bytes across ~6 cells** — every one of them a tie. Answers are unaffected: the tied zones have equal total vertex counts, and a tie cannot move which zone sits last.
- **Why it is worth fixing anyway.** The [generated-file rules](../../../development/generated-file-regeneration-rules.md) make regeneration the way a converter refactor is proved neutral, and that proof is a byte diff. A binary that is only reproducible because a set happened to iterate the same way is a proof that can fail for reasons unrelated to the change under test — and the failure appears as ~6 cells of unexplained diff, which is exactly the shape a real bug would take.
- **The fix is one sort key, and it needs no new dependency.** Break the tie on the polygon id — both the zone key and the within-zone key — so the ordering is a total order on the data. Sorting the candidates before grouping is the same fix in a different place. Breaking the tie by overlap area also works and was measured (0 answers moved, 0 tests changed, +14 bytes), but it costs `shapely` at the converter for nothing the id does not buy.
- **Size:** ~10 lines in `optimise_shortcut_ordering`, plus a test that the same input compiles to the same bytes.
- **Status:** open. Found while rebuilding the index to measure candidate orderings; nothing else was changed.
