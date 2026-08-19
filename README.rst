==============
timezonefinder
==============

.. image:: https://raw.githubusercontent.com/jannikmi/timezonefinder/master/docs/hero_banner.jpeg
   :alt: Coordinate to IANA timezone lookup
   :target: https://timezonefinder.readthedocs.io/en/latest/
   :align: center

**Offline timezone lookup for WGS84 coordinates, with no polygon simplification - so the answer
stays correct at timezone borders.**

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

.. image:: https://img.shields.io/pypi/pyversions/timezonefinder.svg
    :alt: supported python versions
    :target: https://pypi.python.org/pypi/timezonefinder

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :alt: linted and formatted with ruff
    :target: https://github.com/astral-sh/ruff


In comparison to other alternatives this package aims at maximum accuracy around timezone borders while offering fast lookup performance and compatibility with many (Python) runtime environments.
It combines preprocessed polygon data, H3-based spatial shortcuts, and optional acceleration via Numba or a clang-backed point-in-polygon routine.


Quick Guide
-----------

It is recommended to install it together with the optional `Numba <https://numba.pydata.org/>`__ package for increased performance:

.. code-block:: console

    pip install timezonefinder[numba]

The timezone boundary data is installed automatically as the separate ``timezonefinder-data`` distribution, so that a new dataset ships without a new ``timezonefinder`` release. Pin it to hold a deployment to one dataset - the `release history <https://pypi.org/project/timezonefinder-data/#history>`__ lists the versions to choose from: ``pip install timezonefinder "timezonefinder-data==<version>"``.


.. code-block:: python

    # use the global function for convenience:
    from timezonefinder import timezone_at

    tz = timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'


    # For improved performance and control, create and reuse an instance:
    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder(in_memory=True)  # reuse

    query_points = [(13.358, 52.5061), ...]
    for lng, lat in query_points:
        tz = tf.timezone_at(lng=lng, lat=lat)  # 'Europe/Berlin'


**Note:** This library uses the full original timezone dataset with all >440 timezone names, providing full localization capabilities and historical timezone accuracy. For applications that prefer a smaller memory footprint, the reduced "timezones-now" dataset is available via the ``update_data.sh`` script (cf. `Documentation <https://timezonefinder.readthedocs.io/en/latest/data_format.html#alternative-dataset-options>`__).


How it works
------------

A lookup scales the coordinates to 32-bit integers (x 10^7, ~1 cm resolution), finds the point's
H3 hexagon at resolution 3, and reads a precomputed shortcut for that cell. Most cells are covered
by a single timezone, so the answer is returned immediately with no geometry touched at all. Only
an ambiguous cell falls through to the polygons it lists: bounding-box rejection first, then a
ray-casting point-in-polygon test - holes before the outer ring, since holes are smaller and can
reject the polygon outright.

The central trade-off: **the boundary polygons are never simplified**, so border accuracy is limited
only by the source dataset. The H3 index is what makes carrying full-resolution geometry affordable.

Since the dataset includes ocean zones, every coordinate on earth matches some timezone - use
``timezone_at_land()`` when you need to tell land from sea.


Performance
-----------

**Hundreds of thousands of lookups per second on a single core** for uniformly random query points.
The exact figure depends on the acceleration backend, the machine and the dataset version, so the
benchmark reports below carry it - each states the configuration it was measured in - rather than
this page, which would go stale.

The point-in-polygon routine has three interchangeable backends, selected at import time: a
clang-compiled C extension (built automatically when a compiler is available), Numba JIT
compilation (preferred when the optional dependency is installed), and pure Python. The pure-Python
fallback is ~400x slower and always correct - a missing compiler costs speed, never results.

* `benchmark trend chart <https://jannikmi.github.io/timezonefinder/dev/bench/>`__ - appended to on every push to ``master``
* `benchmark reports <https://timezonefinder.readthedocs.io/en/latest/7_performance.html>`__ - lookup, point-in-polygon, initialization and memory
* `benchmarking methodology <https://timezonefinder.readthedocs.io/en/latest/benchmarking_methodology.html>`__ - how these numbers are produced and what they can and cannot tell you


Engineering notes
-----------------

* `Architecture <https://timezonefinder.readthedocs.io/en/latest/architecture.html>`__ - the lookup pipeline, the acceleration backends, and the ceilings this package deliberately does not exceed
* `Data Format <https://timezonefinder.readthedocs.io/en/latest/data_format.html>`__ - binary layouts, coordinate scaling and the H3 index
* `Benchmarking Methodology <https://timezonefinder.readthedocs.io/en/latest/benchmarking_methodology.html>`__ - the measurement design and where every threshold comes from
* `Testing philosophy <https://timezonefinder.readthedocs.io/en/latest/architecture.html#tests-that-protect-guarantees-not-behaviour>`__ - the tests that exist because a rule needed a failure mode, plus the property-based suite and the version/backend matrix
* `How it ships <https://timezonefinder.readthedocs.io/en/latest/architecture.html#how-it-ships>`__ - abi3 wheels, three libc targets, and the checks that stop a broken wheel reaching PyPI
* `Alternatives <https://timezonefinder.readthedocs.io/en/latest/alternatives.html>`__ - the trade-offs against ``tzfpy``, and when to choose it instead
* `Changelog <https://github.com/jannikmi/timezonefinder/blob/master/CHANGELOG.rst>`__


**Alternative:** Need maximum speed at the cost of accuracy? Check out `tzfpy <https://github.com/ringsaturn/tzfpy>`__ - a fast and lightweight alternative based on Rust.


Contributing
------------

**Looking for maintainers. Reach out if you want to contribute!**

Contribution guidelines, the development workflow and the testing/benchmarking gates are documented in `CONTRIBUTING.md <https://github.com/jannikmi/timezonefinder/blob/master/CONTRIBUTING.md>`__.


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

The data ships in the separate ``timezonefinder-data`` distribution and is licensed under the `ODbL license <https://github.com/jannikmi/timezonefinder/blob/master/packages/timezonefinder-data/DATA_LICENSE>`__, following the base dataset from `evansiroky/timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder>`__.
