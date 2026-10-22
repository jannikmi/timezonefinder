# Reusable discovery methods

These methods are reusable audits, not a schedule. Repeat one when its trigger is present or new evidence invalidates its result.

## Exception and diagnostic audit

- `rg` plus Ruff `B904`, `BLE`, `TRY`, `EM`, `RSE`, `S110`, and `S112` covered every `raise` and `except` in runtime and scripts.
- Repeat after meaningful error-path changes, not automatically in every pass.

## Public-contract audit

- Compare runtime docstrings, `:raises:` and `:return:` claims, behavior, and callers.
- Reuse when an exported contract or its implementation changes.

## Assertion-boundary audit

- An AST scan of multi-statement `pytest.raises` and `pytest.warns` blocks found checks whose protected statement was ambiguous.
- Reuse after broad test rewrites.

## Ruff all-rules triage

- A repository-wide `ruff --select ALL` triage excluded prototypes and generated bindings and produced about 180 findings.
- Filter already-refused `EXE001` and `EXE002`, `S311`, `S603` and `S607`, `RUF022` and `RUF023`, and `TD` and `FIX` unless new evidence changes their premise.
- The refusals cover module shebangs, non-cryptographic fixture sampling, fixed subprocess arguments, semantically grouped `__all__`, and exploratory task markers.

## Type-check excluded directories

- Manual mypy runs found real defects before `scripts/` and `tests/` were added to the hook; that seam is now closed.
- The remaining exclusions are `prototypes/`, `docs/`, and `benchmarks/`; `prototypes/` is deliberate.

## Packaging-pattern audit

- Match every unwanted-distribution pattern against the working tree.
- Compare the result with `MANIFEST.in` and `check-manifest` ignores.
- Repeat when repository-only trees or packaging patterns change.

## Issue and premise revalidation

- Check every `GH-<n>` issue state and re-find the code anchor before selection.
- An issue may close or unrelated work may invalidate only part of an item's premise.
- A block on an upstream release clears without any signal in this repository: read the latest release of the project it names, and diff the gating function across its versions, before ranking around the block.

## Supported-version window check

- Compare the classifiers and `requires-python` with the CPython release calendar, `https://endoflife.date/api/python.json`, and with the drop dates in the comment above `requires-python`.
- For a new minor, `uv sync --frozen --python 3.X` into a scratch `UV_PROJECT_ENVIRONMENT` shows which locked dependency has no wheel for it; then run the default selection there with that environment's `bin/` on `PATH`, which the CLI tests need.
- Before proposing a drop, read the per-minor download share from `https://pypistats.org/api/packages/timezonefinder/python_minor` and the `requires-python` NumPy and SciPy declare.
- Repeat when a CPython minor reaches final, or when a date in that comment passes.

## Shortcut coverage sweep

- Replay the converter's candidate rule - `scripts/grid_cells.py::owned_pairs` - against the packaged binaries rather than against the converter's own in-memory geometry. Replay the *rule*, not a site: the sites move when the index does, and a method pinned to one stops running.
- Seven resolution-5 child centers across all 288,122 shortcut cells exercise 2,016,842 coordinates.
- The original sweep found eight bad answers and corrected the diagnosis from pole-enclosing cells to antimeridian-straddling cells.
- After checking every packaged polygon's longitude span and frame, the clean rerun found no answer from a cell lacking a containing polygon.
- `tests/shortcut_test.py::test_the_index_lists_the_polygon_covering_each_sampled_coordinate` is the affordable sampled guard.
- The cells corrected by the exhaustive sweep are covered by committed benchmark fixtures.

## Boxed-value audit of a hot Python loop

- Ask of every value the loop touches whether it is still a numpy scalar or a Python `int`, and whether the common branch raises.
- The two costs are invisible to a correctness reading and each sits below what the benchmark suite resolves, so they are found this way or not at all.
- Run over the candidate loop 2026-09-05 it found three in twenty lines - a `KeyError` per hole-less candidate, four bbox scalar extractions per candidate, and a whole zone id array gathered to read one element - together **-30 % of an ambiguous query** and **-12 % of a uniformly random workload**.
- Settle each on a paired whole-query A/B over the committed fixtures, never on the microbenchmark that found it; `memoryview` over an already-loaded array is the form that buys the Python `int` without a second copy.
- Repeat on any per-candidate or per-point Python loop that is added or materially changed.
