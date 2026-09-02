# GH-332 — reduced timezone dataset as a second distribution


## Related memory

- [Data distribution, packaging, and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Tracks:** issue #332 (and GH-334 for the mapping), which carry the reframing and the costs.
- **Why it is ranked here:** 92 zones instead of 444, and the distribution split turned it from a build-time switch into a packaging decision.
- **Decided, 2026-08-21 — no hand-maintained mapping.** Shipping with one was declined: until the official table exists it is the same liability the zone-precedence engine was rejected for. That decision stands and is unaffected by what follows; only its precondition changed.
- **Unparked, 2026-09-02.** The official table does exist — upstream shipped it in the 2026c release, and GH-334 records the evidence. The park's condition is met, so this is no longer waiting on anything outside the repository. It is still sequenced behind GH-334, which is what puts the mapping in the tree.
- **Status:** blocked on GH-334 — sequenced behind it: eligible for a pass once the mapping is vendored and consumed. The costs on the issue are unchanged; they were never the reason for the park.
- **Last touched:** 2026-09-02 — unparked after verifying the upstream release assets.
