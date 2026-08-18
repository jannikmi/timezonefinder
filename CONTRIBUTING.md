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
- Memory is measured too, by `make memory` - see *Benchmarking* below. If a change makes the library hold data it previously mapped or streamed, that shows up there and nowhere else.
- Validate generated artifacts where they are generated, not where they are read. The correctness of a compiled data directory is established once, by the build; re-checking it when a `TimezoneFinder` is constructed spends every user's startup time re-answering a question that already has an answer, and multiplies across the per-thread instances concurrent workloads are told to use. The check belongs in two places instead - the converter, over the files it just wrote, and the test suite, over the files the repository ships - sharing one implementation (`scripts/data_integrity.py`) so that the two cannot drift into asserting different things. The payoff is not only speed: a check that no longer has to fit in an initialisation budget can afford to be exhaustive, which is why the hole-reference check resolves every ring in the dataset and compares it against an independently derived bounding box.
- Use vectorised/NumPy-aware operations and avoid quadratic fallbacks on large datasets. When performance optimisations add complexity, include comments that summarise the micro-optimisation.
- Respect coordinate scaling constants and FlatBuffers layouts; keep performance-sensitive structures (H3 mappings, bbox filters) cache-friendly. When changing the datatype of shortcut-related FlatBuffers schemas (for example `hybrid_shortcuts_uint16.fbs`), delete any previously generated `.bin` binary artifacts so they are regenerated consistently.

### Benchmarking (`benchmarks/`, pytest-benchmark)

**The reasoning behind these measurements - why the CI numbers are noisy, why a pull request is compared against its own merge base, where every threshold comes from - is documented once, in [Benchmarking Methodology](https://timezonefinder.readthedocs.io/en/latest/benchmarking_methodology.html). Read it before interpreting any number below.** What follows is operational only.

**Running benchmarks locally**

| Command | What it does |
|---|---|
| `make speedtest` | quick sanity check: the tracked core subset only, no JSON output |
| `make benchmarks` | the full suite, writing `tmp/benchmark.json` (the input for the docs) |
| `make benchmarks-ci` | the *exact* measurement CI records: core subset, `--benchmark-min-rounds=50`, tracked estimator applied |
| `make benchmark-noise` | repeats `benchmarks-ci` five times on unchanged code and prints the observed spread plus a threshold derived from it |
| `make memory` | the memory counterpart of `make benchmarks`, writing `tmp/memory.json` |
| `make memory-ci` / `make memory-noise` | the CI memory measurement, and its run-to-run spread |

- `benchmarks/test_timezone_finding.py`, `test_inside_polygon.py`, and `test_initialization.py` are pytest-benchmark suites, not regular tests: they're excluded from `make test`/`make testall` via `testpaths` and only collected when `benchmarks/` is passed explicitly (`make speedtest`, `make benchmarks`, `tox -e benchmarks`).
- **Never run the benchmark suite together with `pytest-run-parallel`'s `--parallel-threads`.** Concurrent test execution makes wall-clock timings meaningless, and the two are a known incompatibility. None of the `benchmarks`/`speedtest`/`reports`/`tox -e benchmarks` entry points pass `--parallel-threads`; don't add it to a benchmark invocation.
- **Never paste a local number into a discussion about a CI alert** as if the two were the same measurement - CI runs a deliberately different acceleration path on different hardware. Compare local-to-local and CI-to-CI only.
- Always pass explicit `ids=`/`pytest.param(..., id=...)` for a benchmark; never rely on pytest's autogenerated `parametrize` ids. `tests/test_benchmark_names.py` and `tests/test_memory_metric_names.py` pin the expected sets - updating one is deliberately visible, because it resets that metric's chart history.
- Changing `BATCH_SIZE` (`benchmarks/conftest.py`), the sampler, the `N_*` counts, or the order the generators consume the shared `rng` invalidates every committed fixture: bump `FIXTURE_VERSION` in `tests/auxiliaries.py`, which the loader enforces along with the `point_sampler` recorded in `metadata.json`. `BATCH_SIZE` is also bounded by the fixture sizes - `_load_batch` needs `BATCH_SIZE` points per fixture (ceiling 5,000) and `pip_inputs_by_stratum` needs `BATCH_SIZE` *per stratum* (ceiling 3,333, the binding one); raising past either means bumping the matching `N_*` in `scripts/generate_benchmark_fixtures.py` and regenerating.
- Measurement and rendering are decoupled: `make benchmarks` produces `tmp/benchmark.json` and `make memory` produces `tmp/memory.json`; `uv run python -m scripts.render_benchmark_reports --benchmark-json=tmp/benchmark.json --memory-json=tmp/memory.json` turns them into `docs/benchmark_results_*.rst`. Regenerating the docs never needs to re-measure - but `make reports` *does*, since it has both `benchmarks` and `memory` as prerequisites, so it replaces every committed figure. Use it after a data update (which is what `update_data.sh` does); when changing only how the reports are rendered, call the renderer directly against a stored JSON, or the layout change arrives buried in unrelated number churn.
- `tests/test_memory_footprint.py` runs in `make test` and enforces deliberately loose ceilings plus the ratio between the mapped and in-memory modes. It is there to catch a mode losing its order of magnitude, not to track drift - if a dataset update pushes a value over its ceiling, confirm the growth is proportional and raise the constant.
- After a change that could plausibly shift performance, report the coefficient of variation (stddev/mean) of the tracked core benchmark (`-m benchmark_core`) across a handful of local runs in the PR description alongside the before/after numbers - single-run numbers on a shared or noisy machine can't distinguish a real regression from scheduler noise. `make benchmark-noise` does exactly this for you.

### Reading the benchmark CI report (`.github/workflows/benchmark.yml`)

- On a **pull request**, the comparison table is written to the `measure` job's own summary immediately, and posted by the separate `benchmark-comment` workflow as a comment on the PR conversation, edited in place on each push rather than appended. It lists, per benchmark, the base and head value of the tracked estimator, the signed change (negative is faster) and the `base / head` factor.
- On a push to `master` the result is appended to the [trend chart](https://jannikmi.github.io/timezonefinder/dev/bench/), published on the `gh-pages` branch under `dev/bench` (`benchmark-data-dir-path`). The GitHub Pages root itself is only a redirect to that path - the action owns everything below it, so don't hand-edit `dev/bench`.
- `REPORT_FILENAME` and the artifact names are duplicated across `benchmark.yml` and `benchmark-comment.yml` because workflows cannot import constants; `tests/test_benchmark_workflows.py` fails if the copies drift.

**Judging a pull request's numbers**

1. Check the warning block first. A different CPU between the two sides, or a changed batch size / fixture set, makes the ratios meaningless - re-run the workflow, or accept that this PR's numbers cannot be compared.
2. A few percent either way is still noise. Rows are flagged at `REGRESSION_THRESHOLD_PCT` (110%) in `scripts/compare_benchmark_runs.py`, and the comparison is reporting only - `--fail-on-regression` exists but is not passed.
3. To reproduce locally, run `make benchmarks-ci` on your branch and on the merge base, then compare the two reports directly:

   ```
   uv run python -m scripts.compare_benchmark_runs --base base.json --head head.json
   ```

   Local-to-local only, as above.

**When a trend chart alert fires**

1. **Check which CPU each run drew** before anything else - the job summary of both runs says so, as does the chart tooltip. A step change that coincides with a change of CPU model is not a code change.
2. **Re-run the workflow.** GitHub-hosted runners are shared and virtualised; run-to-run variation on identical code is the normal explanation for a modest alert. An alert that does not reproduce across re-runs is noise.
3. Alerts are non-blocking (`fail-on-alert: false`) and stay that way.
4. Re-derive `ALERT_THRESHOLD` whenever the runner pool or the core set changes: trigger the `benchmark` workflow via `workflow_dispatch` with `repetitions: 5` (or more), read the derived threshold off the "report noise floor" job summary, and set it in `benchmark.yml`.

### Backward Compability & Stability

- External: Avoid breaking changes to public APIs unless absolutely necessary. If a change is required, provide a clear migration path and update all relevant documentation. A major version bump is warranted for breaking changes.
- Internal: When modifying internal assets like code, data formats or binary assets the changes must NOT be backward compatible. The code is packaged and versioned together and must only work with the exact version of the data files it was built with.
- Before writing compatibility code anyway, check that the thing you would be compatible with was ever released — `git merge-base --is-ancestor <commit> <latest tag>`. This is the step that is easy to skip: on `master`, a format marker or interface introduced since the last tag looks exactly like one that has shipped, so a fallback written for "data compiled by an older release" can read as necessary while no such data exists. The cost is not only an unreachable branch. Guarding an unreleased format version rewrote a 63 MB binary for one changed byte, and the branch itself sat on the lookup path, tested per query for a case that could not arise.

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
- For data regeneration, document the timezone boundary release used. Since #446 a data update releases the separate `timezonefinder-data` distribution: `update_data.sh` sets *its* version from the parsed release tag and records the release in `packages/timezonefinder-data/README.md`, leaving `timezonefinder`'s version and `CHANGELOG.rst` untouched. `update_data.sh` also regenerates the committed benchmark fixtures (`tests/fixtures/benchmarks/`) since they're pinned to `DATA_VERSION`, then automatically runs `make reports` to refresh `docs/data_report.rst` and `docs/benchmark_results_*.rst` against the new binary data (both would otherwise silently go stale) - if you bump `DATA_VERSION` any other way (not via `update_data.sh`), run `make benchmark-fixtures` and `make reports` yourself, in that order, or the benchmark fixture tests will fail with `BenchmarkFixtureError` and the reports will describe the old data. More generally: **regenerating the fixtures for any reason makes `docs/benchmark_results_*.rst` stale**, since those numbers are measured over the fixtures - always follow `make benchmark-fixtures` with `make reports`, whether or not `DATA_VERSION` moved. A standalone `make parse`/`make testparse` (bypassing `update_data.sh`) does not touch `DATA_VERSION`, the fixtures, or the reports at all.
- Keep comments succinct but informative, especially around geometry calculations, numerical tolerances, and shortcut heuristics.
- **Some hand-written pages describe things whose source of truth is a file elsewhere.** Nothing fails when the two diverge, so the update has to be part of the change that caused it. If you touch the left column, re-read the right:

  | Changed | Re-read |
  |---|---|
  | the lookup flow (H3 resolution, hole/outer-ring order, the unique-cell short-circuit) | *How it works* in `README.rst` **and** `docs/index.rst`, plus `docs/architecture.rst` |
  | `[project] dependencies` in `pyproject.toml` (added/removed, not a version bump) | *Dependencies* in `docs/0_getting_started.rst` |
  | `.github/workflows/build.yml`, `[tool.cibuildwheel.*]`, `setup.py` | *How it ships* in `docs/architecture.rst` |
  | `tox.ini` envlist, or the property-based tests | *Tests that protect guarantees* in `docs/architecture.rst` |
  | a heading in any `docs/` page | `README.rst` links into it by anchor — grep for `<page>.html#` |
  | a script under `prototypes/` | the table in `prototypes/README.md` |
  | the packaged dataset | the `# 'Europe/Berlin'`-style result comments in `README.rst` and `docs/` — re-run the lookups rather than trusting them |

  `CLAUDE.md` (*Documentation Files*) states what each of these breaks and why the duplication is deliberate.

## Tooling & Quality Gates

- Format and lint with `make hook` or the individual tools wired in `pyproject.toml` (Ruff, isort, mypy). Ensure pre-commit hooks pass before pushing.
- Honour `.editorconfig` and keep files ASCII unless a different encoding already exists.
- Use `rg`/`uv`-provided helpers for repository introspection; avoid introducing tool-specific dependencies without discussion.

## Pull Request Checklist

- [ ] Branch is rebased on the latest `master` and commit history is clean.
- [ ] Code follows the standards above, with type hints, performance considerations, and Pythonic structure.
- [ ] Tests are updated/added and pass (`pytest`, and `integration`/`tox` where relevant).
- [ ] Documentation and changelog entries reflect the change, including the pages that paraphrase a file you touched (see the table under *Documentation & Communication*).
- [ ] Binary data or configuration changes are justified and the regeneration process is documented in the PR description.

Thank you for helping to keep timezonefinder robust and high-performance!
