# Prepare and publish a code release

This workflow has two mutually exclusive halves: **prepare** opens a release pull request; **tag**
runs only after that pull request is merged. The maintainer merge separates them.

Read the [changelog policy](../development/changelog-and-release-note-policy.md) and
[public compatibility contract](../project/public-api-and-compatibility-contract.md).

## Hard boundaries

- Never merge or enable auto-merge on the release pull request.
- Never tag without explicit authorization in the same session. Pushing the tag publishes to PyPI,
  which will not accept that version again.
- Never force-push, delete a published tag, upload manually, regenerate data, fixtures, reports, or
  bindings, or include unrelated files.
- Stage explicit paths; the checkout may contain another contributor's work.

## Determine the half

Fetch `origin` and tags, inspect `uv version --short`, the top changelog section, and newest tags.

- `X.X.X (unreleased)` and project version equal to newest tag: prepare.
- Top section is a dated version matching the project version and no such tag exists: tag.
- Matching tag already exists: inspect and report its workflow; do nothing.

## Prepare

Require a clean/accounted working tree; current `master` equal to `origin/master`; no open release
pull request or release branch; a non-empty unreleased section; and a green latest `master` run.

Rewrite the entire unreleased section to describe the release end state: merge bullets for one
feature, remove tuning history and review narration, retain decision-relevant trade-offs, and keep
internal work under `Internal:`. Compare every commit since the newest tag with the section and add
missing non-exempt changes without inventing behavior. Show the resulting changelog diff before
selecting the version level so the evidence and the decision are reviewed together.

Compute patch, minor, and major candidates with `uv version --bump <level> --dry-run`. Select the
strongest applicable rule:

| Level | Strongest change |
|---|---|
| major | Breaks exported API, signature, or documented semantics |
| minor | Adds public API or behavior, changes runtime dependencies or Python support, or changes a data format users compile |
| patch | Fixes, documentation, or an internal-only section |

Internal code and bundled formats are versioned together and are not major changes. A data-only
boundary release is outside this workflow. If the invocation explicitly names a level, use it but
state when the table requires a higher one.

Create `release/<version>`, run `uv version --bump <level>`, and replace the top changelog heading
with the version and shell-derived date. Recompute its RST underline and insert a fresh empty
`X.X.X (unreleased)` section above it. Only `CHANGELOG.rst`, `pyproject.toml`, and `uv.lock`
belong in the commit.

Run `make hook`, `make test`, and `make testint`. Confirm the diff against `origin/master`
contains exactly those three files. Commit, push, and open the release pull request. Its body names
the old and new versions, level, the single bullet driving the level and matching rule, the level
not taken and why, changelog edits, verification, and that tagging happens separately. Stop.

## Tag

After the maintainer merges, update local `master` by fast-forward and verify its head is the
release commit. Require the project version to equal the top dated changelog section, and verify the
tag is absent locally and remotely.

Find the `master` workflow run for the exact head SHA and wait for it to succeed. The tag workflow
does not rerun the tox matrix and refuses publication without that green run.

Ask explicitly for authorization to tag the named version on `master` and push it, explaining that
this publishes to PyPI irreversibly. On approval, run `make release`. Confirm a tag-ref workflow
appears and watch publication to completion. Report the tag and workflow URL.

If a tag workflow failed before publication because the matching `master` run was unavailable,
wait for the green run and rerun the failed job; never retag. If the tag already exists, inspect the
existing run. Any failure after publication spends the version and requires a new release.
