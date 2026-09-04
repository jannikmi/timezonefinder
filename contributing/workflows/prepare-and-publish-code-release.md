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

Require a clean/accounted working tree; current `master` equal to `origin/master`; no open release pull request or release branch; a non-empty unreleased section *after assembly* — `make changelog` shows what a release would carry; and a green latest `master` run. A `release/**` branch on `origin` with no pull request is an abandoned attempt, not work in progress: the branch is pushed early so the report render can start (see *Refresh the committed benchmark reports*), so an attempt given up between that push and the pull request leaves one behind. Delete it and start over rather than resuming it; nothing has been published at that point.

### Publish the data distribution first

**A release whose declared `timezonefinder-data` version PyPI does not serve cannot ship, and the ordering is the first thing to check, not the last.** Read the requirement out of the checkout and ask the index what a user's resolver will ask:

```bash
grep timezonefinder-data pyproject.toml
uv run python -c 'from scripts.check_data_dependency import fetch_pypi_payload, released_versions
from scripts.configs import DATA_DISTRIBUTION_NAME
print([str(v) for v in released_versions(fetch_pypi_payload(DATA_DISTRIBUTION_NAME))])'
```

Ask through `released_versions`, not through the raw `releases` map the index serves: a release whose files are all yanked, or which has no files at all, is listed there but cannot satisfy a range requirement. Reusing the guard's own predicate is what keeps this precheck and the tag-time guard from disagreeing — a hand-rolled listing that counts those as published would reintroduce here exactly the gap this check exists to close.

If the declared version is absent, the data release goes first — publish the data, then the code requiring it, or `timezonefinder` is uninstallable for everyone between the two. Every format change is in this position by construction, because `DATA_FORMAT_VERSION` is the data distribution's major version and the root pins `<N+1`; the [data pipeline and release order](../development/data-pipeline-format-versioning-and-release-order.md) carries the rest.

The data release is a `data-v<version>` tag on `master`, published by `publish_data.yml` from the wheel `DATA_BUILD_RUN` names. Before tagging, confirm that run succeeded and that its `artifact-data-wheel` has not expired — the run id is the only reference to it, and an expired artefact is re-made by re-dispatching `compile_data.yml` on the branch and recording the new id:

```bash
gh api repos/<owner>/<repo>/actions/runs/"$(cat DATA_BUILD_RUN)"/artifacts -q '.artifacts[] | "\(.name) expired=\(.expired)"'
```

This tag publishes to PyPI irreversibly and is bound by the same rule as the code tag: **ask for authorization naming the version in the same session**, and never push it on standing instruction alone. `scripts/check_data_dependency.py` refuses the *code* publish while the data is missing, so a forgotten data release is caught rather than shipped — but it is caught at the tag, after the release pull request has been reviewed and merged, which is the wrong end of the process to discover it. Do not write a changelog bullet claiming the data "is published before this release" until it is.

## Rewrite the changelog

Assemble the fragments first. Every non-exempt change since the last release filed one under `changelog.d/`, and `make changelog` previews the section they make:

```bash
make changelog-assemble
```

That folds them into the `X.X.X (unreleased)` section and deletes the files it consumed, additively — existing bullets are never rewritten, so what it produces is the raw material for the rewrite below rather than the result of it. Confirm nothing is left behind before the version commit:

```bash
uv run python -m scripts.changelog_fragments --check --require-consumed
```

A fragment surviving the release is a change that ships with no changelog entry and no way to notice — `changelog.d/` is pruned from the distribution, so the bullet is absent from `CHANGELOG.rst` *and* from the package. It is therefore also *enforced*, not merely documented: `make release` runs the same check before it tags, and the `release` job runs it beside the data-dependency check, ahead of the first irreversible step. `tests/test_release_workflows.py` asserts that ordering. Running it here is what lets a release discover the problem while the version is still spendable.

Rewrite the entire unreleased section to describe the release end state: merge bullets for one feature, remove tuning history and review narration, retain decision-relevant trade-offs, and keep internal work under `Internal:`. Compare every commit since the newest tag with the section and add missing non-exempt changes without inventing behavior. Show the resulting changelog diff before selecting the version level so the evidence and the decision are reviewed together.

Compute patch, minor, and major candidates with `uv version --bump <level> --dry-run`. Select the strongest applicable rule:

| Level | Strongest change |
|---|---|
| major | Breaks exported API, signature, or documented semantics |
| minor | Adds public API or behavior, changes runtime dependencies or Python support, or changes a data format users compile |
| patch | Fixes, documentation, or an internal-only section |

Internal code and bundled formats are versioned together and are not major changes. A data-only boundary release is outside this workflow. If the invocation explicitly names a level, use it but state when the table requires a higher one.

Create `release/<version>`, run `uv version --bump <level>`, and replace the top changelog heading with the version and shell-derived date. Recompute its RST underline and insert a fresh empty `X.X.X (unreleased)` section above it. Only `CHANGELOG.rst`, `pyproject.toml`, `uv.lock`, and the consumed fragment deletions under `changelog.d/` belong in the version commit.

Run `make hook`, `make test`, and `make testint`. Confirm the diff against `origin/master` contains exactly those files. Commit.

### Refresh the committed benchmark reports

The release freezes `docs/benchmark_results_*.rst` as the published performance of the version, so a page measured before the code it describes ships as the release's own claim. The benchmark workflow renders the full pages on a named CI runner; the release consumes that artifact and remains the only place that commits it.

Push the branch as soon as the version commit exists. `benchmark.yml` runs on every push to `release/**` and renders the pages for the pushed commit, so the run this step consumes is already under way before the step is read, and nothing has to be dispatched by hand. From here until the pull request is open, an abandoned attempt leaves a branch on `origin`; the *Prepare* preconditions say to delete it.

```bash
release_sha=$(git rev-parse HEAD)
release_branch=$(git branch --show-current)
git push -u origin "$release_branch"
```

Then check staleness rather than assuming it: if any commit since the newest tag touched `timezonefinder/`, `packages/`, `DATA_VERSION`, or `benchmarks/` without a matching change to `docs/benchmark_results_*.rst`, the pages are stale and must be installed. If nothing did, skip the install and say so in the pull request body — the render still ran, because a push trigger cannot read that check. That costs one otherwise idle 60-minute runner on a release that moved no measured path, and buys a release that can never reach the install step with nothing to install.

`$release_sha` is what makes the install safe: the artifact carries that SHA and the installer refuses to copy a report measured for any other tree.

```bash
gh run list --workflow benchmark.yml --commit "$release_sha" --event push
gh run watch <run-id> --exit-status
rm -rf tmp/benchmark-pages
gh run download <run-id> --name benchmark-pages --dir tmp/benchmark-pages
uv run python -m scripts.benchmark_report_artifact install \
  --artifact-dir tmp/benchmark-pages --expected-commit "$release_sha"
```

Use the run whose displayed head SHA is exactly `$release_sha`; never take the newest run on branch name alone. The workflow pins the plain-install clang path, fixes the report round count, and prints the runner's CPU on every page. A failed job yields no report to commit.

**Any further push to the release branch invalidates this step, and does it by cancelling.** `benchmark.yml`'s concurrency group is the workflow plus the ref with `cancel-in-progress: true`, so pushing a fixup while the render is running kills the run for `$release_sha` rather than adding a second one beside it — `gh run watch --exit-status` then exits non-zero on a *cancelled* run, which reads like a failure and is not one. Recover by re-capturing `release_sha` from the new head and re-running the block, which the branch's own push has already restarted. `gh workflow run benchmark.yml --ref "$release_branch" -f render_reports=true` renders against the branch head for the one case no push covers: an artifact that expired while the release commit stood still. That manual dispatch is now the exception rather than the prerequisite.

Commit the refreshed pages **in their own commit**, so the version commit stays exact and the measurement diff is reviewable on its own. Stage only `docs/benchmark_results_*.rst` and `docs/data_report.rst`. The pull request body names the workflow run and runner CPU, and states that CI's paired same-runner comparison — not these cross-runner absolute pages — is the authority on whether code moved performance.

Push the remaining commits and open the release pull request. Its body names the old and new versions, level, the single bullet driving the level and matching rule, the level not taken and why, changelog edits, verification, whether the reports were refreshed or skipped as current, and that tagging happens separately. Stop.

## Tag

After the maintainer merges, update local `master` by fast-forward and verify its head is the release commit. Require the project version to equal the top dated changelog section, and verify the tag is absent locally and remotely.

Find the `master` workflow run for the exact head SHA and wait for it to succeed. The tag workflow does not rerun the tox matrix and refuses publication without that green run.

Ask explicitly for authorization to tag the named version on `master` and push it, explaining that this publishes to PyPI irreversibly. On approval, run `make release`. Confirm a tag-ref workflow appears and watch publication to completion. Report the tag and workflow URL.

If a tag workflow failed before publication because the matching `master` run was unavailable, wait for the green run and rerun the failed job; never retag. If the tag already exists, inspect the existing run. Any failure after publication spends the version and requires a new release.
