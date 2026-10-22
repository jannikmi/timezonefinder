# TOOL-9 — measure pytest-xdist on the CI test envs

- **Status:** open — a measurement first; adopting xdist is a separate change made only if the measurement shows it pays.
- **Size:** S — the measurement is a few runs and no committed code; adoption would be a dependency in the `test` group plus `-n` on the tox commands.
- **Location:** `tox.ini` (`[testenv]`, `[testenv:slow]` and `[testenv:free-threaded]` `commands`), the `test` matrix in `.github/workflows/build.yml`, and the `test` dependency group in `pyproject.toml`.

## The finding

The tox matrix is the critical path of every pull request. Each env runs pytest serially on an `ubuntu-latest` runner. Public-repository runners have 4 vCPUs, so three of them sit idle. On the run for master commit `3b7f4a15`, the `slow` env took 280 s of pytest for 1942 tests, and every ordinary env took about 60–70 s for about 2,500 tests. The `slow` env now has a matrix job of its own, which takes it off the 3.14 job's path but does not make it shorter. Once that split is in, the slowest jobs are the `slow` job and the 3.12 job, which runs six envs one after another.

## What to measure

1. **Whether the time is spread out enough to split.** xdist distributes tests, not the inside of a single test. Run `uv run pytest -m "slow or integration" --durations=30` serially first. If a handful of tests (for example the whole-dataset sweeps in `shortcut_test.py` or the hypothesis suites in `test_property_api.py`) account for most of the 280 s, parallelising cannot get below the longest of them. Then a split of those tests, not xdist, is the item.
2. **The speed-up across a range of worker counts, not at one point.** Measure `-n 2`, `-n 4` and `-n auto` (with `--with pytest-xdist`) against serial, for both the `slow` selection and the default `not integration and not slow` selection. Do this locally, then on `ubuntu-latest` from a draft pull request, because the CI runner is the machine that matters. CI runners span several CPU classes, so read `machine_info.cpu` or `/proc/cpuinfo` before comparing two runs.
3. **What each worker pays.** Every worker imports the package, opens the dataset and rebuilds session-scoped fixtures. Record each worker's setup cost and peak memory, so a gain on 4 vCPUs is not a loss on a 2-vCPU contributor machine.

## Things that can break, which the measurement must rule out

- **pytest-run-parallel is in the same environment.** The `free-threaded` env's second command uses `--parallel-threads=4`, and `pyproject.toml` already warns against combining that plugin with pytest-benchmark. Confirm that loading xdist leaves that smoke run untouched, or keep `-n` off that command.
- **Tests that share state on disk.** Anything that writes into the checkout or a fixed temporary path collides across workers. A collision shows up as flaky failures, not a clean error, so run each configuration more than once.
- **The numba env.** numba compiles per process, so each worker pays the JIT warm-up again. Measure the numba env on its own and do not assume its result follows the plain env's.

## Adoption bar

Adopt only if a CI measurement shows the slowest job, `slow` or 3.12, finishing clearly sooner (outside the run-to-run spread across several runs), with no new flakes across repeated runs. If only the `slow` env gains, apply `-n` there alone rather than to every env. Record the measured worker count and the per-env timings in this entry. If the measurement refuses the change, close this entry with that evidence, so the idea is not proposed again unmeasured.
