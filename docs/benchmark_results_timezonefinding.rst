

Timezone Finding Performance Benchmark
======================================


**~1.78µs per lookup, ~562k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 2.4454 GHz, Python 3.13.15, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration records the ``min`` estimator for these rows: ``TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory``, ``TimezoneFinder.timezone_at() - random points, in-memory``, ``TimezoneFinder.timezone_at() - unique-shortcut points, in-memory``, ``TimezoneFinder.timezone_ids_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_ids_at() - random points, file-based``, ``TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - random points, file-based``, ``TimezoneFinder.timezone_names_at() - unique-shortcut points, file-based``. This published table leads with ``Mean`` and includes the full suite, so its values answer a different question from the trend chart.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.15 (CPython)

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


**Fixture Version**: 3

**Timezone Data Version**: 2026c



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
     - 12.7ms
     - 12.7ms
     - 73.6µs
     - 12.6ms
     - 12.9ms
     - 15
     - 5.08µs
     - 197k/s
   * - on-land points, in-memory
     - 5.56ms
     - 5.56ms
     - 66.2µs
     - 5.49ms
     - 5.78ms
     - 15
     - 2.23µs
     - 449k/s
   * - random points, in-memory
     - 4.45ms
     - 4.43ms
     - 54.3µs
     - 4.39ms
     - 4.61ms
     - 15
     - 1.78µs
     - 562k/s
   * - unique-shortcut points, in-memory
     - 3.38ms
     - 3.35ms
     - 97.2µs
     - 3.34ms
     - 3.72ms
     - 15
     - 1.35µs
     - 741k/s




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
     - 5.99ms
     - 5.97ms
     - 52.5µs
     - 5.92ms
     - 6.10ms
     - 15
     - 2.40µs
     - 417k/s




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
     - 12.8ms
     - 12.8ms
     - 94.1µs
     - 12.7ms
     - 13.0ms
     - 15
     - 5.13µs
     - 195k/s
   * - on-land points, file-based
     - 5.57ms
     - 5.55ms
     - 62.4µs
     - 5.50ms
     - 5.76ms
     - 15
     - 2.23µs
     - 449k/s
   * - random points, file-based
     - 4.45ms
     - 4.44ms
     - 30.7µs
     - 4.42ms
     - 4.53ms
     - 15
     - 1.78µs
     - 561k/s
   * - unique-shortcut points, file-based
     - 3.32ms
     - 3.32ms
     - 47.8µs
     - 3.25ms
     - 3.45ms
     - 15
     - 1.33µs
     - 753k/s




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
     - 6.03ms
     - 6.02ms
     - 47.3µs
     - 5.97ms
     - 6.15ms
     - 15
     - 2.41µs
     - 415k/s




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
     - 10.6ms
     - 10.6ms
     - 70.3µs
     - 10.6ms
     - 10.8ms
     - 15
     - 4.26µs
     - 235k/s
   * - random points, file-based
     - 2.82ms
     - 2.80ms
     - 39.9µs
     - 2.77ms
     - 2.91ms
     - 15
     - 1.13µs
     - 887k/s
   * - unique-shortcut points, file-based
     - 1.75ms
     - 1.73ms
     - 28.5µs
     - 1.72ms
     - 1.80ms
     - 15
     - 699ns
     - 1.43M/s




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
     - 10.7ms
     - 10.7ms
     - 121µs
     - 10.6ms
     - 11.0ms
     - 15
     - 4.28µs
     - 234k/s
   * - random points, file-based
     - 2.85ms
     - 2.85ms
     - 29.1µs
     - 2.80ms
     - 2.89ms
     - 15
     - 1.14µs
     - 878k/s
   * - unique-shortcut points, file-based
     - 1.79ms
     - 1.78ms
     - 24.3µs
     - 1.76ms
     - 1.83ms
     - 15
     - 714ns
     - 1.40M/s




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
     - 5.49ms
     - 5.48ms
     - 24.7µs
     - 5.45ms
     - 5.55ms
     - 15
     - 2.19µs
     - 456k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** and **file-based** perform about the same (4.45ms vs 4.45ms, 0.1% difference)

* On-land points: **in-memory** and **file-based** perform about the same (5.56ms vs 5.57ms, 0.2% difference)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (3.32ms vs 3.38ms, 1.7% difference)

* Ambiguous-shortcut points: **in-memory** and **file-based** perform about the same (12.7ms vs 12.8ms, 0.9% difference)

* TimezoneFinder.timezone_at_land(): **in-memory** and **file-based** perform about the same (5.99ms vs 6.03ms, 0.7% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 58% faster (1.58x) than **TimezoneFinder.timezone_at()** (2.82ms vs 4.45ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 56% faster (1.56x) than **TimezoneFinder.timezone_at()** (2.85ms vs 4.45ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 90% faster (1.90x) than **TimezoneFinder.timezone_at()** (1.75ms vs 3.32ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 86% faster (1.86x) than **TimezoneFinder.timezone_at()** (1.79ms vs 3.32ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 20% faster (1.20x) than **TimezoneFinder.timezone_at()** (10.6ms vs 12.8ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 20% faster (1.20x) than **TimezoneFinder.timezone_at()** (10.7ms vs 12.8ms)

* Ambiguous-shortcut points are 3.8x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (1.75ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (12.8ms) - 633% faster (7.33x)



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
     - 1.45µs
     - 3.31µs
     - 6.41µs
     - 9.86µs
     - 1.83µs
     - 11.6µs
   * - on-land points
     - 1.48µs
     - 5.86µs
     - 7.54µs
     - 10.1µs
     - 2.31µs
     - 16.6µs
   * - unique-shortcut points
     - 1.45µs
     - 1.51µs
     - 1.57µs
     - 1.63µs
     - 1.45µs
     - 1.69µs
   * - ambiguous-shortcut points
     - 5.59µs
     - 6.45µs
     - 8.90µs
     - 15.0µs
     - 5.22µs
     - 26.1µs
