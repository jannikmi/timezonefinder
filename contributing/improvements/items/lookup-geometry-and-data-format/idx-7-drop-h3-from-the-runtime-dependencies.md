# IDX-7 — drop h3 from the runtime dependencies

## Related memory

- [Benchmarking, tooling and dependency decisions](../../decisions/benchmarking-tooling-and-dependency-decisions.md) — `h3` is the one runtime dependency reopened for removal.
- [IDX-6](idx-6-replace-the-h3-shortcut-index-with-the-grid-tree.md) — the replacement that leaves nothing importing it, and the pull request this item ships in.

## The item

- **Location:** `pyproject.toml` — `h3>=4` under `[project] dependencies`, and `h3` / `h3.*` in the mypy overrides; `uv.lock`; the runtime dependency list `docs/0_getting_started.rst` names.
- **What it is:** once IDX-6 lands, nothing the package installs imports `h3`, yet every install still pulls it in — 2.3 MB, and the published metadata keeps claiming a dependency the code no longer has.
- **Decided 2026-10-12 by the maintainer, against `master` at f706824: option (1) — the pass shipping IDX-6 removes `h3` in the same pull request, under a one-off exception to the dependency boundary stated by artifact.** The exception covers exactly the `h3` requirement under `[project] dependencies`; the `h3` / `h3.*` mypy overrides, unless code mypy still checks imports `h3`; `h3` declared in the `proto` group, if a prototype keeps importing it; and the lockfile lines those edits alone produce. A pass that finds itself touching anything else has left the exception. The [improvement-pass workflow](../../../workflows/run-one-improvement-pass.md)'s boundary carries it beside TOOL-6's, and it expires with this item: the pull request that retires this item deletes it from that boundary. The release that stops importing `h3` thereby also stops installing it.
  - **Why:** the removal is one-off, not a recurring class like TOOL-6's pins, so the exception expires instead of relaxing the boundary for good, and the published metadata stays true in the same release as the code.
  - **Refused: (2) the maintainer removes it after IDX-6 merges, boundary unchanged.** No exception, at the price of a window in which `master` declares a dependency it does not use, and a release cut inside that window ships it.
  - **Refused: (3) keep `h3` declared for one release after IDX-6**, as a courtesy to code importing `h3` through `timezonefinder` without declaring it. Buys downstream time nobody has asked for, for a release of dead weight.
  - **Reversibility:** re-adding the requirement is one line, and a release without `h3` installs harmlessly for everyone who does not import it.
  - **Unpriced:** how much downstream code imports `h3` through this package without declaring it. Nothing here can measure it; IDX-6's changelog fragment is the only warning such code gets, so it says that `h3` is no longer installed.
- **Free-threading:** `h3` is what re-enables the GIL when a finder is constructed on a free-threaded build, so removing it makes the strict xfail on `test_using_a_finder_keeps_the_gil_disabled` in `tests/test_free_threading.py` pass, which fails the suite: this pull request deletes that xfail, and states the free-threading support in `docs/` without claiming a shared instance scales — 1.60x at 8 threads shared against 4.84x per-thread is refcount contention, not a lock. Those test and docs edits are IDX-6's own scope, not the dependency exception.
- **Elsewhere:** `prototypes/latlng_index_bench.py` keeps an H3 control, and it is not the only prototype importing `h3` — `grep -rlE '^\s*(from|import) h3' prototypes/` lists the rest; each either keeps running through `h3` in the `proto` group or is retired with the index it studied. Code under `scripts/` or `tests/` still importing `h3` is IDX-6's to port; declaring `h3` in another group for it is outside the exception.
- **Size:** S.
- **Status:** blocked on IDX-6, whose pull request carries this item; nothing is left to decide.
