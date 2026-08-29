# PERF-4 — the mapped fetch re-acquires the mmap's buffer on every candidate


## Related memory

- [Query performance and shortcut decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- **Location:** `timezonefinder/flatbuf/io/polygons.py`, `read_polygon_array_at`.
- **What it was.**
  Addressing polygons by `(offset, length)` took the mapped fetch from ~4.9 µs to ~830 ns, against ~60 ns for `in_memory=True`.
  What remains of that gap is not I/O and not the vtable: `np.frombuffer(self.coord_buf, …)` re-acquires the `mmap` object's buffer on every call.
  Slicing a **single whole-file `int32` view** instead measures **415 ns against 788 ns** per fetch in isolation.
- **Rejected 2026-08-23 by the maintainer, and kept rather than deleted** because the per-fetch figure above is genuinely large and the idea will otherwise be re-proposed on it.
  That figure is not what a query pays.
  Measured inside `timezone_at`, alternating the two implementations round by round within one process — the design BENCH-1 records as the only one that does not attribute warm-up to the change — over the committed fixtures, 2000 points per stratum:
  **−2.0 % on the ambiguous stratum (12 of 15 rounds) and −0.8 % on a mixed workload (9 of 15, which is a coin flip)**.
  The absolute per-candidate saving reproduces at ~230–320 ns; the *share* this entry previously claimed, "~3 % of a mixed workload", does not.
  A ceiling near 1 % sits below the machine's own noise floor, so by the ranking rule above it would have to stand on correctness or simplicity instead.
  It stands on neither: it changes no answer, and it splits the file-backed fetch into a slice here and `read_polygon_array_at` there.
- **The pinning objection turned out to be the weaker half, and that is the part worth keeping.**
  A whole-file view is a live export held for the accessor's lifetime, which is the pattern behind the `BufferError` fixed in 8.3.0.
  `cleanup()` closes before it drops: `close_resource(coord_buf)` runs first and the `delattr` loop over `coord_offsets`/`coord_lengths`/`coord_buf`/`coord_file` runs after it.
  So a view held as an attribute is **still live when the close is attempted**, `mmap.close()` raises `BufferError`, and `close_resource` swallows it — the mapping would stay open until the accessor is collected, which is exactly the deterministic unmap 8.3.0 restored.
  That is a fixable ordering, not a prohibition: a held view obliges `cleanup()` to delete it *before* the `close_resource(coord_buf)` call and to name it in that loop.
  An accessor-lifetime export is therefore **not** in itself a reason to refuse a change here — the reason this one was refused is the measurement.
  Anything that re-proposes a held view has to clear the noise floor *and* carry that `cleanup()` change; arguing that the mapping stays unpinned is not enough, and today's ordering does not give it for free.
- **Status:** rejected — measured inside the query and found below the noise floor.
- **Last touched:** 2026-08-23 — measured in-query, and rejected on that measurement.
