# Data and conversion script discovery coverage

## Baseline

- **Delta anchor:** `c068642`.
- **Coverage state:** broad triage with explicit unreviewed deltas.

## Covered subjects

- End-to-end or targeted reviews covered `scripts/reporting.py`, `scripts/render_benchmark_reports.py`, `scripts/describe_benchmark_machine.py`, `scripts/timezone_data.py`, and `scripts/measure_memory.py`.
- They also covered `scripts/generate_benchmark_fixtures.py`, `scripts/benchmark_utils.py`, `scripts/file_converter.py`, `scripts/data_integrity.py`, `scripts/check_data_dependency.py`, and `scripts/data_releases.py`.
- `scripts/hex_utils.py`, including the `Hex` cache properties, `scripts/shortcuts.py`, and `scripts/utils.py` received targeted review.
- Converter invocation was compared across `Makefile`, `update_data.sh`, and `docs/2_use_cases.rst`.
- `update_data.sh` was read end to end around tag resolution and download, together with `scripts/upstream_release.py`.

## Known uncovered deltas

- `scripts/block_index.py`, `scripts/measure_query_latency.py`, and `scripts/tune_block_size.py` have not received an independent review since they arrived with the latitude block index.
- `scripts/bootstrap_data.py`, including the path that unpacks a CI-built wheel for a data version absent from PyPI, has not received an independent review since it arrived with the data bootstrap.
- `scripts/assert_acceleration_path.py`, `scripts/data_integrity.py`, `scripts/file_converter.py`, `scripts/render_benchmark_reports.py`, `scripts/timezone_data.py`, and `scripts/utils.py` changed with the frame-of-reference payload in `7c06d0c` and have not received an independent review of those deltas.

## Durable evidence

- Tooling and packaging non-findings live in [developer tooling and packaging checks](../../checked-and-found-sound/developer-tooling-and-packaging-checks.md).

## Next useful gap

- Read the three block-index scripts, starting with `scripts/block_index.py`, whose output controls what the kernels skip; then delta-review the frame-of-reference script changes listed above.
