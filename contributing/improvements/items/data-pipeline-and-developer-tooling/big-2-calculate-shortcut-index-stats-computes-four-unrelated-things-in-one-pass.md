# BIG-2 — `calculate_shortcut_index_stats` computes four unrelated things in one pass

- **Location:** `scripts/reporting.py`, `calculate_shortcut_index_stats`.
- **Defect:** computes coverage, uniqueness, storage and frequency metrics in one pass.
- **Fix:** split along those four seams. Its output is committed in `docs/data_report.rst`, so it
  needs a regenerate-and-diff to prove neutral — cheap: `uv run python -m scripts.reporting`, then
  confirm `git diff docs/data_report.rst` is empty. Size: ~80 lines moved.
- **Value:** readability only, and lower than when this entry was written. The title used to read
  "13 branches / 57 statements, over ruff's `PLR0912`/`PLR0915` defaults"; replacing the hard-coded
  H3 ladder removed six branches, so it now trips neither (40 statements against a default of 50).
  Nothing in CI asks for this split any more.
- **Status:** open.
- **Last touched:** 2026-08-14 — re-verified and corrected.
