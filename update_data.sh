#!/bin/bash
# Download the latest timezone-boundary-builder release, regenerate the packaged
# binary data and prepare a release of the data distribution (version + release note).
# Non-interactive: all behavior is controlled via command line flags (CI-ready).
set -euo pipefail

WORKING_FOLDER_NAME=tmp
DOWNLOADED_TAG_PATH=./$WORKING_FOLDER_NAME/downloaded_tag.txt
RELEASE_API_URL=https://api.github.com/repos/evansiroky/timezone-boundary-builder/releases/latest
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
DOWNLOADED_TAG=$(curl -sL --retry 3 $RELEASE_API_URL | grep '"tag_name"' | cut -d'"' -f4)
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
ZIP_ARCHIVE_PATH=./$WORKING_FOLDER_NAME/data_downloaded$VARIANT-$DOWNLOADED_TAG.zip
UNPACKED_PATH=./$WORKING_FOLDER_NAME/$JSON_PREFIX$VARIANT$JSON_SUFFIX
JSON_PATH=./$WORKING_FOLDER_NAME/$JSON_PREFIX$VARIANT-$DOWNLOADED_TAG$JSON_SUFFIX

if [ -f "$JSON_PATH" ]; then
    echo "skip unpacking: $JSON_PATH already exists."
else
    if [ -f "$ZIP_ARCHIVE_PATH" ]; then
        echo "skipping download: $ZIP_ARCHIVE_PATH already exists."
    else
        URL=$URL_PREFIX/$DOWNLOADED_TAG/timezones$VARIANT$URL_SUFFIX
        echo "DOWNLOADING $URL"

        # install command mac:
        # brew install wget
        wget -O "$ZIP_ARCHIVE_PATH" "$URL" --tries=3
    fi
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
# `timezonefinder` changes, and the root CHANGELOG.rst is not touched (issue #446).
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
