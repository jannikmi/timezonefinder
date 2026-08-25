============
Alternatives
============

The position in one paragraph
-----------------------------

``timezonefinder`` optimises for **correctness at timezone borders**. It stores the boundary
polygons exactly as the source dataset provides them - every vertex of every polygon and every
hole, at ~1 cm coordinate resolution - and never simplifies them. :doc:`data_report` is generated
from the packaged data and carries the current counts. Speed is the constraint that work is done
under, not the goal: the H3 spatial
index, the integer coordinate representation and the optional acceleration backends exist to make
full-resolution geometry affordable, not to shave the last microsecond off a lookup.

`tzfpy <https://github.com/ringsaturn/tzfpy>`__ makes the opposite trade, deliberately and well. It
ships simplified polygons, which makes it smaller and faster per query, at the cost of accuracy near
the borders those polygons describe. The two are now measured against each other under one harness -
same query points, same process, same machine - in :doc:`benchmark_results_comparison`.

**If your query points are rarely near a timezone border - coarse geofencing, analytics
aggregation, high-volume classification where an occasional wrong answer within a few hundred
metres of a boundary costs nothing - choose ``tzfpy``.** It is a good package, it will serve you
better, and its maintainer is a contributor to this one (see :doc:`3_about`). If a wrong answer at
a border is a bug rather than a rounding error, that is what this package is for.

Alternative python packages
---------------------------

- `tzfpy <https://github.com/ringsaturn/tzfpy>`__ - less accurate, more lightweight, faster per lookup
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
     - Complete, non-simplified polygons at ~1 cm coordinate resolution; :doc:`data_report` lists the current vertex, polygon and hole counts
     - Simplified polygons, by design
   * - Border Accuracy
     - Limited only by the source dataset
     - Reduced near borders, in proportion to the simplification
   * - Spatial Index
     - H3 hexagons at resolution 4 (~288k cells); :doc:`data_report` lists the index size
     - Hierarchical tree of ~80k rectangles, falling back to the simplified polygon data
   * - Time to First Answer
     - Imports NumPy and H3, then reads its index when a finder is constructed (:doc:`benchmark_results_initialization`)
     - Imports in about a millisecond, then deserialises its index inside the *first query*
   * - Avg. Lookup Speed
     - Hundreds of thousands of queries/s on one core; :doc:`benchmark_results_timezonefinding` carries the measured figure and names the configuration behind it
     - Faster per query, by a small single-digit factor on a representative query mix and by a larger single-digit one on the ambiguous points that cost this package the most (:doc:`benchmark_results_comparison`)
   * - Memory Usage
     - Single-digit MiB allocated by default (polygon data stays memory-mapped), an order of magnitude more with ``in_memory=True`` (:doc:`benchmark_results_memory`)
     - Not measured here
   * - Distribution Size
     - Tens of MB per wheel, nearly all of it the packaged boundary data (:doc:`data_report` lists the installed binary sizes)
     - A few MB per wheel
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

   **The speed rows are measured, not estimated.** ``benchmarks/test_comparison.py`` runs both
   packages over the same committed query points, in the same process, on the same machine, and
   :doc:`benchmark_results_comparison` is generated from it. That harness exists because the
   alternative - putting two published figures side by side - is exactly the comparison this
   project refuses to make about itself: an unchanged lookup path spread 134-158 % across CI
   runners alone (:doc:`benchmarking_methodology`), so two numbers from two machines say nothing
   about two libraries.

   What it shows: ``tzfpy`` is the faster one per lookup, on every point class and by a single-digit
   factor throughout. The gap is smallest where a coordinate's H3 cell already determines the answer
   and widest where this package has to fall through to a full point-in-polygon test - the shape you
   would predict from the design difference, and the price of the accuracy this package is for.

   That widest gap used to be more than an order of magnitude, and is not any more: the latitude
   block index lets a ray cast skip the parts of a boundary polygon it cannot cross, which is
   precisely the work that made an ambiguous lookup expensive here and does not exist in a
   simplified-polygon design. Read the ratio off the generated page rather than from memory - it is
   the row this project's own changes move most.

   What it also shows, and what this page previously got wrong: **neither package starts instantly.**
   ``tzfpy`` imports in about a millisecond, but it deserialises its index lazily inside the first
   query, and that costs about as much as this package spends importing NumPy and H3 and reading its
   own index. Measured all the way to a first answer, the two land close enough together that
   startup is not a reason to choose either - which is why the decision table below no longer
   lists it.

   What that harness deliberately does not settle is ``tzfpy``'s memory footprint, which is not
   measured here at all, so the figures linked above describe this package only.

.. note::

   **What the simplification costs is measured too, and it is not small where it matters.**
   Run both packages over a uniform sample of the globe and they never disagree - which is true and
   says nothing, because a uniformly drawn coordinate is hundreds of kilometres from the nearest
   border. So ``scripts/measure_tzfpy_agreement.py`` (``make tzfpy-agreement``) asks the question at
   a *stated distance from a border* instead, over points drawn without bias in where on the globe
   they land, and sweeps that distance from this package's own ~1.1 cm coordinate resolution
   outwards.

.. image:: tzfpy_agreement_by_distance.svg
   :alt: Of points a centimetre from a timezone border, about half get a different zone from the two
         packages, a third do at a metre, a quarter at ten metres - and the curve never reaches zero,
         with roughly one point in three thousand still differing a kilometre from any border.
   :width: 100%

.. note::

   Boundary release 2026c on both sides, ``tzfpy`` 1.3.3, 20,000 points per distance, 2026-08-25.
   The last column is disagreements this package does **not** attribute to ``tzfpy`` - see
   *Reading the last column* below.

   .. list-table::
      :header-rows: 1
      :widths: 25 25 25 25

      * - Distance from a border
        - Any border
        - Border of a land zone
        - Not attributed
      * - 1 cm
        - 37.5 %
        - 47.0 %
        - 16
      * - 5 cm
        - 34.2 %
        - 45.2 %
        - 4
      * - 10 cm
        - 32.9 %
        - 43.4 %
        - 1
      * - 50 cm
        - 26.9 %
        - 35.3 %
        - 4
      * - 1 m
        - 25.2 %
        - 33.3 %
        - 2
      * - 5 m
        - 21.3 %
        - 28.2 %
        - 3
      * - 10 m
        - 17.6 %
        - 23.0 %
        - 1
      * - 50 m
        - 4.3 %
        - 5.7 %
        - 5
      * - 100 m
        - 0.12 %
        - 0.15 %
        - 2
      * - 500 m
        - 0 of 20,000
        - 0 of 15,000
        - 1
      * - 1 km
        - 0 of 20,000
        - 0 of 15,000
        - 3

   **The knee is between 10 m and 100 m, and past it the curve stops.** A fifth of points still
   differ at ten metres, one in twenty at fifty, one in eight hundred at a hundred - and beyond a
   hundred metres, across 40,000 sampled points, **not one disagreement is attributable to**
   ``tzfpy``. That is the ~111 m maximum displacement its maintainer states for the simplification,
   holding exactly as stated. Below the knee the curve flattens rather than climbing to 100 %,
   because the points sit on **both** sides of this package's border and only the side ``tzfpy``'s
   boundary has moved away from can disagree.

   The second column drops the ocean zones, whose mutual borders are meridians that no simplification
   can move and which therefore dilute the first; a coastline stays in both, since it is stored in the
   land polygon as well as in the ocean polygon around it.

   Two corrections make the numbers attributable rather than merely suggestive. The measurement
   refuses to report unless both packages carry the **same timezone-boundary-builder release**, so a
   difference cannot be a border that moved between datasets; and it asks whether this package's
   answer is among the zones ``tzfpy`` holds over the point rather than whether the two name the same
   one, because the dataset ships genuinely overlapping zones - ``Asia/Urumqi`` inside
   ``Asia/Shanghai`` - that each package resolves by its own rule. Those overlaps are almost every
   difference away from a border and next to none of the ones near it.

Reading the last column
~~~~~~~~~~~~~~~~~~~~~~~

**Not every difference is the other package's error, and this one is ours.** Where
``timezone_at`` answers but :meth:`~timezonefinder.TimezoneFinder.certain_timezone_at` returns
``None``, no polygon actually contains the point and the answer is a fallback to a neighbouring
zone. Above roughly latitude 88 the shortcut index can omit the polygon covering a cell, which is a
known defect of *this* package. Those points are counted in the last column and kept out of the
rates, because charging them to ``tzfpy`` would put this package's bug on its competitor's tab.

It matters more than the counts suggest: every disagreement beyond 100 m turned out to be one of
these. Reported naively, the curve appeared to carry a tail out to a kilometre and to contradict the
stated tolerance. It does not.


Every disagreement 100 m or more from a border
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Listed in full rather than sampled, so the figures above can be checked rather than taken on trust,
and recorded machine-readably in ``docs/tzfpy_agreement.json`` alongside every rate on this page.
Each coordinate was re-queried against both packages afterwards and its distance to the nearest
border re-measured; the ``border`` column is that measurement, not the distance the point was drawn
at. Boundary release 2026c on both sides, ``tzfpy`` 1.3.3.

**Attributable to** ``tzfpy`` — all 24, and all at 100 m. Beyond that there are none::

     border    latitude    longitude   timezonefinder        tzfpy
      100 m    63.50486    106.56825   Asia/Krasnoyarsk      Asia/Irkutsk
      100 m    10.96478    115.95923   Asia/Manila           Etc/GMT-8
      100 m    11.34167    -63.99829   America/Caracas       Etc/GMT+4
      100 m    32.94443    133.72220   Etc/GMT-9             Asia/Tokyo
      100 m    69.05734   -165.71935   America/Nome          Etc/GMT+11
      100 m     9.82826    112.88880   Asia/Shanghai         Etc/GMT-8
      100 m    16.06440    -82.33148   America/Tegucigalpa   (no zone at all)
      100 m     3.67614    -59.71563   America/Guyana        America/Boa_Vista
      100 m   -10.98399    179.53451   Pacific/Funafuti      Etc/GMT-12
      100 m     7.30759    -60.60160   America/Guyana        America/Caracas
      100 m    10.29734    113.87220   Asia/Ho_Chi_Minh      Etc/GMT-8
      100 m    58.08210     -8.48906   Europe/London         Etc/GMT+1
      100 m   -38.11690    -73.94919   America/Santiago      Etc/GMT+5
      100 m    44.58485     35.08544   Europe/Simferopol     Etc/GMT-2
      100 m   -16.57720   -144.73338   Pacific/Tahiti        Etc/GMT+10
      100 m    39.07428    124.77606   Asia/Pyongyang        Etc/GMT-8
      100 m   -22.98745    151.97899   Australia/Brisbane    Etc/GMT-10
      100 m    11.76343     51.48246   Africa/Mogadishu      Etc/GMT-3
      100 m     8.01813    -58.83736   Etc/GMT+4             America/Guyana
      100 m   -15.56637   -142.00834   Pacific/Tahiti        Etc/GMT+9
      100 m    13.54474     13.13853   Africa/Niamey         Africa/Lagos
      100 m    44.47805    -62.74375   America/Halifax       Etc/GMT+4
      100 m    28.20837   -112.48333   America/Hermosillo    Etc/GMT+7
      100 m     1.73097    -69.62412   America/Manaus        America/Bogota

The ``America/Tegucigalpa`` line is not a wrong zone but *no* zone: ``tzfpy`` returns an empty
result there.

**This package's own errors**, excluded from the rates above — six, all of them the three
antimeridian cells at the north pole that ``potential-improvements.md`` tracks as BUG-3.
``timezone_at`` returns a zone that does not contain the point, which the bracketed column shows by
testing every packaged polygon directly; ``tzfpy`` is right in all six::


     border    latitude    longitude   timezonefinder   tzfpy   (and the zone that really contains the point)
    1,000 m    89.58436   -173.73833   Etc/GMT+11   Etc/GMT+12   (Etc/GMT+12)
    1,000 m    89.18571    179.36790   Etc/GMT+11   Etc/GMT-12   (Etc/GMT-12)
    1,000 m    88.68884    172.89258   Etc/GMT+11   Etc/GMT-12   (Etc/GMT-12)
      500 m    88.55701    179.82164   Etc/GMT+11   Etc/GMT-12   (Etc/GMT-12)
      100 m    89.06007    172.55476   Etc/GMT+11   Etc/GMT-12   (Etc/GMT-12)
      100 m    89.57708   -179.87830   Etc/GMT+11   Etc/GMT+12   (Etc/GMT+12)

These are the check that a fix works: each should become an agreement. Eleven further cases,
spanning the Tuamotus, the Seychelles, San Andrés and the Lesotho border, were on this list until a
shortcut-index fix removed them - which is why the list is regenerated with the measurement rather
than written by hand.

When to choose which package
----------------------------

Only the criteria on which the two actually differ. On dataset coverage and access to the geometry
they are equivalent, so neither is a reason to pick one - and measuring them together removed
startup from this list as well, since the two reach a first answer in about the same time
(:doc:`benchmark_results_comparison`).

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
  This package allocates **single-digit MiB** for its data structures by default, because the
  polygon coordinates stay memory-mapped (:doc:`benchmark_results_memory` reports every mode).
- Precomputed shortcuts shipped with the package instead of rebuilt at every startup.

Two capabilities came along the way: ``get_geometry()`` for querying a timezone's shape (a
multipolygon with holes), and optional Numba JIT compilation.
