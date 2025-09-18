# Contribution Guidelines

These guidelines describe how maintainers, contributors, and coding agents collaborate on timezonefinder. They extend the repository tour in `Agents.md` and focus on delivering production-ready features with strong guarantees around correctness, performance, and maintainability.

## Mission & Expectations

- timezonefinder provides accurate offline timezone lookups across platforms. Every change should preserve numerical correctness at timezone borders and remain friendly to constrained runtimes.
- Assume your work will ship immediately. Submit only production-ready code: defensive error handling, predictable behaviour across Python versions we support, and clear fallbacks when optional accelerators (Numba, clang-based polygon checks) are missing.
- Be explicit about trade-offs. Document assumptions in code comments or pull request notes when optimisations or heuristics change behaviour.

## Development Workflow

1. Fork the repository and create a feature branch: `git checkout -b my-topic`.
2. Install tooling with `uv sync --all-groups` (or `pip install timezonefinder[numba]` for runtime validation only).
3. Activate the environment via `uv run` and work from the project root. Run targeted commands through `make` or `uv run …` to ensure reproducibility.
4. Keep pull requests focused. Reference issue numbers and describe user-facing impact, dataset changes, and risk areas up front.
5. Before opening a PR, run the test matrix that matches the scope of your change and ensure CI will pass. Heavy packaging checks live under the `integration` marker—run them if you touched build config or bundled data.

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

### Performance & Memory Discipline

- Preserve the fast path. Profile hot code (`scripts/check_speed_*.py`, `make speedtest`) when touching polygon math or shortcut lookups.
- Use vectorised/NumPy-aware operations and avoid quadratic fallbacks on large datasets. When performance optimisations add complexity, include comments that summarise the micro-optimisation.
- Respect coordinate scaling constants and FlatBuffers layouts; keep performance-sensitive structures (H3 mappings, bbox filters) cache-friendly.

### Backward Compability & Stability

- External: Avoid breaking changes to public APIs unless absolutely necessary. If a change is required, provide a clear migration path and update all relevant documentation. A major version bump is warranted for breaking changes.
- Internal: When modifying internal assets like code, data formats or binary assets the changes must NOT be backward compatible. The code is packaged and versioned together and must only work with the exact version of the data files it was built with.

### Testing & Coverage

- Add targeted unit tests under `tests/` for every behavioural change. Use fixtures in `tests/auxiliaries.py` to cover edge coordinates and polygon holes.
- Run `uv run pytest -m "not integration"` for fast feedback. Execute `uv run pytest -m "integration"` or `uv run tox` when packaging, build metadata, or binary assets change.
- Maintain deterministic tests—mock filesystem/network access, and avoid relying on system timezone settings. If you alter CLI behaviour, update `tests/test_integration.py` accordingly.

### Documentation & Communication

- Update `README.rst`, `docs/`, and changelog entries (`CHANGELOG.rst`) when behaviour, flags, or datasets change.
- For data regeneration, document the timezone boundary release used, update reports via `scripts/reporting.py`, and note version bumps initiated with `uv version`.
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
