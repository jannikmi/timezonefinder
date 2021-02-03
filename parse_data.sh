#!/bin/bash

WORKING_FOLDER_NAME=tmp
ARCHIVE_NAME=data_downloaded.zip
ZIP_ARCHIVE_PATH=./$WORKING_FOLDER_NAME/$ARCHIVE_NAME
JSON_PREFIX=combined
JSON_SUFFIX=.json
DESTINATION_PATH=./timezonefinder
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

echo "use timezone data with oceans (0: No, 1: Yes)? "
read -r WITH_OCEANS
if [ "$WITH_OCEANS" -eq 1 ]; then
    INTERFIX=-with-oceans
else
    INTERFIX=""
fi
JSON_FILE_NAME=$JSON_PREFIX$INTERFIX$JSON_SUFFIX
JSON_PATH=./$WORKING_FOLDER_NAME/$JSON_FILE_NAME

if [ -f $JSON_PATH ]; then
    echo "skip unpacking: $JSON_PATH already exists."
else
    if [ -f $ZIP_ARCHIVE_PATH ]; then
        echo "skipping download: $ZIP_ARCHIVE_PATH already exists."
    else
        echo "DOWNLOAD..."


        URL=$URL_PREFIX$INTERFIX$URL_SUFFIX
        # install command mac:
        # brew install wget
        wget -O $ZIP_ARCHIVE_PATH $URL --tries=3
    fi
    echo "UNPACKING..."
    unzip $ZIP_ARCHIVE_PATH -d $WORKING_FOLDER_NAME
fi

echo "START PARSING..."
SCRIPT_PATH=./timezonefinder/file_converter.py
echo "calling $SCRIPT_PATH:"
python "$SCRIPT_PATH" -inp "$JSON_PATH" -out "$DESTINATION_PATH"

# TODO
#read -r -p "should all temporary data files be deleted (0: No, 1: Yes)?" do_deletion
#if [ "$do_deletion" -eq 1 ]; then
#    rm -r "$WORKING_FOLDER_NAME"
#fi
