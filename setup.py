# -*- coding:utf-8 -*-

import os
import re

from setuptools import setup


def get_version(package):
    """
    Return package version as listed in `__version__` in `__init__.py`.
    """
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)

version = get_version('timezonefinder')

with open('README.rst') as f:
    readme = f.read()

with open('CHANGELOG.rst') as changelog_file:
    changelog = changelog_file.read()

setup(
    name='timezonefinder',
    version=version,
    packages=['timezonefinder'],
    package_data={'timezonefinder': ['timezone_data.bin']},
    description='Python library to look up timezone from lat / long offline. Improved version of "pytzwhere".',
    author='J. Michelfeit',
    author_email='python@michelfe.it',
    license='MIT licence',
    url='https://github.com/MrMinimal64/timezonefinder',  # use the URL to the github repo
    keywords='timezone coordinates latitude longitude location pytzwhere tzwhere',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Localization',
    ],
    long_description=readme + '\n\n' + changelog,
    install_requires=[
        'numpy',
    ],
)
