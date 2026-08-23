# CLAUDE.md

## Project Overview

`timezonefinder` provides offline timezone lookups by WGS84 coordinates, prioritising accuracy at
timezone borders (no geometry simplification) over raw speed.

Constraints that shape design decisions:

- Primary users are latency-sensitive services doing high-volume, possibly concurrent lookups
  (plus one-off CLI/script use)
- Must run in **containerised deployments with constrained CPU/memory** — don't assume abundant
  RAM or many cores; the `in_memory=False` (memory-mapped) path must stay a viable low-memory option
- Must degrade gracefully without Numba/C-extension — the pure-Python path stays correct, just slower

Non-goals: sub-centimeter precision (the ~1.1 cm coordinate scaling is a deliberate ceiling, not a
bug), and general-purpose geometry — spatial code exists only in service of timezone lookup.

## Development Setup

- Use `uv` for all dependency management; run every Python command via `uv run`
- Run `make hook` after code changes; failures must be fixed before committing. Also run it after
  regenerating anything, *before* reading the diff — see *Generated Files*
- The `Makefile` header comment documents every target. Where the *choice* between targets is the
  non-obvious part, it is covered under *Testing* below and in `CONTRIBUTING.md`
- Don't prefix suggested commands with a redundant `cd` into the project root

## Project Structure

**Two distributions, one uv workspace**: `timezonefinder` at the root, and
`packages/timezonefinder-data/` holding the boundary binaries plus `DATA_LICENSE`. The data package
is deliberately dumb — one `DATA_DIR` constant and a version.

**Moving the binary-format reader into it was considered and rejected**; don't re-propose it. It is
neutral on size (the reader is pure Python, and the C extension forcing the platform-wheel matrix
is in the lookup layer either way), it makes a reader bug cost a ~63 MB upload, and it trades a
cheap in-file format guard for an unguarded cross-distribution Python API on a package whose
version numbers upstream *data* releases. Data version, reader-API version and format version are
three axes and there is one number. It also inverts the converter, which imports `flatbuf/io` to
*write*.


Most modules are self-describing; the non-obvious ones:

- `timezonefinder/configs.py`: central type definitions and runtime constants (coordinate scaling,
  FlatBuffers layout, `DATA_FORMAT_VERSION`). `DEFAULT_DATA_DIR` sources from
  `timezonefinder_data.DATA_DIR`, so the data's *location* differs between a `uv sync` checkout
  (editable, source tree) and an installed wheel — anything asserting it will disagree across the two
- `timezonefinder/utils.py` / `utils_numba.py` / `utils_clang.py`: polygon math, pure-Python plus
  the two acceleration backends. `utils.py` picks the implementation **at import time**, so the
  backends are entirely separate code paths whose timings are not comparable
- `benchmarks/`: `pytest-benchmark` suites, excluded from `make test`/`make testall` via
  `testpaths` — they are collected only when `benchmarks/` is passed explicitly. **Timing only**:
  memory is measured by `scripts/measure_memory.py` (`make memory`), because `tracemalloc` across
  pytest-benchmark's calibration rounds distorts the timings. Its subprocess probe must never
  import `tests/auxiliaries.py`, which allocates a 64 MB `PolygonArray` at import
- `scripts/normalize_benchmark_json.py` / `benchmark_noise.py` / `assert_acceleration_path.py` /
  `compare_benchmark_runs.py` / `describe_benchmark_machine.py`: benchmark CI helpers.
  `ubuntu-latest` pins the runner *image*, not the CPU: the pool spreads up to ~1.58x on unchanged
  code, so any two CI runs are incomparable unless they name the same CPU.
  `docs/benchmarking_methodology.rst` holds the methodology these scripts implement;
  `CONTRIBUTING.md` keeps only the operational instructions and links to it
- `docs/data_format.rst`: authoritative reference for binary layouts and coordinate scaling

## Runtime Lookup Flow

Coordinates → scaled int32 (×10^7) → H3 shortcut map yields candidate polygons → bounding-box
rejection → point-in-polygon (holes first, then outer ring, ray casting). Ocean zones
(`Etc/GMT±XX`) guarantee a match for any coordinate unless `timezone_at_land` is used.

## Code Guidelines

- Define types centrally in `timezonefinder/configs.py` to avoid duplication and circular imports
- Before adding any version-gated import, `__future__` feature, or compatibility shim, check
  `requires-python` and confirm the feature actually needs it on the minimum supported version
- **Do not let an unmeasured micro-optimisation choose the structure.** The shortcut index was
  first wired into `AbstractTimezoneFinder` as five flat array attributes with the slot
  arithmetic and entry decoding inlined at each call site, justified by an attribute hop
  "not worth the tidier grouping" — which was never measured. It costs nothing: routing the
  same lookup through `ShortcutIndex.entry_of` / `candidates_of` / `stop_index_of` measured
  inside the noise on all four strata, both estimators disagreeing. Encapsulate first, then
  measure, and only then trade the design away — with the numbers in the commit. A method
  call is not free, but at ~1 µs per query it is far below what this repository can resolve
- **Removing the last caller of something is half the change: the other half is the callee.**
  Grep for remaining callers in the same commit, and act on what you find — no callers at all
  means delete it; callers only in tests means it is test scaffolding and should say so; callers
  only at build time means it must *leave the runtime modules*, because everything in
  `timezonefinder/utils_numba.py` is compiled and bound at import in every user's process. That
  is how `get_last_change_idx` outlived its query-path caller: precomputing it into the shortcut
  index removed the call, and the `@njit` function stayed behind being compiled for nobody. A
  helper that no longer runs per query is not merely tidy to move — it is cost every user pays
- **A dispatch boundary costs more than any scalar per-query stage computes.** An empty `njit`
  call is ~98 ns and a cffi crossing the same order, against stages of 100-200 ns — so reaching
  for Numba or the C extension to speed one up is a measured dead end, not an untried idea, and
  `njit` on a scalar helper is a net *loss* (`potential-improvements.md`, *Recorded decisions*,
  has the numbers and the inventory of which helpers still pay it). Numba earns its place on
  `inside_polygon`, over arrays of hundreds to tens of thousands of vertices, where the same
  overhead amortises to nothing. Look for the algebra first: the H3 slot lookup lost two thirds
  of its arithmetic to one observation about adjacent bit fields
- Preserve the fast lookup path. `prototypes/query_stage_profile.py` attributes a `timezone_at`
  query to its stages, per backend and per coordinate-access mode, off the committed fixtures —
  read its `FINDINGS` block before arguing about where query time goes, and re-run it rather
  than reasoning from a microbenchmark. **Those numbers are pinned to the commit they were taken
  at and go stale silently**: a change under `timezonefinder/` or to the packaged data can move
  every share quoted from them, so re-measuring belongs to the pull request that moves the
  critical path, not to a later one. They are also **one machine's**: rank on the counts a change
  removes (machine-independent) and on the `clang` / mapped column that a plain install actually
  runs, not on absolute nanoseconds. `potential-improvements.md` (*The measured baseline*) holds
  the anchor, the denominators, the workload conversion and a one-command freshness check
- Keep `COORD2INT_FACTOR` / `DECIMAL_PLACES_SHIFT` in sync between runtime and data converter
- The public API (exported functions and classes) must not break between minor versions; internal
  code, data formats, and binary assets are versioned with the package and need no compatibility.
  Before writing a fallback for older data or an older caller anyway, establish that what you would
  stay compatible with was ever released: `git merge-base --is-ancestor <commit> <latest tag>`. On
  `master` an unreleased format marker is indistinguishable from a shipped one, so such a branch
  reads as load-bearing while being unreachable — and it is not only dead code that costs. Guarding
  one cost a version bump that rewrote the 63 MB coordinate binary for a single changed byte, and
  the fallback itself was a per-lookup branch reached by no dataset that exists
- Keep `__all__` in `__init__.py` files — they define the public API surface. Nothing asserts
  their contents directly; the only incidental protection is that `tests/conftest.py` imports
  from the top-level package, so emptying `timezonefinder/__init__.py` fails collection outright
- Prefer dependency injection over module-level state; global helper functions are NOT thread-safe,
  concurrent workloads should use per-thread `TimezoneFinder(in_memory=True)` instances
- **Check an artifact where it is produced, never where it is consumed.** Whatever the build
  establishes — the packaged binaries above all — must not be re-validated when a finder is
  constructed: that re-derives a settled fact in every user's process, on a path latency-sensitive
  services pay for per thread. Put the assertion in the generator (over what it just wrote) *and*
  in the test suite (over what is committed), sharing one implementation so the two cannot drift;
  `scripts/data_integrity.py` is the pattern. Staying off the init path is also what lets such a
  check be *thorough* — the hole-reference check resolves every ring in the dataset, which no
  per-construction budget would allow. A defensive `if` at load time is the tempting version of
  this and the wrong one: it is slower, and being forced to stay cheap makes it shallower
- **Pick the narrowest integer dtype that fits, guard it, and never reject a width for lack of
  headroom alone.** A width chosen with 1.2x margin is fine; a width chosen *for* margin is
  padding. The data is produced by a converter this repository owns, so an overflow surfaces at
  build time rather than in a user's process — provided something checks, which is the bullet
  above: assert it in the generator and in the test suite, sharing one implementation. The error
  message is the deliverable, not the assertion: name the value that overflowed, the dtype's
  ceiling, which width to move to, and the version bumps that follow. A guarded narrow type is
  strictly better than an unguarded wide one — smaller, and loud instead of silently truncating
- **Declare each path/filename constant once** in the module that owns the resource and import it
  elsewhere; never re-derive a path or retype a filename string in a second file — the two copies
  drift when one is renamed
- **Never point at something outside the repository for a reason.** Two shapes, one failure mode:
  an issue or PR number in code (`# Since #446`, `(issue #446)`) — comments, docstrings, workflow
  headers, config comments — and a path under `plans/`, which is **gitignored and temporary**, so
  the reference is already dangling for everyone but its author. Either way the *reason* stops
  being where the code is: a tracker gets retitled, re-scoped and closed independently, and a plan
  file is deleted when the work lands. Write the reasoning itself; if it is too long for a comment,
  it belongs in `docs/`, and a rejected option belongs wherever it can actually refuse the next
  proposal. `CHANGELOG.rst` is the exception — there an issue number is the release's provenance,
  and `Thanks to … PR #123` is required (see *Changelog*)

## Testing

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

## Changelog

Every change needs a `CHANGELOG.rst` entry in the `X.X.X (unreleased)` section — user-facing ones in
the main bullet list, dev tooling / refactors / CI / test infrastructure appended to the `Internal:`
sub-list. This is easy to forget for changes that don't touch `timezonefinder/` at all (docs,
`scripts/`, CI config, fixtures); those still need one. Exception: edits to `CLAUDE.md` or
`CONTRIBUTING.md` alone.

The changelog is read by users, not by reviewers of the PR that produced it. Describe the **end
state**, never the path taken to it:

- **Amend, don't append.** When a follow-up commit, review round, or fix changes something already
  described in the unreleased section, edit that bullet so it describes where the code landed.
  Adding a second bullet that corrects, tunes, or extends the first one is what makes the section
  unreadable — a released version should read as if the feature arrived in one step.
- **One bullet per user-visible change**, not per commit or per PR. A feature delivered over
  several commits (with its tests, docs, CI wiring and follow-up tuning) is one bullet.
- Keep the *why* only when it's decision-relevant for a reader — a deliberate trade-off, a
  non-obvious constraint, a gotcha. Drop tuning history ("raised from X to Y, then to Z" → state
  the final value), superseded intermediate states, and self-review narration.
- Keep bullets to a few sentences. Details that belong to contributors, not users, go in
  `CONTRIBUTING.md` or a docstring, and the bullet points there.
- Before finishing a task, re-read the whole `X.X.X (unreleased)` section: if two bullets describe
  the same feature, merge them.
- **Remember to acknowledge outside contributions**, in the form the existing `Thanks to …` bullets
  use. Credit the contributor's own PR, which is not the maintainer PR that superseded it.

## Improvement Register

`potential-improvements.md` at the repository root is the single register of what is worth doing
next: every finding a pass turns up — whatever its area, from a correctness defect to a docs
caveat to a data encoding — in one ranking, with the sequencing rules and the decisions already
taken. `.claude/skills/improvement-pass/SKILL.md` drives one pass
over it, and `tests/test_improvement_ledger.py` asserts that the ranking table and the entries name
the same items.

**A pass asks the maintainer nothing.** It runs unattended, so a question put mid-run reaches nobody
and stalls every item ranked below it, and an answer given in a chat session is never written where
the pass that finally implements the item can read it. A choice that is genuinely the maintainer's
is recorded instead — `Status: needs …` plus a `**Decision needed:**` bullet carrying the question,
the options and a recommendation, a pairing `tests/test_improvement_ledger.py` enforces in both
directions — and the pass takes the next eligible item.
`.claude/skills/maintainer-decisions/SKILL.md` is the other half: it collects those questions,
re-verifies each against the current code, briefs them, puts them to the maintainer and records the
answers. It never implements what it asked about, so the design lands as a reviewable decision
before any code is built on it.

It replaced a roadmap issue on the tracker, and the reason generalises: reasoning that lives
outside the repository goes stale silently, because nothing references it, no check reads it, and a
reviewer never sees it in a diff. Issues remain the place a single item is worked out; the ranking,
the sequencing and the decisions live in the file.

**Update it as part of the work that changes it**, not afterwards, whenever you ship an item, open
or close an issue, re-scope one, or settle a design question the register ranked. Two things that
cost more than they look:

- **A recorded decision is kept, never deleted** — including rejected options, which is most of
  their value. The next pass re-proposes whatever is not written down as already refused
- **Correct the reasoning, not just the status.** An entry whose conclusion survived on a premise
  that has since been disproved is the failure mode worth catching: it reads as settled and sends
  the next pass down a path already ruled out. Say what moved

A shipped entry is **deleted**, and its ranking row with it — the code is the evidence it is done
and the changelog says what changed. A rejected or withdrawn one stays, with its one line of reason.

**Deleting the entry is not the whole job: the id must stop appearing anywhere in the file.** Other
entries cite it as a blocker, the dependency graph gives it a node, *Sequencing* prices work against
it, and recorded decisions cite it as the case that settled them. Left behind, every one of those is
a dangling handle — it resolves to nothing, so the next pass either hunts for an entry that is not
there or reads "GH-N has shipped" as live status in a file that is a to-do list, not a history.
`grep` the id after deleting and rewrite each hit to **describe the thing instead of naming the
issue**: what a candidate polygon now costs, not "after GH-536". The reasoning is what was worth
keeping; the number was only ever a handle to it. Recorded decisions are kept, so they get rewritten
this way rather than deleted.

## Generated Files

**Invariant: every generator emits output that is already pre-commit-clean**, so regenerating and
diffing compares like with like. Keep it that way — when it breaks, a re-parse shows spurious diffs
that look like converter drift, or real changes drown in formatting churn, and the lossless check
after a data regeneration (`git status --short packages/timezonefinder-data/timezonefinder_data/data` listing only genuinely changed
binaries) stops meaning anything.

What it takes to hold, for anything you add:

- `scripts/utils.py` `write_json` stringifies keys before `sort_keys`, matching `pretty-format-json`.
  Sorting int keys directly gives numeric order; the hook re-reads the file, where JSON keys are
  strings, and sorts lexicographically
- `scripts/reporting.py` emits no trailing whitespace on empty table cells and exactly one final
  newline, matching `trailing-whitespace` / `end-of-file-fixer`. `BenchmarkReporter.write_report`
  (`scripts/benchmark_utils.py`) applies the same final-newline normalisation for every
  `docs/benchmark_results_*.rst`
- `make flatbuf` runs the formatters itself, since `flatc` output differs from the committed
  bindings under `ruff-format` and `pyupgrade`

Both normalisations are covered by tests in `tests/utils_test.py`. If a generated file still comes
out dirty, fix the generator rather than committing the hook's repair — the repair is invisible and
the next regeneration undoes it.

Corollary: don't edit a generated file directly. Change the generator or the schema and regenerate.

## Documentation Files

- **`README.rst` and `CHANGELOG.rst` must be valid *standalone* RST.** Both are linted by the
  `rstcheck` pre-commit hook, unlike `docs/`, which it excludes — a Sphinx role (`:doc:`, `:ref:`)
  works in the docs build but fails the hook here, and additionally breaks the PyPI page for
  `README.rst`, which is the long description (`readme` in `pyproject.toml`). Link with an
  absolute `https://timezonefinder.readthedocs.io/…` URL instead
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
  `COORD2INT_FACTOR`, `~41k` H3 cells from resolution 3
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

## Data Pipeline & Versioning

- `update_data.sh` downloads a timezone-boundary-builder release into `tmp/` and runs
  `scripts/file_converter.py`, which scales coordinates by 10^7 into int32. A data update releases
  the **separate `timezonefinder-data` distribution** and nothing else: `update_data.sh` sets that
  package's version from the tag it parsed and records the release in
  `packages/timezonefinder-data/README.md`. `timezonefinder`'s version and `CHANGELOG.rst` are not
  touched, and the tag namespace is `data-v*` — a bare version tag publishes the *code*
- **The data distribution's major version is `DATA_FORMAT_VERSION`** (`timezonefinder/configs.py`),
  and the root declares `timezonefinder-data>=…,<N+1`. Bumping either per-file layout version
  (`POLYGON_LAYOUT_VERSION`, `SHORTCUT_LAYOUT_VERSION`) obliges a `DATA_FORMAT_VERSION` bump —
  `tests/test_data_version.py` asserts the pairing, because nothing else would notice. A format
  change is therefore a **two-distribution, ordered release: publish the data first**, then the code
  requiring it, or `timezonefinder` is briefly uninstallable
- **Generators write to `scripts.configs.SOURCE_DATA_DIR`, never `DEFAULT_DATA_DIR`.** The latter
  now resolves to wherever `timezonefinder_data` is *installed*, which under a non-editable install
  is inside `site-packages` — and since `make parse` passes no paths, a converter defaulting to it
  would rewrite the installed wheel instead of the checkout
- Benchmark fixtures in `tests/fixtures/benchmarks/` are pinned to the `DATA_VERSION` they were
  generated against and the loader refuses mismatches. `make data` regenerates them; use
  `make benchmark-fixtures` only when just the fixtures need refreshing
- When modifying a FlatBuffers schema, delete previously generated binary artifacts so they
  regenerate consistently
- `.github/workflows/check_data_updates.yml` opens an update PR weekly when upstream has a new
  release; `release_data_update.yml` merges it and pushes the tag with a GitHub App token (the
  default `GITHUB_TOKEN` would not trigger `build.yml`)

## Release Process

From `master` only — `make release` enforces it and its `Makefile` comments carry the tag/push
ordering constraints. `.claude/skills/cut-release/SKILL.md` drives the manual path end to end
(bump proposal → release PR → tag); data-only releases go out through `release_data_update.yml`
instead and need no manual step.

## Canonical Instructions File

This file is the single source of truth for coding-agent instructions. `AGENTS.md` and
`.cursor/rules/repo-instructions.mdc` are pointer stubs for tools that look for those filenames —
update this file only, and don't let the stubs accumulate their own copies.

**Keep it current.** When you discover a durable repo fact that isn't written down here, add it as
part of the work that surfaced it. The bar is all three of:

- **durable** — still true next month; not a detail of the change you happen to be making
- **non-obvious** — it cost you a cross-reference, a failed hook, or a wrong guess to learn.
  Anything visible in the file you are already editing does not qualify
- **it has a failure mode** — you can name what silently breaks for someone who doesn't know it

Counter-pressure, because this file is loaded into every session and a bloated one gets skimmed:

- Amend an existing section rather than opening a new one — the same rule as *Changelog* above,
  for the same reason
- If the fact belongs at the point of decision (a `Makefile` comment, a docstring, a comment next
  to the constant), put it *there* and don't copy it here. Every duplicated line is a line that
  will drift
- Correct or delete entries once they go stale. A confidently wrong instruction costs more than a
  missing one
- Don't restate what the code, `git log`, or another section already says

An edit confined to this file needs no changelog entry, so recording a fact is cheap.
