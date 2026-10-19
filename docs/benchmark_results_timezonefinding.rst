

Timezone Finding Performance Benchmark
======================================


**~1.26µs per lookup, ~797k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 2.4454 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 14.7ms
     - 14.5ms
     - 403µs
     - 14.3ms
     - 15.9ms
     - 15
     - 5.87µs
     - 170k/s
   * - on-land points, in-memory
     - 4.00ms
     - 4.00ms
     - 32.4µs
     - 3.95ms
     - 4.08ms
     - 15
     - 1.60µs
     - 625k/s
   * - random points, in-memory
     - 3.14ms
     - 3.15ms
     - 28.8µs
     - 3.09ms
     - 3.18ms
     - 15
     - 1.26µs
     - 797k/s
   * - unique-shortcut points, in-memory
     - 2.59ms
     - 2.59ms
     - 25.7µs
     - 2.57ms
     - 2.65ms
     - 15
     - 1.04µs
     - 964k/s




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
     - 4.46ms
     - 4.46ms
     - 57.7µs
     - 4.38ms
     - 4.57ms
     - 15
     - 1.78µs
     - 561k/s




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
     - 14.6ms
     - 14.5ms
     - 251µs
     - 14.4ms
     - 15.4ms
     - 15
     - 5.82µs
     - 172k/s
   * - on-land points, file-based
     - 3.96ms
     - 3.95ms
     - 30.5µs
     - 3.93ms
     - 4.06ms
     - 15
     - 1.58µs
     - 631k/s
   * - random points, file-based
     - 3.14ms
     - 3.12ms
     - 50.8µs
     - 3.11ms
     - 3.31ms
     - 15
     - 1.26µs
     - 796k/s
   * - unique-shortcut points, file-based
     - 2.53ms
     - 2.52ms
     - 36.5µs
     - 2.51ms
     - 2.66ms
     - 15
     - 1.01µs
     - 988k/s




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
     - 4.42ms
     - 4.40ms
     - 37.7µs
     - 4.39ms
     - 4.52ms
     - 15
     - 1.77µs
     - 566k/s




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
     - 10.4ms
     - 10.5ms
     - 68.0µs
     - 10.4ms
     - 10.6ms
     - 15
     - 4.18µs
     - 239k/s
   * - random points, file-based
     - 607µs
     - 606µs
     - 17.6µs
     - 577µs
     - 638µs
     - 15
     - 243ns
     - 4.12M/s
   * - unique-shortcut points, file-based
     - 92.6µs
     - 81.8µs
     - 22.5µs
     - 79.3µs
     - 161µs
     - 15
     - 37.1ns
     - 27.0M/s




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
     - 10.5ms
     - 10.5ms
     - 73.3µs
     - 10.4ms
     - 10.7ms
     - 15
     - 4.22µs
     - 237k/s
   * - random points, file-based
     - 638µs
     - 643µs
     - 15.9µs
     - 615µs
     - 667µs
     - 15
     - 255ns
     - 3.92M/s
   * - unique-shortcut points, file-based
     - 119µs
     - 113µs
     - 11.9µs
     - 109µs
     - 149µs
     - 15
     - 47.7ns
     - 21.0M/s




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
     - 5.55ms
     - 5.53ms
     - 75.6µs
     - 5.51ms
     - 5.82ms
     - 15
     - 2.22µs
     - 450k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** and **file-based** perform about the same (3.14ms vs 3.14ms, 0.0% difference)

* On-land points: **file-based** and **in-memory** perform about the same (3.96ms vs 4.00ms, 0.9% difference)

* Unique-shortcut points: **file-based** is 3% faster (1.03x) than **in-memory** (2.53ms vs 2.59ms)

* Ambiguous-shortcut points: **file-based** and **in-memory** perform about the same (14.6ms vs 14.7ms, 0.8% difference)

* TimezoneFinder.timezone_at_land(): **file-based** and **in-memory** perform about the same (4.42ms vs 4.46ms, 0.9% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 418% faster (5.18x) than **TimezoneFinder.timezone_at()** (607µs vs 3.14ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 392% faster (4.92x) than **TimezoneFinder.timezone_at()** (638µs vs 3.14ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 2631% faster (27.3x) than **TimezoneFinder.timezone_at()** (92.6µs vs 2.53ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2023% faster (21.2x) than **TimezoneFinder.timezone_at()** (119µs vs 2.53ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 39% faster (1.39x) than **TimezoneFinder.timezone_at()** (10.4ms vs 14.6ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 38% faster (1.38x) than **TimezoneFinder.timezone_at()** (10.5ms vs 14.6ms)

* Ambiguous-shortcut points are 5.7x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (92.6µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (14.7ms) - 15740% faster (158x)



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
     - 1.12µs
     - 1.45µs
     - 6.55µs
     - 9.23µs
     - 1.36µs
     - 12.7µs
   * - on-land points
     - 1.20µs
     - 1.71µs
     - 6.89µs
     - 8.63µs
     - 1.72µs
     - 10.5µs
   * - unique-shortcut points
     - 1.08µs
     - 1.18µs
     - 1.49µs
     - 1.52µs
     - 1.11µs
     - 1.58µs
   * - ambiguous-shortcut points
     - 6.04µs
     - 6.93µs
     - 8.94µs
     - 12.4µs
     - 6.01µs
     - 15.2µs
