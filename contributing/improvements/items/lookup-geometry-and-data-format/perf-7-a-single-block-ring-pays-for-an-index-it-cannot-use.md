# PERF-7 — a single-block ring pays for a block index it can never skip with


## Related memory

- [Query-path and shortcut-index decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- **No issue tracks this; found 2026-08-30 while measuring the latitude block index that created it.**
- **What it is.** 29.7 % of boundary polygons fit in a single block, and for those the filter is pure overhead: `pip_with_bbox_check` has already rejected every point outside the ring's bounding box, and a single block's latitude range is that bounding box's — so by the time the kernel runs, the one block always survives and the scan is the full ring either way. What is paid for that is one list-bounded slice (~117 ns) plus, on the clang path, a third `ffi.from_buffer` (~250 ns).
- **What it costs, measured.** `prototypes/query_stage_profile.py` prices one point-in-polygon call on the `small` stratum (112 vertices) at **2,200 ns against 1,802 ns before the index**, clang and memory-mapped — the only stratum the index makes *worse*. The `medium` stratum falls 3,292 → 2,218 ns and `large` 22,968 → 2,488 ns, which is why the whole-query result is decisively positive and this is a residue rather than a regression. The numba path pays only the slice, since it crosses no FFI boundary.
- **The shape of the fix.** `PolygonArray.pip` resolves `(start, stop)` from `block_offsets` first and calls the unblocked kernel when `stop - start == 1`. `HoleArray` resolves ids through `poly_ref`, so the pair has to be overridden together exactly as `coords_of` / `block_ranges_of` already are — that is the trap, and the one this item must not re-discover.
- **Why it was not taken with the index itself.** ~200 ns on an average point-in-polygon call is ~3 % of an ambiguous query and well under the 3–9 % noise floor, so no benchmark in this repository could demonstrate it. The [register rules](../../improvement-register-rules.md) rank such a change on simplicity instead, and a branch on the hot path is not simpler than no branch. It needs the count argument above to be worth anything, which is why the count is recorded here rather than the timing.
- **Check before taking it** that the bounding-box argument still holds: it depends on `pip` only ever being reached through `pip_with_bbox_check`. `certain_timezone_at` and the hole loop both go through it today; a future caller that does not would make the skip real for single-block rings and this item wrong.
- **Status:** open — free, small, and ranked low because it is below what any benchmark here can resolve.
- **Last touched:** 2026-08-30 — created from the profiler's `small` stratum row when the latitude block index landed.
