# Documentation maintenance rules

- **`README.rst` and `CHANGELOG.rst` must be valid *standalone* RST**, because `README.rst` is the
  PyPI long description (`readme` in `pyproject.toml`) and a Sphinx role (`:doc:`, `:ref:`) renders
  in the docs build but breaks that page. Link with an absolute
  `https://timezonefinder.readthedocs.io/…` URL instead. **Nothing enforces this** — `rstcheck`
  lints all three but does not resolve roles, so an unknown one passes at every report level; the
  check that means anything is rendering the file (see the `readme_renderer` command below)
- The `rstcheck` hook covers `docs/` too, with `sphinx` installed into its environment so the
  directives Sphinx owns are recognised, and `[tool.rstcheck]` in `pyproject.toml` naming the three
  it still cannot see (`autoclass`, `autofunction`, `include`). A bare `rstcheck` run reads the same
  config, so it agrees with the hook. It catches structural RST — a directive running into the block
  after it, a malformed table — which is worth knowing because `docs/` used to be excluded and the
  exclusion was silently load-bearing: those defects reached `master` and only `make docs` complained
- **Every target in `README.rst` must be absolute, and an `.. image::` source is a target too.**
  A repo-relative `docs/…` path is a real location on GitHub and no location at all on PyPI,
  which serves the long description without the repository — and `docs/` is excluded from the
  sdist by the `check-manifest` ignore list, so the file is not even shipped. Point images at
  `https://raw.githubusercontent.com/jannikmi/timezonefinder/master/…`. Neither `rstcheck` nor
  `make docs` catches this: both accept a valid directive whose target does not resolve, so
  verify with `uv run --with readme-renderer python -m readme_renderer README.rst -o tmp/readme.html`
  and open it. `docs/index.rst` is the opposite case — it sits next to the images, so its paths
  stay relative
- **Two passages are duplicated on purpose — edit every copy or they drift.** The badge block lives
  in `README.rst` and `docs/badges.rst` because the docs `include` it and an `include` does not
  render on PyPI. The *How it works* summary — the lookup pipeline, the no-simplification trade-off,
  the ocean-zone consequence for `timezone_at()` — lives in `README.rst` *and* `docs/index.rst`,
  because both are front doors reached without going through the other, with `docs/architecture.rst`
  holding the long form. A change to the lookup flow (the H3 resolution, holes-before-outer-ring,
  the unique-cell short-circuit) has to land in all three. Both are deliberate exceptions to the
  declare-once rule above
- **`README.rst` deep-links into `docs/` by anchor, and Sphinx derives an anchor from the heading
  text.** Renaming a heading in `docs/` silently breaks every README link to it: the page still
  loads, just at the top, so nothing 404s and nothing warns — `rstcheck` does not resolve targets
  and `make docs` does not know `README.rst` exists. After renaming a heading in a `docs/` page,
  grep `README.rst` for `<page>.html#`. When adding such a link, read the slug out of the built
  page (`grep -o 'id="[a-z0-9-]*"' docs/_build/html/<page>.html`) instead of deriving it by hand
- `docs/` pages are Sphinx-built. `docs/index.rst` carries four captioned toctrees — *Using it*,
  *Design*, *Performance*, *Project* — and a new page belongs in exactly one of them; listed in
  none it is orphaned and unreachable from the sidebar, listed in two it is a duplicate entry.
  `make docs` warns on both, and must build without new warnings — but `rstcheck` will not catch a
  broken cross-reference there
- Generated docs: `docs/benchmark_results_*.rst` (`scripts/render_benchmark_reports.py`) and
  `docs/data_report.rst` (`scripts/reporting.py`). The don't-hand-edit corollary above applies
- **Never copy an exact figure out of a generated page into hand-written prose** — vertex/polygon
  counts, index or wheel sizes, MiB footprints, queries/s. Regeneration updates the generated page
  and silently leaves every hand-written copy wrong, with nothing to catch it: this bit the
  `~8 MiB`/`~71 MiB` memory figures, which a shortcut-loader change made stale in four places at
  once. State the magnitude that survives a data update ("single-digit MiB", "hundreds of
  thousands of queries/s") and link the generated page for the current number. Figures fixed by a
  constant rather than by the data are fine to state exactly — `~1 cm` resolution follows from
  `COORD2INT_FACTOR`, `~288k` H3 cells from resolution 4
- **A zone name in a snippet is example output, not a constant** — `tz = timezone_at(...)  #
  'Europe/Berlin'`. It is an answer from the packaged dataset, so a data update can change it, and a
  comment copied from a page written against a different dataset is wrong on arrival with nothing to
  catch it. That is how `'Europe/Paris'` — the *reduced* `timezones-now` answer for Berlin
  coordinates, not what ships — once annotated the default dataset's running example in eleven
  places across `README.rst` and `docs/1_usage.rst`, until it was corrected wholesale. Run the
  lookup and paste what it returns
- **Prose that paraphrases a machine-readable file goes stale silently**, because the file changes
  and nothing re-reads the prose. Three such pairs exist deliberately, each because the reasoning is
  worth more than the indirection:
  - `docs/0_getting_started.rst` names the runtime dependencies → `[project] dependencies` in
    `pyproject.toml`. Names only, on purpose: version bounds stay in `pyproject.toml`, so a bump
    cannot falsify the page, but adding or dropping a dependency does
  - `docs/architecture.rst` *How it ships* → `.github/workflows/build.yml`,
    `[tool.cibuildwheel.*]` and `setup.py`. Changing the wheel targets, the abi3 base interpreter,
    the `abi3audit` repair step, what the end-to-end job asserts, or the on-master check changes
    what that section claims
  - `prototypes/README.md` → one row per script in `prototypes/`
  When you touch one side, re-read the other. Describing *why* a choice was made survives longer
  than restating *what* the file says — prefer it
- **A change that moves a measured path regenerates the report pages, in the pull request that
  moves it** — the same obligation `prototypes/query_stage_profile.py`'s `FINDINGS` carry under
  *Code Guidelines*, and easy to discharge for the prototype while forgetting these, because that
  one is named there and these were only ever documented as *how* to run. `make reports` is the
  whole job. It applies to a footprint as much as to a timing: `benchmark_results_memory.rst` is a
  committed measurement too, and a change to what an accessor builds at construction moves it.
  Stale generated measurements are the worst kind of stale — nothing fails, the page still builds
  and renders, and a figure describing a tree that no longer exists reads exactly like a current
  one. Say in the pull request which machine took them, since they are not comparable with CI's
- **`make reports` re-measures everything** — it has both `benchmarks` and `memory` as
  prerequisites — so it rewrites every committed figure on all four report pages. To change only
  the *rendering*, invoke the renderer directly against the stored JSONs; measurement and
  rendering are decoupled:
  `uv run python -m scripts.render_benchmark_reports --benchmark-json=tmp/benchmark.json --memory-json=tmp/memory.json`
  (omit `--memory-json` to leave `docs/benchmark_results_memory.rst` untouched).
  Confirm the JSONs are the ones behind the committed reports by re-rendering *before* your change
  and checking that `git diff docs/benchmark_results_*.rst` is empty.
  `docs/data_report.rst` is the exception among the four: it needs no measurement at all, so
  `uv run python -m scripts.reporting` regenerates it from the packaged binaries in seconds —
  never reach for `make reports` to update it

### Documentation & Communication

- Update `README.rst`, `docs/`, and changelog entries (`CHANGELOG.rst`) when behaviour, flags, or datasets change. This includes internal/dev-tooling changes with no public API impact (new scripts, test infrastructure, CI, refactors)—add those under the `Internal:` sub-list of the unreleased entry rather than skipping the changelog because nothing user-facing changed.
- For data regeneration, document the timezone boundary release used. A data update releases the separate `timezonefinder-data` distribution and nothing else: `update_data.sh` sets *its* version from the parsed release tag and records the release in `packages/timezonefinder-data/README.md`, leaving `timezonefinder`'s version and `CHANGELOG.rst` untouched. `update_data.sh` also regenerates the committed benchmark fixtures (`tests/fixtures/benchmarks/`) since they're pinned to `DATA_VERSION`, then automatically runs `make reports` to refresh `docs/data_report.rst` and `docs/benchmark_results_*.rst` against the new binary data (both would otherwise silently go stale) - if you bump `DATA_VERSION` any other way (not via `update_data.sh`), run `make benchmark-fixtures` and `make reports` yourself, in that order, or the benchmark fixture tests will fail with `BenchmarkFixtureError` and the reports will describe the old data. More generally: **regenerating the fixtures for any reason makes `docs/benchmark_results_*.rst` stale**, since those numbers are measured over the fixtures - always follow `make benchmark-fixtures` with `make reports`, whether or not `DATA_VERSION` moved. A standalone `make parse`/`make testparse` (bypassing `update_data.sh`) does not touch `DATA_VERSION`, the fixtures, or the reports at all.
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

  This file states what each of these breaks and why the duplication is deliberate.
