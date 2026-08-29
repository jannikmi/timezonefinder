# GH-332 — reduced timezone dataset as a second distribution


## Related memory

- [Data distribution, packaging, and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Tracks:** issue #332 (and GH-334 for the mapping), which carry the reframing and the costs.
- **Why it is ranked here:** 92 zones instead of 444, and the distribution split turned it from a
  build-time switch into a packaging decision.
- **Decided, 2026-08-21 — parked until GH-334 unblocks.** Shipping with a hand-maintained mapping
  was declined: until the official table exists it is the same liability the zone-precedence engine
  was rejected for. GH-334 tracks the upstream trigger, so nothing else has to watch it.
- **Status:** parked until GH-334 unblocks — not a candidate for any pass before then.
- **Last touched:** 2026-08-21 — decided to park; the costs written to the issue.
