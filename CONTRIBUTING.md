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
- Each benchmark times one pass over a fixed, committed batch of points/inputs (see `tests/fixtures/benchmarks/`) rather than a single call, so every round performs identical work. Never change the batch size (`benchmarks/conftest.py`'s `BATCH_SIZE`) without accepting that it invalidates historical trend data. It is also bounded by the fixture sizes: `_load_batch` needs `BATCH_SIZE` points per fixture (ceiling 5,000) and `pip_inputs_by_stratum` needs `BATCH_SIZE` *per stratum* (ceiling 3,333, the binding one) - raising past either means bumping the matching `N_*` in `scripts/generate_benchmark_fixtures.py` and regenerating.
- Benchmark query points are drawn by `get_rnd_query_pt_area_weighted` (uniform per unit of **surface area**), not the `get_rnd_query_pt` the rest of the test suite uses (uniform in latitude, which oversamples the poles ~2.5x). Correctness and fuzz tests *want* the polar bias - more edge cases per draw; benchmarks must instead represent real query load. Changing the sampler, the `N_*` counts, or the order the generators consume the shared `rng` invalidates every committed fixture: bump `FIXTURE_VERSION` in `tests/auxiliaries.py`, which the loader enforces along with the `point_sampler` recorded in `metadata.json`.
- **Never run the benchmark suite together with `pytest-run-parallel`'s `--parallel-threads`.** Concurrent test execution makes wall-clock timings meaningless, and the two are a known incompatibility. None of the `benchmarks`/`speedtest`/`reports`/`tox -e benchmarks` entry points pass `--parallel-threads`; don't add it to a benchmark invocation.
- Benchmark node ids are the join key for the historical trend chart. Never rely on pytest's autogenerated `parametrize` ids for a benchmark - always pass explicit `ids=`/`pytest.param(..., id=...)`. `tests/test_benchmark_names.py` pins the exact expected set; update it deliberately (and know you're resetting that metric's history) if you rename or add a benchmark.
- Measurement and rendering are decoupled: `make benchmarks` (or `tox -e benchmarks`) produces `tmp/benchmark.json`; `uv run python -m scripts.render_benchmark_reports --benchmark-json=tmp/benchmark.json` (wrapped by `make reports`) turns it into `docs/benchmark_results_*.rst`. Regenerating the docs never needs to re-run the suite.
- After a change that could plausibly shift performance, report the coefficient of variation (stddev/mean) of the tracked core benchmark (`-m benchmark_core`) across a handful of local runs in the PR description alongside the before/after numbers - single-run numbers on a shared or noisy machine can't distinguish a real regression from scheduler noise. `make benchmark-noise` does exactly this for you (see below).

### Benchmarking on CI (`.github/workflows/benchmark.yml`)

**Running benchmarks locally**

| Command | What it does |
|---|---|
| `make speedtest` | quick sanity check: the tracked core subset only, no JSON output |
| `make benchmarks` | the full suite, writing `tmp/benchmark.json` (the input for the docs) |
| `make benchmarks-ci` | the *exact* measurement CI records: core subset, `--benchmark-min-rounds=50`, tracked estimator applied |
| `make benchmark-noise` | repeats `benchmarks-ci` five times on unchanged code and prints the observed spread plus a threshold derived from it |

**Local numbers are not comparable to CI numbers.** Different CPU, different
memory bandwidth, different background load, and - most importantly - CI
deliberately runs *without* Numba (see below). Never paste a local number into a
discussion about a CI alert as if the two were the same measurement. Compare
local-to-local and CI-to-CI only.

**What CI measures**

- Only the **core** subset (`-m benchmark_core`): three benchmarks, all
  `in_memory`. `test_timezone_at[random-in_memory]` is the headline - uniformly
  random points are the only globally representative workload, containing
  unique- and ambiguous-shortcut queries in their real ratio (~25.5%
  ambiguous), so a change is weighted by how much real query load it helps.
  `unique_shortcut-in_memory` and `ambiguous_shortcut-in_memory` are tracked
  alongside it as diagnostics: on the tracked clang configuration an ambiguous
  lookup costs ~14x a unique one (~7x with Numba), so ambiguous work takes
  ~83% of the wall clock despite being ~25% of the queries - meaning a
  unique-path win moves the headline by only ~0.17x its true size. The
  per-class benchmarks show it undiluted and attribute a change to a path.
  The full suite is for the docs, on demand - it is not run per PR.
- Only the **no-Numba / clang C extension** configuration, because that is what
  a plain `pip install timezonefinder` gives you and what the constrained
  containers named in `CLAUDE.md` actually run. `timezonefinder/utils.py` picks
  the point-in-polygon implementation *at import time*, so Numba and clang are
  completely different code paths whose numbers must never share a benchmark
  name. The workflow asserts the active path
  (`scripts/assert_acceleration_path.py`) rather than assuming it - a Numba
  install sneaking in would otherwise silently corrupt the whole trend history.
- The tracked value is the **min**, not the mean.
  `benchmark-action/github-action-benchmark`'s pytest extractor reads only
  `stats.ops` (`= 1 / stats.mean`), so `scripts/normalize_benchmark_json.py`
  rewrites `ops`/`mean` from the min before handing the report over. Since every
  round performs an identical fixed batch of work, the fastest round is the one
  least perturbed by whatever else the shared runner happened to be doing.

**`ubuntu-latest` does not pin the CPU**

This is the single most important thing to know about these numbers.
`runs-on: ubuntu-latest` guarantees a runner *image*, not hardware. This
project's runs have landed on AMD EPYC 9V74, AMD EPYC 7763 and Intel Xeon
Platinum 8573C parts between 2.30 and 3.69 GHz, and the clock varies run to run
even within one model. Measured across eleven recorded runs whose lookup path
was **unchanged**, the tracked `min` spread 134-158% - larger than most changes
worth reviewing.

Two consequences, which shape everything below:

- Comparing two *different* CI runs tells you as much about which machine each
  drew as about the code. A merged change that was a genuine 1.5x improvement
  once appeared on the chart as a 21% regression for exactly this reason.
- Therefore a pull request is measured **against its own merge base, in the
  same job, on the same runner**, and the cross-machine trend chart is treated
  as the weak signal it is.

Every run says which machine it drew: the `measure` job prints the CPU, the
acceleration path and the workload provenance to its job summary
(`scripts/describe_benchmark_machine.py`), and
`scripts/normalize_benchmark_json.py` stamps the same label into the one field
that reaches the trend chart, so hovering a data point shows the CPU behind it
long after the artifact has expired.

**Reading the benchmark CI report**

- On a **pull request** the measuring job checks out the PR's merge base
  alongside the head, installs and measures both, and uploads two artifacts. It
  holds no write permissions and no secrets, so it behaves identically for
  branch PRs and fork PRs and a fork PR never fails for want of a token. The
  base is measured twice, once before and once after the head, so a runner that
  drifts over the job's lifetime shows up in the base's own spread instead of
  looking like a code change; the two passes are reduced by `min`. This roughly
  doubles the job (~2-3 min), almost all of it the second checkout, `uv sync`
  and C extension build - the measurement itself is seconds.
- The comparison table is written to the `measure` job's own summary
  immediately, and posted by the separate `benchmark-comment` workflow
  (triggered by `workflow_run`, running the base repository's own definition)
  as a **comment on the PR's head commit**, which appears in the PR
  conversation timeline.
- The table lists, per benchmark, the base and head duration of the tracked
  estimator, the signed change (negative is faster) and the `base / head`
  factor. `scripts/compare_benchmark_runs.py` renders it, and it *verifies*
  rather than assumes that both sides ran on one machine - if they did not, or
  if the batch size, fixtures, boundary data or acceleration path differ
  between the two sides, the table carries a warning saying so.
- On a push to `master` the result is appended to the [trend
  chart](https://jannikmi.github.io/timezonefinder/dev/bench/), published on the
  `gh-pages` branch under `dev/bench` (`benchmark-data-dir-path`). The GitHub
  Pages root itself is only a redirect to that path - the action owns everything
  below it, so don't hand-edit `dev/bench`.
- The trend chart is **not** used to judge a pull request. It is cross-machine
  by construction, and `benchmark-comment.yml` deliberately does not compare
  against it (`tests/test_benchmark_workflows.py` enforces that).

**Judging a pull request's numbers**

1. Check the warning block first. A different CPU between the two sides, or a
   changed batch size / fixture set, makes the ratios meaningless - re-run the
   workflow, or accept that this PR's numbers cannot be compared.
2. Same-runner measurement removes the machine-to-machine term but not the
   runner's own jitter, so a few percent either way is still noise. Rows are
   flagged at `REGRESSION_THRESHOLD_PCT` (110%) in
   `scripts/compare_benchmark_runs.py`. That number comes from the closest
   thing there is to a same-runner measurement: a five-run study that spread
   only 106.8%, against a pool that spreads up to 158% across machines - so
   those five must have drawn near-identical hardware. It was mistaken for a
   cross-runner bound when it set the trend threshold; as a stand-in for
   single-machine jitter it is defensible, and an upper bound on it either way.
3. The comparison is **reporting only** - `--fail-on-regression` exists but is
   not passed. Turn it on once a single-runner noise study (`make
   benchmark-noise` on one CI runner) has said what the residual floor actually
   is; until then a gate would fire on noise, and a gate everyone learns to
   ignore is worse than no gate.
4. To reproduce locally, run `make benchmarks-ci` on your branch and on the
   merge base, then compare the two reports directly:

   ```
   uv run python -m scripts.compare_benchmark_runs --base base.json --head head.json
   ```

   Local-to-local only, as above.

**When a trend chart alert fires**

1. **Check which CPU each run drew** before anything else - the job summary of
   both runs says so, as does the chart tooltip. A step change that coincides
   with a change of CPU model is not a code change.
2. **Re-run the workflow.** GitHub-hosted runners are shared and virtualised;
   run-to-run variation on identical code is the normal explanation for a
   modest alert. An alert that does not reproduce across re-runs is noise.
3. `ALERT_THRESHOLD` is **derived from a measurement**: across eleven recorded
   runs whose lookup path was identical the tracked `min` spread 134-158%
   (unique 134.3%, random 145.9%, ambiguous 158.4%) purely because of the
   hardware each run drew. Worst spread plus 20% headroom rounds to the
   shipped **180%**. Be honest about what that buys - at 180% the chart
   catches only a catastrophic regression and is blind to the 10-30% changes
   actually worth reviewing.
   That is not a gap to close by tightening the number: a cross-machine chart
   cannot resolve better than the machines it spans. The same-runner PR
   comparison is the real gate; the trend alert is a deliberately weak backstop
   for `master`, which nothing else watches.
4. Re-derive it whenever the runner pool or the core set changes: trigger the
   `benchmark` workflow via `workflow_dispatch` with `repetitions: 5` (or
   more), read the derived threshold off the "report noise floor" job summary,
   and set `ALERT_THRESHOLD` in `benchmark.yml`. Note what that job measures:
   each repetition runs on a *different* machine, so it characterises the
   runner pool's spread, not a single runner's jitter.
5. Alerts are **non-blocking** (`fail-on-alert: false`) and stay that way:
   `master` must never be blocked on which machine a run drew.
6. `REPORT_FILENAME` and the artifact names are duplicated across
   `benchmark.yml` and `benchmark-comment.yml` because workflows cannot import
   constants; `tests/test_benchmark_workflows.py` fails if the copies drift.

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
- For data regeneration, document the timezone boundary release used, and note version bumps initiated with `uv version`. `update_data.sh` also regenerates the committed benchmark fixtures (`tests/fixtures/benchmarks/`) since they're pinned to `DATA_VERSION`, then automatically runs `make reports` to refresh `docs/data_report.rst` and `docs/benchmark_results_*.rst` against the new binary data (both would otherwise silently go stale) - if you bump `DATA_VERSION` any other way (not via `update_data.sh`), run `make benchmark-fixtures` and `make reports` yourself, in that order, or the benchmark fixture tests will fail with `BenchmarkFixtureError` and the reports will describe the old data. More generally: **regenerating the fixtures for any reason makes `docs/benchmark_results_*.rst` stale**, since those numbers are measured over the fixtures - always follow `make benchmark-fixtures` with `make reports`, whether or not `DATA_VERSION` moved. A standalone `make parse`/`make testparse` (bypassing `update_data.sh`) does not touch `DATA_VERSION`, the fixtures, or the reports at all.
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
