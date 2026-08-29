# GH-364 — free-threaded Python, via a native candidate loop

- **Tracks:** issue #364, whose body now carries the full scoping — the GIL question, the
  thread-safety audit, the packaging arithmetic, the test plan and a slicing table.
- **Why it is ranked here:** one FFI crossing per query instead of per polygon, and the prerequisite
  for releasing the GIL.
- **The correction that matters, 2026-08-21:** this entry previously recorded *"numpy, h3 and cffi
  all publish free-threaded wheels, so nothing blocks"*. That was true and insufficient — **h3 4.5.0
  ships the wheel and omits `Py_mod_gil`, so `import timezonefinder` re-enables the GIL.** Fixed
  upstream (uber/h3-py#493), unreleased. The generalisable half is in the
  [public API and runtime decisions](../../decisions/public-api-compatibility-and-runtime-loading-decisions.md).
- **Two premises settled by the scoping:** the C extension **already** releases the GIL on every
  call (cffi does it automatically, ≤13 ns), and a shared instance is *correct* but does not scale —
  1.60× at 8 threads against 4.84× per-thread — so one-instance-per-thread becomes the performance
  advice rather than ceasing to be necessary.
- **The open question that decides the item, and it is now answerable:** the coordinate offset
  table took ~5 µs out of the ~9.3 µs a candidate used to cost, so what remains — roughly 830 ns of
  fetch plus ~650 ns of FFI plus the Python bbox/hole work, over 1.13 candidates on ~11 % of queries
  — may sit **inside the 3–9 % noise floor**. If it does, this cannot be justified on speed, and the
  free-threading case is weak too, since per-thread instances already scale 4.84× without it. The
  profile behind those figures is current, so settling this needs no new measurement — only the
  arithmetic, done honestly against the
  [measurement baseline](../../query-performance-measurement-baseline.md).
- **Status:** blocked on an h3 release for any claim of support. Four slices are free now — the
  `setup.py` abi3 guard, a free-threaded tox env with a strict-xfail GIL assertion, read-only arrays
  plus a state-immutability test, and the docs contradiction — and are listed on the issue.
- **Last touched:** 2026-08-21 — scoped against a real free-threaded interpreter; the report is the
  issue body and this entry keeps only the ranking-relevant half.

## Related memory

- [Query performance and shortcut decisions](../../decisions/query-performance-and-shortcut-index-decisions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
