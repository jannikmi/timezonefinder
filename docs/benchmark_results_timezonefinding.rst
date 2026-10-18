

Timezone Finding Performance Benchmark
======================================


**~1.08µs per lookup, ~923k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, INTEL(R) XEON(R) PLATINUM 8573C @ 3.1028 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 12.6ms
     - 12.5ms
     - 197µs
     - 12.4ms
     - 13.2ms
     - 15
     - 5.03µs
     - 199k/s
   * - on-land points, in-memory
     - 3.51ms
     - 3.51ms
     - 69.6µs
     - 3.39ms
     - 3.65ms
     - 15
     - 1.40µs
     - 713k/s
   * - random points, in-memory
     - 2.71ms
     - 2.71ms
     - 50.0µs
     - 2.65ms
     - 2.81ms
     - 15
     - 1.08µs
     - 923k/s
   * - unique-shortcut points, in-memory
     - 2.19ms
     - 2.18ms
     - 63.5µs
     - 2.13ms
     - 2.34ms
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
   * - in-memory
     - 3.83ms
     - 3.83ms
     - 58.5µs
     - 3.74ms
     - 3.97ms
     - 15
     - 1.53µs
     - 652k/s




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
     - 12.6ms
     - 12.5ms
     - 330µs
     - 12.3ms
     - 13.6ms
     - 15
     - 5.03µs
     - 199k/s
   * - on-land points, file-based
     - 3.50ms
     - 3.46ms
     - 84.5µs
     - 3.41ms
     - 3.72ms
     - 15
     - 1.40µs
     - 714k/s
   * - random points, file-based
     - 2.71ms
     - 2.69ms
     - 69.6µs
     - 2.63ms
     - 2.84ms
     - 15
     - 1.08µs
     - 923k/s
   * - unique-shortcut points, file-based
     - 2.18ms
     - 2.17ms
     - 31.7µs
     - 2.14ms
     - 2.25ms
     - 15
     - 872ns
     - 1.15M/s




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
     - 3.82ms
     - 3.83ms
     - 63.3µs
     - 3.72ms
     - 3.92ms
     - 15
     - 1.53µs
     - 655k/s




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
     - 9.16ms
     - 9.13ms
     - 230µs
     - 8.93ms
     - 9.66ms
     - 15
     - 3.67µs
     - 273k/s
   * - random points, file-based
     - 516µs
     - 517µs
     - 22.7µs
     - 486µs
     - 576µs
     - 15
     - 206ns
     - 4.85M/s
   * - unique-shortcut points, file-based
     - 71.0µs
     - 68.5µs
     - 8.31µs
     - 64.9µs
     - 98.2µs
     - 15
     - 28.4ns
     - 35.2M/s




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
     - 9.28ms
     - 9.26ms
     - 243µs
     - 9.03ms
     - 10.1ms
     - 15
     - 3.71µs
     - 269k/s
   * - random points, file-based
     - 553µs
     - 549µs
     - 29.5µs
     - 519µs
     - 620µs
     - 15
     - 221ns
     - 4.52M/s
   * - unique-shortcut points, file-based
     - 92.3µs
     - 87.2µs
     - 13.5µs
     - 85.3µs
     - 138µs
     - 15
     - 36.9ns
     - 27.1M/s




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
     - 4.54ms
     - 4.53ms
     - 64.2µs
     - 4.45ms
     - 4.70ms
     - 15
     - 1.82µs
     - 550k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** and **file-based** perform about the same (2.71ms vs 2.71ms, 0.0% difference)

* On-land points: **file-based** and **in-memory** perform about the same (3.50ms vs 3.51ms, 0.1% difference)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.18ms vs 2.19ms, 0.4% difference)

* Ambiguous-shortcut points: **file-based** and **in-memory** perform about the same (12.6ms vs 12.6ms, 0.1% difference)

* TimezoneFinder.timezone_at_land(): **file-based** and **in-memory** perform about the same (3.82ms vs 3.83ms, 0.4% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 425% faster (5.25x) than **TimezoneFinder.timezone_at()** (516µs vs 2.71ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 390% faster (4.90x) than **TimezoneFinder.timezone_at()** (553µs vs 2.71ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 2973% faster (30.7x) than **TimezoneFinder.timezone_at()** (71.0µs vs 2.18ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2261% faster (23.6x) than **TimezoneFinder.timezone_at()** (92.3µs vs 2.18ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 37% faster (1.37x) than **TimezoneFinder.timezone_at()** (9.16ms vs 12.6ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 35% faster (1.35x) than **TimezoneFinder.timezone_at()** (9.28ms vs 12.6ms)

* Ambiguous-shortcut points are 5.7x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (71.0µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (12.6ms) - 17632% faster (177x)



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
     - 1.24µs
     - 5.46µs
     - 8.02µs
     - 1.14µs
     - 11.9µs
   * - on-land points
     - 970ns
     - 4.42µs
     - 5.87µs
     - 7.65µs
     - 1.46µs
     - 9.12µs
   * - unique-shortcut points
     - 899ns
     - 1.12µs
     - 1.29µs
     - 1.35µs
     - 926ns
     - 1.38µs
   * - ambiguous-shortcut points
     - 5.01µs
     - 6.05µs
     - 8.20µs
     - 11.2µs
     - 5.01µs
     - 14.4µs
