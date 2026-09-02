# Prepare and publish a code release

This workflow has two mutually exclusive halves: **prepare** opens a release pull request; **tag** runs only after that pull request is merged. The maintainer merge separates them.

Read the [changelog policy](../development/changelog-and-release-note-policy.md) and [public compatibility contract](../project/public-api-and-compatibility-contract.md).

## Hard boundaries

- Never merge or enable auto-merge on the release pull request.
- Never tag without explicit authorization in the same session. Pushing the tag publishes to PyPI, which will not accept that version again.
- Never force-push, delete a published tag, upload manually, regenerate data, fixtures, or bindings, or include unrelated files. The benchmark reports are the one exception, refreshed only through the step below and only in their own commit.
- Stage explicit paths; the checkout may contain another contributor's work.

## Determine the half

Fetch `origin` and tags, inspect `uv version --short`, the top changelog section, and newest tags.

- `X.X.X (unreleased)` and project version equal to newest tag: prepare.
- Top section is a dated version matching the project version and no such tag exists: tag.
- Matching tag already exists: inspect and report its workflow; do nothing.

## Prepare

Require a clean/accounted working tree; current `master` equal to `origin/master`; no open release pull request or release branch; a non-empty unreleased section; and a green latest `master` run.

### Publish the data distribution first

**A release whose declared `timezonefinder-data` version PyPI does not serve cannot ship, and the ordering is the first thing to check, not the last.** Read the requirement out of the checkout and ask the index what a user's resolver will ask:

```bash
grep timezonefinder-data pyproject.toml
curl -s https://pypi.org/pypi/timezonefinder-data/json | python3 -c 'import json,sys; print(sorted(json.load(sys.stdin)["releases"]))'
```

If the declared version is absent, the data release goes first — publish the data, then the code requiring it, or `timezonefinder` is uninstallable for everyone between the two. Every format change is in this position by construction, because `DATA_FORMAT_VERSION` is the data distribution's major version and the root pins `<N+1`; the [data pipeline and release order](../development/data-pipeline-format-versioning-and-release-order.md) carries the rest.

The data release is a `data-v<version>` tag on `master`, published by `publish_data.yml` from the wheel `DATA_BUILD_RUN` names. Before tagging, confirm that run succeeded and that its `artifact-data-wheel` has not expired — the run id is the only reference to it, and an expired artefact is re-made by re-dispatching `compile_data.yml` on the branch and recording the new id:

```bash
gh api repos/<owner>/<repo>/actions/runs/"$(cat DATA_BUILD_RUN)"/artifacts -q '.artifacts[] | "\(.name) expired=\(.expired)"'
```

This tag publishes to PyPI irreversibly and is bound by the same rule as the code tag: **ask for authorization naming the version in the same session**, and never push it on standing instruction alone. `scripts/check_data_dependency.py` refuses the *code* publish while the data is missing, so a forgotten data release is caught rather than shipped — but it is caught at the tag, after the release pull request has been reviewed and merged, which is the wrong end of the process to discover it. Do not write a changelog bullet claiming the data "is published before this release" until it is.

## Rewrite the changelog

Rewrite the entire unreleased section to describe the release end state: merge bullets for one feature, remove tuning history and review narration, retain decision-relevant trade-offs, and keep internal work under `Internal:`. Compare every commit since the newest tag with the section and add missing non-exempt changes without inventing behavior. Show the resulting changelog diff before selecting the version level so the evidence and the decision are reviewed together.

Compute patch, minor, and major candidates with `uv version --bump <level> --dry-run`. Select the strongest applicable rule:

| Level | Strongest change |
|---|---|
| major | Breaks exported API, signature, or documented semantics |
| minor | Adds public API or behavior, changes runtime dependencies or Python support, or changes a data format users compile |
| patch | Fixes, documentation, or an internal-only section |

Internal code and bundled formats are versioned together and are not major changes. A data-only boundary release is outside this workflow. If the invocation explicitly names a level, use it but state when the table requires a higher one.

Create `release/<version>`, run `uv version --bump <level>`, and replace the top changelog heading with the version and shell-derived date. Recompute its RST underline and insert a fresh empty `X.X.X (unreleased)` section above it. Only `CHANGELOG.rst`, `pyproject.toml`, and `uv.lock` belong in the version commit.

Run `make hook`, `make test`, and `make testint`. Confirm the diff against `origin/master` contains exactly those three files. Commit.

### Refresh the committed benchmark reports

The release freezes `docs/benchmark_results_*.rst` as the published performance of the version, so a page measured before the code it describes ships as the release's own claim. Nothing else regenerates them: the benchmark workflow records only the tracked core subset, never the rendered pages, so a merged performance change that skipped its regeneration leaves them stale until a release notices.

Check staleness rather than assuming it: if any commit since the newest tag touched `timezonefinder/`, `packages/`, `DATA_VERSION`, or `benchmarks/` without a matching change to `docs/benchmark_results_*.rst`, the pages are stale and this step is required. If nothing did, skip it and say so in the pull request body.

Establish the machine is quiet enough to measure on **before** measuring, since a report is only worth committing if it is reproducible. The gate is only readable if it measures the path the reports describe, so assert that first:

```bash
uv run python -m scripts.assert_acceleration_path --expect "$(make -s print-benchmark-acceleration-path)"
```

`benchmark-noise` runs `benchmarks-ci`, which uses this checkout's environment rather than `make benchmarks`' isolated one, and `timezonefinder/utils.py` binds the point-in-polygon backend at import time, preferring numba whenever it is importable. A development environment synced with `--all-groups` therefore has numba, so `make benchmark-noise` would characterise a different implementation than the pages assert, and the assertion above fails in exactly that environment.

That failure is about the *environment the gate runs in*, not about the machine, so it is not on its own a reason to declare the reports stale. `make reports` is unaffected — `benchmarks`, `latency` and `memory` all measure under `BENCHMARK_ENV` and assert the path themselves. Read the floor under that same environment instead of `make benchmark-noise`, so the gate describes the kernel the pages do:

```bash
uv run --isolated --group test --group compare python -m scripts.assert_acceleration_path \
  --expect "$(make -s print-benchmark-acceleration-path)"
for i in 1 2 3 4 5; do
  uv run --isolated --group test --group compare pytest benchmarks -m benchmark_core \
    --benchmark-min-rounds=50 --benchmark-json=tmp/benchmark-core-raw.json
  uv run --isolated --group test --group compare python -m scripts.normalize_benchmark_json \
    --benchmark-json=tmp/benchmark-core-raw.json \
    --output=tmp/benchmark-noise/run-$i.json --estimator=min
done
uv run --isolated --group test --group compare python -m scripts.benchmark_noise \
  tmp/benchmark-noise/run-*.json --estimator=min --min-runs=5
```

Treat the reports as stale only when the floor itself cannot be brought under threshold. Where the environment resolves the asserted path directly, `make benchmark-noise` is the shorter route to the same number.

It repeats the CI core subset five times on unchanged code and prints the observed spread against a threshold derived from it. Over threshold means the machine is too busy — other agent sessions, a build, a sync — and the run must not be committed. Do not treat waiting for an idle machine as a plan: this checkout is worked concurrently, so re-check rather than assume quiet arrives, and if it does not, stop and report the reports as stale rather than committing numbers the threshold rejects.

On a passing noise check, regenerate and commit the pages **in their own commit**, so the version commit stays exactly three files and the measurement diff is reviewable on its own:

```bash
make reports
```

Stage only `docs/benchmark_results_*.rst` and `docs/data_report.rst`. The pages record their own environment, and dispersion columns move with the host even when means do not, so the pull request body states the machine, the observed noise spread, and that CI's paired same-runner comparison — not these pages — is the authority on whether a change moved anything.

Push and open the release pull request. Its body names the old and new versions, level, the single bullet driving the level and matching rule, the level not taken and why, changelog edits, verification, whether the reports were refreshed or skipped as current, and that tagging happens separately. Stop.

## Tag

After the maintainer merges, update local `master` by fast-forward and verify its head is the release commit. Require the project version to equal the top dated changelog section, and verify the tag is absent locally and remotely.

Find the `master` workflow run for the exact head SHA and wait for it to succeed. The tag workflow does not rerun the tox matrix and refuses publication without that green run.

Ask explicitly for authorization to tag the named version on `master` and push it, explaining that this publishes to PyPI irreversibly. On approval, run `make release`. Confirm a tag-ref workflow appears and watch publication to completion. Report the tag and workflow URL.

If a tag workflow failed before publication because the matching `master` run was unavailable, wait for the green run and rerun the failed job; never retag. If the tag already exists, inspect the existing run. Any failure after publication spends the version and requires a new release.
