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

# here is the output of the script i got:

# ./test_musllinux_wheel.sh dist/timezonefinder-6.5.5-cp312-cp312-musllinux_1_2_x86_64.whl
# fetch https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64/APKINDEX.tar.gz
# fetch https://dl-cdn.alpinelinux.org/alpine/v3.20/community/x86_64/APKINDEX.tar.gz
# (1/25) Installing libbz2 (1.0.8-r6)
# (2/25) Installing libexpat (2.6.4-r0)
# (3/25) Installing libffi (3.4.6-r0)
# (4/25) Installing gdbm (1.23-r1)
# (5/25) Installing xz-libs (5.6.2-r0)
# (6/25) Installing libgcc (13.2.1_git20240309-r0)
# (7/25) Installing libstdc++ (13.2.1_git20240309-r0)
# (8/25) Installing mpdecimal (4.0.0-r0)
# (9/25) Installing ncurses-terminfo-base (6.4_p20240420-r2)
# (10/25) Installing libncursesw (6.4_p20240420-r2)
# (11/25) Installing libpanelw (6.4_p20240420-r2)
# (12/25) Installing readline (8.2.10-r0)
# (13/25) Installing sqlite-libs (3.45.3-r1)
# (14/25) Installing python3 (3.12.7-r0)
# (15/25) Installing python3-pycache-pyc0 (3.12.7-r0)
# (16/25) Installing pyc (3.12.7-r0)
# (17/25) Installing py3-setuptools-pyc (70.3.0-r0)
# (18/25) Installing py3-pip-pyc (24.0-r2)
# (19/25) Installing py3-parsing (3.1.2-r1)
# (20/25) Installing py3-parsing-pyc (3.1.2-r1)
# (21/25) Installing py3-packaging-pyc (24.0-r1)
# (22/25) Installing python3-pyc (3.12.7-r0)
# (23/25) Installing py3-packaging (24.0-r1)
# (24/25) Installing py3-setuptools (70.3.0-r0)
# (25/25) Installing py3-pip (24.0-r2)
# Executing busybox-1.36.1-r29.trigger
# OK: 75 MiB in 39 packages
# Processing /wheels/timezonefinder-6.5.5-cp312-cp312-musllinux_1_2_x86_64.whl
# Collecting cffi<2,>=1.15.1 (from timezonefinder==6.5.5)
#   Downloading cffi-1.17.1-cp312-cp312-musllinux_1_1_x86_64.whl.metadata (1.5 kB)
# Collecting h3>4 (from timezonefinder==6.5.5)
#   Downloading h3-4.1.2-cp312-cp312-musllinux_1_2_x86_64.whl.metadata (18 kB)
# Collecting numpy<3,>=1.23 (from timezonefinder==6.5.5)
#   Downloading numpy-2.1.3-cp312-cp312-musllinux_1_1_x86_64.whl.metadata (62 kB)
#      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 62.0/62.0 kB 2.4 MB/s eta 0:00:00
# Collecting pycparser (from cffi<2,>=1.15.1->timezonefinder==6.5.5)
#   Downloading pycparser-2.22-py3-none-any.whl.metadata (943 bytes)
# Downloading cffi-1.17.1-cp312-cp312-musllinux_1_1_x86_64.whl (488 kB)
#    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 488.7/488.7 kB 9.6 MB/s eta 0:00:00
# Downloading h3-4.1.2-cp312-cp312-musllinux_1_2_x86_64.whl (1.0 MB)
#    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 21.3 MB/s eta 0:00:00
# Downloading numpy-2.1.3-cp312-cp312-musllinux_1_1_x86_64.whl (16.4 MB)
#    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 16.4/16.4 MB 21.6 MB/s eta 0:00:00
# Downloading pycparser-2.22-py3-none-any.whl (117 kB)
#    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 117.6/117.6 kB 7.8 MB/s eta 0:00:00
# Installing collected packages: pycparser, numpy, h3, cffi, timezonefinder
# Successfully installed cffi-1.17.1 h3-4.1.2 numpy-2.1.3 pycparser-2.22 timezonefinder-6.5.5
# WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv
# Europe/Berlin
