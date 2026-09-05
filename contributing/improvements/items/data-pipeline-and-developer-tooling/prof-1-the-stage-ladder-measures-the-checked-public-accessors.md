# PROF-1 — the stage ladder measures the checked public accessors, not the query path

- **Location:** `prototypes/query_stage_profile.py` — `make_ladder`, and the `FINDINGS` block's finding 8.
- **Why this outranks the things it measures.** The ladder is the only per-stage attribution this repository has: the sampled block breakdown resolves two blocks (`prologue` / `other`), so every stage share in the [measurement baseline](../../query-performance-measurement-baseline.md) — and therefore every performance item's rank — comes from it.
- **What is wrong. The ladder binds the *checked public* accessors; `timezone_at` calls the unchecked internal ones.** The public forms carry the negative-id guard that landed 2026-08-23: `zone_ids_of` runs `np.asarray(ids) < 0` and `.any()` — two extra numpy calls over a list averaging 2.67 elements — before the fancy index the query path performs alone.

  | ladder binds | `timezone_at` calls | measured, min of 7 rounds, clang |
  |---|---|---|
  | `tf.zone_ids_of` | `self._zone_ids_of` | **1,685 ns vs 564 ns** |
  | `tf.zone_name_from_id` | `self.zone_names.name_of` | **58.8 ns vs 33.9 ns** |

- **Re-verified 2026-09-05 against [#609](https://github.com/jannikmi/timezonefinder/pull/609), which is open and rewrites this file. Half of this item is retired by it and half is not, and the half that is not is the *durable* half.**
  - **Retired:** the `zone_ids_of` rung. #609 implements PERF-2, so the stage stops existing and the rung is deleted with it. The 1,685-vs-564 measurement above stays here as the evidence for the rule, not as a live finding.
  - **Not retired, and reintroduced in a new place:** `zone_name_from_id` is still bound to `tf.zone_name_from_id` on #609's branch (`make_ladder`, verified in its diff), against the `self.zone_names.name_of` the query path calls. On the unique-shortcut stratum — ~89 % of a random workload — that rung is the only one below `h3` and `validate_coordinates`, and it reads ~1.7x its real cost. #609 *did* bind `zone_id_of = tf._zone_id_of` correctly for the stage it added, which is what makes this a per-rung slip rather than a policy.
  - **Not retired:** `s8_bbox` and `s9_holes` omit the match `break` that `s10_full` and `timezone_at` both have, so those two rungs test more candidates per query than the lookup does. It shows: the `hole checks` rung read 1,289 ns/query on the ambiguous stratum where the real path makes **0.779 hole probes per ambiguous query** — since measured at ~160 ns each before the guard that shipped, ~88 ns after.
- **The fix, after #609 lands.** Bind `tf.zone_names.name_of` in `make_ladder`, add the missing `break` to `s8_bbox` and `s9_holes`, re-run both backends, and rewrite finding 8 to state what the ladder now is rather than that it cannot be trusted. ~20 lines plus the re-run.
- **The rule worth keeping at the code site afterwards:** a ladder rung must bind the symbol the lookup binds, and the public/private accessor split on this class exists precisely because the two differ in cost — so the ladder is the one caller for which reaching for the public name is a bug.
- **Then re-derive, in the same pass:** the ambiguous ladder total against the real `timezone_at` row, and every stage share the [measurement baseline](../../query-performance-measurement-baseline.md) quotes from it. The baseline's anchor has not been re-taken since the frame-of-reference payload landed on top of it; #609 re-anchors it at its own head, and this item is what makes the ladder it re-anchors worth anchoring.
- **Status:** blocked on [#609](https://github.com/jannikmi/timezonefinder/pull/609) — it rewrites `make_ladder` and deletes the rung carrying half this entry's evidence, so taking this first would race that pull request in one file and re-measure a ladder about to change.
- **Last touched:** 2026-09-05 — claimed by an improvement pass, re-verified against #609 and yielded rather than raced; the surviving half is stated above so the next pass reads what is true rather than what was true before #609 was written.

## Related memory

- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- [Query-path change-classification log](../../query-path-change-classification-log.md)
