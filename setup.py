# -*- coding:utf-8 -*-
from setuptools import setup

PACKAGE_NAME = "timezonefinder"

setup(
    name=PACKAGE_NAME,
    packages=[PACKAGE_NAME],
    # NOTE: package_data is not required. all data files should be included via MANIFEST.in
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
    install_requires=["numpy>=1.20.3", "h3>=3.7.3"],
    python_requires=">=3.7",
    # TODO http://peak.telecommunity.com/DevCenter/setuptools#setting-the-zip-safe-flag
    #  safe if the project uses pkg_resources for all its data file access
    # http://peak.telecommunity.com/DevCenter/setuptools#accessing-data-files-at-runtime
    #  not possible, because the location of bin files can be specified! -> path has to be variable!
    zip_safe=False,
    extras_require={"numba": ["numba>=0.54.1"]},
    entry_points={
        "console_scripts": ["timezonefinder=timezonefinder.command_line:main"],
    },
)
