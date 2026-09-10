# Publish the data distribution

Publishes one already-declared `timezonefinder-data` version as a `data-v<version>` tag on `master`, which `publish_data.yml` uploads to PyPI from the wheel `DATA_BUILD_RUN` names.

It runs in exactly one situation: the [code-release workflow](prepare-and-publish-code-release.md)'s first precheck found that the index does not serve the version the checkout requires. Every format change is in that position by construction, since `DATA_FORMAT_VERSION` is the data distribution's major version and the root pins `<N+1`. The data must go out first, or `timezonefinder` is uninstallable for everyone between the two releases. The [data pipeline and release order](../development/data-pipeline-format-versioning-and-release-order.md) carries the rest of the reasoning.

## Hard boundaries

- Never push the tag without explicit authorization naming it in the same session. The upload reaches PyPI, which will not accept that version again.
- Never bump the version, regenerate data, or compile a wheel here. This workflow publishes what `master` already declares; a version bump is a data update and `update_data.sh` owns it.
- Never force-push, delete a published tag, or upload by hand.

## The version

The tag names the *data* distribution's own version, never the root's — a bare version tag releases the code:

```bash
data_version=$(uv version --short --package timezonefinder-data)
```

The base version names the binary format and upstream boundary release. A rebuild from the same upstream release uses the next unused PEP 440 post-release (``.post1``, then ``.post2``); it does not increment the component that encodes the upstream release. Confirm its concise change summary is present in ``packages/timezonefinder-data/README.md`` before tagging.

## Before tagging

Confirm four things, cheapest first: local `master` is fast-forwarded to `origin/master` and reports `$data_version` there; the tag is absent both locally and remotely; the `master` workflow run for that exact head SHA is green; and the run `DATA_BUILD_RUN` names succeeded with an `artifact-data-wheel` that has not expired — the run id is the only reference to it, and an expired artefact is re-made by re-dispatching `compile_data.yml` on the branch and recording the new id:

```bash
git ls-remote --tags origin "data-v$data_version"
gh api repos/<owner>/<repo>/actions/runs/"$(cat DATA_BUILD_RUN)"/artifacts -q '.artifacts[] | "\(.name) expired=\(.expired)"'
```

`publish_data.yml` re-checks the first two from its own end — it refuses a tag whose commit is not on `master`, and one whose name disagrees with the declared version — but only after the tag exists, and a tag pushed in error is the one thing this workflow cannot take back.

## Ask, then publish

Stop and ask the maintainer for authorization, naming `data-v$data_version` and stating that pushing it uploads to PyPI permanently. Keep it short: the version, that the code release about to be prepared requires it while the index does not serve it, and that the preparation waits on the answer. On refusal, stop and say so rather than preparing a release pull request that cannot be tagged.

On approval, tag from the up-to-date `master` in the same annotated form `make release` and `release_data_update.yml` both use, and watch it publish:

```bash
git tag -a "data-v$data_version" -m "Data release $data_version"
git push origin "data-v$data_version"
gh run list --workflow publish_data.yml --limit 1
gh run watch <run-id> --exit-status
```

Then re-run the code-release workflow's index query and confirm it lists `$data_version`. The upload is immediate but the JSON that query reads is cached, so a version still missing right after a green publish is a stale read rather than a failed release — re-ask before concluding anything, and never re-push the tag, which publishes nothing the second time. Report the tag and the workflow URL, then return to *Prepare*.
