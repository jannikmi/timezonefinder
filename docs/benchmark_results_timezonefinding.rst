

Timezone Finding Performance Benchmark
======================================


**~708ns per lookup, ~1.41M/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 9V45 96-Core Processor @ 4.3482 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration records the ``min`` estimator for these rows: ``TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory``, ``TimezoneFinder.timezone_at() - random points, in-memory``, ``TimezoneFinder.timezone_at() - unique-shortcut points, in-memory``, ``TimezoneFinder.timezone_ids_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_ids_at() - random points, file-based``, ``TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - random points, file-based``, ``TimezoneFinder.timezone_names_at() - unique-shortcut points, file-based``. This published table leads with ``Mean`` and includes the full suite, so its values answer a different question from the trend chart.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.16 (CPython)

**NumPy Version**: 2.5.2

**Platform**: Linux x86_64

**Processor**: x86_64



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

**Timezone Data Version**: 2026e



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
     - 7.99ms
     - 7.90ms
     - 173µs
     - 7.86ms
     - 8.48ms
     - 15
     - 3.20µs
     - 313k/s
   * - on-land points, in-memory
     - 2.11ms
     - 2.10ms
     - 43.1µs
     - 2.08ms
     - 2.21ms
     - 15
     - 845ns
     - 1.18M/s
   * - random points, in-memory
     - 1.77ms
     - 1.76ms
     - 40.4µs
     - 1.73ms
     - 1.87ms
     - 15
     - 708ns
     - 1.41M/s
   * - unique-shortcut points, in-memory
     - 1.37ms
     - 1.38ms
     - 11.8µs
     - 1.35ms
     - 1.40ms
     - 15
     - 550ns
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
   * - in-memory
     - 2.35ms
     - 2.34ms
     - 36.3µs
     - 2.32ms
     - 2.43ms
     - 15
     - 940ns
     - 1.06M/s




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
     - 7.96ms
     - 7.92ms
     - 209µs
     - 7.81ms
     - 8.67ms
     - 15
     - 3.19µs
     - 314k/s
   * - on-land points, file-based
     - 2.08ms
     - 2.07ms
     - 18.2µs
     - 2.06ms
     - 2.13ms
     - 15
     - 831ns
     - 1.20M/s
   * - random points, file-based
     - 1.70ms
     - 1.69ms
     - 47.6µs
     - 1.66ms
     - 1.85ms
     - 15
     - 680ns
     - 1.47M/s
   * - unique-shortcut points, file-based
     - 1.36ms
     - 1.36ms
     - 6.02µs
     - 1.35ms
     - 1.38ms
     - 15
     - 543ns
     - 1.84M/s




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
     - 2.33ms
     - 2.33ms
     - 23.4µs
     - 2.31ms
     - 2.40ms
     - 15
     - 934ns
     - 1.07M/s




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
     - 5.95ms
     - 5.87ms
     - 160µs
     - 5.83ms
     - 6.39ms
     - 15
     - 2.38µs
     - 421k/s
   * - random points, file-based
     - 320µs
     - 315µs
     - 18.1µs
     - 304µs
     - 371µs
     - 15
     - 128ns
     - 7.81M/s
   * - unique-shortcut points, file-based
     - 41.6µs
     - 37.4µs
     - 11.6µs
     - 37.2µs
     - 82.7µs
     - 15
     - 16.7ns
     - 60.0M/s




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
     - 5.87ms
     - 5.87ms
     - 42.7µs
     - 5.83ms
     - 6.00ms
     - 15
     - 2.35µs
     - 426k/s
   * - random points, file-based
     - 326µs
     - 324µs
     - 10.1µs
     - 318µs
     - 357µs
     - 15
     - 130ns
     - 7.67M/s
   * - unique-shortcut points, file-based
     - 53.7µs
     - 51.9µs
     - 3.74µs
     - 51.7µs
     - 63.3µs
     - 15
     - 21.5ns
     - 46.6M/s




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
     - 3.00ms
     - 3.00ms
     - 14.6µs
     - 2.98ms
     - 3.04ms
     - 15
     - 1.20µs
     - 833k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **file-based** is 4% faster (1.04x) than **in-memory** (1.70ms vs 1.77ms)

* On-land points: **file-based** and **in-memory** perform about the same (2.08ms vs 2.11ms, 1.7% difference)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (1.36ms vs 1.37ms, 1.2% difference)

* Ambiguous-shortcut points: **file-based** and **in-memory** perform about the same (7.96ms vs 7.99ms, 0.3% difference)

* TimezoneFinder.timezone_at_land(): **file-based** and **in-memory** perform about the same (2.33ms vs 2.35ms, 0.7% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 431% faster (5.31x) than **TimezoneFinder.timezone_at()** (320µs vs 1.70ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 422% faster (5.22x) than **TimezoneFinder.timezone_at()** (326µs vs 1.70ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 3162% faster (32.6x) than **TimezoneFinder.timezone_at()** (41.6µs vs 1.36ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2430% faster (25.3x) than **TimezoneFinder.timezone_at()** (53.7µs vs 1.36ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 34% faster (1.34x) than **TimezoneFinder.timezone_at()** (5.95ms vs 7.96ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 36% faster (1.36x) than **TimezoneFinder.timezone_at()** (5.87ms vs 7.96ms)

* Ambiguous-shortcut points are 5.8x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (41.6µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (7.99ms) - 19096% faster (192x)



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
     - 691ns
     - 862ns
     - 3.70µs
     - 5.15µs
     - 815ns
     - 7.76µs
   * - on-land points
     - 651ns
     - 972ns
     - 3.94µs
     - 5.14µs
     - 934ns
     - 6.09µs
   * - unique-shortcut points
     - 621ns
     - 681ns
     - 862ns
     - 941ns
     - 632ns
     - 961ns
   * - ambiguous-shortcut points
     - 3.28µs
     - 3.94µs
     - 5.28µs
     - 6.80µs
     - 3.28µs
     - 8.53µs
