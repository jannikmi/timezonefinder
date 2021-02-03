==============
timezonefinder
==============

.. image:: https://api.travis-ci.org/jannikmi/timezonefinder.svg?branch=master
    :target: https://travis-ci.org/jannikmi/timezonefinder

.. image:: https://readthedocs.org/projects/timezonefinder/badge/?version=latest
    :alt: documentation status
    :target: https://timezonefinder.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/circleci/project/github/conda-forge/timezonefinder-feedstock/master.svg?label=noarch
    :target: https://circleci.com/gh/conda-forge/timezonefinder-feedstock

.. image:: https://img.shields.io/pypi/wheel/timezonefinder.svg
    :target: https://pypi.python.org/pypi/timezonefinder

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit

.. image:: https://pepy.tech/badge/timezonefinder
    :alt: total PyPI downloads
    :target: https://pepy.tech/project/timezonefinder

.. image:: https://img.shields.io/pypi/v/timezonefinder.svg
    :alt: latest version on PyPI
    :target: https://pypi.python.org/pypi/timezonefinder

.. image:: https://anaconda.org/conda-forge/timezonefinder/badges/version.svg
    :alt: latest version on Conda
    :target: https://anaconda.org/conda-forge/timezonefinder

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black



This is a fast and lightweight python package for looking up the corresponding
timezone for given coordinates on earth entirely offline.


Quick Guide:

::

    pip install timezonefinder[numba] # also installs numba -> x100 speedup


.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()
    latitude, longitude = 52.5061, 13.358
    tf.timezone_at(lng=longitude, lat=latitude)  # returns 'Europe/Berlin'


For more refer to the `Documentation <https://timezonefinder.readthedocs.io/en/latest/>`__.

Also check:

`PyPI <https://pypi.python.org/pypi/timezonefinder/>`__

`online GUI and API <https://timezonefinder.michelfe.it>`__

`conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__

ruby port: `timezone_finder <https://github.com/gunyarakun/timezone_finder>`__

`download stats <https://pepy.tech/project/timezonefinder>`__
