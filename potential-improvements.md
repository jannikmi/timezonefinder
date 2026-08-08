# Potential improvements

Working ledger of internal code-quality findings for `timezonefinder`. It is committed so that it
reaches the next quality pass through `master`: every pass reads it before touching a source file,
re-verifies the open entries against the current code, and writes back what it found.

**This is a to-do list, not a history.** A pass that ships an entry *deletes* it in the same pull
request — the code is the evidence that it is done, the changelog says what changed, and
`git log -- potential-improvements.md` still has the text. Entries that were *rejected*, ruled *out
of scope* or *withdrawn* stay: they encode a dead end, and re-discovering one costs a whole pass.
So does the *Deliberately checked and found sound* list at the foot.

Almost everything here is internal quality — diagnostics that get discarded, duplication that will
drift, docstrings describing code that no longer exists, dead definitions, annotations that
contradict their call sites. The exception is the *Behaviour defects* section: entries a quality
pass is not allowed to fix, recorded where they will not be lost.

**How to read an entry.** Locations are given by file plus a code anchor (a function or symbol
name), never a line number, so they survive reformatting. `Size` is a rough count of changed lines.
`Status` is one of `open`, `rejected (reason)`, `out of scope (reason)` or `withdrawn (reason)` —
everything still written down is unfinished or deliberately declined. Do not re-litigate a closed
entry and do not re-add it under a new id.

Order within each section is by expected value per line of review, following the ranking used to
pick work: **defects that will cause a real bug later > duplication that will drift > readability**.

---

## Behaviour defects

Out of scope for a quality pass by definition — fixing one changes observable behaviour. Recorded
here because the alternative is losing them; each needs the maintainer's call, not an agent's.

### BUG-1 — a negative zone or boundary id silently returns the wrong zone

- **Location:** `timezonefinder/timezonefinder.py`, `AbstractTimezoneFinder.zone_id_of` and
  `zone_name_from_id`.
- **Defect:** both index a Python list / numpy array directly, so a negative id is a valid index
  counting from the end rather than an error. Measured against the packaged data:
  `zone_name_from_id(-1)` returns `Etc/GMT+12` and `zone_id_of(-1)` returns `443`, with
  `nr_of_zones == 444`. `zone_name_from_id` explicitly range-checks in its `except IndexError`
  handler, which a negative id never reaches, so the guard reads as complete and is not.
- **Value:** a caller propagating a `-1` sentinel — the conventional "not found" from an index
  lookup — gets a plausible timezone name back instead of an exception. Both are public API.
- **Fix:** reject `< 0` explicitly in both, alongside the existing upper-bound check. Size: ~6
  lines. **This is a behaviour change** (a call that returns today would raise), so it wants a
  maintainer decision and a changelog bullet in the main list, not a quality pass.
- **Status:** open — out of scope for the quality pass that found it.
- **Last touched:** 2026-08-08 — found and measured this pass, while correcting the `:raises:`
  lines of the same two methods (DOC-2).

### API-1 — `AbstractTimezoneFinder.__init__` takes an `in_memory` it never uses

- **Location:** `timezonefinder/timezonefinder.py`, `AbstractTimezoneFinder.__init__`.
- **Defect:** the parameter is accepted and then not read; `TimezoneFinder.__init__` applies its
  *own* copy of the argument to the two `PolygonArray` constructors after calling `super()`. The
  base class loads only data it always keeps in memory, so there is nothing for it to select. This
  is what the docstring corrected in DOC-2 was groping at when it called the parameter inert.
- **Fix:** either drop it from the base signature (subclasses stop forwarding it) or have the base
  store it for subclasses to read. Size: ~10 lines.
- **Why it is not a straight refactor:** `AbstractTimezoneFinder` is importable from the package
  root, so a signature change is public API surface, and `TimezoneFinderL` accepts `in_memory`
  purely to forward it. Needs a decision on whether that parameter should exist at all.
- **Status:** open
- **Last touched:** 2026-08-08 — found this pass. Documented accurately rather than changed; see
  DOC-2.

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

### TYPE-4 — builtins shadowed

- **Location:** `scripts/file_converter.py`, `for dir, bounds in boundary_sources:` (ruff `A001`);
  `scripts/hex_utils.py`, `HexIdSet.from_id(cls, id: int, ...)` (ruff `A002`).
- **Fix:** rename the loop variable and the parameter. `from_id` has one call site
  (`scripts/timezone_data.py`, `Hex.from_id(hex_id, data)`) and passes it positionally, so renaming
  it moves nothing. Size: ~6 lines.
- **Status:** open
- **Last touched:** 2026-08-07 — re-verified; the `A002` site added this pass, same defect and same
  fix, so it belongs here rather than in an entry of its own.

---

## Test quality

### TEST-1 — the benchmark fixture loader pairs two files with a silent `zip`

- **Location:** `benchmarks/conftest.py`, `pip_inputs_by_stratum`, the
  `zip(inputs, strata)` (ruff `B905`).
- **Defect:** `inputs` and `strata` are loaded from two separate fixture files and zipped without
  `strict=`. If they ever disagree in length, `zip` truncates to the shorter one without a word.
  The per-stratum count check below it catches only the case where a bucket ends up short — a
  *misaligned* pairing that still fills every bucket labels each point with the wrong stratum, and
  the per-stratum benchmark report then attributes costs to the wrong polygon sizes while looking
  entirely healthy.
- **Fix:** `strict=True`. Size: 1 line. Both files come from one generator run and are pinned by
  `FIXTURE_VERSION`, so this is defence in depth against corrupt fixtures rather than a live bug —
  but it is the difference between a loud failure and a quietly wrong report.
- **Status:** open
- **Last touched:** 2026-08-08 — re-verified, unchanged. Worth fixing together with TEST-3 below,
  which is the same fixture and the same silent-hole shape.

### TEST-3 — a wholly missing stratum passes the fixture completeness check

- **Location:** `benchmarks/conftest.py`, `pip_inputs_by_stratum`, the
  `for stratum, bucket in grouped.items()` check.
- **Defect:** the check iterates `grouped`, which only ever holds strata the fixture actually
  contained. A stratum missing from the fixture entirely never becomes a key, so the check passes
  and the failure surfaces later as a bare `KeyError: 'large'` from
  `pip_inputs_by_stratum[stratum]` inside the benchmark — the one place the carefully worded
  "regenerate the fixtures via `make benchmark-fixtures`" message would have been useful.
- **Fix:** check against the expected stratum names (`STRATA` in
  `benchmarks/test_inside_polygon.py`, or the stratum set the generator writes) rather than
  against what was found. Size: ~5 lines. Note the declare-once rule — the names exist in
  `scripts/generate_benchmark_fixtures.py` already, so import rather than retype them.
- **Status:** open
- **Last touched:** 2026-08-08 — found this pass.

### TEST-2 — a cleanup test closes over its loop variable

- **Location:** `tests/main_test.py`, `test_cleanup_does_not_raise_to_user` (ruff `B023`).
- **Defect:** the `TestTimezoneFinder.cleanup` defined inside the loop raises `error`, which is
  looked up when `cleanup` runs, not when it is defined. Within one iteration that is the intended
  value, so the test is not wrong today; but each iteration's `tf` is collected later, re-entering
  `__del__` with whatever `error` has become. The failure message names `error_type` as though the
  binding were fixed, which is what makes it read as correct.
- **Fix:** bind the exception as a default argument (or build the subclass from a factory). Size:
  ~4 lines.
- **Value:** low as a live defect, but the test's whole subject is `__del__` at collection time,
  which is exactly when the binding stops meaning what the message says.
- **Status:** open
- **Last touched:** 2026-08-07 — found this pass.

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

## Report rendering

First sweep of `scripts/render_benchmark_reports.py` — the largest module no earlier pass had read.
Nothing in it is wrong; these three are readability and drift.

### REND-1 — a conditional expression hides inside a paragraph of prose

- **Location:** `scripts/render_benchmark_reports.py`, `render_memory`, the second
  `reporter.add_text(...)` call.
- **Defect:** the argument is `"<12 lines of implicitly concatenated prose>" if workload_size else
  "<3 more lines>"`, with the `if`/`else` buried in the middle of what reads as one string literal.
  Correct — the conditional guards the `{workload_size:,}` interpolation that would otherwise fail
  on `None` — but a reader editing the long branch has no reason to look for a ternary at its foot,
  and moving a sentence across it changes which report gets it.
- **Fix:** two named locals, or an `if`/`else` statement around two `add_text` calls. Size: ~15
  lines. Covered by `tests/test_render_benchmark_reports.py`, so a regression is visible.
- **Status:** open
- **Last touched:** 2026-08-08 — found this pass.

### REND-2 — the two memory-mode labels are written down twice

- **Location:** `scripts/render_benchmark_reports.py`, `_memory_mode_label` returns the literals
  `"in-memory"` / `"file-based"`, which `PARAM_LABELS` already maps from `in_memory` /
  `file_based`.
- **Defect:** `PARAM_LABELS` is the module's declared display vocabulary and every other label goes
  through it. Renaming a label there leaves this function rendering the old wording into the
  comparison bullets while the tables above use the new one.
- **Fix:** look the labels up in `PARAM_LABELS`. Size: ~5 lines.
- **Status:** open
- **Last touched:** 2026-08-08 — found this pass.

### REND-3 — set membership expressed as a scan over lists of dicts

- **Location:** `scripts/render_benchmark_reports.py`, `render_timezone_finding`:
  `other = [b for b in benches if b not in in_memory and b not in file_based]`.
- **Defect:** `in` over a list of dicts compares by value, so this is a deep-equality scan to
  answer a question the two lines above already answered by name suffix. Harmless at ~14
  benchmarks, but it reads as though identity mattered and it does not.
- **Fix:** classify on the suffix directly, as the two lines above do. Size: ~3 lines.
- **Status:** open
- **Last touched:** 2026-08-08 — found this pass.

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
| 3 (CLI output path) | 2026-08-07 | `timezonefinder/command_line.py` and `tests/cli_test.py` (rewritten); the previously-unswept `timezonefinder/np_binary_helpers.py`, `benchmarks/conftest.py` and the `scripts/` benchmark-CI helpers (`normalize_benchmark_json.py`, `compare_benchmark_runs.py`, `benchmark_noise.py`) read in full; a repo-wide ruff `--select ALL` triage pass over everything but `prototypes/` and the generated bindings | `docs/`, `.github/workflows/`, `scripts/render_benchmark_reports.py`, `scripts/describe_benchmark_machine.py`, `benchmarks/test_*.py` |
| 4 (docstring contracts) | 2026-08-08 | The three previously-unswept modules — `scripts/render_benchmark_reports.py`, `scripts/describe_benchmark_machine.py` and all three `benchmarks/test_*.py` — read in full; `timezonefinder/timezonefinder.py`, `utils.py`, `zone_names.py`, `polygon_array.py`, `global_functions.py` re-read for docstring/behaviour agreement, every `:raises:`/`:return:` claim in `timezonefinder/` checked against the running code | `docs/`, `.github/workflows/`, `scripts/timezone_data.py`, `scripts/measure_memory.py`, `scripts/generate_benchmark_fixtures.py`, the larger `tests/` modules |

Areas with **no coverage in any pass yet**, and therefore the cheapest place for the next pass to
start: `docs/` prose, `.github/workflows/`, `scripts/timezone_data.py` (592 lines),
`scripts/measure_memory.py`, `scripts/generate_benchmark_fixtures.py`, and the larger test modules
(`tests/main_test.py`, `tests/test_benchmark_ci_tooling.py`,
`tests/test_optimized_hybrid_shortcuts.py`).

The `--select ALL` triage above is worth repeating, but its output needs filtering: 180 findings,
of which the ones already judged not worth acting on are `EXE001`/`EXE002` (shebangs on modules run
via `-m`), `S311` (the fixture samplers are not cryptographic), `S603`/`S607` (subprocess calls in
tests and build scripts with fixed argument lists), `RUF022`/`RUF023` (`__all__` ordering — the
current order groups by meaning, which is more useful than alphabetical) and the `TD`/`FIX` family.

Deliberately checked and found sound, so do not re-raise them:

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
- Pass 4: `scripts/describe_benchmark_machine.py` (read in full, nothing found); the three
  `benchmarks/test_*.py` suites (thin by design — parametrize tables plus a `_run_over` loop, and
  the shared `_run_over` in two of them is deliberately not hoisted into `conftest.py`, since an
  import would put a function call between the benchmark and the code it times);
  `render_benchmark_reports.py`'s four `render_*` functions sharing a load/headline/table/summary
  shape — extracting it would trade four readable functions for a framework, and the differences
  are exactly the report-specific parts.
