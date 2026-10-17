

Timezone Finding Performance Benchmark
======================================


**~1.16µs per lookup, ~859k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, Intel(R) Xeon(R) Platinum 8370C CPU @ 2.7929 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 13.6ms
     - 13.5ms
     - 167µs
     - 13.4ms
     - 14.1ms
     - 15
     - 5.43µs
     - 184k/s
   * - on-land points, in-memory
     - 3.81ms
     - 3.79ms
     - 58.4µs
     - 3.77ms
     - 4.00ms
     - 15
     - 1.52µs
     - 656k/s
   * - random points, in-memory
     - 2.91ms
     - 2.90ms
     - 25.7µs
     - 2.89ms
     - 2.99ms
     - 15
     - 1.16µs
     - 859k/s
   * - unique-shortcut points, in-memory
     - 2.50ms
     - 2.44ms
     - 210µs
     - 2.36ms
     - 3.13ms
     - 15
     - 998ns
     - 1.00M/s




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
     - 4.17ms
     - 4.17ms
     - 28.9µs
     - 4.15ms
     - 4.24ms
     - 15
     - 1.67µs
     - 599k/s




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
     - 13.5ms
     - 13.5ms
     - 253µs
     - 13.3ms
     - 14.4ms
     - 15
     - 5.41µs
     - 185k/s
   * - on-land points, file-based
     - 3.78ms
     - 3.77ms
     - 29.5µs
     - 3.75ms
     - 3.85ms
     - 15
     - 1.51µs
     - 661k/s
   * - random points, file-based
     - 2.92ms
     - 2.92ms
     - 24.6µs
     - 2.91ms
     - 3.01ms
     - 15
     - 1.17µs
     - 856k/s
   * - unique-shortcut points, file-based
     - 2.39ms
     - 2.37ms
     - 81.8µs
     - 2.36ms
     - 2.69ms
     - 15
     - 958ns
     - 1.04M/s




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
     - 4.18ms
     - 4.17ms
     - 32.8µs
     - 4.14ms
     - 4.26ms
     - 15
     - 1.67µs
     - 599k/s




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
     - 10.2ms
     - 10.2ms
     - 147µs
     - 10.0ms
     - 10.6ms
     - 15
     - 4.08µs
     - 245k/s
   * - random points, file-based
     - 625µs
     - 612µs
     - 36.4µs
     - 590µs
     - 737µs
     - 15
     - 250ns
     - 4.00M/s
   * - unique-shortcut points, file-based
     - 71.5µs
     - 68.2µs
     - 8.48µs
     - 67.4µs
     - 96.8µs
     - 15
     - 28.6ns
     - 35.0M/s




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
     - 10.2ms
     - 10.1ms
     - 164µs
     - 10.0ms
     - 10.5ms
     - 15
     - 4.08µs
     - 245k/s
   * - random points, file-based
     - 653µs
     - 646µs
     - 27.5µs
     - 620µs
     - 725µs
     - 15
     - 261ns
     - 3.83M/s
   * - unique-shortcut points, file-based
     - 96.8µs
     - 93.3µs
     - 6.60µs
     - 92.1µs
     - 114µs
     - 15
     - 38.7ns
     - 25.8M/s




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
     - 5.31ms
     - 5.30ms
     - 31.2µs
     - 5.28ms
     - 5.40ms
     - 15
     - 2.13µs
     - 470k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** and **file-based** perform about the same (2.91ms vs 2.92ms, 0.4% difference)

* On-land points: **file-based** and **in-memory** perform about the same (3.78ms vs 3.81ms, 0.7% difference)

* Unique-shortcut points: **file-based** is 4% faster (1.04x) than **in-memory** (2.39ms vs 2.50ms)

* Ambiguous-shortcut points: **file-based** and **in-memory** perform about the same (13.5ms vs 13.6ms, 0.2% difference)

* TimezoneFinder.timezone_at_land(): **in-memory** and **file-based** perform about the same (4.17ms vs 4.18ms, 0.1% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 367% faster (4.67x) than **TimezoneFinder.timezone_at()** (625µs vs 2.92ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 348% faster (4.48x) than **TimezoneFinder.timezone_at()** (653µs vs 2.92ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 3251% faster (33.5x) than **TimezoneFinder.timezone_at()** (71.5µs vs 2.39ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2374% faster (24.7x) than **TimezoneFinder.timezone_at()** (96.8µs vs 2.39ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 33% faster (1.33x) than **TimezoneFinder.timezone_at()** (10.2ms vs 13.5ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 33% faster (1.33x) than **TimezoneFinder.timezone_at()** (10.2ms vs 13.5ms)

* Ambiguous-shortcut points are 5.4x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (71.5µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (13.6ms) - 18879% faster (190x)



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
     - 1.09µs
     - 1.41µs
     - 6.05µs
     - 9.38µs
     - 1.33µs
     - 14.6µs
   * - on-land points
     - 1.14µs
     - 4.94µs
     - 6.89µs
     - 9.43µs
     - 1.69µs
     - 11.4µs
   * - unique-shortcut points
     - 1.07µs
     - 1.31µs
     - 1.48µs
     - 1.52µs
     - 1.10µs
     - 1.55µs
   * - ambiguous-shortcut points
     - 5.53µs
     - 6.76µs
     - 9.04µs
     - 12.3µs
     - 5.58µs
     - 15.1µs
