# BENCH-3 — the tracked measurement and the published pages describe different experiments

## Related memory

- [Benchmarking and performance validation](../../../development/benchmarking-and-performance-validation.md)
- [Benchmarking tooling and dependency decisions](../../decisions/benchmarking-tooling-and-dependency-decisions.md)
- **Location:** `Makefile`'s `benchmarks-ci` and `benchmark-noise` targets against its `benchmarks` / `latency` / `memory` targets and the `BENCHMARK_ENV` they use, `scripts/normalize_benchmark_json.py`, `scripts/render_benchmark_reports.py`, and the `measure` job in `.github/workflows/benchmark.yml`.
- **What it is.** The repository takes two benchmark measurements that read as one. Neither is wrong for its own purpose, but nothing states how they differ, so a number from the trend chart and a number from `docs/benchmark_results_*.rst` cannot be compared even when they carry the same benchmark name.

  | | `benchmarks-ci` (tracked) | `make reports` (published) |
  |---|---|---|
  | selection | `-m benchmark_core` | `-m benchmark`, the full suite |
  | rounds | `--benchmark-min-rounds=50` | pytest-benchmark's default, observed 30-215 |
  | reported value | normalised to the `min` estimator | tables led by `Mean`, with `Median` / `StdDev` / `Min` / `Max` beside it |
  | environment | this checkout's environment | `--isolated --group test --group compare` |
  | scope | timings only | timings plus `latency` and `memory`, plus the data report |

- **The defect inside the divergence, confirmed on this checkout.** `benchmarks-ci` runs under plain `uv run` while `benchmarks` runs under `$(BENCHMARK_ENV)`, and `timezonefinder/utils.py` binds the point-in-polygon backend at import time, preferring numba whenever it is importable. `make install` syncs `--all-groups`, so numba *is* importable here and `timezonefinder.utils.using_numba` is `True`: run locally, `benchmarks-ci` and `benchmark-noise` measure the numba kernel while `BENCHMARK_ACCELERATION_PATH` is `clang` and every committed page asserts clang. Only CI is protected, and by a separate workflow step rather than by the target. `benchmarks` asserts the path itself; `benchmarks-ci` does not.
- **Why it is ranked here:** the mismatch silently mis-measures anything read locally off the CI target — including the release workflow's own noise gate, which is why that step now asserts the path before reading the floor. A gate that characterises a different implementation than it gates is worth more than the readability work below it and less than anything that changes an answer.
- **Not a call to unify the two runs.** They answer different questions and merging them damages both: the tracked measurement exists to detect a *delta* between head and merge base on one runner, so it wants a small fast subset and a noise-resistant estimator; the pages exist to tell a reader what to *expect*, so they want the full workload, absolute values, the tail distribution and the cross-package comparison. Folding the pages into CI's subset would delete the comparison and the tails; folding CI into the pages' suite would multiply a per-pull-request cost that is already a double checkout and a two-pass sandwich.
- **What reconciliation means instead.** Make the difference asserted rather than incidental: give `benchmarks-ci` the same acceleration-path assertion `benchmarks` already has, so no environment can substitute a kernel silently; state on the pages which rows are the tracked core set and which estimator CI records for them, so a reader moving between the chart and the docs knows why two numbers differ; and pin the pages' round count rather than inheriting a default that varies per benchmark, since a table printing `Rounds` 30 beside 215 invites comparison across rows that were not measured alike.
- **Sequenced under BENCH-2, not blocked by it.** BENCH-2 is decided — the pages move to CI — so machine and environment stop differing once it lands and what remains here is selection, rounds and estimator. The acceleration-path assertion is independent of it and can be taken today; in a CI-rendered world it still matters, because the target that lacks it is the one anyone runs locally.
- **Validation:** a test asserting that every make target which measures also asserts the acceleration path; a rendered page naming its estimator and its tracked subset; and `make benchmark-noise` failing rather than reporting a floor when the bound backend is not the asserted one.
- **Status:** open — free; the assertion half is mechanical and the reporting half needs no decision that is not already recorded.
- **Last touched:** 2026-09-02 — recorded when the release workflow's noise gate was found to read the numba kernel in a development environment.
