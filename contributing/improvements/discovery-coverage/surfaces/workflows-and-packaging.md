# Workflow and packaging discovery coverage

## Baseline

- **Delta anchor:** `9ac82ea`.
- **Coverage state:** complete baseline coverage through `c068642`, with one explicit unreviewed delta at the anchor.

## Covered subjects

- Every file under `.github/workflows/` was read end to end.
- The data update, data release, build, and publish workflows were reviewed together around binary eligibility, release ordering, and their shared data wheel.
- `.github/actions/obtain-data-wheel` received targeted review with that handoff.
- `build.yml`, `benchmark.yml`, and the update job were re-read when packaged binaries stopped being committed.
- `.github/actions/obtain-data` now precedes every job that reads the dataset, and the update job stages generated data by name.
- `release_data_update.yml` and `benchmark-comment.yml` were checked in that pass and require no dataset.
- Every `UNWANTED_DIST_PATTERNS` entry was matched against the working tree and compared with `MANIFEST.in` and the `check-manifest` ignore list.
- `tests/test_python_version_support.py` guards workflow-version drift.
- `tests/test_data_wheel_handoff.py` guards the shared-wheel agreements.

## Known uncovered deltas

- `.github/workflows/compile_data.yml` arrived as the packaged-data producer for a hand-made branch and has not received an independent review since its author added it.

## Durable evidence

- Refused findings live in [runtime, geometry, and data checks](../../checked-and-found-sound/runtime-geometry-and-data-checks.md) and [testing and benchmarking checks](../../checked-and-found-sound/testing-and-benchmarking-checks.md).
- Release ordering choices live in [data distribution, packaging, and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md).

## Next useful gap

- Read `.github/workflows/compile_data.yml` independently, then delta-review workflows, actions, and packaging rules changed after `9ac82ea`.
