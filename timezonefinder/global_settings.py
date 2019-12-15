# -*- coding:utf-8 -*-
# NOTE: Changes in the global settings might not immediately affect
# the precompiled (and cached) functions in helpers_numba.py!

PACKAGE_NAME = 'timezonefinder'
DEBUG = False
INPUT_JSON_FILE_NAME = 'combined.json'

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
NR_LAT_SHORTCUTS = 180 * NR_SHORTCUTS_PER_LAT

INVALID_ZONE_ID = 65535  # highest possible with H (2 byte integer)

TIMEZONE_NAMES_FILE = 'timezone_names.json'
DATA_ATTRIBUTE_NAMES = ['poly_zone_ids',
                        'poly_coord_amount',
                        'poly_adr2data',
                        'poly_max_values',
                        'poly_data',
                        'poly_nr2zone_id',
                        'hole_poly_ids',
                        'hole_coord_amount',
                        'hole_adr2data',
                        'hole_data',
                        'shortcuts_entry_amount',
                        'shortcuts_adr2data',
                        'shortcuts_data',
                        'shortcuts_unique_id']
DATA_FILE_ENDING = '.bin'
BIN_FILE_NAMES = [specifier + DATA_FILE_ENDING for specifier in DATA_ATTRIBUTE_NAMES]
DATA_FILE_NAMES = BIN_FILE_NAMES + [TIMEZONE_NAMES_FILE]

# B = unsigned char (1byte = 8bit Integer)
NR_BYTES_B = 1
DTYPE_FORMAT_B_NUMPY = '<i1'

# H = unsigned short (2 byte integer)
NR_BYTES_H = 2
DTYPE_FORMAT_H = b'<H'
DTYPE_FORMAT_H_NUMPY = '<u2'

# i = signed 4byte integer
NR_BYTES_I = 4
DTYPE_FORMAT_SIGNED_I_NUMPY = '<i4'

# I = unsigned 4byte integer
DTYPE_FORMAT_I = b'<I'

# f = 8byte signed float
DTYPE_FORMAT_F_NUMPY = '<f8'

# IMPORTANT: all values between -180 and 180 degree must fit into the domain of i4!
# is the same as testing if 360 fits into the domain of I4 (unsigned!)
MAX_ALLOWED_COORD_VAL = 2 ** (8 * NR_BYTES_I - 1)

# from math import floor,log10
# DECIMAL_PLACES_SHIFT = floor(log10(MAX_ALLOWED_COORD_VAL/180.0)) # == 7
DECIMAL_PLACES_SHIFT = 7
INT2COORD_FACTOR = 10 ** (-DECIMAL_PLACES_SHIFT)
COORD2INT_FACTOR = 10 ** DECIMAL_PLACES_SHIFT
max_int_val = 180.0 * COORD2INT_FACTOR
assert (max_int_val < MAX_ALLOWED_COORD_VAL)

# the maximum possible distance is half the perimeter of earth pi * 12743km = 40,054.xxx km
MAX_HAVERSINE_DISTANCE = 40100

# TESTS

DECIMAL_PLACES_ACCURACY = 7
