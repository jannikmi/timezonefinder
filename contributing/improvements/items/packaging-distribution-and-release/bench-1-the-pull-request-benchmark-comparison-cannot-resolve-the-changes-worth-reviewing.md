# BENCH-1 — the pull request benchmark comparison cannot resolve the changes worth reviewing


## Related memory

- [Data distribution, packaging, and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- **Location:** `scripts/compare_benchmark_runs.py`, `scripts/benchmark_utils.py`
  (`DEFAULT_BENCHMARK_ESTIMATOR`), `benchmarks/`.
- **What it is.** Base and head are measured in two sequential runs, minutes apart, each reduced to
  a single `min`. Everything that drifts between them is attributed to the change, and nothing in
  the output lets a reader tell a real difference from that drift. The comparison is flagged at
  110 % and is reporting-only, and `docs/benchmarking_methodology.rst` already concedes it is
  "blind to the 10-30 % changes actually worth reviewing".
- **Why it is now more than a known limitation:** it was measured, while comparing two shortcut
  structures. **Within a single process**, alternating the two paths round by round against running
  one after the other moved a measured difference from **−13.3 % to −0.3 %** on the unique
  stratum — the whole thirteen points were the first path warming `validate_coordinates`,
  `h3.latlng_to_cell` and `zone_name_from_id` for the second. Two separate processes minutes apart
  have at least that much room, and nothing characterises it. Separately, `min` alone reported
  +0.5 % where a round-level sign count said 26 of 61 — the disagreement being the correct answer,
  "no effect", which a single estimator cannot express.
- **Why it is ranked here:** the remaining performance items — GH-364 among them — each have to demonstrate an effect in the low single digits, and none of them can be reviewed with this tooling.
  Each one currently needs a hand-rolled prototype harness; the shortcut structure work needed two, both of which were deleted with the prototypes once it shipped, so the harness is written again every time.
  **PERF-4 is the worked example, 2026-08-23**: answering it took a third hand-rolled alternating harness, and what that harness showed — a per-fetch saving that vanished into noise as a workload share — is precisely what the committed comparison cannot express.
  It was rejected on evidence this tooling could not have produced.
- **Fixes, in increasing cost, and the first is most of the value:**
  1. **Report dispersion beside the `min`.** pytest-benchmark already records every round, so the
     JSON holds it and the comparison discards it. A reader could then see whether the two
     estimators agree. Small, no workflow change.
  2. **A paired A/B harness** for two candidate implementations of one stage, alternating order —
     the thing both prototypes hand-rolled. Medium, and it belongs in `benchmarks/` rather than in
     `prototypes/` precisely because it will be wanted again.
  3. Interleaving base and head inside one job. **Likely infeasible and recorded so it is not
     attempted blind:** it needs two versions of the library importable in one process, and
     `utils.py` binds its backend at import time.
- **Not a gate.** Whatever is added stays reporting-only until a single-runner noise study says
  what the residual floor is — the same condition `docs/benchmarking_methodology.rst` already puts
  on `--fail-on-regression`. A gate that fires on drift is worse than no gate.
- **Status:** open — free.
- **Last touched:** 2026-08-22 — created, from the measurement flaws found while comparing shortcut
  structures; the methodology doc carries the three A/B designs that produced wrong answers.
