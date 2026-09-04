

Timezone Finding Performance Benchmark
======================================


**~2.18µs per lookup, ~458k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 2.8701 GHz, Python 3.13.15, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 21.8ms
     - 21.8ms
     - 189µs
     - 21.6ms
     - 22.1ms
     - 15
     - 8.72µs
     - 115k/s
   * - on-land points, in-memory
     - 7.05ms
     - 7.05ms
     - 55.8µs
     - 6.98ms
     - 7.18ms
     - 15
     - 2.82µs
     - 355k/s
   * - random points, in-memory
     - 5.45ms
     - 5.44ms
     - 31.7µs
     - 5.40ms
     - 5.50ms
     - 15
     - 2.18µs
     - 458k/s
   * - unique-shortcut points, in-memory
     - 3.49ms
     - 3.48ms
     - 26.2µs
     - 3.46ms
     - 3.53ms
     - 15
     - 1.39µs
     - 717k/s




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
     - 7.65ms
     - 7.63ms
     - 53.2µs
     - 7.60ms
     - 7.79ms
     - 15
     - 3.06µs
     - 327k/s




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
     - 21.8ms
     - 21.8ms
     - 96.7µs
     - 21.6ms
     - 22.0ms
     - 15
     - 8.72µs
     - 115k/s
   * - on-land points, file-based
     - 7.04ms
     - 7.03ms
     - 60.6µs
     - 6.98ms
     - 7.20ms
     - 15
     - 2.82µs
     - 355k/s
   * - random points, file-based
     - 5.44ms
     - 5.43ms
     - 59.3µs
     - 5.37ms
     - 5.63ms
     - 15
     - 2.18µs
     - 459k/s
   * - unique-shortcut points, file-based
     - 3.48ms
     - 3.48ms
     - 17.1µs
     - 3.45ms
     - 3.51ms
     - 15
     - 1.39µs
     - 719k/s




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
     - 7.52ms
     - 7.51ms
     - 42.9µs
     - 7.46ms
     - 7.60ms
     - 15
     - 3.01µs
     - 332k/s




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
     - 17.3ms
     - 17.3ms
     - 100µs
     - 17.1ms
     - 17.5ms
     - 15
     - 6.92µs
     - 144k/s
   * - random points, file-based
     - 3.58ms
     - 3.57ms
     - 48.4µs
     - 3.53ms
     - 3.70ms
     - 15
     - 1.43µs
     - 698k/s
   * - unique-shortcut points, file-based
     - 1.76ms
     - 1.75ms
     - 39.0µs
     - 1.71ms
     - 1.85ms
     - 15
     - 704ns
     - 1.42M/s




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
     - 17.4ms
     - 17.3ms
     - 346µs
     - 17.2ms
     - 18.3ms
     - 15
     - 6.98µs
     - 143k/s
   * - random points, file-based
     - 3.61ms
     - 3.61ms
     - 47.0µs
     - 3.53ms
     - 3.72ms
     - 15
     - 1.44µs
     - 692k/s
   * - unique-shortcut points, file-based
     - 1.79ms
     - 1.77ms
     - 43.2µs
     - 1.74ms
     - 1.88ms
     - 15
     - 715ns
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
     - 5.62ms
     - 5.61ms
     - 34.5µs
     - 5.58ms
     - 5.70ms
     - 15
     - 2.25µs
     - 445k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **file-based** and **in-memory** perform about the same (5.44ms vs 5.45ms, 0.2% difference)

* On-land points: **file-based** and **in-memory** perform about the same (7.04ms vs 7.05ms, 0.1% difference)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (3.48ms vs 3.49ms, 0.2% difference)

* Ambiguous-shortcut points: **file-based** and **in-memory** perform about the same (21.8ms vs 21.8ms, 0.0% difference)

* TimezoneFinder.timezone_at_land(): **file-based** and **in-memory** perform about the same (7.52ms vs 7.65ms, 1.8% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 52% faster (1.52x) than **TimezoneFinder.timezone_at()** (3.58ms vs 5.44ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 51% faster (1.51x) than **TimezoneFinder.timezone_at()** (3.61ms vs 5.44ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 98% faster (1.98x) than **TimezoneFinder.timezone_at()** (1.76ms vs 3.48ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 95% faster (1.95x) than **TimezoneFinder.timezone_at()** (1.79ms vs 3.48ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 26% faster (1.26x) than **TimezoneFinder.timezone_at()** (17.3ms vs 21.8ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 25% faster (1.25x) than **TimezoneFinder.timezone_at()** (17.4ms vs 21.8ms)

* Ambiguous-shortcut points are 6.3x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (1.76ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (21.8ms) - 1140% faster (12.4x)



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
     - 1.50µs
     - 4.70µs
     - 12.7µs
     - 21.1µs
     - 2.23µs
     - 42.5µs
   * - on-land points
     - 1.51µs
     - 7.96µs
     - 12.4µs
     - 29.7µs
     - 2.84µs
     - 43.1µs
   * - unique-shortcut points
     - 1.45µs
     - 1.53µs
     - 1.61µs
     - 1.68µs
     - 1.46µs
     - 1.75µs
   * - ambiguous-shortcut points
     - 7.93µs
     - 12.2µs
     - 21.3µs
     - 40.7µs
     - 8.44µs
     - 43.3µs
