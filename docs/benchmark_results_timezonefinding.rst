

Timezone Finding Performance Benchmark
======================================


**~1.09µs per lookup, ~916k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 3.9326 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 11.3ms
     - 11.3ms
     - 130µs
     - 11.1ms
     - 11.5ms
     - 15
     - 4.52µs
     - 221k/s
   * - on-land points, in-memory
     - 3.24ms
     - 3.23ms
     - 79.9µs
     - 3.11ms
     - 3.37ms
     - 15
     - 1.29µs
     - 772k/s
   * - random points, in-memory
     - 2.73ms
     - 2.73ms
     - 26.7µs
     - 2.68ms
     - 2.77ms
     - 15
     - 1.09µs
     - 916k/s
   * - unique-shortcut points, in-memory
     - 2.09ms
     - 2.09ms
     - 28.8µs
     - 2.05ms
     - 2.14ms
     - 15
     - 837ns
     - 1.20M/s




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
     - 3.46ms
     - 3.46ms
     - 17.8µs
     - 3.43ms
     - 3.49ms
     - 15
     - 1.38µs
     - 723k/s




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
     - 11.3ms
     - 11.3ms
     - 176µs
     - 11.1ms
     - 11.7ms
     - 15
     - 4.51µs
     - 222k/s
   * - on-land points, file-based
     - 3.08ms
     - 3.07ms
     - 65.2µs
     - 3.02ms
     - 3.28ms
     - 15
     - 1.23µs
     - 813k/s
   * - random points, file-based
     - 2.67ms
     - 2.63ms
     - 110µs
     - 2.55ms
     - 2.87ms
     - 15
     - 1.07µs
     - 935k/s
   * - unique-shortcut points, file-based
     - 2.21ms
     - 2.21ms
     - 94.5µs
     - 2.10ms
     - 2.37ms
     - 15
     - 884ns
     - 1.13M/s




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
     - 3.46ms
     - 3.44ms
     - 45.8µs
     - 3.43ms
     - 3.61ms
     - 15
     - 1.38µs
     - 723k/s




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
     - 8.38ms
     - 8.25ms
     - 372µs
     - 8.08ms
     - 9.43ms
     - 15
     - 3.35µs
     - 298k/s
   * - random points, file-based
     - 436µs
     - 428µs
     - 20.5µs
     - 413µs
     - 490µs
     - 15
     - 174ns
     - 5.73M/s
   * - unique-shortcut points, file-based
     - 57.6µs
     - 55.4µs
     - 5.71µs
     - 53.4µs
     - 72.3µs
     - 15
     - 23.0ns
     - 43.4M/s




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
     - 8.31ms
     - 8.25ms
     - 244µs
     - 8.15ms
     - 9.16ms
     - 15
     - 3.32µs
     - 301k/s
   * - random points, file-based
     - 585µs
     - 574µs
     - 49.9µs
     - 523µs
     - 679µs
     - 15
     - 234ns
     - 4.27M/s
   * - unique-shortcut points, file-based
     - 79.6µs
     - 76.6µs
     - 8.62µs
     - 74.8µs
     - 109µs
     - 15
     - 31.9ns
     - 31.4M/s




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
     - 4.37ms
     - 4.33ms
     - 119µs
     - 4.27ms
     - 4.68ms
     - 15
     - 1.75µs
     - 572k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **file-based** is 2% faster (1.02x) than **in-memory** (2.67ms vs 2.73ms)

* On-land points: **file-based** is 5% faster (1.05x) than **in-memory** (3.08ms vs 3.24ms)

* Unique-shortcut points: **in-memory** is 6% faster (1.06x) than **file-based** (2.09ms vs 2.21ms)

* Ambiguous-shortcut points: **file-based** and **in-memory** perform about the same (11.3ms vs 11.3ms, 0.1% difference)

* TimezoneFinder.timezone_at_land(): **file-based** and **in-memory** perform about the same (3.46ms vs 3.46ms, 0.0% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 513% faster (6.13x) than **TimezoneFinder.timezone_at()** (436µs vs 2.67ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 357% faster (4.57x) than **TimezoneFinder.timezone_at()** (585µs vs 2.67ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 3737% faster (38.4x) than **TimezoneFinder.timezone_at()** (57.6µs vs 2.21ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2674% faster (27.7x) than **TimezoneFinder.timezone_at()** (79.6µs vs 2.21ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 35% faster (1.35x) than **TimezoneFinder.timezone_at()** (8.38ms vs 11.3ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 36% faster (1.36x) than **TimezoneFinder.timezone_at()** (8.31ms vs 11.3ms)

* Ambiguous-shortcut points are 5.4x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (57.6µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (11.3ms) - 19526% faster (196x)



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
     - 922ns
     - 1.18µs
     - 5.27µs
     - 7.43µs
     - 1.11µs
     - 9.69µs
   * - on-land points
     - 911ns
     - 1.27µs
     - 5.07µs
     - 6.29µs
     - 1.27µs
     - 7.89µs
   * - unique-shortcut points
     - 911ns
     - 1.02µs
     - 1.29µs
     - 1.35µs
     - 934ns
     - 1.54µs
   * - ambiguous-shortcut points
     - 4.66µs
     - 5.41µs
     - 6.91µs
     - 9.78µs
     - 4.64µs
     - 12.4µs
