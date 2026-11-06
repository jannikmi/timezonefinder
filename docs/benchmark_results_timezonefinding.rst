

Timezone Finding Performance Benchmark
======================================


**~680ns per lookup, ~1.47M/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 9V45 96-Core Processor @ 4.2918 GHz, Python 3.13.17, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration records the ``min`` estimator for these rows: ``TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory``, ``TimezoneFinder.timezone_at() - random points, in-memory``, ``TimezoneFinder.timezone_at() - unique-shortcut points, in-memory``, ``TimezoneFinder.timezone_ids_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_ids_at() - random points, file-based``, ``TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - random points, file-based``, ``TimezoneFinder.timezone_names_at() - unique-shortcut points, file-based``. This published table leads with ``Mean`` and includes the full suite, so its values answer a different question from the trend chart.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.17 (CPython)

**NumPy Version**: 2.5.2

**Platform**: Linux x86_64



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


**Fixture Version**: 5

**Timezone Data Version**: 2026f



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
     - 8.79ms
     - 8.80ms
     - 107µs
     - 8.63ms
     - 8.99ms
     - 15
     - 3.52µs
     - 284k/s
   * - on-land points, in-memory
     - 2.15ms
     - 2.13ms
     - 101µs
     - 2.07ms
     - 2.44ms
     - 15
     - 861ns
     - 1.16M/s
   * - random points, in-memory
     - 1.70ms
     - 1.65ms
     - 121µs
     - 1.64ms
     - 2.09ms
     - 15
     - 680ns
     - 1.47M/s
   * - unique-shortcut points, in-memory
     - 1.42ms
     - 1.42ms
     - 20.0µs
     - 1.41ms
     - 1.49ms
     - 15
     - 569ns
     - 1.76M/s




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
     - 2.31ms
     - 2.29ms
     - 65.8µs
     - 2.25ms
     - 2.47ms
     - 15
     - 925ns
     - 1.08M/s




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
     - 8.94ms
     - 8.86ms
     - 199µs
     - 8.63ms
     - 9.31ms
     - 15
     - 3.57µs
     - 280k/s
   * - on-land points, file-based
     - 2.05ms
     - 2.04ms
     - 20.7µs
     - 2.03ms
     - 2.12ms
     - 15
     - 819ns
     - 1.22M/s
   * - random points, file-based
     - 1.69ms
     - 1.66ms
     - 97.2µs
     - 1.64ms
     - 2.01ms
     - 15
     - 678ns
     - 1.48M/s
   * - unique-shortcut points, file-based
     - 1.37ms
     - 1.37ms
     - 8.90µs
     - 1.36ms
     - 1.39ms
     - 15
     - 549ns
     - 1.82M/s




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
     - 2.28ms
     - 2.26ms
     - 49.1µs
     - 2.23ms
     - 2.41ms
     - 15
     - 913ns
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
     - 6.25ms
     - 6.24ms
     - 201µs
     - 6.06ms
     - 6.84ms
     - 15
     - 2.50µs
     - 400k/s
   * - random points, file-based
     - 344µs
     - 323µs
     - 41.2µs
     - 311µs
     - 452µs
     - 15
     - 138ns
     - 7.27M/s
   * - unique-shortcut points, file-based
     - 40.3µs
     - 38.1µs
     - 4.42µs
     - 37.6µs
     - 50.2µs
     - 15
     - 16.1ns
     - 62.0M/s




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
     - 6.45ms
     - 6.45ms
     - 240µs
     - 6.12ms
     - 6.86ms
     - 15
     - 2.58µs
     - 388k/s
   * - random points, file-based
     - 346µs
     - 330µs
     - 32.2µs
     - 321µs
     - 442µs
     - 15
     - 138ns
     - 7.23M/s
   * - unique-shortcut points, file-based
     - 54.5µs
     - 52.0µs
     - 5.69µs
     - 51.5µs
     - 70.2µs
     - 15
     - 21.8ns
     - 45.9M/s




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
     - 2.93ms
     - 2.91ms
     - 54.1µs
     - 2.87ms
     - 3.07ms
     - 15
     - 1.17µs
     - 854k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **file-based** and **in-memory** perform about the same (1.69ms vs 1.70ms, 0.4% difference)

* On-land points: **file-based** is 5% faster (1.05x) than **in-memory** (2.05ms vs 2.15ms)

* Unique-shortcut points: **file-based** is 4% faster (1.04x) than **in-memory** (1.37ms vs 1.42ms)

* Ambiguous-shortcut points: **in-memory** and **file-based** perform about the same (8.79ms vs 8.94ms, 1.7% difference)

* TimezoneFinder.timezone_at_land(): **file-based** and **in-memory** perform about the same (2.28ms vs 2.31ms, 1.3% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 392% faster (4.92x) than **TimezoneFinder.timezone_at()** (344µs vs 1.69ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 390% faster (4.90x) than **TimezoneFinder.timezone_at()** (346µs vs 1.69ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 3307% faster (34.1x) than **TimezoneFinder.timezone_at()** (40.3µs vs 1.37ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2419% faster (25.2x) than **TimezoneFinder.timezone_at()** (54.5µs vs 1.37ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 43% faster (1.43x) than **TimezoneFinder.timezone_at()** (6.25ms vs 8.94ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 39% faster (1.39x) than **TimezoneFinder.timezone_at()** (6.45ms vs 8.94ms)

* Ambiguous-shortcut points are 6.2x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (40.3µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (8.94ms) - 22065% faster (222x)



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
     - 601ns
     - 791ns
     - 3.91µs
     - 5.46µs
     - 740ns
     - 7.67µs
   * - on-land points
     - 621ns
     - 1.01µs
     - 4.39µs
     - 5.85µs
     - 942ns
     - 7.56µs
   * - unique-shortcut points
     - 581ns
     - 661ns
     - 822ns
     - 902ns
     - 599ns
     - 971ns
   * - ambiguous-shortcut points
     - 3.36µs
     - 4.24µs
     - 5.84µs
     - 7.94µs
     - 3.41µs
     - 9.36µs
