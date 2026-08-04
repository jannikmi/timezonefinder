# CLAUDE.md

## Project Overview

`timezonefinder` is a Python library for offline timezone lookups by WGS84 coordinates. It
prioritises accuracy at timezone borders (no geometry simplification) while staying fast and
broadly runtime-compatible: FlatBuffers polygon data, H3 spatial shortcuts for candidate pruning,
optional Numba/clang acceleration for point-in-polygon, NumPy for coordinate handling.

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
- `make install` to set up, `make lock` when Python versions or dependencies change
- Run `make hook` (pre-commit: ruff format/check, mypy, file integrity, custom FlatBuffers and
  unused-Numba checks) after code changes; failures must be fixed before committing
- Don't prefix suggested commands with a redundant `cd` into the project root

## Project Structure

Most modules are self-describing; the non-obvious ones:

- `timezonefinder/configs.py`: central type definitions and runtime constants (coordinate scaling,
  FlatBuffers layout)
- `timezonefinder/timezonefinder.py`: `TimezoneFinder` (full polygon search) and `TimezoneFinderL`
  (shortcut-only heuristic)
- `timezonefinder/utils.py` / `utils_numba.py` / `utils_clang.py`: polygon math, pure-Python plus
  the two acceleration backends
- `timezonefinder/data/`: binary assets (FlatBuffers polygons/shortcuts, NumPy arrays), generated
- `scripts/file_converter.py`: ingests timezone-boundary-builder GeoJSON, emits the binary assets
- `benchmarks/`: `pytest-benchmark` suites, excluded from `make test`/`make testall` via `testpaths`.
  The CI-tracked `benchmark_core` set is the uniformly-random headline plus the unique/ambiguous
  per-class diagnostics; fixtures are sampled area-uniformly, unlike the test suite's pole-biased
  `get_rnd_query_pt` — see `CONTRIBUTING.md`
- `scripts/normalize_benchmark_json.py` / `benchmark_noise.py` / `assert_acceleration_path.py`:
  benchmark CI helpers — make the trend chart track `min` instead of the noise-sensitive `mean`,
  derive the alert threshold from repeated identical runs, and guard the history against a silent
  numba/clang switch
- `docs/data_format.rst`: authoritative reference for binary layouts and coordinate scaling

## Common Commands

| Task | Command |
|------|---------|
| Unit tests (fast, excludes integration/slow) | `make test` |
| Integration tests | `make testint` |
| All tests | `make testall` |
| Single test / pattern | `uv run pytest tests/…::test_name` / `-k pattern` |
| Benchmarks | `make speedtest` |
| Reproduce the CI benchmark measurement | `make benchmarks-ci` |
| Measure the benchmark noise floor | `make benchmark-noise` |
| Pre-commit validation | `make hook` |
| Full test matrix | `make tox` |
| Regenerate timezone data | `make data` (downloads full dataset) |
| Build docs | `make docs` |
| Compile FlatBuffers schemas | `make flatbuf` |
| Tag + push release | `make release` |

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
- Keep `__all__` in `__init__.py` files — they define the public API surface and are test-checked
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

## Data Pipeline & Versioning

- `update_data.sh` downloads a timezone-boundary-builder release into `tmp/` and runs
  `scripts/file_converter.py`, which scales coordinates by 10^7 into int32. Regenerating data
  warrants a minor version bump
- The reduced `--dataset=now` variant loses historical zone names; the full dataset keeps all 440+
- Benchmark fixtures in `tests/fixtures/benchmarks/` are pinned to the `DATA_VERSION` they were
  generated against and the loader refuses mismatches. `make data` regenerates them; use
  `make benchmark-fixtures` only when just the fixtures need refreshing
- When modifying a FlatBuffers schema, delete previously generated binary artifacts so they
  regenerate consistently
- `.github/workflows/check_data_updates.yml` opens an update PR weekly when upstream has a new
  release; `release_data_update.yml` merges it and pushes the tag with a GitHub App token (the
  default `GITHUB_TOKEN` would not trigger `build.yml`)

## Release Process

From `master` only: update `CHANGELOG.rst`, ensure `make hook` and `make testall` pass, then
`make release` to tag and push.

## Canonical Instructions File

This file is the single source of truth for coding-agent instructions. `AGENTS.md` and
`.cursor/rules/repo-instructions.mdc` are pointer stubs for tools that look for those filenames —
update this file only, and don't let the stubs accumulate their own copies.
