# BATCH-2 — the batch lookups are measured by nothing the CI tracks

## Related memory

- [Benchmarking and performance validation](../../../development/benchmarking-and-performance-validation.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)

- **Location:** `benchmarks/test_timezone_finding.py`, which has a case per stratum for
  `timezone_at` and none for `timezone_ids_at` / `timezone_names_at`.
- **Defect:** the batch path exists to be faster, and the only figures for it are the ones taken by
  hand for the pull request that added it — one machine, one run, recorded in `CHANGELOG.rst` and
  nowhere a regression could be caught. A change that quietly de-vectorises the prologue (a stray
  `float()` per point, a lost `tolist()`) would move nothing the trend chart plots.
- **Measured 2026-08-23**, `clang` / `in_memory=False`, min ns per point over the committed
  fixtures, N = 2,000 — the numbers a benchmark case would have to reproduce:

  | stratum | N scalar calls | batch names | batch ids |
  |---|---:|---:|---:|
  | unique | 830 | 556 (1.49x) | 523 (**1.59x**) |
  | random | 1,791 | 1,508 (1.19x) | 1,471 (1.22x) |
  | ambiguous | 11,096 | 10,860 (1.02x) | 10,753 (1.03x) |

- **Fix, and why it is not free.** Adding cases is three lines; what they cost is the rest of the
  chain. `tests/test_benchmark_names.py` pins the exact node id set, the trend chart keys on those
  ids, and `docs/benchmark_results_timezonefinding.rst` is generated — so the pull request that adds
  them owes a `make reports` run, which re-measures **every** committed figure on all four report
  pages on whatever machine runs it. That is the whole reason the API shipped without them rather
  than a slice that spent half its diff on report churn.
- **Value:** medium. Two of the three strata show a difference far above the 3–9 % noise floor, so
  unlike most performance items here this one *can* be defended by the suite.
- **Size:** S–M — small in code, medium in the regeneration it obliges.
- **Status:** open.
- **Last touched:** 2026-08-23 — recorded when the batch lookups shipped, with the hand figures they
  were measured with.
