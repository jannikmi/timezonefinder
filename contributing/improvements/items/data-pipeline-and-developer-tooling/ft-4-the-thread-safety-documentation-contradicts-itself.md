# FT-4 — the thread-safety documentation contradicts itself

- **Where:** `docs/architecture.rst`, the global-functions paragraph ("they are *not* thread-safe"); `docs/1_usage.rst`, both the usage note ("you **must** create separate `TimezoneFinder` instances for each thread/process. This is the only way to guarantee thread-safe concurrent timezone lookups") and the parallel-computation note; `timezonefinder/global_functions.py`, the module docstring and `timezone_at`'s note, which call the singleton thread-safe for concurrent reads.
- **Defect:** two published pages state the opposite of each other about the same functions, so a reader gets whichever answer they happen to open first.
- **Which one is wrong, and why this is not a maintainer question:** `docs/architecture.rst` is. The audit behind issue #364 found no mutable state to race on — every `self.<attr> = …` in `timezonefinder.py`, `polygon_array.py` and `coord_accessors.py` sits in `__init__`, `cleanup` or `__del__`; there are no module-level caches and no `lru_cache` anywhere in `timezonefinder/`; the mapped path is `mmap` plus `np.frombuffer`, random access with no shared file position and therefore no seek to serialise; and the loaded arrays are now read-only, asserted by `tests/test_resource_management.py`. `_get_tf_instance` initialises under double-checked locking over that immutable state. The code and the tests already say what is true; only one page disagrees with them.
- **The correction the per-thread advice needs is the harder half.** "Create one instance per thread" is right and its stated reason is not: it is not needed for correctness, it is needed for *throughput*. A shared instance scales 1.60x at 8 threads against 4.84x per-thread on a free-threaded build, and `TimezoneFinderL` collapses identically with no polygon data at all — so this is reference-count contention on shared objects, not the mmap, the accessor or the candidate loop. On a GIL-enabled build the distinction is invisible (0.73x–0.99x either way). Say that, rather than deleting the advice or leaving a correctness claim standing under it.
- **What must not be written:** that a shared instance is as fast, or that per-thread instances are optional. Both readings are available from a careless fix, and both are wrong.
- **Size:** S — three sites, prose only.
- **Status:** open.
- **Detail:** issue #364 carries the audit table and the scaling measurements.

## Related memory

- [Documentation maintenance rules](../../../development/documentation-maintenance-rules.md)
- [Public API and compatibility contract](../../../project/public-api-and-compatibility-contract.md)
