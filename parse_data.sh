#!/bin/bash

WORKING_FOLDER_NAME=tmp_data_downloaded
ARCHIVE_NAME=data_downloaded.zip
ARCHIVE_PATH=./$WORKING_FOLDER_NAME/$ARCHIVE_NAME
DATA_FILE_NAME=combined.json
ZIP_SOURCE_PATH=./$WORKING_FOLDER_NAME/dist/$DATA_FILE_NAME
SOURCE_PREFIX=https://github.com/evansiroky/timezone-boundary-builder/releases/latest/download/timezones
SOURCE_SUFFIX=.geojson.zip

echo "TIME ZONE DATA PARSING SCRIPT"

# make script work independent of where you invoke it from
parent_path=$(
    cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
    pwd -P
)
cd "$parent_path" || exit 1

if [ -f $ZIP_SOURCE_PATH ]; then
    echo "skip unpacking: $ZIP_SOURCE_PATH already exists."
else
    if [ -f $ARCHIVE_PATH ]; then
        echo "skipping download: $ARCHIVE_PATH already exists."
    else
        echo "DOWNLOAD..."
        read -r -p "download time zone data with oceans (0: No, 1: Yes)? " with_oceans
        if [ "$with_oceans" -eq 1 ]; then
            SOURCE_INTERFIX=-with-oceans
        else
            SOURCE_INTERFIX=""
        fi
        SOURCE=$SOURCE_PREFIX$SOURCE_INTERFIX$SOURCE_SUFFIX
        # install command mac:
        # brew install wget
        wget -O $ARCHIVE_PATH $SOURCE --tries=3
    fi
    echo "UNPACKING..."
    unzip $ARCHIVE_PATH -d $WORKING_FOLDER_NAME
fi

echo "START PARSING..."
SCRIPT_PATH=./timezonefinder/file_converter.py
echo "calling $SCRIPT_PATH:"
python "$SCRIPT_PATH" -inp "$ZIP_SOURCE_PATH"
echo "...PARSING DONE."

# TODO
#read -r -p "should all temporary data files be deleted (0: No, 1: Yes)?" do_deletion
#if [ "$do_deletion" -eq 1 ]; then
#    rm -r "$WORKING_FOLDER_NAME"
#fi
