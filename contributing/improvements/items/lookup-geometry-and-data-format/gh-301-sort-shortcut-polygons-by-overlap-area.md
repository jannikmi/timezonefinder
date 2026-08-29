# GH-301 — sort shortcut polygons by overlap area


## Related memory

- [Query performance and shortcut decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- **Tracks:** issue #301, **closed as not planned 2026-08-21** with the enumeration as
  justification.
- **Rejected, and kept rather than deleted** because the sort key is genuinely the right one and the
  idea will otherwise be re-proposed on its merits. Bounded by enumeration over the packaged index:
  **12,600 point-in-polygon tests today against 12,234 for the best ordering that exists — 2.90 %
  headroom, on 259 of 41,162 cells.** `last_zone_change_idx` already makes the last zone free and
  the existing sort already puts the largest zone there, and 9,046 of 10,511 ambiguous cells hold
  exactly two zones, where every order costs exactly one test.
- **`shapely` was never the real objection** — it would sit in the `data` group next to `pydantic`,
  a converter-time dependency costing users nothing. It is simply not worth adding for that.
- **The method is the lasting part** and is recorded under *Sequencing*: the question was a count,
  so it needed no machine and no waiting on the accessor work that was about to change what a
  candidate costs — which duly changed it, and left this answer untouched, as a count-based answer
  should be.
- **Status:** rejected.
- **Last touched:** 2026-08-21 — bounded, rejected, issue closed.
