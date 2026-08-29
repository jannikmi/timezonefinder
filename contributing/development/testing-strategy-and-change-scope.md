# Testing strategy and change scope

- Add targeted tests under `tests/` for every behavioural change; mark them `@pytest.mark.unit`,
  `integration`, or `slow`. Shared fixtures live in `tests/auxiliaries.py`
- The point-in-polygon backend is bound at **import** time and Numba wins whenever it is
  importable — which `uv sync --all-groups` makes it, and `uv run` syncs inexactly so it stays.
  A local run therefore exercises the numba path while CI's bare tox envs exercise the clang one.
  A test that cares about the C extension must bind it explicitly rather than assume it is active;
  `tests/test_acceleration_paths.py` does that for the whole lookup stack
- While iterating, run only the file/pattern you're touching; `make test` (~30 s) as a broader
  check; `make testall` once as a final gate before finishing a PR, not after every change
- **`git fetch` and rebase onto the latest `master` *before* the final gate, not after.** Other
  work merges while yours is open, and a rebase after the fact invalidates the run — it tested a
  tree that never existed. Doing it in the wrong order costs a second full `make testall`, and a
  rebase that pulls in a real conflict (a regenerated report, a changed constant) costs one
  anyway. Re-run the gate whenever a rebase actually moves your branch's base
- **A green local gate is one point in a matrix, and cannot fail on what varies across the rest.**
  `make test`/`make testall` run one interpreter with one set of optional dependencies; tox spans
  `py{311,312,313,314}{,-numba,-pytz}`. Two axes bite in practice. Interpreter-generated text
  differs by version — argparse renders a rejected choice bare on 3.11 and quoted from 3.12 on — so
  assert what you actually mean (an exit code, an empty stdout) rather than wording another project
  owns and revises. And the default dev environment installs numba, so via the import-time dispatch
  in `utils.py` a local run exercises the numba `inside_polygon` and *never* the C extension, which
  is what the bare CI envs use. When a change depends on one of these axes, test that axis instead
  of re-running the whole gate; one file elsewhere costs seconds and needs no tox env:
  `uv run --python 3.11 --all-groups --isolated pytest tests/<file>.py`
- **A push only reaches CI through an open PR.** `build.yml` and `benchmark.yml` trigger on
  `pull_request`, on pushes to `master` and tags, and on `workflow_dispatch` — never on a push to a
  topic branch. So pushing a branch that has no PR yet schedules *nothing*, and the empty Actions
  list means it will never start, not that it has not started. Once a PR exists, `pull_request`
  fires on every further push to its head. Open the PR (or `workflow_dispatch`) if you want the
  matrix run; and read an empty check list as "never ran", which is also why a thin green list is
  not evidence that anything passed
- **A test over a file that cannot be run asserts an invariant, not the file's text.** The
  workflows and the composite actions under `.github/actions/` are only ever executed by GitHub,
  which makes "assert this step still contains that shell string" the tempting way to cover them,
  and the wrong one: it fails on every rewording and passes on every bug that keeps the wording,
  so the file becomes expensive to edit without becoming safer. Assert what the structure does not
  already enforce and what breaks silently — an ordering between steps, a gate every acting step
  must carry, two callers that must not pass the same value. And when the invariant is that two
  copies agree, prefer deleting the copy: `tests/test_data_update_workflow.py` needed half as many
  assertions once the steps it covered shared one action instead of three inline blocks
- `slow` tests are exhaustive sweeps of the whole dataset or hypothesis fuzzing, not general
  regression tests. Run them only when the change plausibly affects what they cover:
  - `main_test.py`, `shortcut_test.py`, `global_functions_test.py` slow cases — after touching
    `polygon_array.py`, `coord_accessors.py`, shortcut generation, the data converter, or `make data`
  - `test_property_api.py` — after touching `timezonefinder.py`, the `utils*` modules, or
    coordinate scaling/validation
  - `test_benchmark_fixtures.py::test_generator_*` — after touching
    `scripts/generate_benchmark_fixtures.py`
  - Otherwise (docs, CI config, tooling, reporting code) skip them: wall-clock time, no signal

### Testing & Coverage

- **Global test runs**: Use make commands (`make test`, `make testint`, `make testall`) for running full test suites
- **Isolated unit tests**: When only specific tests are affected, run them directly via `uv run pytest tests/path/to/test_file.py::test_name` or `uv run pytest -k "test_pattern"`
- Add targeted unit tests under `tests/` for every behavioural change. Use fixtures in `tests/auxiliaries.py` to cover edge coordinates and polygon holes.
- Run `make test` for fast feedback (excludes integration and slow tests).
- Run integration tests via `make testint` when packaging, build metadata, or binary assets change
- Run all tests including slow test cases via `make testall` when verifying dataset integrity or core algorithmic changes (shortcuts, geometry).
- Maintain deterministic tests—mock filesystem/network access, and avoid relying on system timezone settings. If you alter CLI behaviour, update `tests/test_integration.py` accordingly.
