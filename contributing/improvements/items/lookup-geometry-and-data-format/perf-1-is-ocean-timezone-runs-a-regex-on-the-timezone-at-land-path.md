# PERF-1 — `is_ocean_timezone` runs a regex on the `timezone_at_land` path


## Related memory

- [Query performance and shortcut decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- **Location:** `timezonefinder/utils.py`, `is_ocean_timezone`; called from
  `AbstractTimezoneFinder.timezone_at_land`.
- **Defect:** the check is `re.match(OCEAN_TIMEZONE_PREFIX, timezone_name)` against the result
  *string*, on every call. Ocean-ness is a fixed property of a zone id for a given dataset, so this
  recomputes a constant from a string per query and couples a behavioural decision to zone naming:
  an upstream rename of the `Etc/GMT` family would silently change which results count as ocean.
- **The ceiling has been taken, and the prediction held.** One `re.match` per `timezone_at_land`
  call, measured at ~310 ns against ~58 ns for the `str.startswith` that replaces it — so the check
  costs ~250 ns, which is ~21 % of a unique-shortcut query, ~2 % of an ambiguous one, and **~6 % of
  a mixed `timezone_at_land` workload** once the strata are weighted. That is inside the 3–9 % noise
  floor, so the benchmark suite cannot demonstrate it even though the saving is real: per the
  ranking rule this ships on simplicity, not as a speed-up, and no before/after in a no-numba
  environment is worth taking. (Numba backend, mapped mode, anchor machine class; the count and the
  ratio travel, the nanoseconds do not.)
- **Fix, corrected.** `OCEAN_TIMEZONE_PREFIX` is `r"Etc/GMT"` — no regex metacharacters — and
  `re.match` anchors at the start, so `name.startswith(OCEAN_TIMEZONE_PREFIX)` is **exactly**
  equivalent and captures the whole measured saving in one line. The boolean array this entry
  originally proposed buys nothing further on speed and is not free: `timezone_at_land` receives a
  *name*, and `is_ocean_timezone` takes one, so an id-indexed array means restructuring both plus a
  per-instance array that `make memory` would show. What the array alone buys is decoupling the
  behaviour from zone naming — worth having only if upstream ever renames the `Etc/GMT` family, and
  the cheap change does not foreclose it.
- **Value:** low to moderate. `timezone_at_land` is public and the packaged data covers the oceans,
  so the branch is taken constantly — but the regex runs on the *result*, after the lookup that
  dominates the query.
- **Decided, 2026-08-20 — take the one-line `str.startswith`, not the boolean array.** The options
  put were: the equivalent one-liner; the precomputed array indexed by zone id that this entry was
  written around; or the one-liner now and the array only if upstream ever renames the `Etc/GMT`
  family. The first was chosen. It ships as a simplification rather than as a speed-up, per the
  measured ceiling above. The array is refused for now and the reason recorded below, so it is not
  re-proposed when this entry is deleted.
- **What implementing it means:** one line in `timezonefinder/utils.py`, and the `import re` goes
  with it if nothing else in the module uses it. Keep `OCEAN_TIMEZONE_PREFIX` as the constant so the
  prefix is still declared once. Changelog bullet in the **Internal** list — no observable behaviour
  changes.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-20 — ceiling measured, the proposed fix corrected to its one-line
  equivalent, then decided.
