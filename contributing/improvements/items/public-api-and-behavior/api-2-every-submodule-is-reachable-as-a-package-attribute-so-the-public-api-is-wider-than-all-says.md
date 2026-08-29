# API-2 — every submodule is reachable as a package attribute, so the public API is wider than `__all__` says


## Related memory

- [Public API and runtime-loading decisions](../../decisions/public-api-compatibility-and-runtime-loading-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Location:** `timezonefinder/__init__.py`.
- **Defect:** `__all__` constrains `import *` only. Because `__init__.py` imports from `timezonefinder.timezonefinder` and `timezonefinder.global_functions`, and those import further modules, `dir(timezonefinder)` also exposes `utils`, `configs`, `polygon_array`, `coord_accessors`, `flatbuf`, `np_binary_helpers`, `zone_names`, `utils_clang`, `utils_numba` and `inside_polygon_ext`. `docs/4_api.rst` documents seven names; roughly twenty are reachable, and `timezonefinder.utils.validate_coordinates` is as importable as the documented API while being covered by no stability promise.
- **Fix:** a module-level `__getattr__` (PEP 562) for lazy submodule access, which narrows the eagerly bound surface and keeps submodule imports out of `import timezonefinder`. Size: ~20 lines.
- **Why it is not a straight refactor:** removing an attribute someone imports today is a breaking change even though it was never documented, so this needs a decision on whether to deprecate first. Same shape as API-1. Note that under PEP 562 `import timezonefinder.utils` keeps working either way — only `timezonefinder.utils` as an *attribute* of the already-imported package changes, which is a much narrower break than the entry's framing suggests.
- **One of the twenty needs no decision and should not wait for one.** The exact count is 20 public names against `__all__`'s 7, and the twentieth is not a submodule: `PackageNotFoundError`, the stdlib exception bound by the version lookup at the bottom of `__init__.py`. Renaming it to `_PackageNotFoundError` is one character of intent over a name nobody can be depending on deliberately. **Split it out** — bundling it with the twelve submodules makes an unarguable one-line fix wait on an arguable design decision.
- **It also decides API-1's blast radius**, since `AbstractTimezoneFinder` is public only through this seam. Answer this one first.
- **Decided, 2026-08-21 — PEP 562 `__getattr__`, without a deprecation cycle.** Chosen over warning for a minor first, and over documenting the surface and changing nothing. The break is narrower than it looks: `import timezonefinder.utils` keeps working, and only attribute access on the already-imported package changes. It also removes the eager submodule binding from `import timezonefinder`, which is a small import-time win. **Breaking**, so it ships in the same major as API-1 — and it goes **first within that major**, since it decides how much surface API-1 touches.
- **The `PackageNotFoundError` half does not wait for the major.** Renaming it to `_PackageNotFoundError` breaks nothing anyone could have relied on deliberately and can ship at any time.
- **Status:** open — decision taken, held for the next major (bar the exception rename).
- **Last touched:** 2026-08-21 — decided, and bound to the batched-major decision.

---
