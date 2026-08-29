# PERF-6 — scalar `njit` helpers on the query path cost more to call than to compute

- **Location:** `timezonefinder/utils_numba.py` — `is_valid_lat` / `is_valid_lng`, reached through `utils.validate_coordinates` on **every** query, and `coord2int`, called twice on every ambiguous one.
- **Measured 2026-08-23**, per call, against writing the same expression inline:

  | | `njit` call | inline Python | boundary |
  |---|---|---|---|
  | `is_valid_lat` | 87.8 ns | 40.6 ns | **+47 ns**, 2x per query |
  | `coord2int` | 94.7 ns | 46.4 ns | **+48 ns**, 2x per ambiguous query |

So coordinate validation spends ~94 ns of a ~1,000 ns unique-zone query crossing a boundary to perform two comparisons — **more than the whole slot-arithmetic reduction that shipped in the same pass was worth**.
- **Why these and not the kernel.** `pt_in_poly_python` is over an array of hundreds to tens of thousands of vertices, so its dispatch is amortised to nothing and numba earns its place. These three take scalars and do one operation. The rule is in the [query-path decisions](../../decisions/query-performance-and-shortcut-index-decisions.md): no scalar per-query stage in the single-digit hundreds of nanoseconds survives a dispatch boundary.
- **What makes it awkward, and why it is not simply "inline them".** `njit` is a no-op decorator when numba is absent (`_numba_replacements.py`), which is the tracked CI configuration and what a plain `pip install` gives — so the penalty is paid by users who installed numba *for speed*, and any fix has to leave the no-numba path no worse. Inlining the expressions at the call site satisfies both, at the cost of the duplication DUP-1 is separately about.
- **Sequencing:** overlaps DUP-1, which wants the same bounds literals imported rather than duplicated, and reaches the opposite conclusion about touching this code. Settle them together or the second will undo the first.
- **Status:** open — free, needs a whole-query A/B rather than the microbenchmark above.
- **Last touched:** 2026-08-23 — measured while refusing numba for the slot arithmetic.

---

## Related memory

- [Query performance and shortcut decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
