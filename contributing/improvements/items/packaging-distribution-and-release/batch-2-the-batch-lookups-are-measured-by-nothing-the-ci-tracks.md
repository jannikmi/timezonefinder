# BATCH-2 — the batch lookups are measured by nothing the CI tracks

## Related memory

- [Benchmarking and performance validation](../../../development/benchmarking-and-performance-validation.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)

- **Location:** `benchmarks/test_timezone_finding.py` now reports `timezone_ids_at` and `timezone_names_at` over the random, unique-shortcut, and ambiguous-shortcut strata, but those cases are not yet in `benchmark_core`.
- **Defect:** the batch path exists to be faster, but CI still tracks only scalar lookup. A change that quietly de-vectorises the prologue or adds a Python pass over the result moves no trend-chart metric.
- **Measured 2026-08-23**, `clang` / `in_memory=False`, min ns per point over the committed fixtures, N = 2,000:

  | stratum | N scalar calls | batch names | batch ids |
  |---|---:|---:|---:|
  | unique | 830 | 556 (1.49x) | 523 (**1.59x**) |
  | random | 1,791 | 1,508 (1.19x) | 1,471 (1.22x) |
  | ambiguous | 11,096 | 10,860 (1.02x) | 10,753 (1.03x) |

- **Remaining slice:** merge PR #566 first so the trusted `workflow_run` consumer on `master` can compare the shared IDs while reporting the six new head-only IDs. Then mark the batch cases `benchmark_core`, run at least five `workflow_dispatch` repetitions on fresh runners, derive `ALERT_THRESHOLD` from the worst spread with `scripts/benchmark_noise.py`, and update the methodology and changelog with the measured threshold. Do not guess the existing 180% threshold applies to the expanded set.
- **Value:** medium. Two strata show a difference above the 3–9% same-machine noise floor, so the suite can catch meaningful batch regressions once calibrated.
- **Size:** S — the cases and reports exist; only safe CI promotion and calibration remain.
- **Status:** blocked until PR #566 lands, then ready for measurement.
- **Last touched:** 2026-08-30 — split after review identified the default-branch comparator ordering and unmeasured expanded threshold.
