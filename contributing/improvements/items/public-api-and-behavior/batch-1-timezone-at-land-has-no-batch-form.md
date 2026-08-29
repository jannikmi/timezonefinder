# BATCH-1 — `timezone_at_land` has no batch form

## Related memory

- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)

- **Location:** `timezonefinder/timezonefinder.py` — `timezone_at_land`, next to the `timezone_ids_at` / `timezone_names_at` pair that shipped without it.
- **Why it was left out**, and it was a scoping decision rather than an oversight: the ocean check is `utils.is_ocean_timezone`, a `re.match` per *answer*. Batching a lookup whose last step is a regex per point would put the regex where a batch is supposed to have removed the per-point work, and the fix for that is PERF-1 — a prefix comparison instead of a regex — which is ranked, cheap and already decided.
- **Fix:** after PERF-1, add `timezone_at_land`-shaped batch answers. The natural shape is a vectorised mask over the *ids*: an ocean zone is a property of the zone id, not of the point, so the whole set of ocean ids can be computed once per finder and the batch answer masked with `np.isin` — no per-point string work at all. That is strictly better than what a per-point loop could do, which is the second reason to wait rather than to write the loop now.
- **Value:** low-to-medium. It closes the asymmetry a user meets immediately (`timezone_at` batches, `timezone_at_land` does not), and the mask makes it cheaper per point than the scalar method is. `certain_timezone_at` is deliberately **not** in scope: it is a different loop, it tests every candidate, and the issue's own scoping excluded it.
- **Size:** ~30 lines plus tests, once PERF-1 has landed.
- **Status:** open — ranked below PERF-1, which is its precondition.
- **Last touched:** 2026-08-23 — split out when the batch lookups shipped, with the reason they stopped at `timezone_at`.
