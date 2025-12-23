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




This is a python package providing offline timezone lookups for WGS84 coordinates.
In comparison to other alternatives this package aims at maximum accuracy around timezone borders (no geometry simplifications) while offering fast lookup performance and compatibility with many (Python) runtime environments.
It combines preprocessed polygon data, H3-based spatial shortcuts, and optional acceleration via Numba or a clang-backed point-in-polygon routine.



Notice: Looking for maintainers. Reach out if you want to contribute!
---------------------------------------------------------------------


Quick Guide
-----------

It is recommended to install it together with the optional `Numba <https://numba.pydata.org/>`__ package for increased performance:

.. code-block:: console

    pip install timezonefinder[numba]


.. code-block:: python

    from timezonefinder import timezone_at

    tz = timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Paris'


    # For thread safety, increased performance and control, re-use an instance:
    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder(in_memory=True)  # reuse

    query_points = [(13.358, 52.5061), ...]
    for lng, lat in query_points:
        tz = tf.timezone_at(lng=lng, lat=lat)  # 'Europe/Paris'



**Note:** This library uses the full original timezone dataset with all >440 timezone names, providing full localization capabilities and historical timezone accuracy. For applications that prefer a smaller memory footprint, the reduced "timezones-now" dataset is available via the ``parse_data.sh`` script (cf. `Documentation <https://timezonefinder.readthedocs.io/en/latest/data_format.html#alternative-dataset-options>`__).


**Alternative:** Need maximum speed at the cost of accuracy? Check out `tzfpy <https://github.com/ringsaturn/tzfpy>`__ - a fast and lightweight alternative based on Rust.


References
----------

* `Documentation <https://timezonefinder.readthedocs.io/en/latest/>`__
* `PyPI <https://pypi.python.org/pypi/timezonefinder/>`__
* `conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__
* `download stats <https://pepy.tech/project/timezonefinder>`__
* `online GUI and API <https://timezonefinder.michelfe.it>`__
* `GUI repository <https://github.com/jannikmi/timezonefinder_gui>`__
* `ruby port <https://github.com/gunyarakun/timezone_finder>`__



LICENSE
-------

``timezonefinder`` is licensed under the `MIT license <https://github.com/jannikmi/timezonefinder/blob/master/LICENSE>`__.

The data is licensed under the `ODbL license <https://github.com/jannikmi/timezonefinder/blob/master/DATA_LICENSE>`__, following the base dataset from `evansiroky/timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder>`__.
