# PROF-1 — the stage ladder measures the checked public accessors, not the query path

- **Location:** `prototypes/query_stage_profile.py` — `make_ladder`, and the `FINDINGS` block's finding 8.
- **Why this outranks the things it measures.** The ladder is the only per-stage attribution this repository has: the sampled block breakdown resolves two blocks (`prologue` / `other`), so every stage share in the [measurement baseline](../../query-performance-measurement-baseline.md) — and therefore every performance item's rank — comes from it.
- **What is wrong. The ladder binds the *checked public* accessors; `timezone_at` calls the unchecked internal ones.** The public forms carry the negative-id guard that landed 2026-08-23: `zone_ids_of` runs `np.asarray(ids) < 0` and `.any()` — two extra numpy calls over a list averaging 2.67 elements — before the fancy index the query path performs alone.

  | ladder binds | `timezone_at` calls | measured, min of 7 rounds, clang |
  |---|---|---|
  | `tf.zone_ids_of` | `self._zone_ids_of` | **1,685 ns vs 564 ns** |
  | `tf.zone_name_from_id` | `self.zone_names.name_of` | **58.8 ns vs 33.9 ns** |

  The public forms carry the negative-id guard that landed 2026-08-23: `zone_ids_of` runs `np.asarray(ids) < 0` and `.any()` — two extra numpy calls over a list averaging 2.67 elements — before the fancy index the query path performs alone. That is **+1,121 ns on the `zone_ids_of` rung of every ambiguous query** and +25 ns on the `zone_name_from_id` rung of every stratum, which is ~1,146 ns of the ~1,438 ns discrepancy the `FINDINGS` block cannot account for.
- **A third infidelity, smaller and in the other direction of the same gap.** `s8_bbox` and `s9_holes` omit the `break` on a match that `s10_full` and `timezone_at` both have, so the two geometry rungs test more candidates per query than the lookup does. It shows: the `hole checks` rung reads 1,289 ns/query on the ambiguous stratum where the real path makes **0.779 hole probes per ambiguous query** — ~160 ns each before the guard PERF-8 shipped, ~88 ns after.
- **What it cost, and what is left.** The `zone_ids_of` rung read **1,781 ns, 29.2 % of the ambiguous ladder** — the largest non-geometry rung there was, and ~3x the stage's real cost — while the entry ranked on that stage was itself ranked *down* on a stale denominator: two errors in opposite directions, neither visible from the file that recorded them. **That rung is gone**: the candidate loop stopped building the array, so the call it mis-bound no longer exists and the ladder's overshoot fell from ~28-30 % to -3 to -6 %. What remains is `zone_name_from_id`, which binds the checked public accessor the same way, on a rung that is 4-8 % of a unique query rather than 29 % of an ambiguous one. **This item is therefore smaller than its measurement suggests** — re-measure the remaining rung before ranking it, and do not reuse the 1,781 ns figure, which priced a call that has been deleted.
- **The fix.** Bind `tf.zone_names.name_of` in `make_ladder` — the `zone_ids_of` rung it also named is gone with the stage — add the missing `break` to `s8_bbox` and `s9_holes`, re-run both backends, and rewrite finding 8 to state what the ladder now is rather than that it cannot be trusted. ~20 lines plus the re-run.

  #609 bound `zone_id_of = tf._zone_id_of` correctly for the stage it added, which is what makes the remaining mis-binding a per-rung slip rather than a policy. **The rule worth keeping at the code site afterwards:** a ladder rung must bind the symbol the lookup binds, and the public/private accessor split on this class exists precisely because the two differ in cost — so the ladder is the one caller for which reaching for the public name is a bug.
- **Then re-derive, in the same pass:** the ambiguous ladder total against the real `timezone_at` row, and every stage share the [measurement baseline](../../query-performance-measurement-baseline.md) quotes from it.
- **Status:** open — free, small, and it is what makes the entries ranked on ladder rungs re-rankable.
- **Last touched:** 2026-09-05 — found and measured in the query-flow discovery round.

## Related memory

- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- [Query-path change-classification log](../../query-path-change-classification-log.md)
