# GH-513 — drop hole polygons entirely


## Related memory

- [Geometry, data-format, and validation decisions](../../decisions/geometry-data-format-and-validation-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Tracks:** issue #513, which carries the measured evidence and the coverage trap.
- **Why it is ranked here:** it would delete the whole hole subsystem. **Blocked, and measurably so** — dropping holes changes answers today and the changed answers are wrong.
- **No longer blocked by GH-301, 2026-08-21.** That was a mis-ranking: what this needs is a correctness *proof*, not a faster ordering, and GH-301 is rejected in any case.
- **The constraint that came out of it**, now a recorded decision: the proof must be **independent of the H3 shortcut index**. Zone precedence is a property of the zones and their geometry; expressed per cell it would make correctness depend on an index whose resolution and layout are implementation details, so a future resolution change would move answers rather than only performance.
- **Status:** blocked by GH-500.
- **Last touched:** 2026-08-21 — the GH-301 dependency removed and the H3-independence constraint recorded on the issue and above.
