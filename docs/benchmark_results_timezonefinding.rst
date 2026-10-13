

Timezone Finding Performance Benchmark
======================================


**~702ns per lookup, ~1.42M/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Darwin arm64, Apple M1 Pro, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration records the ``min`` estimator for these rows: ``TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory``, ``TimezoneFinder.timezone_at() - random points, in-memory``, ``TimezoneFinder.timezone_at() - unique-shortcut points, in-memory``, ``TimezoneFinder.timezone_ids_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_ids_at() - random points, file-based``, ``TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - random points, file-based``, ``TimezoneFinder.timezone_names_at() - unique-shortcut points, file-based``. This published table leads with ``Mean`` and includes the full suite, so its values answer a different question from the trend chart.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.14.2 (CPython)

**NumPy Version**: 2.5.2

**Platform**: Darwin arm64

**Processor**: arm



TimezoneFinder Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~


**C Implementation Available**: True

**Numba JIT Available**: False



Performance Optimizations
~~~~~~~~~~~~~~~~~~~~~~~~~


* ✓ Compiled C extension for point-in-polygon operations

* ✗ Numba JIT compilation not available



Benchmark Input Provenance
~~~~~~~~~~~~~~~~~~~~~~~~~~


**Fixture Version**: 4

**Timezone Data Version**: 2026d



Benchmark Configuration
~~~~~~~~~~~~~~~~~~~~~~~


**Benchmark Source**: pytest-benchmark

**Batch Size**: 2,500

Each benchmark times one pass over 2,500 fixed, committed query points (see benchmarks/conftest.py). Mean/Median/StdDev/Min/Max below are for the full 2,500-query batch; Time/Query and Throughput divide and scale that out to a per-query figure.



In-Memory Mode
~~~~~~~~~~~~~~




TimezoneFinder.timezone_at()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 36 7 7 7 7 7 7 11 11

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query
     - Throughput
   * - ambiguous-shortcut points, in-memory
     - 7.04ms
     - 6.97ms
     - 389µs
     - 6.68ms
     - 8.33ms
     - 15
     - 2.81µs
     - 355k/s
   * - on-land points, in-memory
     - 2.05ms
     - 2.04ms
     - 40.3µs
     - 2.01ms
     - 2.16ms
     - 15
     - 821ns
     - 1.22M/s
   * - random points, in-memory
     - 1.76ms
     - 1.72ms
     - 133µs
     - 1.61ms
     - 2.08ms
     - 15
     - 702ns
     - 1.42M/s
   * - unique-shortcut points, in-memory
     - 1.47ms
     - 1.45ms
     - 89.8µs
     - 1.35ms
     - 1.67ms
     - 15
     - 587ns
     - 1.70M/s




TimezoneFinder.timezone_at_land()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 18 9 9 9 9 9 9 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query
     - Throughput
   * - in-memory
     - 2.26ms
     - 2.23ms
     - 52.4µs
     - 2.21ms
     - 2.38ms
     - 15
     - 903ns
     - 1.11M/s




File-Based Mode
~~~~~~~~~~~~~~~




TimezoneFinder.timezone_at()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 42 6 6 6 6 6 6 11 11

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query
     - Throughput
   * - ambiguous-shortcut points, file-based
     - 7.17ms
     - 7.08ms
     - 388µs
     - 6.71ms
     - 7.92ms
     - 15
     - 2.87µs
     - 349k/s
   * - on-land points, file-based
     - 2.09ms
     - 2.07ms
     - 94.4µs
     - 2.01ms
     - 2.33ms
     - 15
     - 837ns
     - 1.19M/s
   * - random points, file-based
     - 1.74ms
     - 1.68ms
     - 137µs
     - 1.61ms
     - 1.99ms
     - 15
     - 696ns
     - 1.44M/s
   * - unique-shortcut points, file-based
     - 1.39ms
     - 1.37ms
     - 51.1µs
     - 1.34ms
     - 1.52ms
     - 15
     - 555ns
     - 1.80M/s




TimezoneFinder.timezone_at_land()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 18 9 9 9 9 9 9 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query
     - Throughput
   * - file-based
     - 2.26ms
     - 2.25ms
     - 59.2µs
     - 2.20ms
     - 2.38ms
     - 15
     - 905ns
     - 1.10M/s




TimezoneFinder.timezone_ids_at()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 42 6 6 6 6 6 6 11 11

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query
     - Throughput
   * - ambiguous-shortcut points, file-based
     - 5.06ms
     - 5.01ms
     - 124µs
     - 4.90ms
     - 5.27ms
     - 15
     - 2.02µs
     - 494k/s
   * - random points, file-based
     - 307µs
     - 303µs
     - 17.1µs
     - 289µs
     - 354µs
     - 15
     - 123ns
     - 8.13M/s
   * - unique-shortcut points, file-based
     - 46.6µs
     - 46.0µs
     - 1.88µs
     - 45.2µs
     - 52.1µs
     - 15
     - 18.6ns
     - 53.6M/s




TimezoneFinder.timezone_names_at()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 42 6 6 6 6 6 6 11 11

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query
     - Throughput
   * - ambiguous-shortcut points, file-based
     - 5.25ms
     - 5.07ms
     - 351µs
     - 4.87ms
     - 5.86ms
     - 15
     - 2.10µs
     - 476k/s
   * - random points, file-based
     - 314µs
     - 314µs
     - 7.66µs
     - 305µs
     - 331µs
     - 15
     - 125ns
     - 7.97M/s
   * - unique-shortcut points, file-based
     - 64.7µs
     - 64.1µs
     - 2.30µs
     - 62.6µs
     - 70.7µs
     - 15
     - 25.9ns
     - 38.6M/s




TimezoneFinderL (heuristic-only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. note::

   TimezoneFinderL does not support in-memory mode; shortcuts are always loaded from disk.



TimezoneFinderL.timezone_at() (ambiguous-shortcut points)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 18 9 9 9 9 9 9 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query
     - Throughput
   * - -
     - 2.67ms
     - 2.66ms
     - 22.9µs
     - 2.65ms
     - 2.74ms
     - 15
     - 1.07µs
     - 937k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **file-based** and **in-memory** perform about the same (1.74ms vs 1.76ms, 0.9% difference)

* On-land points: **in-memory** is 2% faster (1.02x) than **file-based** (2.05ms vs 2.09ms)

* Unique-shortcut points: **file-based** is 6% faster (1.06x) than **in-memory** (1.39ms vs 1.47ms)

* Ambiguous-shortcut points: **in-memory** and **file-based** perform about the same (7.04ms vs 7.17ms, 1.9% difference)

* TimezoneFinder.timezone_at_land(): **in-memory** and **file-based** perform about the same (2.26ms vs 2.26ms, 0.3% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 466% faster (5.66x) than **TimezoneFinder.timezone_at()** (307µs vs 1.74ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 454% faster (5.54x) than **TimezoneFinder.timezone_at()** (314µs vs 1.74ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 2876% faster (29.8x) than **TimezoneFinder.timezone_at()** (46.6µs vs 1.39ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2043% faster (21.4x) than **TimezoneFinder.timezone_at()** (64.7µs vs 1.39ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 42% faster (1.42x) than **TimezoneFinder.timezone_at()** (5.06ms vs 7.17ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 37% faster (1.37x) than **TimezoneFinder.timezone_at()** (5.25ms vs 7.17ms)

* Ambiguous-shortcut points are 4.8x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (46.6µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (7.17ms) - 15283% faster (154x)



Per-Query Latency Distribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Every table above times one pass over a whole batch of points, so it says what a workload costs on average. This one times each query on its own, in the default memory-mapped mode, and reports the distribution: the slowest queries in this package cost tens of times the median, because a point falling in a very large boundary polygon is answered by one ray cast across that whole ring. A batch mean cannot show that, which is why both are published (``scripts/measure_query_latency.py``, ``make latency``).

5,000 queries per point class, each keeping its fastest of 3 passes.


.. list-table::
   :header-rows: 1
   :widths: 40 10 10 10 10 10 10

   * - Point class
     - p50
     - p90
     - p99
     - p99.9
     - mean
     - max
   * - random points
     - 583ns
     - 709ns
     - 3.00µs
     - 4.67µs
     - 682ns
     - 6.54µs
   * - on-land points
     - 625ns
     - 2.50µs
     - 3.25µs
     - 4.13µs
     - 860ns
     - 5.13µs
   * - unique-shortcut points
     - 583ns
     - 708ns
     - 833ns
     - 875ns
     - 602ns
     - 917ns
   * - ambiguous-shortcut points
     - 2.88µs
     - 3.50µs
     - 4.83µs
     - 6.00µs
     - 2.89µs
     - 7.62µs
