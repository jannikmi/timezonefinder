==============
timezonefinder
==============


..
    Note: can't include the badges file from the docs here, as it won't render on PyPI -> sync manually

.. image:: https://github.com/jannikmi/timezonefinder/actions/workflows/build.yml/badge.svg?branch=master
    :target: https://github.com/jannikmi/timezonefinder/actions?query=branch%3Amaster

.. image:: https://readthedocs.org/projects/timezonefinder/badge/?version=latest
    :alt: documentation status
    :target: https://timezonefinder.readthedocs.io/en/latest/?badge=latest

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

.. image:: https://img.shields.io/conda/vn/conda-forge/timezonefinder.svg
   :target: https://anaconda.org/conda-forge/timezonefinder
   :alt: latest version on conda-forge

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black




Notice: Looking for maintainers. Reach out if you want to contribute!
---------------------------------------------------------------------


This is a python package for looking up the corresponding timezone for given coordinates on earth entirely offline.


It is recommended to install it together with the optional `Numba <https://numba.pydata.org/>`__ package for increased performance:

Quick Guide:

.. code-block:: console

    pip install timezonefinder[numba]


.. code-block:: python

    from timezonefinder import timezone_at

    tz = timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'


    # For thread safety, increased performance and control, re-use an instance:
    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder(in_memory=True)  # reuse

    query_points = [(13.358, 52.5061), ...]
    for lng, lat in query_points:
        tz = tf.timezone_at(lng=lng, lat=lat)  # 'Europe/Berlin'


Need maximum speed at the cost of accuracy? Check out `tzfpy <https://github.com/ringsaturn/tzfpy>`__ - a fast alternative based on Rust.



For more refer to the `Documentation <https://timezonefinder.readthedocs.io/en/latest/>`__.

Also check:

`PyPI <https://pypi.python.org/pypi/timezonefinder/>`__

`online GUI and API <https://timezonefinder.michelfe.it>`__

`conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__

ruby port: `timezone_finder <https://github.com/gunyarakun/timezone_finder>`__

`download stats <https://pepy.tech/project/timezonefinder>`__


LICENSE
-------

``timezonefinder`` is licensed under the `MIT license <https://github.com/jannikmi/timezonefinder/blob/master/LICENSE>`__.

The data is licensed under the `ODbL license <https://github.com/jannikmi/timezonefinder/blob/master/DATA_LICENSE>`__, following the base dataset from `evansiroky/timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder>`__.
