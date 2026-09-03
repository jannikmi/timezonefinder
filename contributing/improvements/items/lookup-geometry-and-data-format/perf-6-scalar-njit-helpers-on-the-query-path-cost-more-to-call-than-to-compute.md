# PERF-6 — scalar `njit` helpers on the query path cost more to call than to compute

- **Location:** `timezonefinder/utils_numba.py` — `is_valid_lat` / `is_valid_lng`, reached through `utils.validate_coordinates` on **every** query, and `coord2int`, called twice on every ambiguous one.
- **Measured 2026-08-23**, per call, against writing the same expression inline:

  | | `njit` call | inline Python | boundary |
  |---|---|---|---|
  | `is_valid_lat` | 87.8 ns | 40.6 ns | **+47 ns**, 2x per query |
  | `coord2int` | 94.7 ns | 46.4 ns | **+48 ns**, 2x per ambiguous query |

So coordinate validation spends ~94 ns of a ~1,000 ns unique-zone query crossing a boundary to perform two comparisons — **more than the whole slot-arithmetic reduction that shipped in the same pass was worth**.
- **Why these and not the kernel.** `pt_in_poly_python` is over an array of hundreds to tens of thousands of vertices, so its dispatch is amortised to nothing and numba earns its place. These three take scalars and do one operation. The rule is in the [query-path decisions](../../decisions/query-performance-and-shortcut-index-decisions.md): no scalar per-query stage in the single-digit hundreds of nanoseconds survives a dispatch boundary.
- **What makes it awkward, and why it is not simply "inline them".** `njit` is a no-op decorator when numba is absent (`_numba_replacements.py`), which is the tracked CI configuration and what a plain `pip install` gives — so the penalty is paid by users who installed numba *for speed*, and any fix has to leave the no-numba path no worse. Inlining the expressions at the call site satisfies both, provided the inline form reads the bounds constants rather than restating the literals.
- **Sequencing:** the bounds themselves are now declared once, as `MIN_*` / `MAX_*` in `configs.py`, and `is_valid_lat` / `is_valid_lng` read them. An inline form must keep reading them, not re-introduce the literals: the constant load measured ~5 ns per query against the ~94 ns of dispatch this item is about, so the two do not trade against each other, and the comment beside the constants says why they are declared pre-negated.
- **Status:** open — free, needs a whole-query A/B rather than the microbenchmark above.
- **Last touched:** 2026-08-23 — measured while refusing numba for the slot arithmetic.

---

## Related memory

- [Query performance and shortcut decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
