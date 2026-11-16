============
Alternatives
============

The position in one paragraph
-----------------------------

``timezonefinder`` optimises for **correctness at timezone borders**: it stores the boundary
polygons exactly as the source dataset publishes them, every vertex and every hole, and never
simplifies them (:doc:`data_report` carries the counts). Its spatial index, integer coordinates and
acceleration backends exist to make that full-resolution geometry affordable.

`tzfpy <https://github.com/ringsaturn/tzfpy>`__ makes the opposite trade in its PyPI build: it ships
simplified polygons, so it is smaller and faster per single lookup, at the cost of accuracy near
borders. Its maintainer, also a contributor here (:doc:`5_contributing`), publishes an experimental
``+full`` variant with the unsimplified dataset, served from the project's own package index rather
than PyPI. Everything measured on this page is the PyPI build; :doc:`benchmark_results_vs_tzfpy`
measures both packages on the same points, in the same process, on the same machine.

- **Choose the PyPI build of** ``tzfpy`` if an occasional wrong answer within a few hundred metres
  of a border costs nothing *and* you look up one point per call - coarse geofencing, or a lookup
  per request or event in a service.
- **Choose** ``timezonefinder`` if border accuracy matters, or if you look up many points at once -
  classifying a dataset, a batch job, an analytics aggregation. ``timezone_names_at()`` answers a
  whole array in one call and outpaces a loop of ``tzfpy`` calls on a representative point mix; it
  is about even on land-only points and slower on border-heavy ones.
- If border accuracy matters and an experimental wheel from a separate package index is acceptable,
  also evaluate ``tzfpy +full``; this project has not measured it.


What remains distinct
---------------------

The full-precision variant is a serious alternative, not a footnote to explain away. For the narrow
job "return one timezone name for this coordinate", it may eventually make ``timezonefinder`` the
worse choice: it promises the same source geometry through an implementation whose simplified
build is substantially faster here. This project has not measured the full build, so it cannot
carry that result across by assumption. Neither the age of this project nor its installed base is a
technical reason for a new user to pick it.

``timezonefinder`` still serves a different contract today:

- Unsimplified geometry is its supported default on PyPI, not an experimental variant requiring a
  separate index and a local-version wheel.
- Its data is a separately versioned PyPI distribution. Applications can update or pin the boundary
  release independently of the lookup code instead of receiving data only inside a native-extension
  release.
- Its public API covers NumPy batch lookup, integer zone-ID results, land-only lookup that can
  distinguish land zones from the ``Etc/GMT`` ocean zones, distinct fast/certain/all-match query
  semantics, geometry as coordinate arrays, and ``zoneinfo``/UTC-offset/localisation helpers.
  ``tzfpy +full`` keeps the smaller ``tzfpy`` API; "same API" does not mean the two projects are
  drop-in replacements.
- The full geometry can remain memory-mapped and reclaimable under pressure. The optional point-in-
  polygon accelerators improve speed, but the lookup stays correct without them and building this
  package itself does not require a Rust toolchain.

Those are reasons for this package to continue, not a permanent entitlement to be preferred. If
``tzfpy +full`` becomes an ordinary PyPI release, proves equivalent border behaviour under the same
harness, and covers the API and deployment constraints an application needs, then full precision by
itself is no reason to choose ``timezonefinder``. Continued coexistence has to be earned on the
remaining differences above.

Alternative python packages
---------------------------

- `tzfpy <https://github.com/ringsaturn/tzfpy>`__ - its PyPI build is less accurate, more lightweight
  and faster per lookup; its experimental ``+full`` build does not simplify the geometry
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
     - Complete, non-simplified polygons at the ~11 cm resolution timezone-boundary-builder publishes; :doc:`data_report` lists the current vertex, polygon and hole counts
     - Simplified polygons, by design; the experimental ``+full`` build, distributed outside PyPI, embeds the unsimplified dataset instead
   * - Border Accuracy
     - Limited only by the source dataset
     - Reduced near borders, in proportion to the simplification (PyPI build, :doc:`border_accuracy_vs_tzfpy`; the ``+full`` build does not simplify)
   * - Spatial Index
     - an aligned grid tree, 0.75-degree cells refining to 0.1875; :doc:`data_report` lists the index size
     - Hierarchical tree of ~80k rectangles, falling back to the simplified polygon data
   * - Time to First Answer
     - Imports NumPy, then reads its index when a finder is constructed (:doc:`benchmark_results_initialization`)
     - Imports in about a millisecond, then deserialises its index inside the *first query*
   * - Avg. Lookup Speed
     - Hundreds of thousands of queries/s on one core; :doc:`benchmark_results_timezonefinding` carries the measured figure and names the configuration behind it. For bulk lookups the batch API (``timezone_names_at()``) is faster than a loop of ``tzfpy`` calls on a representative query mix, since ``tzfpy`` has no batch API; it pays from a few dozen points per call (:doc:`benchmark_results_batch_break_even`)
     - The simplified PyPI build is faster per single query, by a small single-digit factor on a representative query mix and by a larger single-digit one on the ambiguous points that cost this package the most; looping it over many points is slower than this package's batch API except on ambiguous points; the ``+full`` build is not measured here (:doc:`benchmark_results_vs_tzfpy`)
   * - Memory Usage
     - Single-digit MiB allocated by default (polygon data stays memory-mapped), an order of magnitude more with ``in_memory=True`` (:doc:`benchmark_results_memory`)
     - Not measured here
   * - Distribution Size
     - Tens of MB per wheel, nearly all of it the packaged boundary data (:doc:`data_report` lists the installed binary sizes)
     - A few MB per wheel for the simplified PyPI build; the ``+full`` wheel is larger
   * - Build & Platform Coverage
     - Builds without a Rust toolchain; the C extension is optional and its absence only costs speed
     - Requires Rust to build wheels on platforms or Python versions without a prebuilt one
   * - Additional Features
     - Batch and integer-ID lookup, land-only and certainty variants, coordinate-array geometry,
       and time conversion helpers
     - Returns every matching zone and GeoJSON representations of the shapes and the timezone's
       indexes
   * - Maintainership
     - Single repository
     - Downstream of several repositories (tzf, tzf-rel, tzf-rs) across Go, Rust and Python

.. note::

   **The speed rows are measured, not estimated.** ``benchmarks/test_comparison.py`` runs both
   packages over the same committed query points, in the same process, on the same machine, and
   :doc:`benchmark_results_vs_tzfpy` is generated from it. That harness exists because the
   alternative - putting two published figures side by side - is exactly the comparison this
   project refuses to make about itself: an unchanged lookup path spread 134-158 % across CI
   runners alone (:doc:`benchmarking_methodology`), so two numbers from two machines say nothing
   about two libraries.

   What it shows: ``tzfpy`` is the faster one per lookup, on every point class and by a single-digit
   factor throughout. The gap is smallest where a coordinate's shortcut cell already determines the answer
   and widest where this package has to fall through to a full point-in-polygon test - the shape you
   would predict from the design difference, and the price of the accuracy this package is for.

   That widest gap used to be more than an order of magnitude, and is not any more: the latitude
   block index lets a ray cast skip the parts of a boundary polygon it cannot cross, which is
   precisely the work that made an ambiguous lookup expensive here and does not exist in a
   simplified-polygon design. Read the ratio off the generated page rather than from memory - it is
   the row this project's own changes move most.

   What it also shows, and what this page previously got wrong: **neither package starts instantly.**
   ``tzfpy`` imports in about a millisecond, but it deserialises its index lazily inside the first
   query, and that costs about as much as this package spends importing NumPy and reading its
   own index. Measured all the way to a first answer, the two land close enough together that
   startup is not a reason to choose either - which is why the decision table below no longer
   lists it.

   What that harness deliberately does not settle is ``tzfpy``'s memory footprint, which is not
   measured here at all, so the figures linked above describe this package only. It also has not
   measured the full-precision ``tzfpy`` variant.

Border accuracy
~~~~~~~~~~~~~~~

What the simplification costs is measured, at stated distances from a border rather than over uniform points, where the two packages never disagree. Within metres of a border the two packages differ on most sampled land-zone border locations, and the disagreement stops at about a hundred metres, the maximum displacement ``tzfpy``'s maintainer states for its simplification. :doc:`border_accuracy_vs_tzfpy` has the chart, the tables and every disagreement found beyond that distance.

When to choose which package
----------------------------

Only criteria that currently differ are listed. Dataset coverage and access to geometry exist in
both projects, so neither is a reason to pick one. Measuring the PyPI builds together also removed
startup from this list: they reach a first answer in about the same time
(:doc:`benchmark_results_vs_tzfpy`). The ``+full`` rows below describe its distribution contract;
its performance and memory have not been measured by this project's harness.

.. list-table::
   :header-rows: 1
   :widths: 58 42

   * - Use Case
     - Recommended Package
   * - Full precision as a supported dependency from PyPI
     - ``timezonefinder``
   * - Full precision when an experimental, separately indexed wheel is acceptable
     - Also evaluate ``tzfpy +full``; no winner is measured here
   * - NumPy batch and integer-ID APIs, land-only lookup, or built-in time conversion
     - ``timezonefinder``
   * - Boundary data versioned independently of lookup code
     - ``timezonefinder``
   * - Source builds where a Rust toolchain is unavailable
     - ``timezonefinder``
   * - Lookup throughput, one point per call
     - ``tzfpy`` PyPI build (``+full`` not measured here)
   * - Lookup throughput, many points per call (bulk or batch workloads)
     - ``timezonefinder`` via ``timezone_names_at()`` on a representative point mix; about even
       on land-only points and slower on border-heavy ones (:doc:`benchmark_results_vs_tzfpy`)
   * - Minimal distribution size
     - ``tzfpy`` PyPI build

Existing applications also have a legitimate compatibility reason to stay with either package,
but ecosystem inertia is a maintenance obligation, not a claim of technical superiority.


Comparison to pytzwhere
-----------------------

This project was originally derived from `pytzwhere <https://pypi.python.org/pypi/tzwhere>`__
(`github <https://github.com/pegler/pytzwhere>`__), which is no longer maintained and uses the
outdated ``tz_world`` dataset. A 2026 reader is not choosing between the two, but the origin story
explains the shape of everything above.

When this package was forked, ``pytzwhere`` parsed a 76 MB CSV file fully into memory on every startup and rebuilt its shortcuts each time, using up to **450 MB of RAM** to answer a lookup. Its last release (3.0.3) ships precomputed shortcuts but still decodes every polygon at startup. Re-measured side by side by ``prototypes/pytzwhere_headline_comparison.py``, whose docstring records the run and its limits, a default install of this package (C extension):

- **adds over an order of magnitude less memory** and **starts an order of magnitude faster**, with no loading pause before the first query. The optional ``numba`` extra adds several times that memory, nearly all of it the ``numba`` import;
- **answers a single query roughly an order of magnitude faster** at the median and faster still at the slowest;
- **answers a batch tens of times faster** than ``pytzwhere`` can loop over the same points, since it has no batch API; a loop of this package's own single-point calls gains only the per-query factor above;
- **answers every point**, where ``pytzwhere`` has no ocean zones, answers under a third of the globe, misses a sixth of land points and raises ``KeyError`` near the poles;
- **runs on a current stack**, where ``pytzwhere`` fails on NumPy 1.24 or newer and has to be pinned to Python 3.10 with older ``numpy`` and ``shapely``.

Two things go the other way. The installed data is somewhat larger, because it carries holes, ocean zones and a current dataset. And the pure-Python fallback, used only where neither the C extension nor ``numba`` is available, answers a large set of points several times *more slowly* than ``pytzwhere``: its median query is as fast, but the queries that need polygon tests run them in interpreted Python, while ``pytzwhere`` hands them to shapely's compiled GEOS on edge-indexed polygons. Batching cannot help there, because those tests run per point.

Where both answer on land they agree for about four points in five, which measures a decade of border and zone-name changes between the datasets as much as either implementation.

Against that, the design decisions below are all the same decision made repeatedly:

- 32-bit integer coordinates instead of 64-bit floats. The coordinate grid steps ~1.1 cm at the
  equator, far finer than the discrete polygons in the source data, so the extra precision was
  paying for nothing.
- Memory-friendly binary files instead of text, read on demand rather than parsed up front.
  This package allocates **single-digit MiB** for its data structures by default, because the
  polygon coordinates stay memory-mapped (:doc:`benchmark_results_memory` reports every mode).
- Precomputed shortcuts shipped with the package instead of rebuilt at every startup.

Two capabilities came along the way: ``get_geometry()`` for querying a timezone's shape (a
multipolygon with holes), and optional Numba JIT compilation.
