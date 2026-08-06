# CLAUDE.md

## Project Overview

`timezonefinder` provides offline timezone lookups by WGS84 coordinates, prioritising accuracy at
timezone borders (no geometry simplification) over raw speed.

Constraints that shape design decisions:

- Primary users are latency-sensitive services doing high-volume, possibly concurrent lookups
  (plus one-off CLI/script use)
- Must run in **containerised deployments with constrained CPU/memory** — don't assume abundant
  RAM or many cores; the `in_memory=False` (memory-mapped) path must stay a viable low-memory option
- Must degrade gracefully without Numba/C-extension — the pure-Python path stays correct, just slower

Non-goals: sub-centimeter precision (the ~1.1 cm coordinate scaling is a deliberate ceiling, not a
bug), and general-purpose geometry — spatial code exists only in service of timezone lookup.

## Development Setup

- Use `uv` for all dependency management; run every Python command via `uv run`
- Run `make hook` after code changes; failures must be fixed before committing. Also run it after
  regenerating anything, *before* reading the diff — see *Generated Files*
- The `Makefile` header comment documents every target. Where the *choice* between targets is the
  non-obvious part, it is covered under *Testing* below and in `CONTRIBUTING.md`
- Don't prefix suggested commands with a redundant `cd` into the project root

## Project Structure

Most modules are self-describing; the non-obvious ones:

- `timezonefinder/configs.py`: central type definitions and runtime constants (coordinate scaling,
  FlatBuffers layout)
- `timezonefinder/utils.py` / `utils_numba.py` / `utils_clang.py`: polygon math, pure-Python plus
  the two acceleration backends. `utils.py` picks the implementation **at import time**, so the
  backends are entirely separate code paths whose timings are not comparable
- `benchmarks/`: `pytest-benchmark` suites, excluded from `make test`/`make testall` via
  `testpaths` — they are collected only when `benchmarks/` is passed explicitly. **Timing only**:
  memory is measured by `scripts/measure_memory.py` (`make memory`), because `tracemalloc` across
  pytest-benchmark's calibration rounds distorts the timings. Its subprocess probe must never
  import `tests/auxiliaries.py`, which allocates a 64 MB `PolygonArray` at import
- `scripts/normalize_benchmark_json.py` / `benchmark_noise.py` / `assert_acceleration_path.py` /
  `compare_benchmark_runs.py` / `describe_benchmark_machine.py`: benchmark CI helpers.
  `ubuntu-latest` pins the runner *image*, not the CPU: the pool spreads up to ~1.58x on unchanged
  code, so any two CI runs are incomparable unless they name the same CPU. `CONTRIBUTING.md` holds
  the methodology these scripts implement
- `docs/data_format.rst`: authoritative reference for binary layouts and coordinate scaling

## Runtime Lookup Flow

Coordinates → scaled int32 (×10^7) → H3 shortcut map yields candidate polygons → bounding-box
rejection → point-in-polygon (holes first, then outer ring, ray casting). Ocean zones
(`Etc/GMT±XX`) guarantee a match for any coordinate unless `timezone_at_land` is used.

## Code Guidelines

- Define types centrally in `timezonefinder/configs.py` to avoid duplication and circular imports
- Before adding any version-gated import, `__future__` feature, or compatibility shim, check
  `requires-python` and confirm the feature actually needs it on the minimum supported version
- Preserve the fast lookup path; profile hot code (polygon math, shortcut lookups) when modifying it
- Keep `COORD2INT_FACTOR` / `DECIMAL_PLACES_SHIFT` in sync between runtime and data converter
- The public API (exported functions and classes) must not break between minor versions; internal
  code, data formats, and binary assets are versioned with the package and need no compatibility
- Keep `__all__` in `__init__.py` files — they define the public API surface. Nothing asserts
  their contents directly; the only incidental protection is that `tests/conftest.py` imports
  from the top-level package, so emptying `timezonefinder/__init__.py` fails collection outright
- Prefer dependency injection over module-level state; global helper functions are NOT thread-safe,
  concurrent workloads should use per-thread `TimezoneFinder(in_memory=True)` instances
- **Declare each path/filename constant once** in the module that owns the resource and import it
  elsewhere; never re-derive a path or retype a filename string in a second file — the two copies
  drift when one is renamed

## Testing

- Add targeted tests under `tests/` for every behavioural change; mark them `@pytest.mark.unit`,
  `integration`, or `slow`. Shared fixtures live in `tests/auxiliaries.py`
- While iterating, run only the file/pattern you're touching; `make test` (~30 s) as a broader
  check; `make testall` once as a final gate before finishing a PR, not after every change
- `slow` tests are exhaustive sweeps of the whole dataset or hypothesis fuzzing, not general
  regression tests. Run them only when the change plausibly affects what they cover:
  - `main_test.py`, `shortcut_test.py`, `global_functions_test.py` slow cases — after touching
    `polygon_array.py`, `coord_accessors.py`, shortcut generation, the data converter, or `make data`
  - `test_property_api.py` — after touching `timezonefinder.py`, the `utils*` modules, or
    coordinate scaling/validation
  - `test_benchmark_fixtures.py::test_generator_*` — after touching
    `scripts/generate_benchmark_fixtures.py`
  - Otherwise (docs, CI config, tooling, reporting code) skip them: wall-clock time, no signal

## Changelog

Every change needs a `CHANGELOG.rst` entry in the `X.X.X (unreleased)` section — user-facing ones in
the main bullet list, dev tooling / refactors / CI / test infrastructure appended to the `Internal:`
sub-list. This is easy to forget for changes that don't touch `timezonefinder/` at all (docs,
`scripts/`, CI config, fixtures); those still need one. Exception: edits to `CLAUDE.md` or
`CONTRIBUTING.md` alone.

The changelog is read by users, not by reviewers of the PR that produced it. Describe the **end
state**, never the path taken to it:

- **Amend, don't append.** When a follow-up commit, review round, or fix changes something already
  described in the unreleased section, edit that bullet so it describes where the code landed.
  Adding a second bullet that corrects, tunes, or extends the first one is what makes the section
  unreadable — a released version should read as if the feature arrived in one step.
- **One bullet per user-visible change**, not per commit or per PR. A feature delivered over
  several commits (with its tests, docs, CI wiring and follow-up tuning) is one bullet.
- Keep the *why* only when it's decision-relevant for a reader — a deliberate trade-off, a
  non-obvious constraint, a gotcha. Drop tuning history ("raised from X to Y, then to Z" → state
  the final value), superseded intermediate states, and self-review narration.
- Keep bullets to a few sentences. Details that belong to contributors, not users, go in
  `CONTRIBUTING.md` or a docstring, and the bullet points there.
- Before finishing a task, re-read the whole `X.X.X (unreleased)` section: if two bullets describe
  the same feature, merge them.

## Generated Files

**Invariant: every generator emits output that is already pre-commit-clean**, so regenerating and
diffing compares like with like. Keep it that way — when it breaks, a re-parse shows spurious diffs
that look like converter drift, or real changes drown in formatting churn, and the lossless check
after a data regeneration (`git status --short timezonefinder/data` listing only genuinely changed
binaries) stops meaning anything.

What it takes to hold, for anything you add:

- `scripts/utils.py` `write_json` stringifies keys before `sort_keys`, matching `pretty-format-json`.
  Sorting int keys directly gives numeric order; the hook re-reads the file, where JSON keys are
  strings, and sorts lexicographically
- `scripts/reporting.py` emits no trailing whitespace on empty table cells and exactly one final
  newline, matching `trailing-whitespace` / `end-of-file-fixer`. `BenchmarkReporter.write_report`
  (`scripts/benchmark_utils.py`) applies the same final-newline normalisation for every
  `docs/benchmark_results_*.rst`
- `make flatbuf` runs the formatters itself, since `flatc` output differs from the committed
  bindings under `ruff-format` and `pyupgrade`

Both normalisations are covered by tests in `tests/utils_test.py`. If a generated file still comes
out dirty, fix the generator rather than committing the hook's repair — the repair is invisible and
the next regeneration undoes it.

Corollary: don't edit a generated file directly. Change the generator or the schema and regenerate.

## Documentation Files

- **`README.rst` and `CHANGELOG.rst` must be valid *standalone* RST.** Both are linted by the
  `rstcheck` pre-commit hook, unlike `docs/`, which it excludes — a Sphinx role (`:doc:`, `:ref:`)
  works in the docs build but fails the hook here, and additionally breaks the PyPI page for
  `README.rst`, which is the long description (`readme` in `pyproject.toml`). Link with an
  absolute `https://timezonefinder.readthedocs.io/…` URL instead
- **Every target in `README.rst` must be absolute, and an `.. image::` source is a target too.**
  A repo-relative `docs/…` path is a real location on GitHub and no location at all on PyPI,
  which serves the long description without the repository — and `docs/` is excluded from the
  sdist by the `check-manifest` ignore list, so the file is not even shipped. Point images at
  `https://raw.githubusercontent.com/jannikmi/timezonefinder/master/…`. Neither `rstcheck` nor
  `make docs` catches this: both accept a valid directive whose target does not resolve, so
  verify with `uv run --with readme-renderer python -m readme_renderer README.rst -o tmp/readme.html`
  and open it. `docs/index.rst` is the opposite case — it sits next to the images, so its paths
  stay relative
- **The badge block is duplicated in `README.rst` and `docs/badges.rst` on purpose** — the docs
  include it, but an `include` does not render on PyPI. This is a deliberate exception to the
  declare-once rule above; edit both copies or they drift
- `docs/` pages are Sphinx-built. A new page needs a `docs/index.rst` toctree entry or it is
  orphaned and unreachable from the sidebar. `make docs` must build without new warnings —
  `rstcheck` will not catch a broken cross-reference there
- Generated docs: `docs/benchmark_results_*.rst` (`scripts/render_benchmark_reports.py`) and
  `docs/data_report.rst` (`scripts/reporting.py`). The don't-hand-edit corollary above applies
- **`make reports` re-measures everything** — it has both `benchmarks` and `memory` as
  prerequisites — so it rewrites every committed figure on all four report pages. To change only
  the *rendering*, invoke the renderer directly against the stored JSONs; measurement and
  rendering are decoupled:
  `uv run python -m scripts.render_benchmark_reports --benchmark-json=tmp/benchmark.json --memory-json=tmp/memory.json`
  (omit `--memory-json` to leave `docs/benchmark_results_memory.rst` untouched).
  Confirm the JSONs are the ones behind the committed reports by re-rendering *before* your change
  and checking that `git diff docs/benchmark_results_*.rst` is empty

## Data Pipeline & Versioning

- `update_data.sh` downloads a timezone-boundary-builder release into `tmp/` and runs
  `scripts/file_converter.py`, which scales coordinates by 10^7 into int32. Regenerating data
  warrants a minor version bump
- Benchmark fixtures in `tests/fixtures/benchmarks/` are pinned to the `DATA_VERSION` they were
  generated against and the loader refuses mismatches. `make data` regenerates them; use
  `make benchmark-fixtures` only when just the fixtures need refreshing
- When modifying a FlatBuffers schema, delete previously generated binary artifacts so they
  regenerate consistently
- `.github/workflows/check_data_updates.yml` opens an update PR weekly when upstream has a new
  release; `release_data_update.yml` merges it and pushes the tag with a GitHub App token (the
  default `GITHUB_TOKEN` would not trigger `build.yml`)

## Release Process

From `master` only — `make release` enforces it and its `Makefile` comments carry the tag/push
ordering constraints.

## Canonical Instructions File

This file is the single source of truth for coding-agent instructions. `AGENTS.md` and
`.cursor/rules/repo-instructions.mdc` are pointer stubs for tools that look for those filenames —
update this file only, and don't let the stubs accumulate their own copies.

**Keep it current.** When you discover a durable repo fact that isn't written down here, add it as
part of the work that surfaced it. The bar is all three of:

- **durable** — still true next month; not a detail of the change you happen to be making
- **non-obvious** — it cost you a cross-reference, a failed hook, or a wrong guess to learn.
  Anything visible in the file you are already editing does not qualify
- **it has a failure mode** — you can name what silently breaks for someone who doesn't know it

Counter-pressure, because this file is loaded into every session and a bloated one gets skimmed:

- Amend an existing section rather than opening a new one — the same rule as *Changelog* above,
  for the same reason
- If the fact belongs at the point of decision (a `Makefile` comment, a docstring, a comment next
  to the constant), put it *there* and don't copy it here. Every duplicated line is a line that
  will drift
- Correct or delete entries once they go stale. A confidently wrong instruction costs more than a
  missing one
- Don't restate what the code, `git log`, or another section already says

An edit confined to this file needs no changelog entry, so recording a fact is cheap.
