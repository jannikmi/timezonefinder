# Potential improvements

Working ledger of internal code-quality findings for `timezonefinder`. It is committed so that it
reaches the next quality pass through `master`: every pass reads it before touching a source file,
re-verifies the open entries against the current code, and writes back what it found, shipped or
rejected.

None of these are bugs users can hit today. Everything here is internal quality — diagnostics that
get discarded, duplication that will drift, docstrings describing code that no longer exists, dead
definitions, annotations that contradict their call sites.

**How to read an entry.** Locations are given by file plus a code anchor (a function or symbol
name), never a line number, so they survive reformatting. `Size` is a rough count of changed lines.
`Status` is one of `open`, `shipped (PR #N)`, `rejected (reason)`, `out of scope (reason)`,
`withdrawn (reason)`. Entries that are shipped, rejected or out of scope are **closed** — do not
re-litigate them and do not re-add them under a new id.

Order within each section is by expected value per line of review, following the ranking used to
pick work: **defects that will cause a real bug later > duplication that will drift > readability**.

Closed before this ledger existed, in [#464](https://github.com/jannikmi/timezonefinder/pull/464):
the duplicated `get_corrected_hex_boundaries`, the duplicate `MAX_LAT`/`MAX_LNG` declaration in
`scripts/configs.py`, and the mislabelled latitude assertion. Not listed below.

---

## Error reporting

### ERR-1 — `run_command` throws away the subprocess output it just collected

- **Location:** `tests/auxiliaries.py`, `run_command`, the `except subprocess.CalledProcessError`
  block.
- **Defect:** built `error_msg` from the child's stdout and stderr, then raised a *fresh*
  `CalledProcessError` that never used it, with `from None` suppressing the original as well.
- **Fix:** echo the captured streams, then re-raise the original with a bare `raise` (keeps the
  traceback and the attached streams). Size: ~10 lines.
- **Value:** `run_command` is what `build_wheel` / `build_sdist` use, so a packaging failure under
  `make testint` reported an exit code and nothing about the cause — the one situation where the
  build log is the whole point.
- **Status:** shipped (PR #475)
- **Last touched:** 2026-08-07 — shipped.

### ERR-2 — the report generator hides which file it choked on

- **Location:** `scripts/reporting.py`, `load_binary_data`, the two `get_polygon_collection` calls.
- **Defect:** neither passed the optional `file_path`, which exists solely so an
  incompatible-layout `ValueError` can name the offending file — the runtime accessors in
  `timezonefinder/coord_accessors.py` both pass it, and `boundary_coord_path` / `hole_coord_path`
  were in scope on the adjacent lines.
- **Fix:** pass them. Size: 2 lines.
- **Value:** `make reports` against a stale data directory produced an error that could not say
  which of the two files was wrong.
- **Status:** shipped (PR #475)
- **Last touched:** 2026-08-07 — shipped, with a test that mirrors the packaged data directory by
  symlink and replaces only the boundary coordinate file.

### ERR-3 — exception chaining left implicit in two places

- **Location:** `timezonefinder/timezonefinder.py`, `get_geometry` (the
  `self.timezone_names.index` lookup); `scripts/timezone_data.py`,
  `PolygonCollection.polygon_vertex_hexes`.
- **Defect:** both re-raise inside an `except` without `from`, which ruff flags as `B904`. Both
  suppressions are wanted; nothing said so, making them indistinguishable from a forgotten `from`.
- **Fix:** `raise ... from None` plus a comment naming the reason. Size: ~8 lines.
- **Status:** shipped (PR #475)
- **Last touched:** 2026-08-07 — shipped.

### ERR-4 — error paths that name nothing

- **Location:** `scripts/helper_classes.py`, `Boundaries.overlaps` (bare `raise TypeError`);
  `scripts/timezone_data.py`, `polygon_vertex_hexes` (`RuntimeError("original polygon coordinates
  missing")`, naming no polygon).
- **Fix:** interpolate the offending value / index into the message. Size: ~8 lines.
- **Status:** shipped (PR #475)
- **Last touched:** 2026-08-07 — shipped.

### ERR-5 — `except` tuple listing a subclass next to its base

- **Location:** `timezonefinder/command_line.py`, `main`, the temp-file read:
  `except (FileNotFoundError, OSError, UnicodeDecodeError)`.
- **Defect:** `FileNotFoundError` is a subclass of `OSError`, so listing it changes nothing and
  implies a distinction that does not exist. (`UnicodeDecodeError` derives from `ValueError` and
  does have to be listed.)
- **Fix:** drop the redundant entry, note why the third stays. Size: 3 lines.
- **Status:** shipped (PR #475)
- **Last touched:** 2026-08-07 — shipped.

---

## Command line interface

### CLI-1 — the lookup function is resolved twice per invocation

- **Location:** `timezonefinder/command_line.py`, `get_timezone_function`, called from both
  `_lookup_timezone` and `_print_lookup_details`.
- **Defect:** `_print_lookup_details` calls `get_timezone_function` purely to read `__name__` off
  the result. For `-f 3` and `-f 4` that constructs a **second** `TimezoneFinderL`, loading the
  shortcut binary all over again, only to discard it.
- **Fix:** resolve the function once in `main` and pass it down. Size: ~15 lines.
- **Value:** removes a duplicated data load from every verbose CLI call on those two function ids.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified, unchanged.

### CLI-2 — `_print_lookup_details` does not print

- **Location:** `timezonefinder/command_line.py`, `_print_lookup_details`.
- **Defect:** it returns a formatted string; `main` prints it. The name says the opposite of what
  it does.
- **Fix:** rename to `_format_lookup_details`. It is a private helper, so no API surface moves.
  Size: 3 lines.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified, unchanged.

### CLI-3 — `main` writes its own output to a temp file and reads it back

- **Location:** `timezonefinder/command_line.py`, `main` and `redirect_stdout_to_temp_file`.
- **Defect:** `main` redirects stdout to a temp file, prints `details` into it, then (verbose only)
  re-opens the file, reads it, strips it and prints it — for a string it still holds in a local
  variable. Nothing else inside the redirected block writes to stdout: the lookup functions do not
  print. The temp file, the `mkstemp`, the read-back, the `warnings.warn` on read failure and the
  `os.remove` cleanup are an elaborate route to `if args.v: print(details.strip())`.
- **Fix:** print the string directly and delete the context manager, or — if the redirection is
  meant to catch output from *library* code that might print in future — say so in a comment and
  keep it. Deciding which is the judgement call. `redirect_stdout_to_temp_file` has exactly one
  caller (`main`) and is not exported, so removing it moves no API surface. Size: ~40 lines removed.
- **Value:** removes the file-system round trip and the two error paths that only exist because of
  it (ERR-5 was one of them) from every CLI invocation.
- **Status:** open
- **Last touched:** 2026-08-07 — found this pass.

---

## Duplication

### DUP-1 — the coordinate bounds are declared three times

`±90` / `±180` appear as literals in executable code in three places:

| Location | Role |
|---|---|
| `timezonefinder/configs.py` — `MAX_LAT_VAL` / `MAX_LNG_VAL` | canonical, exported in `__all__` |
| `timezonefinder/utils_numba.py` — `is_valid_lat` / `is_valid_lng` | the actual bounds check |
| `timezonefinder/utils.py` — `validate_lat` / `validate_lng` | literals passed to `_validate_coordinate` **only** to build the error message |

- **Defect:** `_validate_coordinate`'s `min_bound` / `max_bound` are never compared against
  anything — they are interpolated into an f-string. The validator and the message describing it
  are independent and can disagree with nothing to catch it.
- **Fix:** import the constants. Size: ~6 lines.
- **Value:** low. Unlike a file name or an H3 resolution, ±90/±180 are physical facts about the
  coordinate system and will never change; the duplication is real but the drift risk is close to
  nil.
- **Cost, and why this is still open:** both remaining copies sit on the lookup fast path.
  `validate_coordinates` runs on every query, and in the tracked no-numba configuration `njit` is a
  no-op, so `is_valid_lat` is plain Python — the substitution trades two `LOAD_CONST` for two
  `LOAD_GLOBAL` plus a negation, per call. Per `CONTRIBUTING.md` this needs a before/after
  measurement in a no-numba environment (`uv sync --group test`, then `make benchmark-noise`).
  Worth doing only if that comes back neutral. **No measurement has been taken yet** — do not
  retry blind, record the numbers here when you do.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified, unchanged.

### DUP-2 — `file_converter.py` recomputes and re-creates its output directories

- **Location:** `scripts/file_converter.py`, `write_numpy_binaries` and `write_flatbuffer_files`.
- **Defect:** each recomputes `holes_dir` / `boundaries_dir` and `mkdir`s them.
  `write_numpy_binaries` also calls `np.save` directly for the zone ids while using
  `store_per_polygon_vector` for everything else, so that one file is written without the progress
  line the others print.
- **Fix:** hoist the directory setup to the caller; route the zone ids through the same helper.
  Size: ~25 lines.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified, unchanged.

---

## Docstrings that describe code that no longer exists

Cheap to fix, and actively misleading while they stand — a `:param:` for an argument that does not
exist reads as a feature someone removed by accident.

### DOC-1 — documented parameters that were removed

| Location | Documents | Actual signature |
|---|---|---|
| `scripts/shortcuts.py` — `compile_h3_map` | `use_parallel`, `max_workers` | `data`, `candidates` |
| `scripts/shortcuts.py` — `compile_shortcut_mapping` | `use_parallel`, `max_workers` | `data` |
| `scripts/reporting.py` — `calculate_timezone_metrics` | `all_tz_names` | `nr_of_polygons`, `nr_of_zones`, `polygons_per_timezone` |
| `tests/auxiliaries.py` — `convert_to_reduced_timezone` | `mapping` | `timezone` |
| `tests/test_package_contents.py` — `load_gitignore_patterns` | `gitignore_path` | *(none)* |

- **Defect:** the two `shortcuts.py` entries are leftovers from a parallel implementation that was
  removed; the prose above them still discusses thread pools and worker counts that no longer exist.
- **Fix:** delete the stale `:param:` lines and the parallelism prose. Size: ~20 lines.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified, unchanged.

### DOC-2 — docstring statements that contradict the code

- **`timezone_names.json` does not exist.** `timezonefinder/timezonefinder.py` (`get_geometry`) and
  `timezonefinder/global_functions.py` (`get_geometry`) both tell users the zone names live in
  `timezone_names.json`. The file is `timezone_names.txt` — see `timezonefinder/zone_names.py`.
  These are **public API docstrings**.
- **`in_memory` is not ignored.** `AbstractTimezoneFinder.__init__`'s docstring says *"Ignored for
  polygon coordinate data (always uses memory-mapped file access). Kept for API compatibility."*
  `TimezoneFinder.__init__` passes it straight into both `PolygonArray` constructors, which is
  exactly what selects `MemoryCoordAccessor` over `FileCoordAccessor`, and `docs/1_usage.rst`
  documents it as working. The claim is true only for `TimezoneFinderL`, which has no polygon data.
- **`read_zone_names` does not return an empty list.** `timezonefinder/zone_names.py` documents
  *":return: List of timezone names (empty list if file not found)"*; the body calls `open()`
  unguarded and raises `FileNotFoundError`.
- **Fix:** correct the three statements. Size: ~8 lines.
- **Value:** highest of the docstring items — the first two are read by users, not just
  contributors, and the `in_memory` one contradicts the usage docs.
- **Status:** open
- **Last touched:** 2026-08-07 — all three re-verified, unchanged.

---

## Dead and inert code

### DEAD-1 — unreferenced definitions

Confirmed unreferenced across `timezonefinder/`, `scripts/`, `tests/`, `benchmarks/`, `docs/` and
`prototypes/`.

- `scripts/utils.py` — `load_json`, `load_pickle`, `write_pickle`. The pickle pair also keeps
  `import pickle` alive in a data-generation path.
- `timezonefinder/_numba_replacements.py` — `i8`. The shim exists to mirror the numba names the
  package actually imports; an extra one is an unexercised claim.
- `tests/auxiliaries.py` — `convert_to_reduced_timezone`, self-documented as *"NOTE: unused, but
  kept for future reference"*. Git history is the mechanism for that.
- **Fix:** delete. Size: ~40 lines removed.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified all five still present and still unreferenced (PR #463
  swept a different set).

### DEAD-2 — leftovers that are referenced but inert

- `scripts/shortcuts.py` — `has_coherent_sequences` builds `lst_iter = iter(lst)` solely to take
  `next()` as the initial `prev`, then loops over `lst` from the start. Correct (the first
  comparison is a no-op) but it reads as an off-by-one bug.
- `scripts/helper_classes.py` — `compile_bboxes` unpacks `x_coords, y_coords = coords` and then
  immediately reassigns `y_coords = coords[1]`.
- `scripts/shortcuts.py` — `process_single_hex` returns the `hex_id` it was handed, so its only
  caller writes `hex_id, polys_optimised = process_single_hex(hex_id, data)`, reassigning the loop
  variable to itself (ruff `PLW2901`). Vestigial from the parallel-map version.
- **Fix:** simplify each in place. Size: ~15 lines.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified, unchanged.

---

## Type annotations that do not match reality

### TYPE-1 — the shortcut compilation chain has both annotations backwards

- **Location:** `scripts/shortcuts.py` — `check_shortcut_sorting(polygon_ids: np.ndarray, ...)` is
  handed a `list[int]` by `process_single_hex`, and it in turn hands an `np.ndarray` to
  `has_coherent_sequences(lst: list[int])`.
- **Fix:** widen both rather than swapping them — `tests/shortcut_test.py` does call the latter with
  real lists. Size: ~6 lines.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified, unchanged.

### TYPE-2 — implicit `Optional` (ruff `RUF013`)

- **Location:** `scripts/benchmark_utils.py` — `additional_info: dict[str, Any] = None`,
  `provenance: dict[str, Any] = None`; `scripts/reporting.py` — `additional_rows: list = None`.
- **Defect:** PEP 484 forbids implicit `Optional`. `no_implicit_optional = true` is already set in
  `[tool.mypy]`, but these live in `scripts/`, which the mypy hook does not currently cover.
- **Fix:** annotate `| None`. Size: 3 lines.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified, unchanged.

### TYPE-3 — `load_binary_data` returns an untyped nine-key bag

- **Location:** `scripts/reporting.py`, `load_binary_data(...) -> dict`.
- **Defect:** returns `shortcuts`, `nr_of_polygons`, `nr_of_zones`, `polygon_lengths`,
  `all_hole_lengths`, `polynrs_of_holes`, `poly_zone_ids`, `all_tz_names`, `output_path`, then the
  rest of the module indexes it by string literal.
- **Fix:** a `TypedDict` or dataclass, making a typo a type error instead of a `KeyError` at report
  time. Size: ~30 lines.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified, unchanged.

### TYPE-4 — `dir` builtin shadowed

- **Location:** `scripts/file_converter.py`, `for dir, bounds in boundary_sources:` (ruff `A001`).
- **Fix:** rename the loop variable. Size: ~4 lines.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified, unchanged.

---

## Larger, needs a judgement call first

### BIG-1 — `_iter_boundary_ids_of_zone` re-opens `zone_positions.npy` on every call

- **Location:** `timezonefinder/timezonefinder.py`, `_iter_boundary_ids_of_zone`.
- **Defect:** calls `np.load(..., mmap_mode="r")` per invocation, under a comment reading *"load
  only on demand"*. Off the `timezone_at` hot path but on `certain_timezone_at`'s and
  `get_geometry`'s.
- **Why it is not a straight refactor:** caching it is a memory/latency trade, and `CLAUDE.md` is
  explicit that the memory-mapped path must stay viable for constrained containers. Needs a
  decision plus a benchmark, not just an edit.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified, unchanged.

### BIG-2 — `calculate_shortcut_index_stats` is 13 branches / 57 statements

- **Location:** `scripts/reporting.py`, `calculate_shortcut_index_stats`. Over ruff's `PLR0912` /
  `PLR0915` defaults.
- **Defect:** computes coverage, uniqueness, storage and frequency metrics in one pass.
- **Fix:** split along those four seams. Straightforward, but its output is committed in
  `docs/data_report.rst`, so it needs a regenerate-and-diff to prove neutral. Size: ~80 lines moved.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified, unchanged.

---

## Tooling

### TOOL-1 — ruff runs close to its default rule set

- **Location:** `pyproject.toml`, `[tool.ruff]` — no `lint.select`.
- **Defect:** several findings in this ledger (`B904`, `RUF013`, `A001`, `PLW2901`, `PLR09xx`) were
  surfaced by ad-hoc `uv run ruff check --select ...` runs and are not caught by CI as configured.
- **Fix:** enable a chosen subset. Best done *after* the existing findings are cleared, so the first
  run is not a wall of noise. Note that `TRY003` / `EM101` / `EM102` fire in the hundreds across
  `scripts/` and are not worth adopting — pick deliberately rather than taking a whole family.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified; ERR-3 cleared the last two `B904` hits, so `B904` is
  now clean and could be enabled on its own.

---

## Scope notes

`prototypes/` is excluded throughout — it carries its own crop of ruff findings (`RUF012` mutable
class defaults, `RUF034` useless `if`/`else`, `B905` unstrict `zip`) that are appropriate to leave
in exploratory code.

`timezonefinder/data/` and `timezonefinder/flatbuf/generated/` are generated and are never edited
directly; findings there belong against the generator or the schema instead.

---

## Coverage log

| Pass | Date | Swept | Not reached |
|---|---|---|---|
| 1 | 2026-08-06 | `timezonefinder/`, `scripts/`, `tests/`, `benchmarks/` — broad triage, findings above | `prototypes/` (deliberate), `docs/`, `.github/workflows/` |
| 2 (error diagnostics) | 2026-08-07 | Every `raise` and `except` site in `timezonefinder/` and `scripts/` (via `rg` plus ruff `B904`/`BLE`/`TRY`/`EM`/`RSE`/`S110`/`S112`); `timezonefinder/command_line.py` read in full | `docs/`, `.github/workflows/`, `benchmarks/`, `scripts/` report-rendering internals |

Areas with **no coverage in any pass yet**, and therefore the cheapest place for the next pass to
start: `benchmarks/` beyond `conftest.py`, the `scripts/` benchmark-CI helpers
(`normalize_benchmark_json.py`, `compare_benchmark_runs.py`, `benchmark_noise.py`,
`render_benchmark_reports.py`, `describe_benchmark_machine.py`) and `timezonefinder/np_binary_helpers.py`.

Deliberately checked and found sound this pass, so do not re-raise them: the broad `except
Exception` in `MemoryCoordAccessor`/`FileCoordAccessor.__init__` (cleans up partial state and
re-raises), `utils.close_resource`'s suppression list (documented at length, `BufferError` included
on purpose), `TimezoneFinder.__del__`'s two-tier handler (warns on the unexpected case), and
`scripts/reporting.py`'s `main` catching `Exception` to print a traceback and return an exit code.
