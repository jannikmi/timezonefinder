# -*- coding:utf-8 -*-
# NOTE: Changes in the global settings might not immediately affect
# the precompiled (and cached) functions in helpers_numba.py!

PACKAGE_NAME = 'timezonefinder'
# TODO
DATA_PACKAGE_NAME = 'timezonefinder_data'
OCEAN_DATA_PACKAGE_NAME = 'timezonefinder_data_oceans'
# TODO
# DEBUG = False
DEBUG = True
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

BINARY_FILE_ENDING = '.bin'

# LOCAL DATA FILES
DIRECT_SHORTCUT_NAME = 'shortcuts_direct_id'
UNIQUE_SHORTCUT_NAME = 'shortcuts_unique_id'  # TODO from external?!
DATA_ATTRIBUTES_LOCAL = [UNIQUE_SHORTCUT_NAME, DIRECT_SHORTCUT_NAME]
BIN_FILES_LOCAL = [specifier + BINARY_FILE_ENDING for specifier in DATA_ATTRIBUTES_LOCAL]
TIMEZONE_NAMES_FILE = 'timezone_names.json'
DATA_FILES_LOCAL = BIN_FILES_LOCAL + [TIMEZONE_NAMES_FILE]

# EXTERNAL DATA FILES
# loaded from the # TODO external data packages
POLY_ZONE_IDS = 'poly_zone_ids'
POLY_COORD_AMOUNT = 'poly_coord_amount'
POLY_ADR_DATA = 'poly_adr2data'
POLY_MAX_VALUE = 'poly_max_values'
POLY_DATA = 'poly_data'
POLY_NR_ZONE_ID = 'poly_nr2zone_id'
HOLE_POLY_IDS = 'hole_poly_ids'
HOLE_COORD_AMOUNT = 'hole_coord_amount'
HOLE_ADR_DATA = 'hole_adr2data'
HOLE_DATA = 'hole_data'
SHORTCUTS_ENTRY_AMOUNT = 'shortcuts_entry_amount'
SHORTCUTS_ADR_DATA = 'shortcuts_adr2data'
SHORTCUTS_DATA = 'shortcuts_data'
DATA_ATTRIBUTES_EXTERNAL = [
    POLY_ZONE_IDS,
    POLY_COORD_AMOUNT,
    POLY_ADR_DATA,
    POLY_MAX_VALUE,
    POLY_DATA,
    POLY_NR_ZONE_ID,
    HOLE_POLY_IDS,
    HOLE_COORD_AMOUNT,
    HOLE_ADR_DATA,
    HOLE_DATA,
    SHORTCUTS_ENTRY_AMOUNT,
    SHORTCUTS_ADR_DATA,
    SHORTCUTS_DATA,
]
DATA_ATTRIBUTES = DATA_ATTRIBUTES_LOCAL + DATA_ATTRIBUTES_EXTERNAL
BIN_FILES_EXTERNAL = [specifier + BINARY_FILE_ENDING for specifier in DATA_ATTRIBUTES]
DATA_FILES_LOCAL = DATA_FILES_LOCAL + BIN_FILES_EXTERNAL  # TODO split up (change). needed in setup of data packages!

# B = unsigned char (1byte = 8bit Integer)
NR_BYTES_B = 1
DTYPE_FORMAT_B_NUMPY = '<i1'

# H = unsigned short (2 byte integer)
NR_BYTES_H = 2
DTYPE_FORMAT_H = b'<H'
DTYPE_FORMAT_H_NUMPY = '<u2'
THRES_DTYPE_H = 2 ** (NR_BYTES_H * 8)  # = 65536

# value to write for representing an invalid zone (e.g. no shortcut polygon)
# = 65535 = highest possible value with H (2 byte unsigned integer)
INVALID_VALUE_DTYPE_H = THRES_DTYPE_H - 1

# i = signed 4byte integer
NR_BYTES_I = 4
DTYPE_FORMAT_SIGNED_I_NUMPY = '<i4'

# I = unsigned 4byte integer
DTYPE_FORMAT_I = b'<I'
THRES_DTYPE_I = 2 ** (NR_BYTES_I * 8)

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
