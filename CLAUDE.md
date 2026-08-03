# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`timezonefinder` is a Python library for offline timezone lookups by WGS84 coordinates. It prioritizes accuracy around timezone borders (no geometry simplifications) while maintaining fast performance and broad Python runtime compatibility. The implementation combines:

- Preprocessed polygon data in FlatBuffers format
- H3-based spatial shortcuts for candidate pruning
- Optional Numba acceleration or clang-backed C extension for point-in-polygon tests
- NumPy arrays for efficient coordinate handling

## Development Setup

- **Package Manager**: Use `uv` for all dependency management (installed via `make install`)
- **Python Commands**: Always run via `uv run` (e.g., `uv run pytest`, `uv run python script.py`)
- **Installation**: `make install` or `uv sync --all-groups`
- **Dependency Lock**: When Python versions or dependencies change, update `uv.lock` via `make lock`
- **Pre-commit Hooks**: Must run `make hook` after code changes to validate formatting and linting before committing

## Project Structure

- **`timezonefinder/`**: Core library
  - `timezonefinder.py`: Main `TimezoneFinder` class (full polygon search) and `TimezoneFinderL` (shortcut-only heuristic)
  - `global_functions.py`: Public API entry points (`timezone_at`, `timezone_at_land`, etc.)
  - `configs.py`: Centralized type definitions and runtime constants (coordinate scaling, FlatBuffers layout)
  - `utils.py`: Point-in-polygon, bbox, and polygon math utilities
  - `utils_numba.py`: Numba-accelerated polygon math (optional)
  - `utils_clang.py`: CFFI bindings to clang-compiled C extension
  - `coord_accessors.py`: Coordinate view utilities (memory-efficient slicing)
  - `polygon_array.py`: Polygon data structure and accessors
  - `zone_names.py`: Timezone ID to name mappings
  - `command_line.py`: CLI entry point for the `timezonefinder` command
  - `flatbuf/`: FlatBuffers schema definitions and I/O helpers

- **`timezonefinder/data/`**: Binary data assets (compiled at package build time)
  - NumPy arrays for zone names and metadata
  - FlatBuffers binary files for polygons and shortcut indexes
  - Zone name lookup tables

- **`scripts/`**: Data generation and testing utilities
  - `file_converter.py`: Ingests timezone-boundary-builder GeoJSON and emits FlatBuffers + NumPy assets
  - `update_data.sh`: Downloads timezone-boundary-builder release and runs the converter
  - `check_speed_*.py`: Performance benchmarks
  - `reporting.py`: Generates `docs/data_report.rst` from benchmarks

- **`tests/`**: pytest suite with unit, integration, and slow test markers
  - `auxiliaries.py`: Test fixtures (edge coordinates, hole test cases)

- **`docs/`**: Sphinx documentation (build with `make docs`)
  - `data_format.rst`: Authoritative reference for binary layouts and coordinate scaling

## Common Commands

| Task | Command |
|------|---------|
| Install dependencies | `make install` |
| Run unit tests | `make test` |
| Run integration tests | `make testint` |
| Run all tests | `make testall` |
| Single test | `uv run pytest tests/path/test_file.py::test_name` |
| Pattern matching | `uv run pytest -k "test_pattern"` |
| Performance benchmarks | `make speedtest` |
| Pre-commit validation | `make hook` |
| Full test matrix (tox) | `make tox` |
| Regenerate timezone data | `make data` (downloads full dataset) |
| Parse test data | `make testparse` |
| Build documentation | `make docs` |
| Compile FlatBuffers schemas | `make flatbuf` |
| Build release wheels | `make build` |
| Create git tag + push | `make release` |

## Runtime Lookup Flow

1. Query coordinates are converted to scaled int32 values (scaled by 10^7 internally)
2. H3 shortcut map yields candidate polygon IDs
3. Bounding box tests eliminate geometrically impossible candidates
4. Point-in-polygon checks holes first (faster rejection), then outer boundary
5. Ray-casting algorithm confirms inclusion
6. Ocean zones (`Etc/GMT+/-XX`) guarantee a match for any possible coordinate unless `timezone_at_land` is used

## Code Guidelines

### Type Hints & Architecture
- Add type hints to all new code; use `typing.Protocol`, `TypedDict`, `Literal` to encode constraints
- Define all types centrally in `timezonefinder/configs.py` to avoid duplication and circular imports
- Types should reflect runtime behavior—avoid `Any` unless truly justified
- Run `uv run mypy` locally to verify type compliance

### Performance & Correctness
- Preserve the fast lookup path; profile hot code (polygon math, shortcut lookups) when modifying
- Use vectorized NumPy operations where applicable
- Respect coordinate scaling constants (`COORD2INT_FACTOR`, `DECIMAL_PLACES_SHIFT`) and keep them in sync between runtime and data converter
- Keep H3 shortcut maps and bounding-box filters cache-friendly

### Public API & Backward Compatibility
- External API (public functions and classes) should not break between minor versions
- Internal code, data formats, and binary assets are versioned together with the package and do NOT need backward compatibility
- Maintain `__all__` definitions in `__init__.py` files—they define the public API surface

### Code Quality
- Write complete solutions without placeholder TODOs or commented-out experiments
- Prefer pure functions; clearly delimit side effects
- Use dependency injection instead of module-level state
- Treat concurrency as a first-class concern (global helper functions are NOT thread-safe; prefer explicit `TimezoneFinder(in_memory=True)` instances for concurrent workloads)

### Testing
- Add targeted unit tests for every behavioral change under `tests/`
- Use test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Fixtures (edge coordinates, hole cases) are in `tests/auxiliaries.py`
- Integration tests validate packaging/build processes
- For performance-sensitive changes, run `make speedtest` or individual benchmarks

## Important Runtime Details

- **Numba Optional**: When `numba` is installed, `utils.pt_in_poly_python` uses Numba JIT compilation for 10–50× speedup. If absent, the CFFI-backed clang C extension is used as a fallback.
- **TimezoneFinderL**: Heuristic-only implementation using shortcuts; prefer full `TimezoneFinder` when correctness matters.
- **Global State**: `global_functions.py` delays instantiation of the default finder to avoid side effects before first use.
- **Thread Safety**: Global helper functions like `timezone_at()` are NOT thread-safe. For concurrent workloads, create explicit `TimezoneFinder(in_memory=True)` instances per thread.
- **Dataset Variants**: The reduced "now" dataset (used via `update_data.sh --dataset=now`) loses historical names; the full dataset preserves all 440+ timezone identifiers.

## Data Pipeline & Versioning

- **Data Regeneration**: `update_data.sh` downloads a timezone-boundary-builder release, unpacks to `tmp/`, then runs `scripts/file_converter.py` to emit FlatBuffers and NumPy arrays
- **Coordinate Scaling**: The converter multiplies all coordinates by 10^7 to preserve 7 decimal places (∼1.1 cm precision) as int32 values
- **Schema Changes**: When modifying FlatBuffers schemas (e.g., `hybrid_shortcuts_uint16.fbs`), delete any previously generated `.fbs` binary artifacts so they regenerate consistently
- **Data Versioning**: Regenerating data typically warrants a minor version bump; update `CHANGELOG.rst` and tag releases via `make release`
- **Auto-generated Docs**: `scripts/reporting.py` updates `docs/data_report.rst` with benchmark results

## Release Process

1. Update `CHANGELOG.rst`
2. Ensure `make hook` passes (formatting, linting, type checking)
3. Ensure `make testall` passes (full test suite)
4. From `master` branch only, run `make release` to tag and push the version

## Pre-commit Hooks

The repository uses pre-commit for automated checks. Always run `make hook` after making code changes. Checks include:

- **Formatting**: ruff format, blacken-docs
- **Linting**: ruff check, mypy (type checking)
- **File integrity**: mixed line endings, trailing whitespace, YAML/JSON validation
- **Custom checks**: FlatBuffers file detection, unused Numba warnings

Failures must be fixed before committing or submitting PRs.

## Cursor Rules Integration

This CLAUDE.md incorporates key guidance from `.cursorrules`. The Cursor rules file contains additional detail on specific patterns (e.g., data pipeline configs, FlatBuffers compilation) and should be consulted for nuanced design decisions.
