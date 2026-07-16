#!/bin/bash
# Download the latest timezone-boundary-builder release, regenerate the packaged
# binary data, run the tests and prepare a release (version bump + changelog entry).
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

echo "START PARSING..."
SCRIPT_PATH=./scripts/file_converter.py
echo "calling $SCRIPT_PATH:"
# ensure Python can import the local 'scripts' package
if ! PYTHONPATH=. uv run python "$SCRIPT_PATH" -inp "$JSON_PATH"; then
    echo "file_converter.py failed!"
    exit 1
fi

echo "runnings tests..."
if ! uv run tox; then
    # assert that all tests are passing
    echo "tests failed!"
    exit 1
fi

# update DATA_VERSION to the release tag recorded at download time
# (checked weekly against upstream by .github/workflows/check_data_updates.yml)
if [ -s "$DOWNLOADED_TAG_PATH" ]; then
    cp "$DOWNLOADED_TAG_PATH" DATA_VERSION
    echo "DATA_VERSION set to $(cat DATA_VERSION)"
else
    echo "WARNING: downloaded release tag unknown, DATA_VERSION not updated"
fi

# patch version bump (data-only releases are patch releases)
uv version --bump patch
NEW_VERSION=$(uv version --short)

# prepend a changelog entry for the data update
DATA_TAG=$(cat DATA_VERSION)
ENTRY_TITLE="$NEW_VERSION ($(date +%Y-%m-%d))"
ENTRY_UNDERLINE=$(printf '%*s' "${#ENTRY_TITLE}" '' | tr ' ' '-')
{
    # keep the changelog header (first 3 lines), insert the new entry below it
    head -n 3 "$CHANGELOG_PATH"
    printf '\n\n%s\n%s\n\n' "$ENTRY_TITLE" "$ENTRY_UNDERLINE"
    printf '* updated the data to `%s <%s/releases/tag/%s>`__\n' "$DATA_TAG" "$DATA_REPO_URL" "$DATA_TAG"
    tail -n +4 "$CHANGELOG_PATH"
} >"$CHANGELOG_PATH.new"
mv "$CHANGELOG_PATH.new" "$CHANGELOG_PATH"
echo "added $CHANGELOG_PATH entry: $ENTRY_TITLE"

if [ "$RM_TMP" -eq 1 ]; then
    echo "deleting temporary data files..."
    rm -r "$WORKING_FOLDER_NAME"
fi

echo "SUCCESS! the new package version $NEW_VERSION can now be released!"
