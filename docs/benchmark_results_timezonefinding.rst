

Timezone Finding Performance Benchmark
======================================


**~1.17µs per lookup, ~858k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 2.8000 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 14.2ms
     - 14.2ms
     - 102µs
     - 14.0ms
     - 14.4ms
     - 15
     - 5.68µs
     - 176k/s
   * - on-land points, in-memory
     - 3.80ms
     - 3.77ms
     - 136µs
     - 3.75ms
     - 4.29ms
     - 15
     - 1.52µs
     - 658k/s
   * - random points, in-memory
     - 2.92ms
     - 2.90ms
     - 44.2µs
     - 2.87ms
     - 3.04ms
     - 15
     - 1.17µs
     - 858k/s
   * - unique-shortcut points, in-memory
     - 2.40ms
     - 2.42ms
     - 34.4µs
     - 2.35ms
     - 2.44ms
     - 15
     - 959ns
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
   * - in-memory
     - 4.16ms
     - 4.14ms
     - 57.7µs
     - 4.10ms
     - 4.28ms
     - 15
     - 1.66µs
     - 602k/s




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
     - 14.1ms
     - 14.0ms
     - 274µs
     - 13.7ms
     - 14.8ms
     - 15
     - 5.62µs
     - 178k/s
   * - on-land points, file-based
     - 3.80ms
     - 3.78ms
     - 38.3µs
     - 3.76ms
     - 3.88ms
     - 15
     - 1.52µs
     - 659k/s
   * - random points, file-based
     - 2.92ms
     - 2.90ms
     - 37.1µs
     - 2.89ms
     - 3.00ms
     - 15
     - 1.17µs
     - 857k/s
   * - unique-shortcut points, file-based
     - 2.36ms
     - 2.36ms
     - 15.3µs
     - 2.35ms
     - 2.39ms
     - 15
     - 946ns
     - 1.06M/s




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
     - 4.14ms
     - 4.12ms
     - 54.5µs
     - 4.11ms
     - 4.32ms
     - 15
     - 1.66µs
     - 604k/s




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
     - 10.8ms
     - 241µs
     - 10.5ms
     - 11.2ms
     - 15
     - 4.33µs
     - 231k/s
   * - random points, file-based
     - 627µs
     - 622µs
     - 37.3µs
     - 595µs
     - 746µs
     - 15
     - 251ns
     - 3.99M/s
   * - unique-shortcut points, file-based
     - 73.4µs
     - 68.9µs
     - 13.6µs
     - 67.8µs
     - 122µs
     - 15
     - 29.4ns
     - 34.0M/s




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
     - 10.8ms
     - 10.7ms
     - 137µs
     - 10.6ms
     - 11.0ms
     - 15
     - 4.30µs
     - 232k/s
   * - random points, file-based
     - 655µs
     - 644µs
     - 35.3µs
     - 624µs
     - 769µs
     - 15
     - 262ns
     - 3.82M/s
   * - unique-shortcut points, file-based
     - 96.1µs
     - 93.3µs
     - 5.69µs
     - 92.4µs
     - 111µs
     - 15
     - 38.5ns
     - 26.0M/s




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
     - 5.32ms
     - 5.32ms
     - 35.8µs
     - 5.27ms
     - 5.39ms
     - 15
     - 2.13µs
     - 470k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** and **file-based** perform about the same (2.92ms vs 2.92ms, 0.1% difference)

* On-land points: **file-based** and **in-memory** perform about the same (3.80ms vs 3.80ms, 0.2% difference)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.36ms vs 2.40ms, 1.4% difference)

* Ambiguous-shortcut points: **file-based** and **in-memory** perform about the same (14.1ms vs 14.2ms, 1.0% difference)

* TimezoneFinder.timezone_at_land(): **file-based** and **in-memory** perform about the same (4.14ms vs 4.16ms, 0.3% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 365% faster (4.65x) than **TimezoneFinder.timezone_at()** (627µs vs 2.92ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 346% faster (4.46x) than **TimezoneFinder.timezone_at()** (655µs vs 2.92ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 3119% faster (32.2x) than **TimezoneFinder.timezone_at()** (73.4µs vs 2.36ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2359% faster (24.6x) than **TimezoneFinder.timezone_at()** (96.1µs vs 2.36ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 30% faster (1.30x) than **TimezoneFinder.timezone_at()** (10.8ms vs 14.1ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 31% faster (1.31x) than **TimezoneFinder.timezone_at()** (10.8ms vs 14.1ms)

* Ambiguous-shortcut points are 5.9x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (73.4µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (14.2ms) - 19218% faster (193x)



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
     - 1.43µs
     - 6.33µs
     - 9.94µs
     - 1.35µs
     - 15.9µs
   * - on-land points
     - 1.12µs
     - 4.92µs
     - 6.66µs
     - 9.06µs
     - 1.67µs
     - 10.7µs
   * - unique-shortcut points
     - 1.08µs
     - 1.31µs
     - 1.51µs
     - 1.57µs
     - 1.11µs
     - 1.65µs
   * - ambiguous-shortcut points
     - 5.62µs
     - 6.88µs
     - 9.42µs
     - 12.7µs
     - 5.66µs
     - 15.9µs
