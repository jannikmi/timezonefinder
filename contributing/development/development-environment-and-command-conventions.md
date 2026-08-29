# Development environment and command conventions

- Use `uv` for all dependency management; run every Python command via `uv run`
- Run `make hook` after code changes; failures must be fixed before committing. Also run it after
  regenerating anything, *before* reading the diff — see *Generated Files*
- The `Makefile` header comment documents every target. Where the *choice* between targets is the
  non-obvious part, it is covered by the
  [testing strategy](testing-strategy-and-change-scope.md)
- Don't prefix suggested commands with a redundant `cd` into the project root

## Development Workflow

1. Fork the repository and create a feature branch: `git checkout -b my-topic`.
2. Install tooling with `uv sync --all-groups` (or `pip install timezonefinder[numba]` for runtime validation only).
3. Activate the environment via `uv run` and work from the project root. Run targeted commands through `make` or `uv run …` to ensure reproducibility.
4. Formatting and linting are enforced via pre-commit hooks (install with `make hook`) and can be run manually with `ruff`, `isort`, and `mypy`.
5. Keep pull requests focused. Reference issue numbers and describe user-facing impact, dataset changes, and risk areas up front.
6. Before opening a PR, run the test matrix that matches the scope of your change and ensure CI will pass. Heavy packaging checks live under the `integration` marker—run them if you touched build config or bundled data. Expensive validation tests (like geometry or shortcut consistency checks) live under the `slow` marker—run them if you touched core logic.

## Tooling & Quality Gates

- Format and lint with `make hook` or the individual tools wired in `pyproject.toml` (Ruff, isort, mypy). Ensure pre-commit hooks pass before pushing.
- Honour `.editorconfig` and keep files ASCII unless a different encoding already exists.
- Use `rg`/`uv`-provided helpers for repository introspection; avoid introducing tool-specific dependencies without discussion.
