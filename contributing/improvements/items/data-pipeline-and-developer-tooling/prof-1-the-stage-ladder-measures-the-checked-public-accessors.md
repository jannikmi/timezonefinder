# PROF-1 — the stage ladder measures the checked public accessors, not the query path

- **Location:** `prototypes/query_stage_profile.py` — `make_ladder`, and the `FINDINGS` block's finding 8.
- **Why this outranks the things it measures.** The ladder is the only per-stage attribution this repository has: the sampled block breakdown resolves two blocks (`prologue` / `other`), so every stage share in the [measurement baseline](../../query-performance-measurement-baseline.md) — and therefore every performance item's rank — comes from it. Its `FINDINGS` block already records the symptom, that it "overshoots the real function by ~30-37 % on the ambiguous stratum", attributes it to the candidate loop having become shared code, and tells readers not to quote a rung until it is fixed. **The cause is narrower than that and is a one-line-per-rung defect**, so the instrument can be repaired rather than distrusted.
- **What is actually wrong. The ladder binds the *checked public* accessors; `timezone_at` calls the unchecked internal ones.**

  | ladder binds | `timezone_at` calls | measured, min of 7 rounds, clang |
  |---|---|---|
  | `tf.zone_ids_of` | `self._zone_ids_of` | **1,685 ns vs 564 ns** |
  | `tf.zone_name_from_id` | `self.zone_names.name_of` | **58.8 ns vs 33.9 ns** |

  The public forms carry the negative-id guard that landed 2026-08-23: `zone_ids_of` runs `np.asarray(ids) < 0` and `.any()` — two extra numpy calls over a list averaging 2.67 elements — before the fancy index the query path performs alone. That is **+1,121 ns on the `zone_ids_of` rung of every ambiguous query** and +25 ns on the `zone_name_from_id` rung of every stratum, which is ~1,146 ns of the ~1,438 ns discrepancy the `FINDINGS` block cannot account for.
- **A third infidelity, smaller and in the other direction of the same gap.** `s8_bbox` and `s9_holes` omit the `break` on a match that `s10_full` and `timezone_at` both have, so the two geometry rungs test more candidates per query than the lookup does. It shows: the `hole checks` rung reads 1,289 ns/query on the ambiguous stratum where the real path makes **0.779 hole probes per ambiguous query at ~250 ns each**, ~195 ns.
- **What it has been costing.** The most recent run reads `zone_ids_of` at **1,781 ns, 29.2 % of the ambiguous ladder** — the largest non-geometry rung there is, and ~3x the stage's real cost. [PERF-2](../lookup-geometry-and-data-format/perf-2-the-candidate-loop-builds-a-zone-id-array-to-read-one-element.md) is the entry ranked on that stage, and it was ranked *down* on a stale denominator while the ladder was reporting the stage 3x too large — two errors in opposite directions, neither visible from the file that records them.
- **The fix.** Bind `tf._zone_ids_of` and `tf.zone_names.name_of` in `make_ladder`, add the missing `break` to `s8_bbox` and `s9_holes`, re-run both backends, and rewrite finding 8 to state what the ladder now is rather than that it cannot be trusted. ~25 lines plus the re-run. **The rule worth keeping at the code site afterwards:** a ladder rung must bind the symbol the lookup binds, and the public/private accessor split on this class exists precisely because the two differ in cost — so the ladder is the one caller for which reaching for the public name is a bug.
- **Then re-derive, in the same pass:** the ambiguous ladder total against the real `timezone_at` row, and every stage share the [measurement baseline](../../query-performance-measurement-baseline.md) quotes from it.
- **Status:** open — free, small, and it is what makes the entries ranked on ladder rungs re-rankable.
- **Last touched:** 2026-09-05 — found and measured in the query-flow discovery round.

## Related memory

- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- [Query-path change-classification log](../../query-path-change-classification-log.md)
