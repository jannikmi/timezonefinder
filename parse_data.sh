#!/bin/bash

WORKING_FOLDER_NAME=tmp
ARCHIVE_NAME=data_downloaded.zip
ZIP_ARCHIVE_PATH=./$WORKING_FOLDER_NAME/$ARCHIVE_NAME
DOWNLOADED_TAG_PATH=./$WORKING_FOLDER_NAME/downloaded_tag.txt
RELEASE_API_URL=https://api.github.com/repos/evansiroky/timezone-boundary-builder/releases/latest
JSON_PREFIX=combined
JSON_SUFFIX=.json
URL_PREFIX=https://github.com/evansiroky/timezone-boundary-builder/releases/latest/download/timezones
URL_SUFFIX=.geojson.zip

echo "TIME ZONE DATA PARSING SCRIPT"

# make script work independent of where you invoke it from
parent_path=$(
    cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
    pwd -P
)
cd "$parent_path" || exit 1
mkdir -p "$WORKING_FOLDER_NAME" # if does not exist

echo "Which dataset version to download?"
echo "1) Original full dataset"
echo "2) Reduced timezones-now dataset"
read -r DATASET_CHOICE

if [ "$DATASET_CHOICE" -eq 2 ]; then
    DATASET_SUFFIX=-now
else
    DATASET_SUFFIX=""
fi

echo "use timezone data with oceans (0: No, 1: Yes)? "
read -r WITH_OCEANS
if [ "$WITH_OCEANS" -eq 1 ]; then
    INTERFIX=-with-oceans
else
    INTERFIX=""
fi
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

# patch version bump
uv version --bump patch

# TODO
 read -r -p "should all temporary data files be deleted (0: No, 1: Yes)?" do_deletion
 if [ "$do_deletion" -eq 1 ]; then
    rm -r "$WORKING_FOLDER_NAME"
fi

# TODO add changelog entry: keep title, current date, parse data version
# $(uv version) (2022-12-06)
#------------------
#
#* updated the data to `2022g <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2022g>`__.
#echo -e "DATA-Line-1\n$(cat input)" > input

echo "SUCCESS! the new package version $(uv version) can now be released!"
