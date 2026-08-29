# DEAD-6 — `_iter_boundaries_in_shortcut` has no caller outside the test suite

- **Location:** `timezonefinder/timezonefinder.py`,
  `AbstractTimezoneFinder._iter_boundaries_in_shortcut`.
- **Defect:** a method on the shipped base class whose only call site in the whole tree is
  `tests/main_test.py`. `TimezoneFinder.timezone_at` and `certain_timezone_at` both inline the same
  `match` on the shortcut value rather than calling it, so it is a third copy of that dispatch that
  nothing in the package executes — and being a copy, it can drift from the two that matter without
  any test noticing, since the test that calls it is the only thing pinning it.
- **Fix:** delete it and have the test walk the shortcut mapping directly, or — if it is meant as
  the readable form of a dispatch the hot paths inline for speed — say so in a comment naming the
  two inlined copies, so the next reader does not delete the wrong one. Size: ~20 lines either way.
- **Value:** low, and it is the *drift* that carries it rather than the dead weight. Ranked
  accordingly.
- **Status:** open.
- **Last touched:** 2026-08-20 — found while tracing BIG-1's call sites.
