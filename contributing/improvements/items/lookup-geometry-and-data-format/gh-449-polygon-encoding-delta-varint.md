# GH-449 — polygon encoding: delta + varint


## Related memory

- [Geometry, data-format, and validation decisions](../../decisions/geometry-data-format-and-validation-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Tracks:** issue #449, which carries the measurements, the three transforms and the two candidate encodings.
- **Why it is ranked here:** the highest-value data-format item on its own merits — lossless delta+zigzag+varint cuts the payload 63.4 → 35.3 MB. Steps 1 (AoS → SoA) and 2 (a format version constant) shipped; encoding and precision remain.
- **Postponed, 2026-08-21.** The two candidate encodings are not comparable — one keeps 1e-7 precision, the other spends it — so choosing means pricing ~11 cm of resolution, and nothing in the repository says what that is worth. GH-542 establishes it; either answer unblocks this.
- **The precondition neither the issue nor this entry had, and it belongs here because it is a cross-item constraint:** decode cost lands on the candidate loop. A ~8.5 ms decode for the largest polygon is catastrophic there and ~828 µs still bad — and the loop has since been stripped of the ~4.9 µs per-candidate fetch it used to carry, which makes the constraint **tighter**, not looser: a decode step now has to fit into a candidate loop with nothing left to hide behind.
- **Shape:** a binary format change cannot half-land, so this is prototyped and measured before it is migrated in one piece.
- **Status:** blocked by GH-542 and DATA-BINARIES.
- **Last touched:** 2026-08-21 — postponed; the precision half split out to GH-542 and the reasoning written to the issue.
