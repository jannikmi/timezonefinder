# DOC-3 — the `zoneinfo` snippets never say that Windows needs `tzdata`

- **Location:** `docs/2_use_cases.rst`, sections *Creating aware datetime objects* and *Getting a
  location's time zone offset* — the two `ZoneInfo(tz_name)` snippets and the sentence recommending
  the stdlib module for new code.
- **Defect:** `zoneinfo` resolves keys through `zoneinfo.TZPATH`, which names system directories
  (`/usr/share/zoneinfo` and friends) that exist on Linux and macOS and do not exist on Windows;
  CPython there falls back to the `tzdata` PyPI package, which is not a dependency of
  `timezonefinder` and is not installed by anything in this repository. Both documented snippets
  therefore raise `ZoneInfoNotFoundError` on a clean Windows install, and the prose recommends the
  module without the caveat.
- **Value:** this is the first thing a new user runs, and the exception names the timezone key
  rather than the missing database, so the reader's first hypothesis is that the lookup returned a
  bad zone name — a bug report against this package rather than a one-line install.
- **Fix:** one sentence after the first snippet, saying that Windows has no system zone database
  and needs `pip install tzdata`. Deliberately *not* a dependency: `zoneinfo` is the user's choice
  of consumer, not something this package imports, and `pytz` users need nothing. Size: ~3 lines.
  GH-502 inherits the same caveat if it lands first.
- **Status:** open — the snippets arrived in 8.3.0 without the caveat; PR #538 added the explicit
  recommendation on top of them, also without it. Docs-only, so no decision is needed.
- **Last touched:** 2026-08-20 — found while reviewing PR #538. Verified the mechanism rather than
  the platform: `zoneinfo.TZPATH` holds only system paths, `tzdata` is absent from the environment
  and undeclared in either `pyproject.toml`.

---
