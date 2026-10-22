# Prepare and publish a code release

This workflow has two mutually exclusive halves: **prepare** opens a release pull request; **tag** runs only after the maintainer merges it. That merge is the authorization to publish: `tag_code_release.yml` tags the merged commit once its `master` build is green.

Read the [changelog policy](../development/changelog-and-release-note-policy.md) and [public compatibility contract](../project/public-api-and-compatibility-contract.md).

## Hard boundaries

- Never merge or enable auto-merge on the release pull request.
- Never push a tag by hand without explicit authorization naming it in the same session, and never ask for the release pull request's merge before the release is ready to publish. Both namespaces on this branch publish to PyPI, which never accepts a version twice: a bare `<version>` tag publishes `timezonefinder`, a `data-v<version>` tag publishes `timezonefinder-data`.
- Never force-push, delete a published tag, upload manually, regenerate data, fixtures, or bindings, or include unrelated files. The benchmark reports are the one exception, refreshed only through the step below and only in their own commit.
- Stage explicit paths; the checkout may contain another contributor's work.

## Determine the half

Fetch `origin` and tags, inspect `uv version --short`, the top changelog section, and newest tags.

- Project version equals the newest tag and pending fragments generate a non-empty section: prepare.
- Top section is a dated version matching the project version and no such tag exists: tag.
- Matching tag already exists: inspect and report its workflow; do nothing.

## Prepare

Require a clean/accounted working tree; current `master` equal to `origin/master`; no open release pull request or release branch; a non-empty unreleased section *after assembly* (`make changelog` shows it); and a green latest `master` run. A `release/**` branch on `origin` with no pull request is an abandoned attempt, because the branch is pushed early for the report render: delete it and start over. Nothing has been published at that point.

[Recheck the adoption claims](recheck-the-adoption-claims.md); a stale one is fixed in its own pull request first, never in the version commit.

### Publish the data distribution first

**A release whose declared `timezonefinder-data` version PyPI does not serve cannot ship, so check that first.** Read the requirement out of the checkout and ask the index what a user's resolver will ask:

```bash
grep timezonefinder-data pyproject.toml
uv run python -c 'from scripts.check_data_dependency import fetch_pypi_payload, released_versions
from scripts.configs import DATA_DISTRIBUTION_NAME
print([str(v) for v in released_versions(fetch_pypi_payload(DATA_DISTRIBUTION_NAME))])'
```

Ask through `released_versions`, not the raw `releases` map: a release whose files are all yanked, or which has none, is listed there but cannot satisfy a range. Reusing the tag-time guard's own predicate keeps this precheck and the guard from disagreeing.

If the declared version is absent, the data goes first, or `timezonefinder` is uninstallable for everyone in between. Every format change is in this position by construction, because `DATA_FORMAT_VERSION` is the data distribution's major version and the root pins `<N+1`; the [data pipeline and release order](../development/data-pipeline-format-versioning-and-release-order.md) carries the rest. Stop: [publish the data distribution](publish-the-data-distribution.md) owns that tag and its authorization. Return once the index serves the version.

`scripts/check_data_dependency.py` refuses the *code* publish while the data is missing, but only at the tag, after review and merge, which is the wrong end to discover it. Do not write a changelog bullet claiming the data "is published before this release" until it is.

## Rewrite the changelog

Assemble the fragments first; `make changelog` previews the section they make:

```bash
make changelog-assemble
```

That generates an `X.X.X (unreleased)` section, folds the fragments into their groups, and deletes the files it consumed. Confirm nothing is left behind before the version commit:

```bash
uv run python -m scripts.changelog_fragments --check --require-consumed
```

A surviving fragment is a change that ships with no entry and no way to notice, since `changelog.d/` is pruned from the distribution. `make release` and the `release` job run the same check ahead of the first irreversible step (`tests/test_release_workflows.py` asserts the ordering); running it here finds the problem while the version is still spendable.

Curate the grouped section as atomic changes: split independent outcomes, merge duplicates, remove performance claims and process history, and retain compatibility trade-offs. Correct a misfiled fragment, but do not re-sort the section. Compare every commit since the newest tag with the section and add missing non-exempt changes without inventing behavior. Show the changelog diff before selecting the version level so the evidence and the decision are reviewed together.

Compute patch, minor, and major candidates with `uv version --bump <level> --dry-run`. Select the strongest applicable rule:

| Level | Strongest change |
|---|---|
| major | Breaks exported API, signature, or documented semantics |
| minor | Adds public API or behavior, changes runtime dependencies or Python support, or changes a data format users compile |
| patch | Fixes, documentation, or an internal-only section |

Internal code and bundled formats are versioned together and are not major changes. A data-only boundary release is outside this workflow. If the invocation names a level, use it but state when the table requires a higher one.

Create `release/<version>`, run `uv version --bump <level>`, and replace the generated heading with the version and shell-derived date. Recompute its RST underline; do not insert an empty pending section above it. Only `CHANGELOG.rst`, `pyproject.toml`, `uv.lock`, and the consumed fragment deletions belong in the version commit.

Run `make hook`, `make test`, and `make testint`. Confirm the diff against `origin/master` contains exactly those files. Commit.

### Refresh the committed benchmark reports

The release freezes `docs/benchmark_results_*.rst` as the version's published performance. Only the artifact `benchmark.yml` renders on a named CI runner may be committed, and the stamp enforces it: `benchmark_report_artifact install` refuses a report measured for any other tree. **A pull request may publish its own render**, and one that changes what the pages measure should (dispatch `render_reports=true` against its head and install the result); the release is still the last word.

Push the branch as soon as the version commit exists. On every push to `release/**`, `benchmark.yml` renders the pages for the pushed commit, and its `commit-reports` job installs that artifact in its own commit on the branch, pushed with the data-updater App token so the pull request's CI runs on the new head. The render skips a head commit that is itself such a pages commit, which is what stops it looping. Nothing is dispatched, downloaded or installed by hand.

**Any further push to the release branch cancels the render for the earlier head.** `benchmark.yml`'s concurrency group is the workflow plus the ref with `cancel-in-progress: true`, and `commit-reports` refuses a branch that moved past the commit it rendered, so the new push renders and commits for itself. A cancelled run reads like a failure and is not one.

Two cases still install by hand: `gh workflow run benchmark.yml --ref "$release_branch" -f render_reports=true` for an artifact that expired while the release commit stood still, and a missing App secret, which `commit-reports` names. Install only the run whose head SHA is exactly the commit beneath the pages: `gh run download <run-id> --name benchmark-pages --dir tmp/benchmark-pages`, then `uv run python -m scripts.benchmark_report_artifact install --artifact-dir tmp/benchmark-pages --expected-commit <sha>`, and stage only the pages.

Wait for the pages commit before opening the pull request. Its body names the workflow run and runner CPU, and states that CI's paired same-runner comparison, not these cross-runner pages, decides whether code moved performance.

Push the remaining commits and open the release pull request. Its body names the old and new versions, the level, the bullet driving it and its rule, the level not taken and why, changelog edits, verification, the reports' run, and that merging publishes. Stop.

## Tag

The maintainer merges; `tag_code_release.yml` does the rest. On a successful `master` push build it checks out the built commit, never `master`'s tip, and pushes the annotated `<version>` tag only when that commit moved the project version, the top changelog section is dated for it, every fragment was consumed and the tag is absent. Its failures appear in the Actions tab only, because a `workflow_run` belongs to no pull request.

Tag by hand only when that workflow could not: its App secrets absent, or its run failed after the merge. Ask explicitly for authorization to tag the named version, explaining that this publishes to PyPI irreversibly, then tag the release commit itself: `git tag -a <version> <sha> -m "Release <version>" && git push origin <version>`. `make release` tags `master`'s head, which is the wrong commit once anything else merged.

**Then verify the upload, not the run.** A skipped job does not fail its run, so a green tag run is no evidence of publication: a `publish-pypi` job skipped at its `pypi` deployment environment leaves every gate green and nothing on PyPI. The release is done when the index serves the version and `publish-pypi` concluded `success`, not `skipped`:

```bash
gh api repos/<owner>/<repo>/actions/runs/<run-id>/jobs -q '.jobs[] | "\(.conclusion)\t\(.name)"'
uv run python -c 'from scripts.check_data_dependency import fetch_pypi_payload, released_versions
print([str(v) for v in released_versions(fetch_pypi_payload("timezonefinder"))])'
```

Report the tag, the workflow URL and that answer; never "published" on a green run alone.

Recover a skipped or failed upload by fixing the cause and re-running that job, never by retagging: the tag and GitHub Release already exist, and pushing it again publishes nothing. A run that failed for want of the green `master` run is the same: wait, then rerun. Any failure after a successful upload requires a new release.
