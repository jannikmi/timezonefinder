# BIG-1 — `_iter_boundary_ids_of_zone` re-opens `zone_positions.npy` on every call

- **Location:** `timezonefinder/timezonefinder.py`, `_iter_boundary_ids_of_zone`.
- **Defect:** calls `np.load(..., mmap_mode="r")` per invocation, under a comment reading *"load only on demand"*. Off the `timezone_at` hot path — that method inlines the shortcut branch and never calls the iterator — but on `certain_timezone_at`'s and `get_geometry`'s.
- **What it removes, as a count:** **one file open, header parse and `mmap` per call**, for a file that is read twice and never changes. Same shape as the per-candidate accessor rebuild the coordinate offset table removed — a per-call rebuild of something constant — on a different function, which is the reason to expect more of these rather than to treat the pattern as done with.
- **Measured.** Numba backend, mapped mode, anchor machine class; `certain_timezone_at` is not one of the [measurement baseline](../../query-performance-measurement-baseline.md), so the share below is of that call, not of a workload:

  | | today | with the array read once | share of the call |
  |---|---|---|---|
  | `certain_timezone_at`, Berlin | 198 µs | 83 µs | 58 % |
  | `certain_timezone_at`, Moscow | 188 µs | 78 µs | 58 % |
  | `certain_timezone_at`, Aspen CO | 142 µs | 29 µs | 79 % |
  | `certain_timezone_at`, Pacific ocean | 129 µs | 19 µs | 85 % |
  | `get_geometry`, Berlin | 6.60 ms | 5.88 ms | 11 % |

Reproduced twice against a generator of identical shape, so the delta is the `np.load` and not generator overhead. The absolute figures are this machine's; the ratios and the count are not.
- **The memory/latency trade this was blocked on does not exist.** `zone_positions.npy` is **1,018 bytes** — 445 `uint16`. Reading it into memory at construction costs about a kilobyte per instance and *removes* a per-call mmap rather than adding a resident one, so the mapped mode gets strictly better rather than paying for the fast one. `zone_ids` (2,772 B) is already read eagerly in the same `__init__`, which makes the current laziness an inconsistency rather than a strategy. Needs one `__slots__` entry.
- **Decided, 2026-08-20 — cache lazily on first use, do not read it at construction.** The options put were: read the array eagerly in `__init__` (no open mapping, but the cost lands on every construction); cache the mapping lazily on first use (free construction, one mapping pinned for the instance lifetime, a `cleanup()` path to write); or leave it. The second was chosen, against the eager reading this entry originally recommended, and **the reason is the one the eager case under-weighted**: `zone_positions` serves only `certain_timezone_at` and `get_geometry`, which the `timezone_at` majority never calls, so an eager read charges every user for an array most of them do not touch — on a path that is *itself* a tracked benchmark (`docs/benchmark_results_initialization.rst`) and that the documented one-instance-per-thread pattern multiplies by the thread count. Lazily, the cost is paid once by the callers who want it and by nobody else. The pinning objection that once made this trade hard for the coordinate accessor does not apply at a kilobyte — and no longer applies there either, since that cache holds integers.
- **What implementing it means:** one `__slots__` entry holding the mapping, populated on first call and released in `cleanup()` next to the boundary and hole accessors — `close_resource` already takes anything with a `close()`, so `__del__` and the context manager are covered by the existing two-tier handler rather than by a third path. The "load only on demand" comment stays true and starts being accurate.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-20 — measured, re-ranked into the performance cluster on the strength of it, then decided. The benchmark the entry was waiting on has been taken.

## Related memory

- [Query performance and shortcut decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
