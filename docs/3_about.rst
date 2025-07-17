
=====
About
=====


.. include:: ./badges.rst


``timezonefinder`` is a python package for looking up the corresponding timezone for given coordinates on earth entirely offline.

Timezones internally are being represented by polygons and the timezone membership of a given point (= lat lng coordinate pair) is determined by a point in polygon (PIP) check.
In many cases an expensive PIP check can be avoided.

For detailed information about the data format in use, see :doc:`data_format`.

Among other tweaks this index makes ``timezonefinder`` efficient (also check the :ref:`performance chapter <performance>`).


References
----------

`GitHub <https://github.com/jannikmi/timezonefinder>`__

`PyPI <https://pypi.python.org/pypi/timezonefinder/>`__

`online GUI and API <http://timezonefinder.michelfe.it>`__

`conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__

ruby port: `timezone_finder <https://github.com/gunyarakun/timezone_finder>`__

`download stats <https://pepy.tech/project/timezonefinder>`__


LICENSE
-------

``timezonefinder``  is licensed under the `MIT license <https://github.com/jannikmi/timezonefinder/blob/master/LICENSE>`__.

The data is licensed under the `ODbL license <https://github.com/jannikmi/timezonefinder/blob/master/DATA_LICENSE>`__, following the base dataset from `evansiroky/timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder>`__.



Alternative python packages
---------------------------

- `tzfpy <https://github.com/ringsaturn/tzfpy>`__ (less accurate, more lightweight, faster)
- `pytzwhere <https://pypi.python.org/pypi/tzwhere>`__ (not maintained)


Comparison to tzfpy
-----------------------

``tzfpy`` is a Python binding of the Rust package ``tzf-rs``, which serves as an alternative to ``timezonefinder`` with different trade-offs.

Both packages will likely coexist as they serve different use cases:

**Comprehensive Comparison:**

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Feature
     - timezonefinder
     - tzfpy
   * - Implementation
     - Pure Python with optional C extensions and Numba compilation
     - Python binding of Rust package ``tzf-rs``
   * - Startup Time
     - Requires initialization time
     - No startup time (immediate)
   * - `Lookup Speed <https://github.com/ringsaturn/tz-benchmark>`__
     - Median: ~215k Queries per second (QPS). Up to 800k with less accurate TimezoneFinderL
     - Median: ~511k QPS
   * - Data Representation
     - Complete timezone polygons
     - Simplified timezone polygons
   * - Accuracy
     - Higher accuracy with full polygon data
     - Lower accuracy due to simplified polygons
   * - Distribution Size
     - ~50 MB
     - ~6 MB
   * - Memory Usage
     - ~40MB
     - ~40MB
   * - Spatial Index
     - H3 hexagon-based index with ~40k cells
     - Hierarchical tree of ~80k rectangles with fallback to polygon data
   * - Build Complexity
     - Easier to build when wheels are missing
     - Requires Rust to build wheels for some platforms
   * - Python Compatibility
     - Better compatibility across Python versions
     - Requires Rust to build wheels on certain platforms or Python versions
   * - Additional Features
     - ``get_geometry()`` for retrieving the timezone shapes
     - None
   * - Maintainability
     - Single repository
     - Downstream of multiple repositories (tzf, tzf-rel, tzf-rs) languages (Go, Rust, Python)



**When to Choose Which Package:**

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - Use Case
     - Recommended Package
   * - Lookup Performance
     - ``tzfpy``
   * - Initialization Time
     - ``tzfpy``
   * - Minimal Distribution Size
     - ``tzfpy``
   * - Data Accuracy
     - ``timezonefinder``
   * - Compatibility with varied Python environments
     - ``timezonefinder``
   * - Access to timezone geometry data
     - ``timezonefinder``
   * - Maintainability and Ease of Contribution
     - ``timezonefinder``
   * - Memory efficiency
     - Either




Comparison to pytzwhere
-----------------------

This project has originally been derived from `pytzwhere <https://pypi.python.org/pypi/tzwhere>`__
(`github <https://github.com/pegler/pytzwhere>`__), but aims at providing
improved performance and usability.

``pytzwhere`` is parsing a 76MB .csv file (floats stored as strings!) completely into memory and computing shortcuts from this data on every startup.
This is time, memory and CPU consuming. Additionally calculating with floats is slow,
keeping those 4M+ floats in the RAM all the time is unnecessary and the precision of floats is not even needed in this case (s. detailed comparison and speed tests below).

In comparison most notably initialisation time and memory usage are significantly reduced.
``pytzwhere`` is using up to 450MB of RAM (with ``shapely`` and ``numpy`` active),
because it is parsing and keeping all the timezone polygons in the memory.
This uses unnecessary time/ computation/ memory and this was the reason I created this package in the first place.
This package uses at most 40MB (= encountered memory consumption of the python process) and has some more advantages:

**Differences:**

-  highly decreased memory usage
-  highly reduced start up time
-  usage of 32bit int (instead of 64+bit float) reduces computing time and memory consumption. The accuracy of 32bit int is still high enough. According to my calculations the worst accuracy is 1cm at the equator. This is far more precise than the discrete polygons in the data.
-  the data is stored in memory friendly binary files (approx. 41MB in total, original data 120MB .json)
-  data is only being read on demand (not completely read into memory if not needed)
-  precomputed shortcuts are included to quickly look up which polygons have to be checked
- function ``get_geometry()`` enables querying timezones for their geometric shape (= multipolygon with holes)
- further speedup possible by the use of ``numba`` (code JIT compilation)
- tz_where is still using the outdated tz_world data set


Contact
--------


Tell me if and how your are using this package. This encourages me to develop and test it further.

Most certainly there is stuff I missed, things I could have optimized even further or explained more clearly, etc.
I would be really glad to get some feedback.

If you encounter any bugs, have suggestions etc. do not hesitate to **open an Issue** or **add a Pull Requests** on Git.
Please refer to the :ref:`contribution guidelines <contributing>`


Acknowledgements
----------------

Thanks to:

- `Adam <https://github.com/adamchainz>`__ for adding organisational features to the project and for helping me with publishing and testing routines.
- `ringsaturn <https://github.com/ringsaturn>`__ for valuable feedback, sponsoring this project, creating the ``tzfpy`` package and adding the ``pytz`` compatibility extra
- `theirix  <https://github.com/theirix>`__ for adding support for cibuildwheel
- `snowman2 <https://github.com/snowman2>`__ for creating the conda-forge recipe.
- `synapticarbors <https://github.com/synapticarbors>`__ for fixing Numba import with py27.
- `zedrdave <https://github.com/zedrdave>`__ for valuable feedback.
- `Tyler Huntley <https://github.com/Ty1776>`__ for adding docstrings
- `Greg Meyer <https://github.com/gmmeyer>`__ for updating h3 to >4
- `ARYAN RAJ <https://github.com/nikkhilaaryan>`__ for providing example scripts and updating python version support
