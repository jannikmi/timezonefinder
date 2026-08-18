#!/bin/bash
# Download the latest timezone-boundary-builder release, regenerate the packaged
# binary data and prepare a release (version bump + changelog entry).
# Non-interactive: all behavior is controlled via command line flags (CI-ready).
set -euo pipefail

WORKING_FOLDER_NAME=tmp
ARCHIVE_NAME=data_downloaded.zip
ZIP_ARCHIVE_PATH=./$WORKING_FOLDER_NAME/$ARCHIVE_NAME
DOWNLOADED_TAG_PATH=./$WORKING_FOLDER_NAME/downloaded_tag.txt
RELEASE_API_URL=https://api.github.com/repos/evansiroky/timezone-boundary-builder/releases/latest
JSON_PREFIX=combined
JSON_SUFFIX=.json
URL_PREFIX=https://github.com/evansiroky/timezone-boundary-builder/releases/latest/download/timezones
URL_SUFFIX=.geojson.zip
CHANGELOG_PATH=CHANGELOG.rst
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

JSON_FILE_NAME=$JSON_PREFIX$INTERFIX$DATASET_SUFFIX$JSON_SUFFIX
JSON_PATH=./$WORKING_FOLDER_NAME/$JSON_FILE_NAME

if [ -f $JSON_PATH ]; then
    echo "skip unpacking: $JSON_PATH already exists."
else
    if [ -f $ZIP_ARCHIVE_PATH ]; then
        echo "skipping download: $ZIP_ARCHIVE_PATH already exists."
    else
        URL=$URL_PREFIX$INTERFIX$DATASET_SUFFIX$URL_SUFFIX
        echo "DOWNLOADING $URL"

        # install command mac:
        # brew install wget
        wget -O $ZIP_ARCHIVE_PATH $URL --tries=3

        # record which release tag the "latest" download URL resolved to,
        # so DATA_VERSION can be updated after a successful parse
        curl -sL $RELEASE_API_URL | grep '"tag_name"' | cut -d'"' -f4 >"$DOWNLOADED_TAG_PATH"
        echo "downloaded data release: $(cat "$DOWNLOADED_TAG_PATH")"
    fi
    echo "UNPACKING..."
    unzip $ZIP_ARCHIVE_PATH -d $WORKING_FOLDER_NAME
fi

# hand the parse the release tag recorded at download time: DATA_VERSION still
# names the *previous* one until the parse has succeeded, so it is the only thing
# here that knows which release the data being written comes from. Empty when the
# download was skipped, which leaves the converter to fall back to DATA_VERSION.
DOWNLOADED_TAG=""
if [ -s "$DOWNLOADED_TAG_PATH" ]; then
    DOWNLOADED_TAG=$(cat "$DOWNLOADED_TAG_PATH")
fi

PARSE_ARGS=(-inp "$JSON_PATH")
if [ -n "$DOWNLOADED_TAG" ]; then
    PARSE_ARGS+=(--data-version "$DOWNLOADED_TAG")
fi

echo "START PARSING..."
echo "calling scripts.file_converter:"
if ! uv run python -m scripts.file_converter "${PARSE_ARGS[@]}"; then
    echo "file_converter failed!"
    exit 1
fi

# update DATA_VERSION to the release tag recorded at download time
# (checked weekly against upstream by .github/workflows/check_data_updates.yml).
# The packaged stamp the runtime reads (AbstractTimezoneFinder.data_version) needs
# no second copy here: the parse above already wrote it from the same tag.
if [ -n "$DOWNLOADED_TAG" ]; then
    cp "$DOWNLOADED_TAG_PATH" DATA_VERSION
    echo "DATA_VERSION set to $(cat DATA_VERSION)"
else
    echo "WARNING: downloaded release tag unknown, DATA_VERSION not updated"
fi

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

# patch version bump (data-only releases are patch releases)
uv version --bump patch
NEW_VERSION=$(uv version --short)

# insert the data release below the unreleased section. The release workflow
# separately refuses to merge while that section contains pending work.
DATA_TAG=$(cat DATA_VERSION)
RELEASE_DATE=$(date +%Y-%m-%d)
uv run python -m scripts.changelog insert-data-release "$CHANGELOG_PATH" \
    --version "$NEW_VERSION" \
    --date "$RELEASE_DATE" \
    --data-tag "$DATA_TAG" \
    --data-repo-url "$DATA_REPO_URL"
echo "added $CHANGELOG_PATH entry: $NEW_VERSION ($RELEASE_DATE)"

if [ "$RM_TMP" -eq 1 ]; then
    echo "deleting temporary data files..."
    rm -r "$WORKING_FOLDER_NAME"
fi

echo "SUCCESS! the new package version $NEW_VERSION can now be released!"
