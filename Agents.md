# Agents Guide for timezonefinder

## Mission

This Python library `timezonefinder` provides offline timezone lookups for WGS84 coordinates by combining preprocessed polygon data, H3-based spatial shortcuts, and optional acceleration via Numba or a clang-backed point-in-polygon routine. In comparison to other alternatives this package aims at maximum accuracy around timezone borders (no geometry simplifications) while offering fast lookup performance and compatibility with many (Python) runtime environments. The shipped dataset targets current/future timezone behavior by using the "same since now" reduced boundaries that merge zones equivalent in their timekeeping.

## Repository Tour

- `timezonefinder/`: core library with `TimezoneFinder` (full polygon search), `TimezoneFinderL` (shortcut-only heuristic), global helper functions, CLI entry point, and utilities for polygon math and binary IO.
- `timezonefinder/data/`: packaged binary assets (FlatBuffers coordinate stores, NumPy metadata arrays, zone name list, shortcut index) consumed at runtime.
- `scripts/`: tooling for regenerating data (`file_converter.py`, `parse_data.sh`), reporting, and helper configs shared by tests; relies on `uv` for builds.
- `tests/`: PyTest suite with fast unit coverage plus integration tests that build wheels/sdists inside venvs to validate packaging.
- `docs/`: Sphinx documentation mirroring PyPI content; `docs/data_format.rst` is the authoritative reference for binary layouts.
- `Makefile`, `tox.ini`, `pyproject.toml`: developer entry points for dependency sync, lint/test orchestration, and distribution metadata.
- `timezonefinder/command_line.py` defines the officially supported and tested CLI interface that mirrors the parts of the Python API.

## Runtime Model

The primary lookup flow converts query coordinates to scaled int32 values, collects candidate polygon IDs via the H3 shortcut map, rejects polygons whose bbox rules them out, checks holes first, and then applies a ray casting point-in-polygon test. When candidates share a timezone ID, the implementation short-circuits without extra geometry checks. Ocean zones (`Etc/GMT+/-XX`) guarantee a timezone match for all possible input coordinates unless callers explicitly use `timezone_at_land`.

## Data Pipeline

`parse_data.sh` downloads a chosen timezone-boundary-builder release (full or "now", optional ocean polygons), unpacks it to `tmp/`, executes `scripts/file_converter.py` to emit FlatBuffers/NumPy assets under `timezonefinder/data/`, runs `tox`, bumps the project version with `uv run --bump minor`, and offers to clean intermediates. The converter multiplies coordinates by 10^7, persists bboxes, hole registries, shortcut maps, and zone metadata; adjust `scripts/configs.py` when experimenting with alternative resolutions or debugging flags.

## Development Workflow

- useful commands are documented in the `Makefile`
- Install tooling via `uv sync --all-groups` (or `pip install timezonefinder[numba]` for runtime only); extras `numba` and `pytz` live in `pyproject.toml`.
- all python commands should be run via `uv run`
- Day-to-day tests: `uv run pytest -m "not integration"`; heavy packaging checks: `uv run pytest -m "integration"` or `uv run tox`.
- Format/lint: Ruff, isort, mypy, and pre-commit hooks are wired through `pyproject.toml` and the `Makefile` targets (`make hook`).
- Docs: build with `(cd docs && make html)`; badges in `docs/badges.rst` stay in sync manually with `README.rst`.
- Packaging: wheels/sdists use `uv build`; integration tests exercise both `setup.py` and `uv` paths, so keep them green after touching build config.
- CI/CD: GitHub Actions testing and deployment pipeline is defined `.github/workflows/build.yml`
- Coding standards, performance targets, typing requirements, and PR expectations live in `CONTRIBUTING.md`. Review them before starting an implementation or handing work to another agent.
- pre-commit hooks are configured in `.pre-commit-config.yaml` and should be installed before making changes with `make hook`

## Testing Notes

Unit tests rely on fixture polygons plus scripts under `tests/auxiliaries.py`. Integration tests spin up disposable venvs and install built artifacts, which is slow but catches missing runtime dependencies - skip unless you change packaging or compiled assets. Performance harnesses live in `scripts/check_speed_*.py` and can be invoked via `make speedtest` when altering hotspots.

## Release Touchpoints

Regenerating data changes the binary blobs in `timezonefinder/data/` and typically warrants a minor version bump via `uv version`. Update `CHANGELOG.rst`, regenerate `docs/data_report.rst` through `scripts/reporting.py`, and tag releases with `make release`.

## Pitfalls & Knowledge

- the optional Numba dependency accelerates `utils.pt_in_poly_python`; when absent, the CFFI-backed clang extension is used - verify both paths if you touch `utils.py` or polygon math.
- Keep coordinate scaling factors (`DECIMAL_PLACES_SHIFT`, `COORD2INT_FACTOR`) in sync between runtime and converter; altering them invalidates shipped binaries.
- `TimezoneFinderL` is heuristic only; prefer full `TimezoneFinder` when correctness matters, and document any behavior changes in `docs/2_use_cases.rst`.
- When swapping datasets, remember the reduced "now" data loses location-specific names; mention this in user-facing docs to preempt surprise regressions.
- Global state in `timezonefinder/global_functions.py` intentionally delays instantiation; avoid side effects before the first call and prefer dependency injection inside tests.
- Thread-safety: Global helper functions are not thread-safe - prefer explicit `TimezoneFinder(in_memory=True)` instances for concurrent workloads.
