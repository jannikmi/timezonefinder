# Potential improvements

A triaged register of the internal quality debt `timezonefinder` is carrying, kept in the open.
Every entry has been verified against the current code and ranked, and each one records the
judgement that was made about it — including the ones judged not worth doing.

Entries are ordered within each section by expected value per line of review: **defects that will
cause a real bug later > duplication that will drift > readability**. That ranking is the point of
the file. Listing everything that could be improved is easy and worth little; what costs something
is deciding which findings earn a reviewer's attention, and writing down why the rest do not.

Almost everything here is internal quality — diagnostics that get discarded, duplication that will
drift, docstrings describing code that no longer exists, dead definitions, annotations that
contradict their call sites. None of it is a user-visible bug, with one deliberate exception: the
*Behaviour defects* section, which holds findings that would change observable behaviour to fix.
Those need the maintainer's call rather than a cleanup pass, and they are recorded here because the
alternative is losing them.

**How to read an entry.** Locations are given by file plus a code anchor (a function or symbol
name), never a line number, so they survive reformatting. `Size` is a rough count of changed lines.
`Status` is one of `open`, `rejected (reason)`, `out of scope (reason)` or `withdrawn (reason)` —
everything still written down is unfinished or deliberately declined. Do not re-litigate a closed
entry and do not re-add it under a new id.

**How it is maintained.** The file is committed so that it reaches the next quality pass through
`master`: every pass reads it before touching a source file, re-verifies the open entries against
the current code, and writes back what it found. It is a to-do list, not a history — a pass that
ships an entry *deletes* it in the same pull request, since the code is the evidence that it is
done, the changelog says what changed, and `git log -- potential-improvements.md` still has the
text. Entries that were *rejected*, ruled *out of scope* or *withdrawn* stay: they encode a dead
end, and re-discovering one costs a whole pass. So does the *Deliberately checked and found sound*
list at the foot.

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

### API-2 — every submodule is reachable as a package attribute, so the public API is wider than `__all__` says

- **Location:** `timezonefinder/__init__.py`.
- **Defect:** `__all__` constrains `import *` only. Because `__init__.py` imports from
  `timezonefinder.timezonefinder` and `timezonefinder.global_functions`, and those import further
  modules, `dir(timezonefinder)` also exposes `utils`, `configs`, `polygon_array`,
  `coord_accessors`, `flatbuf`, `np_binary_helpers`, `zone_names`, `utils_clang`, `utils_numba` and
  `inside_polygon_ext`. `docs/4_api.rst` documents seven names; roughly twenty are reachable, and
  `timezonefinder.utils.validate_coordinates` is as importable as the documented API while being
  covered by no stability promise.
- **Fix:** a module-level `__getattr__` (PEP 562) for lazy submodule access, which narrows the
  eagerly bound surface and keeps submodule imports out of `import timezonefinder`. Size: ~20 lines.
- **Why it is not a straight refactor:** removing an attribute someone imports today is a breaking
  change even though it was never documented, so this needs a decision on whether to deprecate
  first. Same shape as API-1.
- **Status:** open
- **Last touched:** 2026-08-13 — found by a wide-angle review (see the roadmap, issue #506);
  verified by running `dir(timezonefinder)`.

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

## Performance

### PERF-1 — `is_ocean_timezone` runs a regex on the `timezone_at_land` path

- **Location:** `timezonefinder/utils.py`, `is_ocean_timezone`; called from
  `AbstractTimezoneFinder.timezone_at_land`.
- **Defect:** the check is `re.match(OCEAN_TIMEZONE_PREFIX, timezone_name)` against the result
  *string*, on every call. Ocean-ness is a fixed property of a zone id for a given dataset, so this
  recomputes a constant from a string per query and couples a behavioural decision to zone naming:
  an upstream rename of the `Etc/GMT` family would silently change which results count as ocean.
- **Fix:** precompute a boolean array indexed by zone id once at load and test that instead.
  Correct by construction, faster, and decoupled from naming. Size: ~15 lines.
- **Cost, and why this is still open:** it sits on a query path, so per DUP-1's precedent and
  `CONTRIBUTING.md` it needs a before/after measurement in a no-numba environment, where the
  surrounding code is plain Python. It also adds a small per-instance array, which `make memory`
  would show. **No measurement has been taken yet** — do not retry blind, record the numbers here.
- **Value:** low to moderate. `timezone_at_land` is public and the packaged data covers the oceans,
  so the branch is taken constantly — but the regex runs on the *result*, after the lookup that
  dominates the query.
- **Status:** open
- **Last touched:** 2026-08-13 — found by a wide-angle review (see the roadmap, issue #506).

## Dead and inert code

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


### DEAD-5 — `REDUCED_TIMEZONE_MAPPING` has no consumer, and is annotated as a set

- **Location:** `tests/locations.py`, `REDUCED_TIMEZONE_MAPPING`.
- **Defect:** two independent ones. It is now unreferenced: its only reader was
  `tests/auxiliaries.py`'s `convert_to_reduced_timezone`, deleted with DEAD-1 this pass, and its own
  comment already said *"unused, but kept for future reference"*. It is also annotated
  `set[str, str]` while being a `dict` literal — `set[str, str]` is accepted at runtime (no arity
  check on `types.GenericAlias`) and mypy does not see `tests/`, so nothing catches it.
- **Fix:** delete it, or annotate `dict[str, str]` and say what still needs it. Size: ~35 lines
  removed, or 1 changed.
- **Value:** low. It is reference data rather than code — the zone merges of the reduced
  `timezones-now` dataset — which is why DEAD-1 deleted its consumer and left it standing rather
  than deciding for the maintainer. Recorded so the decision is made once.
- **Status:** open
- **Last touched:** 2026-08-14 — found this pass, as a consequence of DEAD-1.

---

## Type annotations that do not match reality

### TYPE-2 — implicit `Optional` (ruff `RUF013`)

- **Location:** `scripts/benchmark_utils.py` — `additional_info: dict[str, Any] = None`,
  `provenance: dict[str, Any] = None`.
- **Defect:** PEP 484 forbids implicit `Optional`. `no_implicit_optional = true` is already set in
  `[tool.mypy]`, but these live in `scripts/`, which the mypy hook does not currently cover.
- **Fix:** annotate `| None`. Size: 2 lines.
- **Status:** open
- **Last touched:** 2026-08-14 — the third site, `scripts/reporting.py`'s `additional_rows`, shipped
  this pass; these two are what is left. See TOOL-4 for the reason nothing catches them.


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

### TEST-11 — nothing checks that the files a distribution must *add* are present

- **Location:** `tests/test_package_contents.py`.
- **Defect:** `test_essential_files_in_distribution` covers files that exist in the checkout, so it
  cannot cover what only the build produces — `PKG-INFO`, the `.dist-info` metadata. A dead
  `EXPECTED_DIST_PATTERNS` set naming `PKG-INFO` sat in the module unreferenced, with a `TODO test`
  above it; it was deleted this pass rather than left to read as coverage that exists.
- **Fix:** assert those names against the built archives, next to the two checks already there.
  Size: ~15 lines.
- **Value:** low — an sdist without `PKG-INFO` fails at upload, so the failure is loud elsewhere.
  Recorded so the deleted constant is not rediscovered as a gap nobody knew about.
- **Status:** open
- **Last touched:** 2026-08-10 — found this pass.

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

### BIG-2 — `calculate_shortcut_index_stats` computes four unrelated things in one pass

- **Location:** `scripts/reporting.py`, `calculate_shortcut_index_stats`.
- **Defect:** computes coverage, uniqueness, storage and frequency metrics in one pass.
- **Fix:** split along those four seams. Its output is committed in `docs/data_report.rst`, so it
  needs a regenerate-and-diff to prove neutral — cheap: `uv run python -m scripts.reporting`, then
  confirm `git diff docs/data_report.rst` is empty. Size: ~80 lines moved.
- **Value:** readability only, and lower than when this entry was written. The title used to read
  "13 branches / 57 statements, over ruff's `PLR0912`/`PLR0915` defaults"; replacing the hard-coded
  H3 ladder removed six branches, so it now trips neither (40 statements against a default of 50).
  Nothing in CI asks for this split any more.
- **Status:** open
- **Last touched:** 2026-08-14 — re-verified and corrected. Deliberately not taken this pass: with
  the linter justification gone it ranked below the annotation and dead-code work.

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

### BIG-4 — `load_binary_data`'s hole branch silently yields empty lists when a file is missing

- **Location:** `scripts/reporting.py`, `load_binary_data`.
- **Defect:** the `if hole_registry_path.exists() and hole_coord_path.exists():` branch has no
  `else`, so a data directory missing either file reports zero holes rather than saying so. Every
  hole figure in `docs/data_report.rst` then reads as a legitimate zero.
- **Fix:** raise, or state the absence in the report. Size: ~8 lines. **Check first whether this is
  a behaviour change** — if any caller compiles data without holes, it is, and the entry belongs
  under *Behaviour defects* instead.
- **Value:** low-moderate, and narrower than when this entry was first written. It originally also
  covered the function being 37 statements with a function-local import mid-body; PR #509 landed
  during this pass and rewrote the loads through `PolygonArray`/`HoleArray`, taking it to 24
  statements with no local import, so only the silent-empty branch is left.
- **Status:** open
- **Last touched:** 2026-08-14 — found this pass and re-verified against #509 after rebasing onto
  it; the size complaint it was written about is gone.

---

## Report rendering

First swept by pass 4 — `scripts/render_benchmark_reports.py` was the largest module no earlier
pass had read. Nothing in it is wrong; the two below are readability.

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

### TOOL-3 — `make parse` and `make testparse` cannot run at all

- **Location:** `Makefile`, the `parse` and `testparse` targets; the absolute `from scripts...`
  imports at the head of `scripts/file_converter.py`.
- **Defect:** both targets invoke the converter *by path* (`uv run python
  ./scripts/file_converter.py ...`), which puts `scripts/` on `sys.path[0]` rather than the
  repository root, so the script's own `from scripts.timezone_data import TimezoneData` raises
  `ModuleNotFoundError: No module named 'scripts'` before any work starts. `scripts` is not among
  the installed packages in `[tool.setuptools] packages` either, so the environment does not supply
  it. Reproduced on unmodified `origin/master` with `make testparse`; the failure is immediate and
  total, not conditional on the machine.
- **Value:** `testparse` is the only cheap end-to-end exercise of the data converter — it runs
  against `tests/test_input.json` in a second, where `make data` needs a ~55 MB download and a full
  parse. Nothing in `tests/` covers `parse_data()`, so while these targets are broken the converter
  has no runnable smoke test at all, and a contributor following the `Makefile` header comment hits
  a traceback that looks like a broken checkout.
- **Fix:** invoke it as a module — `uv run python -m scripts.file_converter ...` — which is already
  how `scripts/reporting.py` is run elsewhere (`uv run python -m scripts.reporting`). Confirm the
  `argparse` entry point still behaves under `-m`, and check the other by-path invocations for the
  same defect: `update_data.sh` also calls the converter. Size: ~4 lines.
- **Status:** open
- **Last touched:** 2026-08-13 — found while regenerating the packaged data for the hole
  deduplication work (issue #350), which needed `PYTHONPATH=.` prefixed to every converter run.

### TOOL-2 — the `check-manifest` ignore list names two files that do not exist

- **Location:** `.pre-commit-config.yaml`, the `check-manifest` hook's `--ignore` argument.
- **Defect:** it lists `CONTRIBUTING.rst` (the file is `CONTRIBUTING.md`) and `publish.py` (gone
  from the repository). Both are inert — an ignore entry that matches nothing only fails to
  suppress a report — so this is tidiness, not a hole. The same argument also carries `.*` and
  `.*/*`, which exempt every dotfile and dot-directory from `check-manifest` entirely; that is what
  leaves `tests/test_package_contents.py` as the only guard over `.github/`, `.vscode/` and
  `.cursor/`.
- **Fix:** drop the two stale entries. Size: 1 line. Re-run `make hook` afterwards — the point of
  the list is that `check-manifest` stays green.
- **Status:** open
- **Last touched:** 2026-08-10 — found this pass, while correcting the same class of defect in the
  packaging test.

### TOOL-4 — the mypy hook excludes `scripts/`, where the annotations have drifted furthest

- **Location:** `.pre-commit-config.yaml`, the mypy hook's
  `exclude: ^((tests|prototypes|scripts|docs|benchmarks)/)`.
- **Defect:** `[tool.mypy]` is configured strictly enough to catch real defects, and nothing runs it
  over the four directories that hold most of the repo's Python. `scripts/reporting.py` alone had
  accumulated 17 errors, including a return annotation contradicted by the value returned and an
  entry point annotated `-> None` while returning exit codes; all were fixed this pass.
- **Fix:** narrow the exclude one directory at a time, `scripts/` first since it is now closest.
  Measured on this branch, `uv run mypy scripts/` reports **20 errors**, of which **15 are in six
  files under `scripts/`** — `shortcuts.py` (4), `file_converter.py` (4), `benchmark_utils.py` (3),
  `timezone_data.py` (2), `measure_memory.py` (1), `hex_utils.py` (1) — while `reporting.py` and
  `configs.py` are clean. The other five come from modules pulled in transitively and would not be
  fixed by narrowing the exclude to `scripts/`: four in `tests/auxiliaries.py` (two `numpy.bool`
  returns annotated `bool`, two `str` arguments to a `Path` parameter) and one missing `cffi` stub
  in `timezonefinder/utils_clang.py` that the hook already supplies via `additional_dependencies`.
  Two of the fifteen are TYPE-2's remaining sites. Size: ~30 lines plus one hook edit.
- **Value:** moderate. This is the mechanism behind TYPE-2, TYPE-4, TYPE-5 and most of what this
  pass fixed, so clearing it stops the class rather than the instances. Note the counts above are a
  moving target — re-measure rather than trusting them.
- **Status:** open
- **Last touched:** 2026-08-14 — found this pass, and re-measured after rebasing onto PR #509,
  which added `scripts/data_integrity.py` and moved several of the counts.

---

## Scope notes

`prototypes/` is excluded throughout — it carries its own crop of ruff findings (`RUF012` mutable
class defaults, `RUF034` useless `if`/`else`, `B905` unstrict `zip`) that are appropriate to leave
in exploratory code.

`timezonefinder/data/` and `timezonefinder/flatbuf/generated/` are generated and are never edited
directly; findings there belong against the generator or the schema instead.

**Structural work belongs in the issue tracker, not here.** Issue #506 is the roadmap: it ranks the
open issues and records decisions already taken (including ideas that were considered and dropped).
An entry only belongs in this ledger if it names code that exists *and* a quality pass could close
it by editing that code — everything else has no anchor to re-verify against and can never be
deleted by the pass that reads it.

---

## Coverage log

| Pass | Date | Swept | Not reached |
|---|---|---|---|
| 1 | 2026-08-06 | `timezonefinder/`, `scripts/`, `tests/`, `benchmarks/` — broad triage, findings above | `prototypes/` (deliberate), `docs/`, `.github/workflows/` |
| 2 (error diagnostics) | 2026-08-07 | Every `raise` and `except` site in `timezonefinder/` and `scripts/` (via `rg` plus ruff `B904`/`BLE`/`TRY`/`EM`/`RSE`/`S110`/`S112`); `timezonefinder/command_line.py` read in full | `docs/`, `.github/workflows/`, `benchmarks/`, `scripts/` report-rendering internals |
| 3 (CLI output path) | 2026-08-07 | `timezonefinder/command_line.py` and `tests/cli_test.py` (rewritten); the previously-unswept `timezonefinder/np_binary_helpers.py`, `benchmarks/conftest.py` and the `scripts/` benchmark-CI helpers (`normalize_benchmark_json.py`, `compare_benchmark_runs.py`, `benchmark_noise.py`) read in full; a repo-wide ruff `--select ALL` triage pass over everything but `prototypes/` and the generated bindings | `docs/`, `.github/workflows/`, `scripts/render_benchmark_reports.py`, `scripts/describe_benchmark_machine.py`, `benchmarks/test_*.py` |
| 4 (docstring contracts) | 2026-08-08 | The three previously-unswept modules — `scripts/render_benchmark_reports.py`, `scripts/describe_benchmark_machine.py` and all three `benchmarks/test_*.py` — read in full; `timezonefinder/timezonefinder.py`, `utils.py`, `zone_names.py`, `polygon_array.py`, `global_functions.py` re-read for docstring/behaviour agreement, every `:raises:`/`:return:` claim in `timezonefinder/` checked against the running code | `docs/`, `.github/workflows/`, `scripts/timezone_data.py`, `scripts/measure_memory.py`, `scripts/generate_benchmark_fixtures.py`, the larger `tests/` modules |
| 5 (checks that cannot fail) | 2026-08-09 | `tests/main_test.py`, `scripts/timezone_data.py`, `scripts/measure_memory.py` and `scripts/generate_benchmark_fixtures.py` read in full — the four previously unswept modules named by pass 4; every multi-statement `pytest.raises`/`pytest.warns` block in `tests/` and `benchmarks/` enumerated with an AST scan (all four were in `tests/main_test.py`, all four now split) | `docs/`, `.github/workflows/`, `tests/test_benchmark_ci_tooling.py`, `tests/test_optimized_hybrid_shortcuts.py`, `tests/test_render_benchmark_reports.py` |
| 6 (packaging guard patterns) | 2026-08-10 | The five test modules pass 5 left unread — `tests/test_package_contents.py`, `tests/test_benchmark_ci_tooling.py`, `tests/test_optimized_hybrid_shortcuts.py`, `tests/test_render_benchmark_reports.py`, `tests/utils_test.py` — plus `tests/auxiliaries.py` and `tests/main_test.py` re-read; every `UNWANTED_DIST_PATTERNS` entry matched against the working tree, and `MANIFEST.in` / the `check-manifest` ignore list compared against it | `docs/`, `.github/workflows/` |
| 7 (leaked state and duplicate checks) | 2026-08-14 | `.github/workflows/` read in full - the last area with no coverage in any pass (new guard: `tests/test_python_version_support.py`); `scripts/hex_utils.py` and `scripts/shortcuts.py` re-read in full; `scripts/timezone_data.py`'s `ZoneCollection` validators read and given their first tests; a repeated repo-wide ruff `--select ALL` triage over `timezonefinder/`, `scripts/`, `tests/`, `benchmarks/` (3811 findings, filtered per the note below - nothing new above the bar beyond DEAD-4 and REND-4) | `docs/` prose; `scripts/reporting.py` and `scripts/render_benchmark_reports.py` internals beyond the ruff sweep |
| 8 (the data report generator) | 2026-08-14 | `scripts/reporting.py` read in full — the last large module no pass had read end to end, and the source of five of this pass's six items; `scripts/hex_utils.py`'s `Hex` cache properties and `scripts/utils.py` re-read; `scripts/render_benchmark_reports.py` revisited only at the REND-2 site. `uv run mypy` run by hand over `scripts/`, which the pre-commit hook excludes — the first time any pass has done so, and the mechanism behind most findings here (recorded as TOOL-3) | `docs/` prose; `scripts/shortcuts.py`, `benchmark_utils.py`, `file_converter.py`, `timezone_data.py` and `measure_memory.py`, whose mypy errors TOOL-4 counts but which were not read for it; `scripts/data_integrity.py`, added by #509 mid-pass |

Every module under `tests/` has been read at least once, pass 7 covered `.github/workflows/`
and pass 8 `scripts/reporting.py`. The only area with **no coverage in any pass** is `docs/` prose —
mostly outside a code-quality pass's scope. The cheapest real starting point is therefore the ranked
open entries above rather than fresh discovery, with one exception worth knowing: pass 8 found that
running mypy by hand over an excluded directory surfaces defects no pass had seen, and only
`scripts/reporting.py` has been cleared that way (TOOL-3).

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
- Pass 7: `.github/workflows/benchmark.yml`, `benchmark-comment.yml`, `check_data_updates.yml` and
  `release_data_update.yml` (read in full, nothing found beyond the version drift now guarded);
  `timezonefinder/global_functions.py`'s module-level `TF_INSTANCE` and its `global` statement
  (ruff `PLW0603`) — deliberate and documented as not thread-safe, with per-thread instances the
  stated alternative; `scripts/hex_utils.py`'s `get_corrected_hex_boundaries` (the antimeridian and
  pole clipping, covered by `tests/hex_utils_test.py` since pass 1's follow-up).
- Pass 8: `scripts/reporting.py`'s two output redirectors — `redirect_output_to_file` (a decorator,
  opening `"a"`) and `redirect_output_to_file_contextmanager` (opening `"w"`) — which look like
  duplicates but differ in append-vs-truncate, and both have callers that depend on which they got;
  `calculate_shortcut_index_stats`'s `naive_storage_bytes`, whose conditional covers the whole
  parenthesised expression rather than just the division, so a zero entry count yields `0 * 0` and
  not a `ZeroDivisionError` — correct, and confusing enough to re-derive rather than re-raise;
  `generate_metrics_rows`'s non-numeric `str(value)` fallback, kept reachable by annotating the
  parameter `Mapping[str, object]` rather than deleted to satisfy a narrower annotation.
- Pass 6: `tests/test_benchmark_ci_tooling.py` and `tests/test_render_benchmark_reports.py` (both
  read in full, nothing found — each assertion names why it exists); `tests/auxiliaries.py`'s
  `matches_pattern`, whose `fnmatch` semantics (`*` crosses `/`, POSIX case sensitivity) are what
  the packaging patterns depend on and are correct as documented; the `.git/*` entry in
  `UNWANTED_DIST_PATTERNS`, which matches nothing in a working tree by design and is exempted
  rather than removed.
