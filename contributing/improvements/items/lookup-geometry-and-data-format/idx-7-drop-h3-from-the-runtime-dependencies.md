# IDX-7 — drop h3 from the runtime dependencies

## Related memory

- [Benchmarking, tooling and dependency decisions](../../decisions/benchmarking-tooling-and-dependency-decisions.md) — `h3` is the one runtime dependency reopened for removal.
- [IDX-6](idx-6-replace-the-h3-shortcut-index-with-the-grid-tree.md) — the replacement that leaves nothing importing it.

## The item

- **Location:** `pyproject.toml` — `h3>=4` under `[project] dependencies`, and `h3` / `h3.*` in the mypy overrides; `uv.lock`; the runtime dependency list `docs/0_getting_started.rst` names.
- **What it is:** once IDX-6 lands, nothing the package installs imports `h3`, yet every install still pulls it in — 2.3 MB, and the published metadata keeps claiming a dependency the code no longer has. Dropping it is a change to the published dependencies, which the [improvement-pass workflow](../../../workflows/run-one-improvement-pass.md)'s hard boundaries keep out of a pass's reach; its one exception covers lint and formatter pins.
- **Elsewhere:** FT-3 is moot once `h3` is gone, and closes with this item. `prototypes/latlng_index_bench.py` keeps an H3 control; if it is to stay runnable, `h3` moves to the `proto` group rather than disappearing.
- **Decision needed:** who removes `h3` from the runtime dependencies once IDX-6 has stopped importing it.
  - **(1) The pass shipping IDX-6 removes it, in the same pull request, under a one-off exception stated by artifact:** the `h3` requirement, the `h3` / `h3.*` mypy overrides, the lockfile lines that removal alone produces, and `h3` in the `proto` group if the prototype keeps its control. The release that stops importing `h3` then also stops installing it. Costs a second exception to a boundary that exists to keep dependency changes out of unattended work; stating it by artifact, as TOOL-6's is, keeps it from being read wider.
  - **(2) The maintainer removes it after IDX-6 merges, boundary unchanged.** No exception, at the price of a window in which `master` declares a dependency it does not use, and a release cut inside that window ships it.
  - **(3) Keep `h3` declared for one release after IDX-6**, as a courtesy to code importing `h3` through `timezonefinder` without declaring it, then drop it under (1) or (2). Buys downstream time nobody has asked for, for a release of dead weight.
  - **Recommendation: (1).** The removal is one-off, not a recurring class like TOOL-6's pins, so the exception expires with this item rather than relaxing the boundary for good, and it keeps the metadata true in the same release as the code.
  - **Reversibility:** re-adding the requirement is one line, and a release without `h3` installs harmlessly for everyone who does not import it.
  - **Unpriced:** how much downstream code imports `h3` through this package without declaring it. Nothing here can measure it; the changelog entry is the only warning such code gets.
- **Size:** S.
- **Status:** needs the decision above; blocked on IDX-6 as well.
