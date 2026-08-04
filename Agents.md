# Agents Guide for timezonefinder

## Mission

This Python library `timezonefinder` provides offline timezone lookups for WGS84 coordinates by combining preprocessed polygon data, H3-based spatial shortcuts, and optional acceleration via Numba or a clang-backed point-in-polygon routine. In comparison to other alternatives this package aims at maximum accuracy around timezone borders (no geometry simplifications) while offering fast lookup performance and compatibility with many (Python) runtime environments. The shipped dataset uses the full original timezone dataset with all >440 timezone names, providing full localization capabilities and historical timezone accuracy.

## Repository Tour

- `timezonefinder/`: core library with `TimezoneFinder` (full polygon search), `TimezoneFinderL` (shortcut-only heuristic), global helper functions, CLI entry point, and utilities for polygon math and binary IO.
- `timezonefinder/data/`: packaged binary assets (FlatBuffers coordinate stores, NumPy metadata arrays, zone name list, shortcut index) consumed at runtime.
- `scripts/`: tooling for regenerating data (`file_converter.py`, `update_data.sh`), reporting, and helper configs shared by tests; relies on `uv` for builds.
- `tests/`: PyTest suite with fast unit coverage plus integration tests that build wheels/sdists inside venvs to validate packaging.
- `docs/`: Sphinx documentation mirroring PyPI content; `docs/data_format.rst` is the authoritative reference for binary layouts.
- `Makefile`, `tox.ini`, `pyproject.toml`: developer entry points for dependency sync, lint/test orchestration, and distribution metadata.
- `timezonefinder/command_line.py` defines the officially supported and tested CLI interface that mirrors the parts of the Python API.

## Runtime Model

The primary lookup flow converts query coordinates to scaled int32 values, collects candidate polygon IDs via the H3 shortcut map, rejects polygons whose bbox rules them out, checks holes first, and then applies a ray casting point-in-polygon test. When candidates share a timezone ID, the implementation short-circuits without extra geometry checks. Ocean zones (`Etc/GMT+/-XX`) guarantee a timezone match for all possible input coordinates unless callers explicitly use `timezone_at_land`.

## Data Pipeline

`update_data.sh` downloads a chosen timezone-boundary-builder release (`--dataset=full|same-since-now`, optional `--with-oceans`), unpacks it to `tmp/`, executes `scripts/file_converter.py` to emit FlatBuffers/NumPy assets under `timezonefinder/data/`, records the downloaded release tag in the `DATA_VERSION` file, regenerates the committed benchmark fixtures under `tests/fixtures/benchmarks/` (see below), bumps the patch version, prepends the matching `CHANGELOG.rst` entry, and deletes intermediates when `--rm-tmp` is passed. The script is non-interactive and safe to run in CI: `.github/workflows/check_data_updates.yml` compares `DATA_VERSION` against the latest upstream release weekly and, when a new release is available, runs the script and opens a ready-to-review update PR (falling back to a notification issue if the automated update fails). When the update PR's CI/CD pipeline passes, `.github/workflows/release_data_update.yml` merges it and pushes the version tag with a GitHub App token (the default `GITHUB_TOKEN` would not trigger the release pipeline in `build.yml`); on failure it labels the PR `automation-failed` and notifies the maintainer. The converter multiplies coordinates by 10^7, persists bboxes, hole registries, shortcut maps, and zone metadata; adjust `scripts/configs.py` when experimenting with alternative resolutions or debugging flags. When changing the datatype of shortcut-related FlatBuffers schemas (for example `hybrid_shortcuts_uint16.fbs`), delete any previously generated `.fbs` binary artifacts so they are regenerated consistently.

### Benchmark fixtures

`tests/fixtures/benchmarks/` holds a committed, seeded set of benchmark inputs (`scripts/generate_benchmark_fixtures.py`, `make benchmark-fixtures`) so two runs of the same commit execute byte-identical work. Some of these fixtures are derived from the boundary data itself: on-land/shortcut classification depends on `TimezoneFinder`'s shortcut map, and `pip_inputs.npy` stores positional polygon IDs. Each fixture set therefore records the `DATA_VERSION` it was generated against in `tests/fixtures/benchmarks/metadata.json`, and the loader (`tests/auxiliaries.py`'s `load_benchmark_points`/`load_pip_inputs`) raises `BenchmarkFixtureError` if the currently installed `DATA_VERSION` (or polygon count) doesn't match, rather than silently benchmarking a stale or invalid workload. `update_data.sh` regenerates the fixtures automatically right after bumping `DATA_VERSION`, so a manual data update only needs `make data`; only run `make benchmark-fixtures` by hand when only the fixtures (not the boundary data) need refreshing, e.g. after changing the generator's sampling logic.

## Development Workflow

- useful commands are documented in the `Makefile`
- Install tooling via `uv sync --all-groups` (or `pip install timezonefinder[numba]` for runtime only); extras `numba` and `pytz` live in `pyproject.toml`.
- all python commands should be run via `uv run`
- whenever dependencies or the set of officially supported/tested Python versions change, update the lockfile with `make lock`
- **Testing**: Use make commands (`make test`, `make testint`, `make testall`) for global test runs. When only specific isolated unit tests are affected, run them directly via `uv run pytest tests/path/to/test_file.py::test_name` or `uv run pytest -k "test_pattern"`. For full test suites: `make test` (unit tests excluding integration and slow), `make testint` (integration tests), `make testall` (all tests including slow), or `uv run tox` (all environments).
- Format/lint: Ruff, isort, mypy, and pre-commit hooks are wired through `pyproject.toml` and the `Makefile` targets (`make hook`).
- Docs: build with `(cd docs && make html)`; badges in `docs/badges.rst` stay in sync manually with `README.rst`.
- Packaging: wheels/sdists use `uv build`; integration tests exercise both `setup.py` and `uv` paths, so keep them green after touching build config.
- CI/CD: GitHub Actions testing and deployment pipeline is defined `.github/workflows/build.yml`
- Coding standards, performance targets, typing requirements, and PR expectations live in `CONTRIBUTING.md`. Review them before starting an implementation or handing work to another agent.
- pre-commit hooks are configured in `.pre-commit-config.yaml` and should be installed before making changes with `make hook`

## Testing Notes

Unit tests rely on fixture polygons plus scripts under `tests/auxiliaries.py`. Integration tests spin up disposable venvs and install built artifacts, which is slow but catches missing runtime dependencies - skip unless you change packaging or compiled assets. Performance harnesses live in `scripts/check_speed_*.py` and can be invoked via `make speedtest` when altering hotspots.

`slow`-marked tests are excluded from `make test` because they're exhaustive, not general-purpose: they iterate every polygon/timezone/shortcut cell (`main_test.py`'s `test_coords_of`/`test_holes_of_poly`/`test_get_geometry`, `global_functions_test.py::test_get_geometry`, `shortcut_test.py`'s completeness/consistency checks - relevant after touching `polygon_array.py`, shortcut generation, or the data converter) or hypothesis-fuzz the lookup API (`test_property_api.py` - relevant after touching the lookup path itself). Default to targeted `pytest` runs or `make test` while iterating; only run `make testall` (or the specific slow tests that match what you changed) before finishing a PR.

## Release Touchpoints

Regenerating data changes the binary blobs in `timezonefinder/data/` and typically warrants a minor version bump via `uv version`. Update `CHANGELOG.rst`, regenerate `docs/data_report.rst` through `scripts/reporting.py`, and tag releases with `make release`.

## Pitfalls & Knowledge

- the optional Numba dependency accelerates `utils.pt_in_poly_python`; when absent, the CFFI-backed clang extension is used - verify both paths if you touch `utils.py` or polygon math.
- Keep coordinate scaling factors (`DECIMAL_PLACES_SHIFT`, `COORD2INT_FACTOR`) in sync between runtime and converter; altering them invalidates shipped binaries.
- `TimezoneFinderL` is heuristic only; prefer full `TimezoneFinder` when correctness matters, and document any behavior changes in `docs/2_use_cases.rst`.
- The default dataset is the full original dataset. The reduced "now" dataset is available via update_data.sh for users who prefer a smaller memory footprint, but it loses location-specific names.
- Global state in `timezonefinder/global_functions.py` intentionally delays instantiation; avoid side effects before the first call and prefer dependency injection inside tests.
- Thread-safety: Global helper functions are not thread-safe - prefer explicit `TimezoneFinder(in_memory=True)` instances for concurrent workloads.
- do not remove the __all__ definitions in `__init__.py` files; they define the public API surface and are checked by tests.
- Declare path/filename constants once, in whichever module owns the resource, and import them everywhere else - do not re-derive the same path or re-type the same file/directory name as a string literal in a second file. `tests/auxiliaries.py`'s `BENCHMARK_FIXTURES_DIR`/`BENCHMARK_FIXTURES_METADATA_PATH`/`DATA_VERSION_FILE`/`*_FIXTURE` name constants are the pattern: `scripts/generate_benchmark_fixtures.py`, `scripts/check_speed_*.py`, and the tests that load these fixtures all import them rather than hardcoding "random_points", "pip_inputs", "metadata.json", etc. a second time. A duplicated literal drifts silently the next time one copy is renamed.
