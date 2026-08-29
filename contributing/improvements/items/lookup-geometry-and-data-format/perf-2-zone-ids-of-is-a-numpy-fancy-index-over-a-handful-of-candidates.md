# PERF-2 — `zone_ids_of` is a numpy fancy-index over a handful of candidates

- **Location:** `timezonefinder/timezonefinder.py` — `zone_ids_of`, in the candidate-narrowing
  block.
- **Halved since it was written, and the reasoning has to move with it.** This entry used to
  cover *two* numpy calls, the second being `get_last_change_idx` at 149/283 ns — and it recorded
  that precomputing that index into the shortcut binaries was refused. **That refusal was
  reversed and has shipped**: the stop index is now one `uint8` per distinct candidate list in
  the shortcut index, read rather than computed, so this entry is down to `zone_ids_of` alone.
  Anyone reading the old text would optimise a call that no longer runs.
- **Measured (2026-08-23):** `zone_ids_of` 599/556 ns (numba/clang), ~5–6 % of an ambiguous query
  and nothing at all on the unique-zone path, which never builds a candidate list.
- **Why it is there:** a numpy fancy-index over a list of a handful of elements, where the
  per-call overhead dominates whatever is computed. The candidate slice next to it (215/269 ns)
  is the same shape of cost.
- **Fix:** narrow the candidates in one pass without the numpy round-trip. ~25 lines, no
  data-format change, no behaviour change.
- **Ranked on simplicity, not on the timing.** ~6 % of an ambiguous query is ~5 % of a random
  workload — the same order as the machine's own noise, so the benchmark suite cannot demonstrate
  it and it must not be sold as a speed-up; what carries it is that a scalar loop over three
  elements is also the simpler code. Take the before/after with
  `prototypes/query_stage_profile.py` on both backends anyway, and record it here — it is the only
  place the number will exist.
- **Status:** open.
- **Last touched:** 2026-08-23 — halved when the stop index moved into the shortcut binary; see
  the [query-path decisions](../../decisions/query-performance-and-shortcut-index-decisions.md) for
  the dispatch-boundary rule governing the rest of this block.

## Related memory

- [Query performance and shortcut decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
