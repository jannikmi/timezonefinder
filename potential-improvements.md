# Potential improvements

Findings from a code-quality triage pass over `timezonefinder/`, `scripts/`, `tests/` and
`benchmarks/`. None of these are bugs users can hit today: everything here is internal quality —
duplication that will drift, diagnostics that get discarded, docstrings that describe code that no
longer exists, and dead definitions.

Each entry names a location, the defect, and why it is worth doing. Line numbers are against the
commit this file was added on and will drift; the descriptions are written to survive that.

The items are ordered by expected value per line of review, following the same ranking used to
pick them: **defects that will cause a real bug later > duplication that will drift > readability**.

> Already addressed in [#464](https://github.com/jannikmi/timezonefinder/pull/464): the duplicated
> `get_corrected_hex_boundaries`, the duplicate `MAX_LAT`/`MAX_LNG` declaration in
> `scripts/configs.py`, and the mislabelled latitude assertion. Not repeated below.

---

## 1. Error paths that discard their own diagnostics

### 1.1 `run_command` throws away the subprocess output it just collected

`tests/auxiliaries.py` (~line 91), in `run_command`'s `except subprocess.CalledProcessError` block.

It builds `error_msg` by appending the child's stdout and stderr, then raises a **fresh**
`CalledProcessError` that never uses `error_msg`, with `from None` suppressing the original as
well. Every diagnostic the handler gathered is dropped on the floor.

`run_command` is what `build_wheel` and `build_sdist` use, so a packaging failure under
`make testint` reports an exit code and nothing about the cause — the one situation where the
build log is the whole point. Either raise with the assembled message or drop the dead assembly;
re-raising the original with `raise` would preserve the traceback too.

*Small — one function.*

### 1.2 The report generator hides which file it choked on

`scripts/reporting.py`, in `load_binary_data`: `get_polygon_collection(coord_buf)` and
`get_polygon_collection(hole_coord_buf)`.

`get_polygon_collection`'s optional `file_path` argument exists solely so an incompatible-layout
`ValueError` can name the offending file — the runtime accessors in
`timezonefinder/coord_accessors.py` both pass it. These two call sites do not, although
`boundary_coord_path` / `hole_coord_path` are in scope on the adjacent lines. Running
`make reports` against a stale data directory therefore produces an error that cannot say which of
the two files was wrong.

*Two lines.*

### 1.3 Exception chaining dropped in two places

- `timezonefinder/timezonefinder.py`, `get_geometry`: `raise ValueError(f"The timezone '{tz_name}' does not exist.")`
  inside `except ValueError` — no `from`, so the chain is silently swallowed rather than marked
  intentional.
- `scripts/timezone_data.py` (~line 177): `raise RuntimeError("original polygon coordinates missing")`
  inside `except KeyError`, likewise.

Ruff flags both under `B904`. `raise ... from None` is fine if the chaining is unwanted — the point
is to say so.

### 1.4 Error paths that name nothing

- `scripts/helper_classes.py`, `Boundaries.overlaps`: bare `raise TypeError` with no message and no
  mention of what was actually passed.
- `timezonefinder/command_line.py`, in `main`: `except (FileNotFoundError, OSError, UnicodeDecodeError)`
  — `FileNotFoundError` is a subclass of `OSError`, so listing it changes nothing and implies a
  distinction that does not exist.

---

## 2. Wasted work and misleading names in the CLI

`timezonefinder/command_line.py`.

`get_timezone_function(function_id)` is called twice per invocation: once by `_lookup_timezone` to
do the lookup, and again by `_print_lookup_details` purely to read `__name__` off the result. For
`-f 3` and `-f 4` that constructs a **second** `TimezoneFinderL`, loading the shortcut binary all
over again, only to discard it. Resolving the function once in `main` and passing it down removes
the duplicate load and the duplicate dispatch.

In the same file, `_print_lookup_details` does not print — it returns a formatted string, and
`main` prints it. The name says the opposite of what it does.

*Small, self-contained, no behaviour change.*

---

## 3. The coordinate bounds are still declared three times

`±90` / `±180` appear as literals in executable code in three places:

| Location | Role |
|---|---|
| `timezonefinder/configs.py` — `MAX_LAT_VAL` / `MAX_LNG_VAL` | canonical, exported in `__all__` |
| `timezonefinder/utils_numba.py` — `is_valid_lat` / `is_valid_lng` | the actual bounds check |
| `timezonefinder/utils.py` — `validate_lat` / `validate_lng` | literals passed to `_validate_coordinate` **only** to build the error message |

The third copy is the uncomfortable one: `_validate_coordinate`'s `min_bound` / `max_bound`
parameters are never compared against anything, they are interpolated into an f-string. The
validator and the message describing it are independent, so they can disagree with nothing to catch
it.

**Why this was left alone rather than fixed:** both remaining copies sit on the lookup fast path —
`validate_coordinates` runs on every query, and in the tracked no-numba configuration `njit` is a
no-op, so `is_valid_lat` is plain Python. Substituting the constants trades two `LOAD_CONST` for two
`LOAD_GLOBAL` plus a negation, per call. Justifying that needs a before/after measurement in a
no-numba environment (`uv sync --group test`, then `make benchmark-noise`), per `CONTRIBUTING.md`.

Weigh that against the payoff, which is smaller than it looks: unlike a file name or an H3
resolution, ±90/±180 are physical facts about the coordinate system and will never change. The
duplication is real; the drift risk is close to nil. Worth doing only if the benchmark comes back
neutral, which it plausibly will.

---

## 4. Docstrings that describe code that no longer exists

Cheap to fix, and actively misleading while they stand — a `:param:` for an argument that does not
exist reads as a feature someone removed by accident.

### 4.1 Parameters that were removed

| Location | Documents | Actual signature |
|---|---|---|
| `scripts/shortcuts.py` — `compile_h3_map` | `use_parallel`, `max_workers` | `data`, `candidates` |
| `scripts/shortcuts.py` — `compile_shortcut_mapping` | `use_parallel`, `max_workers` | `data` |
| `scripts/reporting.py` — `calculate_timezone_metrics` | `all_tz_names` | `nr_of_polygons`, `nr_of_zones`, `polygons_per_timezone` |
| `tests/auxiliaries.py` — `convert_to_reduced_timezone` | `mapping` | `timezone` |
| `tests/test_package_contents.py` — `load_gitignore_patterns` | `gitignore_path` | *(none)* |

The two `shortcuts.py` entries are leftovers from a parallel implementation that was removed; the
prose above them still discusses thread pools and worker counts that no longer exist.

### 4.2 Statements that contradict the code

- **`timezone_names.json` does not exist.** `timezonefinder/timezonefinder.py` (`get_geometry`) and
  `timezonefinder/global_functions.py` (`get_geometry`) both tell users the zone names live in
  `timezone_names.json`. The file is `timezone_names.txt` — see `timezonefinder/zone_names.py`.
  These are public API docstrings.
- **`in_memory` is not ignored.** `AbstractTimezoneFinder.__init__`'s docstring says
  *"Ignored for polygon coordinate data (always uses memory-mapped file access). Kept for API
  compatibility."* `TimezoneFinder.__init__` passes it straight into both `PolygonArray`
  constructors, which is exactly what selects `MemoryCoordAccessor` over `FileCoordAccessor`.
  `docs/1_usage.rst` documents it as working. True only for `TimezoneFinderL`, which has no polygon
  data at all.
- **`read_zone_names` does not return an empty list.** `timezonefinder/zone_names.py` documents
  *":return: List of timezone names (empty list if file not found)"*; the body calls `open()`
  unguarded and raises `FileNotFoundError`.

---

## 5. Dead definitions

All confirmed unreferenced across `timezonefinder/`, `scripts/`, `tests/`, `benchmarks/`, `docs/`
and `prototypes/`.

- `scripts/utils.py` — `load_json`, `load_pickle`, `write_pickle`. No callers. The pickle pair also
  keeps `import pickle` alive in a data-generation path.
- `timezonefinder/_numba_replacements.py` — `i8`. The shim exists to mirror the numba names the
  package actually imports; an extra one is an unexercised claim.
- `tests/auxiliaries.py` — `convert_to_reduced_timezone`, self-documented as
  *"NOTE: unused, but kept for future reference"*. Git history is the mechanism for that.

Related leftovers that are not unreferenced but are inert:

- `scripts/shortcuts.py` — `has_coherent_sequences` builds `lst_iter = iter(lst)` solely to take
  `next()` as the initial `prev`, then loops over `lst` from the start. Correct (the first
  comparison is a no-op) but it reads as an off-by-one bug.
- `scripts/helper_classes.py` — `compile_bboxes` unpacks `x_coords, y_coords = coords` and then
  immediately reassigns `y_coords = coords[1]`.
- `scripts/shortcuts.py` — `process_single_hex` returns the `hex_id` it was handed, so its only
  caller writes `hex_id, polys_optimised = process_single_hex(hex_id, data)`, reassigning the loop
  variable to itself (ruff `PLW2901`). Vestigial from the parallel-map version.

---

## 6. Type annotations that do not match reality

- `scripts/shortcuts.py` — the production call chain has both annotations backwards:
  `check_shortcut_sorting(polygon_ids: np.ndarray, ...)` is handed a `list[int]` by
  `process_single_hex`, and it in turn hands an `np.ndarray` to
  `has_coherent_sequences(lst: list[int])`. (`tests/shortcut_test.py` does call the latter with
  real lists, so a widened annotation is the fix rather than a straight swap.)
- `scripts/benchmark_utils.py` — `additional_info: dict[str, Any] = None` and
  `provenance: dict[str, Any] = None`; `scripts/reporting.py` —
  `additional_rows: list = None`. Implicit `Optional`, which PEP 484 forbids and ruff flags as
  `RUF013`. Note `no_implicit_optional = true` is already set in `[tool.mypy]`; these live in
  `scripts/`, which the mypy hook does not currently cover.
- `scripts/reporting.py` — `load_binary_data(...) -> dict` returns a nine-key bag
  (`shortcuts`, `nr_of_polygons`, `nr_of_zones`, `polygon_lengths`, `all_hole_lengths`,
  `polynrs_of_holes`, `poly_zone_ids`, `all_tz_names`, `output_path`) that is then indexed by string
  literal across the rest of the module. A `TypedDict` or dataclass would make a typo a type error
  instead of a `KeyError` at report time.
- `scripts/file_converter.py` — `for dir, bounds in boundary_sources:` shadows the `dir` builtin
  (ruff `A001`).

---

## 7. Larger, needs a judgement call first

- **`_iter_boundary_ids_of_zone` re-opens `zone_positions.npy` on every call.**
  `timezonefinder/timezonefinder.py` calls `np.load(..., mmap_mode="r")` per invocation, under a
  comment reading *"load only on demand"*. It is off the `timezone_at` hot path but on
  `certain_timezone_at`'s and `get_geometry`'s. Caching it would be a memory/latency trade — and
  `CLAUDE.md` is explicit that the memory-mapped path must stay viable for constrained containers —
  so this needs a decision, not just a refactor.
- **`calculate_shortcut_index_stats` is 13 branches / 57 statements** (`scripts/reporting.py`),
  over ruff's `PLR0912` / `PLR0915` defaults. It computes coverage, uniqueness, storage and
  frequency metrics in one pass; splitting it along those seams is straightforward but touches a
  function whose output is committed in `docs/data_report.rst`, so it needs a regenerate-and-diff to
  prove it neutral.
- **`scripts/file_converter.py` duplication.** `write_numpy_binaries` and `write_flatbuffer_files`
  each recompute `holes_dir` / `boundaries_dir` and `mkdir` them. `write_numpy_binaries` also calls
  `np.save` directly for the zone ids while using `store_per_polygon_vector` for everything else,
  so that one file is written without the progress line the others print.

---

## Notes on scope

`prototypes/` was excluded throughout — it carries its own crop of ruff findings
(`RUF012` mutable class defaults, `RUF034` useless `if`/`else`, `B905` unstrict `zip`) that are
appropriate to leave in exploratory code.

Ruff currently runs close to its default rule set — `[tool.ruff]` in `pyproject.toml` sets no
`lint.select`. Several items above (`B904`, `RUF013`, `A001`, `PLW2901`, `PLR09xx`) were surfaced by
ad-hoc `uv run ruff check --select ...` runs and will not be caught by CI as configured. Enabling a
subset deliberately is itself a candidate improvement, best done after the existing findings are
cleared so the first run is not a wall of noise.
