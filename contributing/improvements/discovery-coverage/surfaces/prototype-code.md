# Prototype code discovery coverage

## Baseline

- **Delta anchor:** `72678a1`.
- **Coverage state:** inside improvement-pass scope since 2026-09-07, when the maintainer reversed the blanket exclusion; still periphery for ranking, so reach it through a signal rather than a sweep.

## Covered subjects

- `prototypes/query_stage_profile.py`'s `FINDINGS` were reconciled with the query measurement baseline.

## Known uncovered deltas

- `prototypes/shortcut_resolution_query_bench.py` has a stale header describing the fixed shortcut-coverage gap and naming `is_special` as the likely repair site.
- Exploratory lint debt is still intentionally not discovery work: the scope reversal left the ruff and mypy exclusions in place.
- No prototype has been read against `prototypes/README.md`'s one-row-per-script pairing since the reversal.

## Next useful gap

- Correct the stale header in `prototypes/shortcut_resolution_query_bench.py`, which the reversal makes takeable on its own.
