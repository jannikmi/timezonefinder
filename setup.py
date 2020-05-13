# -*- coding:utf-8 -*-
from setuptools import setup

from timezonefinder.global_settings import PACKAGE_DATA_FILES, PACKAGE_NAME

setup(
    name=PACKAGE_NAME,
    packages=[PACKAGE_NAME],
    package_data={PACKAGE_NAME: PACKAGE_DATA_FILES},
    description='fast python package for finding the timezone of any point on earth (coordinates) offline',
    # version: in VERSION file https://packaging.python.org/guides/single-sourcing-package-version/
    # With this approach you must make sure that the VERSION file is included in all your source
    # and binary distributions (e.g. add include VERSION to your MANIFEST.in).
    author='J. Michelfeit',
    author_email='python@michelfe.it',
    license='MIT licence',
    url='https://github.com/MrMinimal64/timezonefinder',  # use the URL to the github repo
    project_urls={
        "Source Code": "https://github.com/MrMinimal64/timezonefinder",
        "Documentation": "https://timezonefinder.readthedocs.io/en/latest/",
        "Changelog": "https://github.com/MrMinimal64/timezonefinder/blob/master/CHANGELOG.rst",
        "License": "https://github.com/MrMinimal64/timezonefinder/blob/master/LICENSE",
    },
    keywords='timezone coordinates latitude longitude location pytzwhere tzwhere',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Localization',
    ],
    install_requires=['numpy>=1.16'],
    python_requires='>=3.6',
    # TODO http://peak.telecommunity.com/DevCenter/setuptools#setting-the-zip-safe-flag
    #  if the project uses pkg_resources for all its data file access
    # http://peak.telecommunity.com/DevCenter/setuptools#accessing-data-files-at-runtime
    # zip_safe=False,
    extras_require={'numba': ["numba>=0.48"]},
)
