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

## Durable evidence

- Refused runtime and geometry findings live in [runtime, geometry, and data checks](../../checked-and-found-sound/runtime-geometry-and-data-checks.md).
- Public loading and compatibility choices live in [public API, compatibility, and runtime loading decisions](../../decisions/public-api-compatibility-and-runtime-loading-decisions.md).

## Known uncovered deltas

- `timezonefinder/block_payload.py`, the packed kernels in `timezonefinder/utils_numba.py`, `timezonefinder/utils_clang.py`, and `inside_poly_extension/inside_polygon_int.c` arrived with the frame-of-reference payload in `7c06d0c` and have not received an independent review.
- The frame-of-reference payload also collapsed the two coordinate accessors onto one buffer; that changed path has not received an independent review.

## Next useful gap

- Review the frame-of-reference payload and changed coordinate-access path first, then delta-review other modules added or materially changed after `72678a1` rather than repeating the broad read.
