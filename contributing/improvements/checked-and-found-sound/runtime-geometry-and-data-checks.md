# Runtime, geometry, and data checks

Do not re-raise these findings without new evidence.

- Pass 2: the broad `except Exception` in `MemoryCoordAccessor`/`FileCoordAccessor.__init__` (cleans
  up partial state and re-raises), `utils.close_resource`'s suppression list (documented at length,
  `BufferError` included on purpose), `TimezoneFinder.__del__`'s two-tier handler (warns on the
  unexpected case), and `scripts/reporting.py`'s `main` catching `Exception` to print a traceback
  and return an exit code.

- Pass 3: `coord_accessors.py`'s bare `open()` (ruff `SIM115`) — the handle deliberately outlives
  the call and is closed by `cleanup()`; the `profile` name probes in `scripts/hex_utils.py` and
  `scripts/shortcuts.py` (ruff `B018`) — the standard `line_profiler` idiom, not a stray
  expression; `scripts/measure_memory.py`'s `subprocess.run` without `check=` (ruff `PLW1510`) —
  it inspects `returncode` on the next line and raises with the child's output, which is strictly
  better than `CalledProcessError`; and `np_binary_helpers.py`'s six near-identical `get_*_path`
  helpers — collapsing them into a mapping would trade six importable names for one lookup key and
  works against the declare-each-path-once rule.

- Pass 7: `.github/workflows/benchmark.yml`, `benchmark-comment.yml`, `check_data_updates.yml` and
  `release_data_update.yml` (read in full, nothing found beyond the version drift now guarded);
  `timezonefinder/global_functions.py`'s module-level `TF_INSTANCE` and its `global` statement
  (ruff `PLW0603`) — deliberate and documented as not thread-safe, with per-thread instances the
  stated alternative; `scripts/hex_utils.py`'s `get_corrected_hex_boundaries` (the antimeridian and
  pole clipping, covered by `tests/hex_utils_test.py`).

- Pass 10: `scripts/data_integrity.py` (read in full — its two validators each build their own
  `PolygonArray`/`HoleArray`, which looks like duplication and is not worth collapsing: they are
  separate entry points with different subjects, one about whether a directory's files agree and
  one an expectation about the upstream data, and `__del__` releases the accessors either way);
  `packages/timezonefinder-data/timezonefinder_data/__init__.py` and `scripts/data_releases.py`
  (read in full, nothing found); `timezonefinder/zone_names.py`, whose asymmetric defaults —
  `read_zone_names` takes a path, `write_zone_names` requires one — are deliberate and documented,
  since defaulting the write side to `DEFAULT_DATA_DIR` would rewrite the installed dataset in
  `site-packages`.
