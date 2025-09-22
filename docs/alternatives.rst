============
Alternatives
============

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
   * - `Avg. Lookup Speed <https://github.com/ringsaturn/tz-benchmark>`__
     - ~270k Queries per second (QPS). >730k with less accurate TimezoneFinderL
     - ~320k QPS
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
