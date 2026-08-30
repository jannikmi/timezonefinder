#!/bin/bash
# Download the latest timezone-boundary-builder release, regenerate the packaged
# binary data and prepare a release of the data distribution (version + release note).
# Non-interactive: all behavior is controlled via command line flags (CI-ready).
set -euo pipefail

WORKING_FOLDER_NAME=tmp
DOWNLOADED_TAG_PATH=./$WORKING_FOLDER_NAME/downloaded_tag.txt
# Staged next to the tag and installed with it, once the parse has succeeded.
DATA_SOURCE_PATH=./$WORKING_FOLDER_NAME/data_source.txt
JSON_PREFIX=combined
JSON_SUFFIX=.json
# the tagged release asset, not `releases/latest/download/...`: see the tag resolution below
URL_PREFIX=https://github.com/evansiroky/timezone-boundary-builder/releases/download
URL_SUFFIX=.geojson.zip
DATA_PACKAGE=timezonefinder-data
DATA_REPO_URL=https://github.com/evansiroky/timezone-boundary-builder

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --dataset=full             use the original full dataset (default)
  --dataset=same-since-now   use the reduced "timezones-now" dataset, merging
                             timezones with identical behavior from now on
  --with-oceans              include ocean timezones (Etc/GMT+-XX)
  --rm-tmp                   delete the temporary data folder ($WORKING_FOLDER_NAME) at the end
  -h, --help                 show this help message and exit
EOF
}

DATASET_SUFFIX=""
INTERFIX=""
RM_TMP=0

for arg in "$@"; do
    case $arg in
    --dataset=full) DATASET_SUFFIX="" ;;
    --dataset=same-since-now) DATASET_SUFFIX=-now ;;
    --with-oceans) INTERFIX=-with-oceans ;;
    --rm-tmp) RM_TMP=1 ;;
    -h | --help)
        usage
        exit 0
        ;;
    *)
        echo "ERROR: unknown option '$arg'" >&2
        usage >&2
        exit 1
        ;;
    esac
done

echo "TIME ZONE DATA UPDATE SCRIPT"

# make script work independent of where you invoke it from
parent_path=$(
    cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
    pwd -P
)
cd "$parent_path" || exit 1
mkdir -p "$WORKING_FOLDER_NAME" # if does not exist

# Resolve the release tag first: everything downstream is named after it. Asking the
# API which release is "latest" and fetching `releases/latest/download/...` were two
# independent questions, so a release landing between them attributed one release's
# data to the other - permanently, and with nothing able to notice afterwards. One
# answer now governs the download URL, the file names and DATA_VERSION alike.
echo "RESOLVING THE LATEST RELEASE..."
DOWNLOADED_TAG=$(uv run python -m scripts.upstream_release resolve-tag)
if [ -z "$DOWNLOADED_TAG" ]; then
    echo "ERROR: could not determine the latest timezone-boundary-builder release." >&2
    echo "Without it the data cannot be attributed to a release, so nothing is parsed." >&2
    exit 1
fi
echo "latest release: $DOWNLOADED_TAG"
echo "$DOWNLOADED_TAG" >"$DOWNLOADED_TAG_PATH"

# Both artefacts carry the release *and* the dataset variant: a leftover file from
# another release (or another variant) must not satisfy the "already downloaded"
# checks below and be parsed in place of what was asked for.
VARIANT=$INTERFIX$DATASET_SUFFIX
ASSET_NAME=timezones$VARIANT$URL_SUFFIX
ZIP_ARCHIVE_PATH=./$WORKING_FOLDER_NAME/data_downloaded$VARIANT-$DOWNLOADED_TAG.zip
UNPACKED_PATH=./$WORKING_FOLDER_NAME/$JSON_PREFIX$VARIANT$JSON_SUFFIX
JSON_PATH=./$WORKING_FOLDER_NAME/$JSON_PREFIX$VARIANT-$DOWNLOADED_TAG$JSON_SUFFIX

# Nothing needs downloading when a previous run left either artefact behind - but the
# archive is the only one of the two that *can* be checked, since the unpacked JSON
# carries no digest of its own.
if [ ! -f "$ZIP_ARCHIVE_PATH" ] && [ ! -f "$JSON_PATH" ]; then
    URL=$URL_PREFIX/$DOWNLOADED_TAG/$ASSET_NAME
    echo "DOWNLOADING $URL"

    # install command mac:
    # brew install wget
    wget -O "$ZIP_ARCHIVE_PATH" "$URL" --tries=3
fi

# Whatever produced the archive - this run's download, or a leftover from an
# interrupted one, or a run that already unpacked it - nothing below can tell a
# truncated or replaced file from a good one, and what this script produces is merged
# and published unattended. So the bytes are checked against the size and SHA-256 the
# release API publishes before anything reads them, on every run rather than only on
# the one that downloaded them: re-hashing 55 MB costs a fraction of a second, and
# skipping it is how an archive corrupted after its first run gets parsed anyway.
if [ -f "$ZIP_ARCHIVE_PATH" ]; then
    echo "VERIFYING THE DOWNLOAD..."
    if ! uv run python -m scripts.upstream_release verify \
        --tag "$DOWNLOADED_TAG" \
        --asset "$ASSET_NAME" \
        --archive "$ZIP_ARCHIVE_PATH" \
        --stage "$DATA_SOURCE_PATH"; then
        echo "the downloaded archive is not what $DOWNLOADED_TAG published!" >&2
        exit 1
    fi
else
    # The JSON outlived the archive it came out of, or was put here by hand. Either
    # way nothing states what those bytes are, and this script's output is released
    # without a human reading it. Parsing data of your own is supported - through
    # file_converter, which claims no release for what it is given.
    echo "ERROR: $JSON_PATH exists but $ZIP_ARCHIVE_PATH does not, so nothing can" >&2
    echo "establish what it holds, and an unattended release must not parse it." >&2
    echo "Delete the JSON to re-download and verify $DOWNLOADED_TAG, or parse it" >&2
    echo "deliberately: uv run python -m scripts.file_converter -inp $JSON_PATH" >&2
    exit 1
fi

if [ -f "$JSON_PATH" ]; then
    echo "skip unpacking: $JSON_PATH already exists."
else
    echo "UNPACKING..."
    unzip -o "$ZIP_ARCHIVE_PATH" -d $WORKING_FOLDER_NAME
    # The archive unpacks under a name that says nothing about where it came from, and
    # this is the last point at which anything knows. The converter reads the release
    # back off this name and refuses an upstream file that lacks it.
    mv "$UNPACKED_PATH" "$JSON_PATH"
fi

echo "START PARSING..."
echo "calling scripts.file_converter:"
# no --data-version: $JSON_PATH carries the release, and the parse reads it there
if ! uv run python -m scripts.file_converter -inp "$JSON_PATH"; then
    echo "file_converter failed!"
    exit 1
fi

# update DATA_VERSION to the release just parsed
# (checked weekly against upstream by .github/workflows/check_data_updates.yml).
# The packaged stamp the runtime reads (AbstractTimezoneFinder.data_version) needs
# no second copy here: the parse above already wrote it from the same tag.
cp "$DOWNLOADED_TAG_PATH" DATA_VERSION
echo "DATA_VERSION set to $(cat DATA_VERSION)"

# ... and the archive those bytes came from, installed here rather than where it was
# verified so that the two stamps advance together: a run that fails between the two
# would otherwise leave DATA_SOURCE describing a release the packaged data is not.
cp "$DATA_SOURCE_PATH" DATA_SOURCE
echo "DATA_SOURCE records $(grep '^sha256' DATA_SOURCE)"

# the committed benchmark fixtures (tests/fixtures/benchmarks/) are pinned to
# DATA_VERSION (see tests/auxiliaries.py's BenchmarkFixtureError) and derived
# from the boundary data just regenerated above (on-land/shortcut
# classification, pip_inputs polygon ids) - they must be regenerated together
# or the benchmark fixture tests fail after this data update
echo "REGENERATING BENCHMARK FIXTURES..."
if ! uv run python -m scripts.generate_benchmark_fixtures; then
    echo "generate_benchmark_fixtures failed!"
    exit 1
fi

# docs/benchmark_results_*.rst are measured over the benchmark fixtures and
# the binary data, both of which were just replaced above, so they are now
# stale. (Regenerating the fixtures alone is enough to stale them - the rule
# is fixtures-changed, not DATA_VERSION-changed.) Only regenerate them
# here, after DATA_VERSION and the fixtures are back in sync (running the
# pytest-benchmark suite earlier, e.g. from scripts/file_converter.py itself,
# would either reject the mismatched fixtures with BenchmarkFixtureError or -
# worse - silently benchmark the new data against fixtures pinned to the old
# DATA_VERSION)
echo "REGENERATING PERFORMANCE REPORTS..."
if ! make reports; then
    echo "make reports failed!"
    exit 1
fi

# A data update releases the *data* distribution and nothing else: no version of
# `timezonefinder` changes, and the root CHANGELOG.rst is not touched.
# The version follows from the release just parsed rather than from a bump - it states
# which upstream release this is, prefixed by the data format generation.
DATA_TAG=$(cat DATA_VERSION)
NEW_VERSION=$(uv run python -m scripts.data_releases derive-version --data-tag "$DATA_TAG")
uv version --package "$DATA_PACKAGE" "$NEW_VERSION"

# record it in the data package's own README, which is its PyPI long description
RELEASE_DATE=$(date +%Y-%m-%d)
uv run python -m scripts.data_releases insert-data-release \
    --version "$NEW_VERSION" \
    --date "$RELEASE_DATE" \
    --data-tag "$DATA_TAG" \
    --data-repo-url "$DATA_REPO_URL"
echo "recorded the data release $NEW_VERSION ($RELEASE_DATE)"

if [ "$RM_TMP" -eq 1 ]; then
    echo "deleting temporary data files..."
    rm -r "$WORKING_FOLDER_NAME"
fi

echo "SUCCESS! $DATA_PACKAGE $NEW_VERSION can now be released (tag data-v$NEW_VERSION)!"
