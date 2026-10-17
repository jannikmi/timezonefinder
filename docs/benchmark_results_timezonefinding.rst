

Timezone Finding Performance Benchmark
======================================


**~1.35µs per lookup, ~741k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2420 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 14.4ms
     - 14.3ms
     - 277µs
     - 14.2ms
     - 15.0ms
     - 15
     - 5.77µs
     - 173k/s
   * - on-land points, in-memory
     - 4.20ms
     - 4.20ms
     - 22.2µs
     - 4.18ms
     - 4.26ms
     - 15
     - 1.68µs
     - 595k/s
   * - random points, in-memory
     - 3.37ms
     - 3.34ms
     - 133µs
     - 3.26ms
     - 3.81ms
     - 15
     - 1.35µs
     - 741k/s
   * - unique-shortcut points, in-memory
     - 2.58ms
     - 2.57ms
     - 33.3µs
     - 2.54ms
     - 2.67ms
     - 15
     - 1.03µs
     - 970k/s




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
     - 4.64ms
     - 4.64ms
     - 30.3µs
     - 4.60ms
     - 4.69ms
     - 15
     - 1.86µs
     - 539k/s




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
     - 14.5ms
     - 14.4ms
     - 218µs
     - 14.3ms
     - 15.1ms
     - 15
     - 5.78µs
     - 173k/s
   * - on-land points, file-based
     - 4.30ms
     - 4.28ms
     - 49.1µs
     - 4.22ms
     - 4.39ms
     - 15
     - 1.72µs
     - 582k/s
   * - random points, file-based
     - 3.31ms
     - 3.28ms
     - 60.8µs
     - 3.25ms
     - 3.44ms
     - 15
     - 1.32µs
     - 756k/s
   * - unique-shortcut points, file-based
     - 2.59ms
     - 2.57ms
     - 27.5µs
     - 2.55ms
     - 2.64ms
     - 15
     - 1.03µs
     - 967k/s




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
     - 4.64ms
     - 4.65ms
     - 52.2µs
     - 4.57ms
     - 4.77ms
     - 15
     - 1.86µs
     - 539k/s




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
     - 181µs
     - 10.5ms
     - 11.1ms
     - 15
     - 4.24µs
     - 236k/s
   * - random points, file-based
     - 685µs
     - 683µs
     - 28.8µs
     - 641µs
     - 750µs
     - 15
     - 274ns
     - 3.65M/s
   * - unique-shortcut points, file-based
     - 85.6µs
     - 82.4µs
     - 9.45µs
     - 79.4µs
     - 116µs
     - 15
     - 34.3ns
     - 29.2M/s




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
     - 10.6ms
     - 10.6ms
     - 59.5µs
     - 10.5ms
     - 10.7ms
     - 15
     - 4.23µs
     - 236k/s
   * - random points, file-based
     - 696µs
     - 697µs
     - 17.4µs
     - 670µs
     - 729µs
     - 15
     - 278ns
     - 3.59M/s
   * - unique-shortcut points, file-based
     - 120µs
     - 114µs
     - 11.4µs
     - 110µs
     - 146µs
     - 15
     - 47.9ns
     - 20.9M/s




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
     - 5.51ms
     - 5.50ms
     - 36.5µs
     - 5.48ms
     - 5.59ms
     - 15
     - 2.20µs
     - 454k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **file-based** and **in-memory** perform about the same (3.31ms vs 3.37ms, 2.0% difference)

* On-land points: **in-memory** is 2% faster (1.02x) than **file-based** (4.20ms vs 4.30ms)

* Unique-shortcut points: **in-memory** and **file-based** perform about the same (2.58ms vs 2.59ms, 0.3% difference)

* Ambiguous-shortcut points: **in-memory** and **file-based** perform about the same (14.4ms vs 14.5ms, 0.2% difference)

* TimezoneFinder.timezone_at_land(): **file-based** and **in-memory** perform about the same (4.64ms vs 4.64ms, 0.1% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 383% faster (4.83x) than **TimezoneFinder.timezone_at()** (685µs vs 3.31ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 375% faster (4.75x) than **TimezoneFinder.timezone_at()** (696µs vs 3.31ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 2919% faster (30.2x) than **TimezoneFinder.timezone_at()** (85.6µs vs 2.59ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2057% faster (21.6x) than **TimezoneFinder.timezone_at()** (120µs vs 2.59ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 36% faster (1.36x) than **TimezoneFinder.timezone_at()** (10.6ms vs 14.5ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 37% faster (1.37x) than **TimezoneFinder.timezone_at()** (10.6ms vs 14.5ms)

* Ambiguous-shortcut points are 5.6x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (85.6µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (14.5ms) - 16781% faster (169x)



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
     - 1.16µs
     - 1.54µs
     - 6.98µs
     - 10.1µs
     - 1.45µs
     - 14.3µs
   * - on-land points
     - 1.19µs
     - 5.61µs
     - 7.42µs
     - 9.60µs
     - 1.82µs
     - 11.6µs
   * - unique-shortcut points
     - 1.12µs
     - 1.39µs
     - 1.56µs
     - 1.63µs
     - 1.15µs
     - 1.84µs
   * - ambiguous-shortcut points
     - 5.99µs
     - 6.96µs
     - 9.18µs
     - 12.2µs
     - 5.95µs
     - 15.5µs
