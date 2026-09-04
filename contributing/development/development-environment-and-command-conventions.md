# Development environment and command conventions

- Use `uv` for all dependency management; run every Python command via `uv run`
- `uv run` syncs *inexactly*: it refreshes the default dependency groups and neither removes nor updates anything outside them, so the optional groups keep whatever version `uv sync --all-groups` last installed. A lockfile bump that moves a shared dependency past a stale optional package's ceiling therefore breaks that package's import while `find_spec` still finds it — for `numba` (whose import failure `utils_numba.py` swallows by design) the only symptom is `tests/main_test.py::*::test_using_numba` failing, which reads as a code regression. Recovery is `make install`. No `uv run` form prunes; only an exact `uv sync` does, which is why both of the `Makefile`'s syncs pass `--all-groups` (the benchmark workflow's deliberate `uv sync --group test` is the one place a pruned, numba-free environment is the point)
- Run `make hook` after code changes; failures must be fixed before committing. Also run it after regenerating anything, *before* reading the diff — see *Generated Files*
- The `Makefile` header comment documents every target. Where the *choice* between targets is the non-obvious part, it is covered by the [testing strategy](testing-strategy-and-change-scope.md)
- Don't prefix suggested commands with a redundant `cd` into the project root

## Development Workflow

1. Fork the repository and create a feature branch: `git checkout -b my-topic`.
2. Install tooling with `uv sync --all-groups` (or `pip install timezonefinder[numba]` for runtime validation only), then run `make bootstrap` to obtain the packaged boundary data. A clone does not carry it — the ~62 MB dataset is git-ignored — so this is a required step, not a convenience: it fetches the `timezonefinder-data` release this checkout declares, verified against the digest PyPI publishes for it, and does nothing on a second run. Run it again after switching to a commit that declares a different data version: `make test`, `make testall`, `make testint` and `make reports` refuse to start against a missing *or stale* dataset rather than failing inside a reader, and the stale case is the one no amount of "the files are there" can see.
3. Activate the environment via `uv run` and work from the project root. Run targeted commands through `make` or `uv run …` to ensure reproducibility.
4. Formatting and linting are enforced via pre-commit hooks (install with `make hook`) and can be run manually with `ruff`, `isort`, and `mypy`.
5. Keep pull requests focused. Reference issue numbers and describe user-facing impact, dataset changes, and risk areas up front.
6. Before opening a PR, run the test matrix that matches the scope of your change and ensure CI will pass. Heavy packaging checks live under the `integration` marker—run them if you touched build config or bundled data. Expensive validation tests (like geometry or shortcut consistency checks) live under the `slow` marker—run them if you touched core logic.

## Tooling & Quality Gates

- Format and lint with `make hook` or the individual tools wired in `pyproject.toml` (Ruff, isort, mypy). Ensure pre-commit hooks pass before pushing.
- Honour `.editorconfig` and keep files ASCII unless a different encoding already exists.
- Use `rg`/`uv`-provided helpers for repository introspection; avoid introducing tool-specific dependencies without discussion.
