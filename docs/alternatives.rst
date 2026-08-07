============
Alternatives
============

The position in one paragraph
-----------------------------

``timezonefinder`` optimises for **correctness at timezone borders**. It stores the boundary
polygons exactly as the source dataset provides them - 7,925,313 boundary vertices across 1,322
polygons, plus 756 holes, at ~1 cm coordinate resolution (see :doc:`data_report`) - and never
simplifies them. Speed is the constraint that work is done under, not the goal: the H3 spatial
index, the integer coordinate representation and the optional acceleration backends exist to make
full-resolution geometry affordable, not to shave the last microsecond off a lookup.

`tzfpy <https://github.com/ringsaturn/tzfpy>`__ makes the opposite trade, deliberately and well. It
ships simplified polygons, which makes it smaller, faster to start and faster per query, at the cost
of accuracy near the borders those polygons describe.

**If your query points are rarely near a timezone border - coarse geofencing, analytics
aggregation, high-volume classification where an occasional wrong answer within a few hundred
metres of a boundary costs nothing - choose ``tzfpy``.** It is a good package, it will serve you
better, and its maintainer is a contributor to this one (see :doc:`3_about`). If a wrong answer at
a border is a bug rather than a rounding error, that is what this package is for.

Alternative python packages
---------------------------

- `tzfpy <https://github.com/ringsaturn/tzfpy>`__ - less accurate, more lightweight, faster
- `pytzwhere <https://pypi.python.org/pypi/tzwhere>`__ - not maintained


Comparison to tzfpy
-------------------

``tzfpy`` is a Python binding of the Rust package ``tzf-rs``. Both packages use the full original
dataset (>440 timezones), so both offer full localization and historical timezone accuracy; the
difference is in what they do with that dataset's geometry.

.. list-table::
   :header-rows: 1
   :widths: 24 40 36

   * - Feature
     - timezonefinder
     - tzfpy
   * - Implementation
     - Pure Python, with an optional C extension and optional Numba JIT compilation
     - Python binding of the Rust crate ``tzf-rs``
   * - Dataset Version
     - Full original dataset (>440 timezones)
     - Full original dataset (>440 timezones)
   * - Data Representation
     - Complete, non-simplified polygons: 7,925,313 boundary vertices across 1,322 polygons at ~1 cm coordinate resolution (:doc:`data_report`)
     - Simplified polygons, by design
   * - Border Accuracy
     - Limited only by the source dataset
     - Reduced near borders, in proportion to the simplification
   * - Spatial Index
     - H3 hexagons at resolution 3, ~41k cells, 1.49 MB (:doc:`data_report`)
     - Hierarchical tree of ~80k rectangles, falling back to the simplified polygon data
   * - Startup Time
     - Requires initialization; measured per class and mode in :doc:`benchmark_results_initialization`
     - None (immediate)
   * - Avg. Lookup Speed
     - ~286k queries/s on one core for uniformly random points, with Numba and without the C extension, on macOS arm64 (:doc:`benchmark_results_timezonefinding`)
     - `~320k queries/s <https://github.com/ringsaturn/tz-benchmark>`__ reported by a third-party benchmark on unstated hardware
   * - Memory Usage
     - ~6 MiB allocated by default (polygon data stays memory-mapped), ~69 MiB with ``in_memory=True`` (:doc:`benchmark_results_memory`)
     - Not measured here
   * - Distribution Size
     - ~52 MB per wheel for 8.2.5 on PyPI; ~64 MB of binary data once installed (:doc:`data_report`)
     - ~4-5 MB per wheel for 1.3.2 on PyPI
   * - Build & Platform Coverage
     - Builds without a Rust toolchain; the C extension is optional and its absence only costs speed
     - Requires Rust to build wheels on platforms or Python versions without a prebuilt one
   * - Additional Features
     - ``get_geometry()`` returns the timezone shapes
     - Returns GeoJSON representations of the shapes and the timezone's indexes
   * - Maintainership
     - Single repository
     - Downstream of several repositories (tzf, tzf-rel, tzf-rs) across Go, Rust and Python

.. note::

   **The two speed figures are indicative, not a like-for-like measurement.** They come from
   different machines, different acceleration paths and different query workloads. This project
   documents at length why two measurements taken on different hardware cannot be compared - see
   :doc:`benchmarking_methodology`, where an unchanged lookup path spread 134-158 % across CI
   runners alone - and that caveat applies just as much to this table. Read the row as "the two
   packages are in the same order of magnitude, and ``tzfpy`` is the faster one"; anything finer
   would require benchmarking both under one harness, which nobody has done.

   The same applies in reverse to memory: ``tzfpy``'s footprint has not been measured here, so the
   ~6 MiB figure describes this package only and is not a claim about the comparison.


When to choose which package
----------------------------

Only the criteria on which the two actually differ. On dataset coverage and access to the geometry
they are equivalent, so neither is a reason to pick one.

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - Use Case
     - Recommended Package
   * - Accuracy near timezone borders
     - ``timezonefinder``
   * - Compatibility with varied Python environments and platforms
     - ``timezonefinder``
   * - Maintainability and ease of contribution
     - ``timezonefinder``
   * - Lookup throughput
     - ``tzfpy``
   * - Initialization time
     - ``tzfpy``
   * - Minimal distribution size
     - ``tzfpy``

Both packages will likely coexist, because these are genuinely different products.


Comparison to pytzwhere
-----------------------

This project was originally derived from `pytzwhere <https://pypi.python.org/pypi/tzwhere>`__
(`github <https://github.com/pegler/pytzwhere>`__), which is no longer maintained and uses the
outdated ``tz_world`` dataset. A 2026 reader is not choosing between the two, but the origin story
explains the shape of everything above.

``pytzwhere`` parses a 76 MB CSV file - floating point coordinates stored as decimal strings - fully
into memory on every startup, and computes its shortcuts from that data each time. With ``shapely``
and ``numpy`` active it used up to **450 MB of RAM** to answer a timezone lookup. That was the
reason this package exists.

Against that, the design decisions below are all the same decision made repeatedly:

- 32-bit integer coordinates instead of 64-bit floats. The worst-case accuracy is ~1 cm at the
  equator, far finer than the discrete polygons in the source data, so the extra precision was
  paying for nothing.
- Memory-friendly binary files instead of text, read on demand rather than parsed up front.
  This package allocates **~6 MiB** for its data structures by default, because the polygon
  coordinates stay memory-mapped (:doc:`benchmark_results_memory` reports every mode).
- Precomputed shortcuts shipped with the package instead of rebuilt at every startup.

Two capabilities came along the way: ``get_geometry()`` for querying a timezone's shape (a
multipolygon with holes), and optional Numba JIT compilation.
