# GH-502 — first-class `zoneinfo` / UTC-offset helpers


## Related memory

- [Public API and runtime-loading decisions](../../decisions/public-api-compatibility-and-runtime-loading-decisions.md)
- **Tracks:** issue #502, which carries the API sketch and the sign-convention trap.
- **Why it is ranked here:** moves the two most common downstream steps into the library, and the library is the only party that knows the `Etc/GMT±X` convention is inverted.
- **Decided, 2026-08-21 — ship the full set** (`zoneinfo_at`, `utc_offset_at`, `localize`, mirrored in `global_functions.py`). Additive, so it needs no major — but it should ride the API major so the documentation is rewritten once.
- **Its strongest argument is half spent, and the entry says so rather than letting it read as current:** #538 added the sign warning to `docs/2_use_cases.rst`, so the case is now the narrower one of readers who never open that page. That page also explains that Windows needs the separately installed `tzdata` package; any helper returning a `ZoneInfo` inherits the same platform caveat and must document it at its own call site.
- **Status:** open — decision taken, implementation not started.
- **Last touched:** 2026-08-21 — decided; the reasoning and the #538 correction written to the issue.
