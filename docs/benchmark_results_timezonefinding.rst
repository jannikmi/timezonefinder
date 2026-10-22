

Timezone Finding Performance Benchmark
======================================


**~1.07µs per lookup, ~935k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 3.6926 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 11.2ms
     - 11.2ms
     - 105µs
     - 11.1ms
     - 11.5ms
     - 15
     - 4.50µs
     - 222k/s
   * - on-land points, in-memory
     - 3.27ms
     - 3.26ms
     - 15.9µs
     - 3.24ms
     - 3.30ms
     - 15
     - 1.31µs
     - 765k/s
   * - random points, in-memory
     - 2.67ms
     - 2.66ms
     - 45.3µs
     - 2.62ms
     - 2.80ms
     - 15
     - 1.07µs
     - 935k/s
   * - unique-shortcut points, in-memory
     - 2.23ms
     - 2.22ms
     - 17.4µs
     - 2.21ms
     - 2.27ms
     - 15
     - 891ns
     - 1.12M/s




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
     - 3.60ms
     - 3.60ms
     - 22.9µs
     - 3.58ms
     - 3.66ms
     - 15
     - 1.44µs
     - 694k/s




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
     - 11.2ms
     - 206µs
     - 11.1ms
     - 11.8ms
     - 15
     - 4.51µs
     - 222k/s
   * - on-land points, file-based
     - 3.20ms
     - 3.20ms
     - 14.0µs
     - 3.17ms
     - 3.22ms
     - 15
     - 1.28µs
     - 782k/s
   * - random points, file-based
     - 2.67ms
     - 2.68ms
     - 26.8µs
     - 2.63ms
     - 2.73ms
     - 15
     - 1.07µs
     - 935k/s
   * - unique-shortcut points, file-based
     - 2.19ms
     - 2.19ms
     - 12.2µs
     - 2.17ms
     - 2.21ms
     - 15
     - 876ns
     - 1.14M/s




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
     - 3.54ms
     - 3.53ms
     - 31.5µs
     - 3.50ms
     - 3.59ms
     - 15
     - 1.42µs
     - 707k/s




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
     - 8.29ms
     - 8.22ms
     - 150µs
     - 8.12ms
     - 8.63ms
     - 15
     - 3.32µs
     - 302k/s
   * - random points, file-based
     - 448µs
     - 445µs
     - 20.0µs
     - 422µs
     - 491µs
     - 15
     - 179ns
     - 5.58M/s
   * - unique-shortcut points, file-based
     - 58.0µs
     - 55.9µs
     - 5.07µs
     - 53.7µs
     - 69.0µs
     - 15
     - 23.2ns
     - 43.1M/s




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
     - 8.37ms
     - 8.37ms
     - 66.0µs
     - 8.27ms
     - 8.48ms
     - 15
     - 3.35µs
     - 299k/s
   * - random points, file-based
     - 468µs
     - 466µs
     - 16.9µs
     - 447µs
     - 505µs
     - 15
     - 187ns
     - 5.34M/s
   * - unique-shortcut points, file-based
     - 78.5µs
     - 77.1µs
     - 4.66µs
     - 75.2µs
     - 93.5µs
     - 15
     - 31.4ns
     - 31.9M/s




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
     - 4.56ms
     - 4.56ms
     - 46.3µs
     - 4.50ms
     - 4.65ms
     - 15
     - 1.82µs
     - 548k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** and **file-based** perform about the same (2.67ms vs 2.67ms, 0.1% difference)

* On-land points: **file-based** is 2% faster (1.02x) than **in-memory** (3.20ms vs 3.27ms)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.19ms vs 2.23ms, 1.8% difference)

* Ambiguous-shortcut points: **in-memory** and **file-based** perform about the same (11.2ms vs 11.3ms, 0.2% difference)

* TimezoneFinder.timezone_at_land(): **file-based** and **in-memory** perform about the same (3.54ms vs 3.60ms, 1.9% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 497% faster (5.97x) than **TimezoneFinder.timezone_at()** (448µs vs 2.67ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 472% faster (5.72x) than **TimezoneFinder.timezone_at()** (468µs vs 2.67ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 3673% faster (37.7x) than **TimezoneFinder.timezone_at()** (58.0µs vs 2.19ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2690% faster (27.9x) than **TimezoneFinder.timezone_at()** (78.5µs vs 2.19ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 36% faster (1.36x) than **TimezoneFinder.timezone_at()** (8.29ms vs 11.3ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 35% faster (1.35x) than **TimezoneFinder.timezone_at()** (8.37ms vs 11.3ms)

* Ambiguous-shortcut points are 5.0x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (58.0µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (11.3ms) - 19327% faster (194x)



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
     - 851ns
     - 1.10µs
     - 4.91µs
     - 6.79µs
     - 1.02µs
     - 8.94µs
   * - on-land points
     - 882ns
     - 1.22µs
     - 4.98µs
     - 6.39µs
     - 1.24µs
     - 7.77µs
   * - unique-shortcut points
     - 841ns
     - 932ns
     - 1.17µs
     - 1.23µs
     - 857ns
     - 1.29µs
   * - ambiguous-shortcut points
     - 4.42µs
     - 5.11µs
     - 6.54µs
     - 8.38µs
     - 4.39µs
     - 9.84µs
