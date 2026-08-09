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

### DUP-3 — the zone-id ordering rule is enforced twice, in two classes' worth of code

- **Location:** `scripts/timezone_data.py`, `ZoneCollection.validate_structure` and
  `ZoneCollection.zone_positions`.
- **Defect:** both walk `poly_zone_ids` element by element checking it is non-decreasing, and both
  raise the same message (`"Zone IDs must be in non-decreasing order, found {} after {}"`) built
  from their own locals. `validate_structure` runs at construction, so by the time
  `zone_positions` runs the invariant is already guaranteed — its copy can only fire if a caller
  mutated the array in place.
- **Fix:** keep the validator's scan and drop the one in `zone_positions`, or express both through
  one helper. Size: ~10 lines.
- **Value:** two Python-level passes over every polygon during data generation, and two places to
  edit if the ordering rule ever changes.
- **Status:** open
- **Last touched:** 2026-08-09 — found this pass.

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

### DEAD-3 — a negative-zone-id guard that the dtype check above it makes unreachable

- **Location:** `scripts/timezone_data.py`, `ZoneCollection.validate_structure`, the
  `if min_zone_id < 0` branch.
- **Defect:** the same method rejects any `poly_zone_ids` whose `dtype.kind != "u"` a dozen lines
  earlier, so the array is unsigned by the time `.min()` is taken and the branch cannot fire. It
  reads as the guard against negative ids, which is what makes it worth removing rather than
  leaving: the real negative-id exposure is BUG-1, elsewhere and still open.
- **Fix:** delete the branch (and the now-unused `min_zone_id`). Size: ~4 lines.
- **Status:** open
- **Last touched:** 2026-08-09 — found this pass.

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

### TYPE-5 — generator functions with no return annotation

- **Location:** `scripts/timezone_data.py` — `HoleCollection.holes_in_poly` and
  `TimezoneData.holes_in_poly`; `scripts/generate_benchmark_fixtures.py` —
  `write_points_fixture`.
- **Defect:** the two `holes_in_poly` are generators returning polygon arrays and are annotated
  with nothing at all, so a caller cannot tell from the signature that iterating is required. Every
  neighbouring method in both classes is annotated, which is what makes these read as oversights
  rather than as a choice.
- **Fix:** `Iterator[np.ndarray]` and `None`. Size: ~4 lines.
- **Status:** open
- **Last touched:** 2026-08-09 — found this pass.

---

## Test quality

### TEST-4 — `test_overflow` leaves numpy's error state changed for the rest of the session

- **Location:** `tests/main_test.py`, `TestTimezonefinderClass.test_overflow`.
- **Defect:** calls `np.seterr(all="warn")` and never restores it, so every later test in the same
  process runs with `under` promoted from `ignore` to `warn`. Its `warnings.filterwarnings("error")`
  *is* undone, but only because pytest's warnings plugin wraps each test in `catch_warnings()` —
  the test does not scope it itself. It also re-imports `warnings` inside the function body, which
  the module already imports at the top.
- **Fix:** the correct pattern already exists as `strict_numpy_warnings` in
  `benchmarks/conftest.py`, whose docstring says in as many words that it is per-test *so it
  cannot leak into other modules collected in the same session*. Move that fixture somewhere both
  suites can use (`tests/auxiliaries.py` is where the other shared benchmark helpers live) and have
  `test_overflow` request it. Size: ~15 lines.
- **Value:** a leaked global makes an unrelated later test's failure depend on collection order,
  which is the hardest kind of test failure to attribute.
- **Status:** open
- **Last touched:** 2026-08-09 — found this pass, while splitting the dead `pytest.raises` blocks
  in the same file. Deliberately left out of that change: leaked state is a different defect from a
  check that cannot fail, and the fix crosses `tests/` and `benchmarks/`.

### TEST-5 — eight cleanup tests differ only in which exception they raise

- **Location:** `tests/main_test.py`, `TestTimezonefinderCleanup` — every test from
  `test_cleanup_attribute_error_suppressed` through `test_cleanup_type_error_warned`.
- **Defect:** each defines the same `TimezoneFinder` subclass overriding `cleanup` to raise one
  exception, then repeats the same `catch_warnings` block and the same `ResourceWarning` filter.
  The only things that vary are the exception and whether zero or one warning is expected. Adding a
  ninth exception to `__del__`'s suppression list means copying the block a ninth time, and a copy
  that asserts the wrong count is invisible.
- **Fix:** one parametrized test over `(exception, expected_warning_count)`, plus the two that
  additionally assert the message. Size: ~90 lines removed.
- **Status:** open
- **Last touched:** 2026-08-09 — found this pass.

### TEST-7 — the wheel install test builds and installs with two different interpreters

- **Location:** `tests/test_integration.py`, `test_install_from_artifacts[wheel]`, via
  `tests/auxiliaries.py`'s `BUILD_WHEEL_CMD` and `setup_venv`.
- **Defect:** `uv build --wheel` picks its own interpreter, while `setup_venv` creates the target
  venv from `sys.executable` — the one running pytest. When those differ, the ABI-tagged wheel
  (`cp3XY-cp3XY-…`) is rejected by the venv's pip and the test fails with *"is not a supported
  wheel on this platform"*, which reads like a packaging bug rather than a mismatched pair of
  interpreters. The sdist half of the same test passes, because an sdist has no ABI tag.
- **Reproduced:** on unmodified `origin/master` (c0a6887), on a machine whose default `python3` is
  3.14 while the project venv is 3.12: `uv build` produces `cp314`, `setup_venv` builds a 3.12
  venv. CI never sees it, since there the two are the same interpreter. **A local `make testall`
  therefore cannot be fully green on such a machine** — treat this one failure as pre-existing.
- **Fix:** build for the interpreter the test will install into — `uv build --wheel --python
  {sys.executable}`. Size: ~5 lines.
- **Status:** open
- **Last touched:** 2026-08-09 — found this pass, as the only failure in the final `make testall`
  gate; confirmed pre-existing by running the same test on unmodified `origin/master`.

### TEST-6 — a stale two-line comment closes `tests/main_test.py`

- **Location:** `tests/main_test.py`, the last two lines of the file.
- **Defect:** the same comment (*"TEST equality for all results. in_memory_mode = True/False must
  not change the results"*) appears twice, and it reads as a to-do for something
  `TestTimezonefinderClassTestMEM` already does — it re-runs the whole `TestTimezonefinderClass`
  suite with `in_memory_mode = True`.
- **Fix:** delete both lines. Size: 2 lines.
- **Status:** open
- **Last touched:** 2026-08-09 — found this pass.

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

### BIG-3 — the GeoJSON parser threads nine accumulator lists through three call levels

- **Location:** `scripts/timezone_data.py`, `TimezoneData.from_geojson` and the three classmethods
  below it: `_process_timezone_feature` (12 parameters), `_process_polygon_with_holes` (12),
  `_process_hole` (8).
- **Defect:** `from_geojson` declares nine empty lists plus two counters and passes them down two
  levels for the callees to append to. `poly_id` and `nr_of_holes` are additionally returned and
  reassigned at each level, so each function both mutates shared state and threads a counter — and
  which arguments are inputs and which are outputs is visible only by reading the bodies. The
  parameter order also has to match at three call sites with nothing checking it: several
  neighbouring parameters share a type (`PolygonList` appears twice, `list[int]` three times), so
  a transposition type-checks.
- **Fix:** one mutable accumulator (a dataclass with the nine lists and two counters) passed once,
  turning the three signatures into `(accumulator, <the thing being parsed>)`. Size: ~120 lines
  touched, no logic moved.
- **Why it is not a straight refactor:** this is the data converter, and the only thing that proves
  it neutral is regenerating the binaries and confirming `git status --short timezonefinder/data`
  is empty — which needs a timezone-boundary-builder download (`update_data.sh`), not just a test
  run. Worth doing, but the verification is the expensive part, so it should be its own pass.
- **Status:** open
- **Last touched:** 2026-08-09 — found this pass.

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
- **Last touched:** 2026-08-09 — `B904` and `B023` are now both clean repo-wide (excluding
  `prototypes/`) and could be enabled on their own. `B905` is down to 9 sites: two in
  `scripts/timezone_data.py`'s validators and one in `tests/utils_test.py` where the lengths are
  checked on the line above, the rest genuinely paired by construction. The one worth looking at
  on its own merits is `timezonefinder/flatbuf/io/hybrid_shortcuts.py`'s
  `zip(poly_id_hex_ids, poly_id_lengths)` — the only one on the library's own load path. A
  truncation there drops shortcut entries silently, and `_iter_boundaries_in_shortcut` treats a
  missing hex id as "no candidate polygons" (`shortcut_mapping.get(hex_id)` is `None` → `return`),
  so those coordinates would answer `None` rather than raise. Both arrays come out of one
  FlatBuffers message, so this needs a corrupt file to happen at all — but it is the one site where
  the failure mode is a wrong answer.

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

| 5 (checks that cannot fail) | 2026-08-09 | `tests/main_test.py`, `scripts/timezone_data.py`, `scripts/measure_memory.py` and `scripts/generate_benchmark_fixtures.py` read in full — the four previously unswept modules named by pass 4; every multi-statement `pytest.raises`/`pytest.warns` block in `tests/` and `benchmarks/` enumerated with an AST scan (all four were in `tests/main_test.py`, all four now split) | `docs/`, `.github/workflows/`, `tests/test_benchmark_ci_tooling.py`, `tests/test_optimized_hybrid_shortcuts.py`, `tests/test_render_benchmark_reports.py` |

Areas with **no coverage in any pass yet**, and therefore the cheapest place for the next pass to
start: `docs/` prose, `.github/workflows/`, and the larger test modules
(`tests/test_benchmark_ci_tooling.py`, `tests/test_optimized_hybrid_shortcuts.py`,
`tests/test_render_benchmark_reports.py`, `tests/utils_test.py`,
`tests/test_package_contents.py`).

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
- Pass 5: `scripts/measure_memory.py` (read in full, nothing found); `benchmarks/test_inside_polygon.py`'s
  `STRATA` list, which repeats the `PIP_STRATA` names as explicit `pytest.param` ids — deliberate,
  since `CONTRIBUTING.md` requires benchmark ids to be written out rather than derived, and
  deriving them from a data file would let a fixture regeneration silently reset chart history;
  `tests/main_test.py`'s `test_edge_shortcut_validity`, which asserts nothing beyond "does not
  raise" on the base class — that *is* its subject, and `test_edge_shortcut_result` covers the
  expected values for the class that has polygon data.
