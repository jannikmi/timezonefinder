

Timezone Finding Performance Benchmark
======================================


**~1.31µs per lookup, ~762k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2441 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 14.8ms
     - 14.7ms
     - 262µs
     - 14.4ms
     - 15.4ms
     - 15
     - 5.91µs
     - 169k/s
   * - on-land points, in-memory
     - 4.21ms
     - 4.17ms
     - 83.1µs
     - 4.16ms
     - 4.47ms
     - 15
     - 1.69µs
     - 593k/s
   * - random points, in-memory
     - 3.28ms
     - 3.25ms
     - 54.4µs
     - 3.22ms
     - 3.42ms
     - 15
     - 1.31µs
     - 762k/s
   * - unique-shortcut points, in-memory
     - 2.57ms
     - 2.56ms
     - 21.9µs
     - 2.55ms
     - 2.61ms
     - 15
     - 1.03µs
     - 971k/s




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
     - 4.78ms
     - 4.77ms
     - 65.6µs
     - 4.70ms
     - 4.94ms
     - 15
     - 1.91µs
     - 523k/s




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
     - 14.7ms
     - 14.6ms
     - 358µs
     - 14.4ms
     - 15.8ms
     - 15
     - 5.88µs
     - 170k/s
   * - on-land points, file-based
     - 4.26ms
     - 4.25ms
     - 56.7µs
     - 4.20ms
     - 4.42ms
     - 15
     - 1.70µs
     - 587k/s
   * - random points, file-based
     - 3.26ms
     - 3.25ms
     - 33.4µs
     - 3.22ms
     - 3.34ms
     - 15
     - 1.30µs
     - 767k/s
   * - unique-shortcut points, file-based
     - 2.62ms
     - 2.62ms
     - 25.2µs
     - 2.59ms
     - 2.69ms
     - 15
     - 1.05µs
     - 953k/s




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
     - 4.74ms
     - 4.73ms
     - 39.8µs
     - 4.68ms
     - 4.85ms
     - 15
     - 1.90µs
     - 528k/s




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
     - 10.8ms
     - 10.7ms
     - 183µs
     - 10.6ms
     - 11.3ms
     - 15
     - 4.32µs
     - 232k/s
   * - random points, file-based
     - 661µs
     - 657µs
     - 24.1µs
     - 630µs
     - 719µs
     - 15
     - 265ns
     - 3.78M/s
   * - unique-shortcut points, file-based
     - 86.5µs
     - 81.8µs
     - 11.1µs
     - 78.1µs
     - 114µs
     - 15
     - 34.6ns
     - 28.9M/s




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
     - 101µs
     - 10.6ms
     - 11.0ms
     - 15
     - 4.28µs
     - 234k/s
   * - random points, file-based
     - 699µs
     - 696µs
     - 20.6µs
     - 664µs
     - 739µs
     - 15
     - 280ns
     - 3.57M/s
   * - unique-shortcut points, file-based
     - 117µs
     - 110µs
     - 14.0µs
     - 109µs
     - 155µs
     - 15
     - 46.7ns
     - 21.4M/s




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
     - 5.70ms
     - 5.69ms
     - 23.7µs
     - 5.67ms
     - 5.73ms
     - 15
     - 2.28µs
     - 439k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **file-based** and **in-memory** perform about the same (3.26ms vs 3.28ms, 0.6% difference)

* On-land points: **in-memory** and **file-based** perform about the same (4.21ms vs 4.26ms, 1.2% difference)

* Unique-shortcut points: **in-memory** and **file-based** perform about the same (2.57ms vs 2.62ms, 1.9% difference)

* Ambiguous-shortcut points: **file-based** and **in-memory** perform about the same (14.7ms vs 14.8ms, 0.5% difference)

* TimezoneFinder.timezone_at_land(): **file-based** and **in-memory** perform about the same (4.74ms vs 4.78ms, 0.9% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 393% faster (4.93x) than **TimezoneFinder.timezone_at()** (661µs vs 3.26ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 366% faster (4.66x) than **TimezoneFinder.timezone_at()** (699µs vs 3.26ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 2933% faster (30.3x) than **TimezoneFinder.timezone_at()** (86.5µs vs 2.62ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2148% faster (22.5x) than **TimezoneFinder.timezone_at()** (117µs vs 2.62ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 36% faster (1.36x) than **TimezoneFinder.timezone_at()** (10.8ms vs 14.7ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 37% faster (1.37x) than **TimezoneFinder.timezone_at()** (10.7ms vs 14.7ms)

* Ambiguous-shortcut points are 5.7x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (86.5µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (14.8ms) - 16971% faster (171x)



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
     - 1.14µs
     - 1.51µs
     - 6.74µs
     - 9.61µs
     - 1.42µs
     - 14.5µs
   * - on-land points
     - 1.19µs
     - 5.40µs
     - 6.82µs
     - 9.32µs
     - 1.78µs
     - 10.4µs
   * - unique-shortcut points
     - 1.11µs
     - 1.39µs
     - 1.56µs
     - 1.60µs
     - 1.15µs
     - 1.65µs
   * - ambiguous-shortcut points
     - 5.90µs
     - 6.76µs
     - 8.78µs
     - 11.5µs
     - 5.85µs
     - 15.8µs
