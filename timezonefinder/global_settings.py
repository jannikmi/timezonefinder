from __future__ import absolute_import, division, print_function, unicode_literals

INPUT_JSON_FILE_NAME = 'combined.json'

DEBUG = False

# in debugging mode parse only some polygons
DEBUG_POLY_STOP = 20

# no "magic numbers" import all as "constants" from this global settings file
# ATTENTION: Don't change these settings or timezonefinder wont work!
# different setups of shortcuts are not supported, because then addresses in the .bin
# need to be calculated depending on how many shortcuts are being used.
# number of shortcuts per longitude
NR_SHORTCUTS_PER_LNG = 1
# shortcuts per latitude
NR_SHORTCUTS_PER_LAT = 2

INVALID_ZONE_ID = 65535  # highest possible with H (2 byte integer)

# B = unsigned char (1byte = 8bit Integer)
NR_BYTES_B = 1
# H = unsigned short (2 byte integer)
NR_BYTES_H = 2
# I = unsigned 4byte integer
# i = signed 4byte integer
NR_BYTES_I = 4

# the maximum possible distance is half the perimeter of earth pi * 12743km = 40,054.xxx km
MAX_HAVERSINE_DISTANCE = 40100
