

Timezone Finding Performance Benchmark
======================================


**~1.24µs per lookup, ~808k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Darwin arm64, Apple M1 Pro, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration records the ``min`` estimator for these rows: ``TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory``, ``TimezoneFinder.timezone_at() - random points, in-memory``, ``TimezoneFinder.timezone_at() - unique-shortcut points, in-memory``, ``TimezoneFinder.timezone_ids_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_ids_at() - random points, file-based``, ``TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - random points, file-based``, ``TimezoneFinder.timezone_names_at() - unique-shortcut points, file-based``. This published table leads with ``Mean`` and includes the full suite, so its values answer a different question from the trend chart.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.14.2 (CPython)

**NumPy Version**: 2.5.2

**Platform**: Darwin arm64

**Processor**: arm



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
     - 13.2ms
     - 13.2ms
     - 645µs
     - 12.1ms
     - 14.2ms
     - 15
     - 5.26µs
     - 190k/s
   * - on-land points, in-memory
     - 4.21ms
     - 4.03ms
     - 365µs
     - 3.87ms
     - 4.91ms
     - 15
     - 1.69µs
     - 593k/s
   * - random points, in-memory
     - 3.09ms
     - 3.05ms
     - 145µs
     - 3.00ms
     - 3.57ms
     - 15
     - 1.24µs
     - 808k/s
   * - unique-shortcut points, in-memory
     - 2.18ms
     - 2.14ms
     - 142µs
     - 2.02ms
     - 2.51ms
     - 15
     - 873ns
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
   * - in-memory
     - 4.35ms
     - 4.28ms
     - 214µs
     - 4.14ms
     - 4.85ms
     - 15
     - 1.74µs
     - 574k/s




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
     - 13.0ms
     - 12.8ms
     - 942µs
     - 11.6ms
     - 14.6ms
     - 15
     - 5.20µs
     - 192k/s
   * - on-land points, file-based
     - 4.23ms
     - 4.13ms
     - 376µs
     - 3.89ms
     - 5.24ms
     - 15
     - 1.69µs
     - 591k/s
   * - random points, file-based
     - 3.14ms
     - 3.06ms
     - 172µs
     - 2.98ms
     - 3.62ms
     - 15
     - 1.26µs
     - 797k/s
   * - unique-shortcut points, file-based
     - 2.12ms
     - 2.08ms
     - 82.7µs
     - 2.02ms
     - 2.30ms
     - 15
     - 846ns
     - 1.18M/s




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
     - 4.73ms
     - 4.78ms
     - 367µs
     - 4.09ms
     - 5.46ms
     - 15
     - 1.89µs
     - 529k/s




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
     - 515µs
     - 9.50ms
     - 11.4ms
     - 15
     - 4.24µs
     - 236k/s
   * - random points, file-based
     - 2.20ms
     - 2.17ms
     - 105µs
     - 2.07ms
     - 2.40ms
     - 15
     - 882ns
     - 1.13M/s
   * - unique-shortcut points, file-based
     - 1.22ms
     - 1.21ms
     - 80.6µs
     - 1.13ms
     - 1.41ms
     - 15
     - 488ns
     - 2.05M/s




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
     - 10.3ms
     - 10.5ms
     - 717µs
     - 9.35ms
     - 11.4ms
     - 15
     - 4.12µs
     - 243k/s
   * - random points, file-based
     - 2.24ms
     - 2.24ms
     - 115µs
     - 2.11ms
     - 2.55ms
     - 15
     - 896ns
     - 1.12M/s
   * - unique-shortcut points, file-based
     - 1.23ms
     - 1.22ms
     - 75.9µs
     - 1.15ms
     - 1.39ms
     - 15
     - 493ns
     - 2.03M/s




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
     - 3.47ms
     - 3.36ms
     - 267µs
     - 3.17ms
     - 4.04ms
     - 15
     - 1.39µs
     - 721k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** and **file-based** perform about the same (3.09ms vs 3.14ms, 1.4% difference)

* On-land points: **in-memory** and **file-based** perform about the same (4.21ms vs 4.23ms, 0.3% difference)

* Unique-shortcut points: **file-based** is 3% faster (1.03x) than **in-memory** (2.12ms vs 2.18ms)

* Ambiguous-shortcut points: **file-based** and **in-memory** perform about the same (13.0ms vs 13.2ms, 1.3% difference)

* TimezoneFinder.timezone_at_land(): **in-memory** is 9% faster (1.09x) than **file-based** (4.35ms vs 4.73ms)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 42% faster (1.42x) than **TimezoneFinder.timezone_at()** (2.20ms vs 3.14ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 40% faster (1.40x) than **TimezoneFinder.timezone_at()** (2.24ms vs 3.14ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 73% faster (1.73x) than **TimezoneFinder.timezone_at()** (1.22ms vs 2.12ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 72% faster (1.72x) than **TimezoneFinder.timezone_at()** (1.23ms vs 2.12ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 23% faster (1.23x) than **TimezoneFinder.timezone_at()** (10.6ms vs 13.0ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 26% faster (1.26x) than **TimezoneFinder.timezone_at()** (10.3ms vs 13.0ms)

* Ambiguous-shortcut points are 6.0x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (1.22ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (13.2ms) - 979% faster (10.8x)



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
     - 959ns
     - 2.71µs
     - 8.58µs
     - 14.8µs
     - 1.44µs
     - 28.3µs
   * - on-land points
     - 917ns
     - 4.62µs
     - 7.75µs
     - 17.8µs
     - 1.69µs
     - 27.4µs
   * - unique-shortcut points
     - 833ns
     - 916ns
     - 958ns
     - 1.00µs
     - 843ns
     - 1.04µs
   * - ambiguous-shortcut points
     - 4.46µs
     - 7.08µs
     - 13.2µs
     - 24.8µs
     - 4.82µs
     - 26.3µs
