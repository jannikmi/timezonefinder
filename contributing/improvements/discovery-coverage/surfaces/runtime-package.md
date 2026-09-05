# Runtime package discovery coverage

## Baseline

- **Delta anchor:** `72678a1`.
- **Coverage state:** broad triage; no runtime module was recorded as never read at the anchor.

## Covered subjects

- Contract or implementation reviews covered `timezonefinder/command_line.py` with `tests/cli_test.py`, plus `timezonefinder/np_binary_helpers.py`, `timezonefinder/timezonefinder.py`, `timezonefinder/utils.py`, and `timezonefinder/zone_names.py`.
- They also covered `timezonefinder/polygon_array.py`, `timezonefinder/global_functions.py`, the coordinate accessors, `timezonefinder/shortcut_index.py`, and `timezonefinder/configs.py`.
- Every runtime `raise` and `except`, plus every `:raises:` and `:return:` claim, was compared with behavior.
- The id-taking APIs and their internal callers were traced.
- `timezonefinder/timezonefinder.py` was read end to end for the batch path.
- Persistent loaded-array mutability was audited in both storage modes.
- The binary-data-to-`timezone_at` flow was read end to end on 2026-09-05 — `block_payload.py`, `coord_accessors.py`, `polygon_array.py`, the packed kernels in `utils_numba.py` / `utils_clang.py` / `inside_polygon_int.c`, and the candidate loop in `timezonefinder.py` — against the committed benchmark fixtures rather than by reading alone. It produced the hole-registry guard that has since shipped, [PERF-9](../../items/lookup-geometry-and-data-format/perf-9-the-candidate-loop-reads-numpy-scalars-where-a-memoryview-yields-an-int.md), [FMT-3](../../items/lookup-geometry-and-data-format/fmt-3-the-payload-offset-width-is-justified-by-a-bound-that-is-not-the-one-it-holds.md), a re-scoped [PERF-2](../../items/lookup-geometry-and-data-format/perf-2-the-candidate-loop-builds-a-zone-id-array-to-read-one-element.md), and [PROF-1](../../items/data-pipeline-and-developer-tooling/prof-1-the-stage-ladder-measures-the-checked-public-accessors.md) against the instrument itself.

## Durable evidence

- Refused runtime and geometry findings live in [runtime, geometry, and data checks](../../checked-and-found-sound/runtime-geometry-and-data-checks.md).
- Public loading and compatibility choices live in [public API, compatibility, and runtime loading decisions](../../decisions/public-api-compatibility-and-runtime-loading-decisions.md).

## Known uncovered deltas

- `timezonefinder/_data_integrity.py` arrived at 942 lines with the CLI data validator in `64aa293` and has not been read.
- The lazy public surface and the dropped `in_memory` argument (`82703f2`, `timezonefinder/__init__.py`, `global_functions.py`, `command_line.py`) have not received an independent review.

## Next useful gap

- Read `timezonefinder/_data_integrity.py` first — it is the largest never-read runtime module and it decides what a compiled data directory is allowed to be.
- Then delta-review the API-major lazy public surface, rather than repeating the broad read or the query flow just covered.
