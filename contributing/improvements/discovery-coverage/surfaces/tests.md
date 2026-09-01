# Test discovery coverage

## Baseline

- **Delta anchor:** `72678a1`.
- **Coverage state:** every test module present at the anchor had been read at least once according to the migrated inventory.

## Covered subjects

- Focused reviews covered `tests/main_test.py`, `tests/auxiliaries.py`, `tests/test_package_contents.py`, and `tests/test_benchmark_ci_tooling.py`.
- They also covered `tests/test_render_benchmark_reports.py`, `tests/shortcut_test.py`, `tests/test_integration.py`, `tests/test_script_invocations.py`, and `tests/utils_test.py`.
- An AST scan enumerated every multi-statement `pytest.raises` and `pytest.warns` block.
- `ZoneCollection` validators received direct-test coverage review.

## Durable evidence

- Refused test and benchmark findings live in [testing and benchmarking checks](../../checked-and-found-sound/testing-and-benchmarking-checks.md).

## Next useful gap

- Delta-review tests added or substantially rewritten after `72678a1`.
