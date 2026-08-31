# Prototype code discovery coverage

## Baseline

- **Delta anchor:** `72678a1`.
- **Coverage state:** deliberately outside normal improvement-pass scope.

## Covered subjects

- `prototypes/query_stage_profile.py`'s `FINDINGS` were reconciled with the query measurement baseline.

## Known uncovered deltas

- `prototypes/shortcut_resolution_query_bench.py` has a stale header describing the fixed shortcut-coverage gap and naming `is_special` as the likely repair site.
- Exploratory lint debt is intentionally not discovery work for an ordinary pass.

## Next useful gap

- Correct the stale header only when that prototype is otherwise in scope.
