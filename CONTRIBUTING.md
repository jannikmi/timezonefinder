# Contribution Guidelines

These guidelines describe how maintainers, contributors, and coding agents collaborate on timezonefinder. They extend the repository tour in `CLAUDE.md` and focus on delivering production-ready features with strong guarantees around correctness, performance, and maintainability.

## Mission & Expectations

- timezonefinder provides accurate offline timezone lookups across platforms. Every change should preserve numerical correctness at timezone borders and remain friendly to constrained runtimes.
- Assume your work will ship immediately. Submit only production-ready code: defensive error handling, predictable behaviour across Python versions we support, and clear fallbacks when optional accelerators (Numba, clang-based polygon checks) are missing.
- Be explicit about trade-offs. Document assumptions in code comments or pull request notes when optimisations or heuristics change behaviour.

## Development Workflow

1. Fork the repository and create a feature branch: `git checkout -b my-topic`.
2. Install tooling with `uv sync --all-groups` (or `pip install timezonefinder[numba]` for runtime validation only).
3. Activate the environment via `uv run` and work from the project root. Run targeted commands through `make` or `uv run …` to ensure reproducibility.
4. Formatting and linting are enforced via pre-commit hooks (install with `make hook`) and can be run manually with `ruff`, `isort`, and `mypy`.
5. Keep pull requests focused. Reference issue numbers and describe user-facing impact, dataset changes, and risk areas up front.
6. Before opening a PR, run the test matrix that matches the scope of your change and ensure CI will pass. Heavy packaging checks live under the `integration` marker—run them if you touched build config or bundled data. Expensive validation tests (like geometry or shortcut consistency checks) live under the `slow` marker—run them if you touched core logic.

## Coding Standards (also for Agents)

### Production-Ready Implementation

- Write complete solutions—no placeholders, commented-out experiments, or TODOs without filed issues.
- Prefer pure functions or clearly delimited side effects. Use dependency injection instead of module-level state when possible.
- Treat concurrency as a first-class concern. Avoid introducing shared global state; guard mutable caches and document thread expectations.

### Pythonic, Functional Design

- Strive for expressive, readable code that leverages Python's standard library and idioms (`with` statements, comprehensions, `enum.Enum`, context managers).
- Bias towards small, composable functions with explicit inputs/outputs. When mutability is required, minimise scope and communicate intent.
- Maintain backwards-compatible APIs. Deprecations require documentation updates and tests that cover both old and new paths.

### Strong Typing & Contracts

- Add or refine type hints for new code. Use `typing.Protocol`, `TypedDict`, and `Literal` to capture constraints.
- Keep annotations consistent with runtime behaviour—no `Any` unless justified. Ensure `mypy` (configured in `pyproject.toml`) passes locally.
- Validate external inputs early and raise precise exceptions. Update `docs/data_format.rst` if binary schemas change.
- all types should be defined centrally in `timezonefinder/configs.py` to avoid duplication and circular imports
- the same applies to path/filename constants anywhere in the repo, not just `timezonefinder/`: define a directory or filename once, in the module that owns the resource, and import it elsewhere instead of retyping the literal (see `tests/auxiliaries.py`'s `BENCHMARK_FIXTURES_DIR` and fixture-name constants, reused by `scripts/generate_benchmark_fixtures.py` and `benchmarks/conftest.py`)

### Performance & Memory Discipline

- Preserve the fast path. Profile hot code with the `benchmarks/` pytest-benchmark suites (`make speedtest` for a quick core-subset check, `make benchmarks` for the full suite) when touching polygon math or shortcut lookups.
- Use vectorised/NumPy-aware operations and avoid quadratic fallbacks on large datasets. When performance optimisations add complexity, include comments that summarise the micro-optimisation.
- Respect coordinate scaling constants and FlatBuffers layouts; keep performance-sensitive structures (H3 mappings, bbox filters) cache-friendly. When changing the datatype of shortcut-related FlatBuffers schemas (for example `hybrid_shortcuts_uint16.fbs`), delete any previously generated `.fbs` binary artifacts so they are regenerated consistently.

### Benchmarking (`benchmarks/`, pytest-benchmark)

- `benchmarks/test_timezone_finding.py`, `test_inside_polygon.py`, and `test_initialization.py` are pytest-benchmark suites, not regular tests: they're excluded from `make test`/`make testall` via `testpaths` and only collected when `benchmarks/` is passed explicitly (`make speedtest`, `make benchmarks`, `tox -e benchmarks`).
- Each benchmark times one pass over a fixed, committed batch of points/inputs (see `tests/fixtures/benchmarks/`) rather than a single call, so every round performs identical work. Never change the batch size (`benchmarks/conftest.py`'s `BATCH_SIZE`) without accepting that it invalidates historical trend data.
- **Never run the benchmark suite together with `pytest-run-parallel`'s `--parallel-threads`.** Concurrent test execution makes wall-clock timings meaningless, and the two are a known incompatibility. None of the `benchmarks`/`speedtest`/`reports`/`tox -e benchmarks` entry points pass `--parallel-threads`; don't add it to a benchmark invocation.
- Benchmark node ids are the join key for the historical trend chart. Never rely on pytest's autogenerated `parametrize` ids for a benchmark - always pass explicit `ids=`/`pytest.param(..., id=...)`. `tests/test_benchmark_names.py` pins the exact expected set; update it deliberately (and know you're resetting that metric's history) if you rename or add a benchmark.
- Measurement and rendering are decoupled: `make benchmarks` (or `tox -e benchmarks`) produces `tmp/benchmark.json`; `uv run python -m scripts.render_benchmark_reports --benchmark-json=tmp/benchmark.json` (wrapped by `make reports`) turns it into `docs/benchmark_results_*.rst`. Regenerating the docs never needs to re-run the suite.
- After a change that could plausibly shift performance, report the coefficient of variation (stddev/mean) of the tracked core benchmark (`-m benchmark_core`) across a handful of local runs in the PR description alongside the before/after numbers - single-run numbers on a shared or noisy machine can't distinguish a real regression from scheduler noise.

### Backward Compability & Stability

- External: Avoid breaking changes to public APIs unless absolutely necessary. If a change is required, provide a clear migration path and update all relevant documentation. A major version bump is warranted for breaking changes.
- Internal: When modifying internal assets like code, data formats or binary assets the changes must NOT be backward compatible. The code is packaged and versioned together and must only work with the exact version of the data files it was built with.

### Testing & Coverage

- **Global test runs**: Use make commands (`make test`, `make testint`, `make testall`) for running full test suites
- **Isolated unit tests**: When only specific tests are affected, run them directly via `uv run pytest tests/path/to/test_file.py::test_name` or `uv run pytest -k "test_pattern"`
- Add targeted unit tests under `tests/` for every behavioural change. Use fixtures in `tests/auxiliaries.py` to cover edge coordinates and polygon holes.
- Run `make test` for fast feedback (excludes integration and slow tests).
- Run integration tests via `make testint` when packaging, build metadata, or binary assets change
- Run all tests including slow test cases via `make testall` when verifying dataset integrity or core algorithmic changes (shortcuts, geometry).
- Maintain deterministic tests—mock filesystem/network access, and avoid relying on system timezone settings. If you alter CLI behaviour, update `tests/test_integration.py` accordingly.

### Documentation & Communication

- Update `README.rst`, `docs/`, and changelog entries (`CHANGELOG.rst`) when behaviour, flags, or datasets change. This includes internal/dev-tooling changes with no public API impact (new scripts, test infrastructure, CI, refactors)—add those under the `Internal:` sub-list of the unreleased entry rather than skipping the changelog because nothing user-facing changed.
- For data regeneration, document the timezone boundary release used, and note version bumps initiated with `uv version`. `update_data.sh` also regenerates the committed benchmark fixtures (`tests/fixtures/benchmarks/`) since they're pinned to `DATA_VERSION`, then automatically runs `make reports` to refresh `docs/data_report.rst` and `docs/benchmark_results_*.rst` against the new binary data (both would otherwise silently go stale) - if you bump `DATA_VERSION` any other way (not via `update_data.sh`), run `make benchmark-fixtures` and `make reports` yourself, in that order, or the benchmark fixture tests will fail with `BenchmarkFixtureError` and the reports will describe the old data. A standalone `make parse`/`make testparse` (bypassing `update_data.sh`) does not touch `DATA_VERSION`, the fixtures, or the reports at all.
- Keep comments succinct but informative, especially around geometry calculations, numerical tolerances, and shortcut heuristics.

## Tooling & Quality Gates

- Format and lint with `make hook` or the individual tools wired in `pyproject.toml` (Ruff, isort, mypy). Ensure pre-commit hooks pass before pushing.
- Honour `.editorconfig` and keep files ASCII unless a different encoding already exists.
- Use `rg`/`uv`-provided helpers for repository introspection; avoid introducing tool-specific dependencies without discussion.

## Pull Request Checklist

- [ ] Branch is rebased on the latest `main` and commit history is clean.
- [ ] Code follows the standards above, with type hints, performance considerations, and Pythonic structure.
- [ ] Tests are updated/added and pass (`pytest`, and `integration`/`tox` where relevant).
- [ ] Documentation and changelog entries reflect the change.
- [ ] Binary data or configuration changes are justified and the regeneration process is documented in the PR description.

Thank you for helping to keep timezonefinder robust and high-performance!
