# -*- coding:utf-8 -*-
from setuptools import setup

PACKAGE_NAME = "timezonefinder"

# DATA FILES
# BINARY
BINARY_FILE_ENDING = ".bin"

POLY_ZONE_IDS = "poly_zone_ids"
POLY_COORD_AMOUNT = "poly_coord_amount"
POLY_ADR2DATA = "poly_adr2data"
POLY_MAX_VALUES = "poly_max_values"
POLY_DATA = "poly_data"
POLY_NR2ZONE_ID = "poly_nr2zone_id"

HOLE_COORD_AMOUNT = "hole_coord_amount"
HOLE_ADR2DATA = "hole_adr2data"
HOLE_DATA = "hole_data"

SHORTCUTS_ENTRY_AMOUNT = "shortcuts_entry_amount"
SHORTCUTS_ADR2DATA = "shortcuts_adr2data"
SHORTCUTS_DATA = "shortcuts_data"
SHORTCUTS_UNIQUE_ID = "shortcuts_unique_id"

BINARY_DATA_ATTRIBUTES = [
    POLY_ZONE_IDS,
    POLY_COORD_AMOUNT,
    POLY_ADR2DATA,
    POLY_MAX_VALUES,
    POLY_DATA,
    POLY_NR2ZONE_ID,
    HOLE_COORD_AMOUNT,
    HOLE_ADR2DATA,
    HOLE_DATA,
    SHORTCUTS_ENTRY_AMOUNT,
    SHORTCUTS_ADR2DATA,
    SHORTCUTS_DATA,
    SHORTCUTS_UNIQUE_ID,
]

SHORTCUTS_DIRECT_ID = "shortcuts_direct_id"  # for TimezoneFinderL only

# JSON
JSON_FILE_ENDING = ".json"
TIMEZONE_NAMES = "timezone_names"
HOLE_REGISTRY = "hole_registry"
JSON_DATA_ATTRIBUTES = [TIMEZONE_NAMES]
TIMEZONE_NAMES_FILE = TIMEZONE_NAMES + JSON_FILE_ENDING
HOLE_REGISTRY_FILE = HOLE_REGISTRY + JSON_FILE_ENDING

DATA_ATTRIBUTE_NAMES = BINARY_DATA_ATTRIBUTES + [HOLE_REGISTRY]

# all data files that should be included in the build:
ALL_BINARY_FILES = [
    specifier + BINARY_FILE_ENDING for specifier in BINARY_DATA_ATTRIBUTES
] + [SHORTCUTS_DIRECT_ID + BINARY_FILE_ENDING]
ALL_JSON_FILES = [TIMEZONE_NAMES_FILE, HOLE_REGISTRY_FILE]
PACKAGE_DATA_FILES = ALL_BINARY_FILES + ALL_JSON_FILES

setup(
    name=PACKAGE_NAME,
    packages=[PACKAGE_NAME],
    package_data={PACKAGE_NAME: PACKAGE_DATA_FILES},
    include_package_data=True,
    description="fast python package for finding the timezone of any point on earth (coordinates) offline",
    # version: in VERSION file https://packaging.python.org/guides/single-sourcing-package-version/
    # With this approach you must make sure that the VERSION file is included in all your source
    # and binary distributions (e.g. add include VERSION to your MANIFEST.in).
    author="Jannik Michelfeit",
    author_email="python@michelfe.it",
    license="MIT licence",
    url=f"https://github.com/jannikmi/{PACKAGE_NAME}",  # use the URL to the github repo
    project_urls={
        "Source Code": f"https://github.com/jannikmi/{PACKAGE_NAME}",
        "Documentation": f"https://{PACKAGE_NAME}.readthedocs.io/en/latest/",
        "Changelog": f"https://github.com/jannikmi/{PACKAGE_NAME}/blob/master/CHANGELOG.rst",
        "License": f"https://github.com/jannikmi/{PACKAGE_NAME}/blob/master/LICENSE",
    },
    keywords="timezone coordinates latitude longitude location pytzwhere tzwhere",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Localization",
    ],
    install_requires=["numpy>=1.16"],
    python_requires=">=3.6",
    # TODO http://peak.telecommunity.com/DevCenter/setuptools#setting-the-zip-safe-flag
    #  safe if the project uses pkg_resources for all its data file access
    # http://peak.telecommunity.com/DevCenter/setuptools#accessing-data-files-at-runtime
    #  not possible, because the location of bin files can be specified! -> path has to be variable!
    zip_safe=False,
    extras_require={"numba": ["numba>=0.48"]},
    entry_points={
        "console_scripts": ["timezonefinder=timezonefinder.command_line:main"],
    },
)
