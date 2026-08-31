# Benchmark and report discovery coverage

## Baseline

- **Delta anchor:** `72678a1`.
- **Coverage state:** broad review of the original benchmark suites and report tooling, with explicit newer deltas.

## Covered subjects

- `benchmarks/conftest.py`, `benchmarks/test_initialization.py`, `benchmarks/test_inside_polygon.py`, and `benchmarks/test_timezone_finding.py` were read in full.
- The batch lookup cases and their generated-report summaries received targeted coverage.
- `scripts/normalize_benchmark_json.py`, `scripts/compare_benchmark_runs.py`, and `scripts/benchmark_noise.py` were read.
- `scripts/describe_benchmark_machine.py`, `scripts/measure_memory.py`, and `scripts/render_benchmark_reports.py` were read.

## Known uncovered deltas

- `benchmarks/test_comparison.py` has only a recorded case-list review.
- The per-query latency harness is newer than the broad sweep.

## Durable evidence

- Refused findings live in [testing and benchmarking checks](../../checked-and-found-sound/testing-and-benchmarking-checks.md).

## Next useful gap

- Read `benchmarks/test_comparison.py` end to end, then delta-review benchmark or report code changed after `72678a1`.
