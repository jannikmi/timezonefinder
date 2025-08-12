#!/bin/bash

# Script to test a musllinux wheel in an Alpine Linux Docker container

# Check if the wheel file is provided as an argument
if [ $# -eq 0 ]; then
  echo "Usage: $0 /path/to/your/wheel.whl"
  exit 1
fi

# Get the wheel file path from the argument and resolve the absolute path
WHEEL_PATH=$(realpath "$1")

# Ensure the wheel file exists
if [ ! -f "$WHEEL_PATH" ]; then
  echo "Wheel file not found at $WHEEL_PATH"
  exit 1
fi

# Get the wheel file name
WHEEL_FILE="$(basename "$WHEEL_PATH")"

# Run the Alpine Docker container, mounting the wheel's directory
docker run --rm -v "$(dirname "$WHEEL_PATH"):/wheels" alpine:latest sh -c "
  apk add --no-cache python3 py3-pip &&
  pip3 install --break-system-packages /wheels/$WHEEL_FILE &&
  python3 -c 'from timezonefinder import TimezoneFinder; tf = TimezoneFinder(); print(tf.timezone_at(lng=13.41, lat=52.52))'
"
