

Timezone Finding Performance Benchmark
======================================


**~1.32µs per lookup, ~760k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2440 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 14.5ms
     - 14.5ms
     - 117µs
     - 14.4ms
     - 14.8ms
     - 15
     - 5.81µs
     - 172k/s
   * - on-land points, in-memory
     - 4.23ms
     - 4.23ms
     - 49.6µs
     - 4.16ms
     - 4.35ms
     - 15
     - 1.69µs
     - 591k/s
   * - random points, in-memory
     - 3.29ms
     - 3.29ms
     - 27.1µs
     - 3.26ms
     - 3.36ms
     - 15
     - 1.32µs
     - 760k/s
   * - unique-shortcut points, in-memory
     - 2.58ms
     - 2.58ms
     - 20.8µs
     - 2.57ms
     - 2.65ms
     - 15
     - 1.03µs
     - 968k/s




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
     - 4.60ms
     - 91.9µs
     - 4.58ms
     - 4.92ms
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
     - 206µs
     - 14.3ms
     - 15.2ms
     - 15
     - 5.78µs
     - 173k/s
   * - on-land points, file-based
     - 4.20ms
     - 4.18ms
     - 50.5µs
     - 4.17ms
     - 4.37ms
     - 15
     - 1.68µs
     - 596k/s
   * - random points, file-based
     - 3.31ms
     - 3.32ms
     - 26.5µs
     - 3.26ms
     - 3.35ms
     - 15
     - 1.32µs
     - 755k/s
   * - unique-shortcut points, file-based
     - 2.58ms
     - 2.58ms
     - 13.0µs
     - 2.57ms
     - 2.62ms
     - 15
     - 1.03µs
     - 968k/s




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
     - 4.59ms
     - 4.59ms
     - 16.3µs
     - 4.57ms
     - 4.62ms
     - 15
     - 1.84µs
     - 544k/s




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
     - 10.5ms
     - 10.5ms
     - 44.7µs
     - 10.4ms
     - 10.6ms
     - 15
     - 4.20µs
     - 238k/s
   * - random points, file-based
     - 683µs
     - 679µs
     - 24.7µs
     - 645µs
     - 739µs
     - 15
     - 273ns
     - 3.66M/s
   * - unique-shortcut points, file-based
     - 85.2µs
     - 82.1µs
     - 9.91µs
     - 78.9µs
     - 117µs
     - 15
     - 34.1ns
     - 29.3M/s




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
     - 10.5ms
     - 130µs
     - 10.4ms
     - 11.0ms
     - 15
     - 4.23µs
     - 237k/s
   * - random points, file-based
     - 716µs
     - 712µs
     - 25.0µs
     - 682µs
     - 762µs
     - 15
     - 287ns
     - 3.49M/s
   * - unique-shortcut points, file-based
     - 115µs
     - 111µs
     - 9.96µs
     - 108µs
     - 143µs
     - 15
     - 46.0ns
     - 21.7M/s




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
     - 5.58ms
     - 5.56ms
     - 45.8µs
     - 5.54ms
     - 5.72ms
     - 15
     - 2.23µs
     - 448k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** and **file-based** perform about the same (3.29ms vs 3.31ms, 0.7% difference)

* On-land points: **file-based** and **in-memory** perform about the same (4.20ms vs 4.23ms, 0.8% difference)

* Unique-shortcut points: **in-memory** and **file-based** perform about the same (2.58ms vs 2.58ms, 0.0% difference)

* Ambiguous-shortcut points: **file-based** and **in-memory** perform about the same (14.5ms vs 14.5ms, 0.5% difference)

* TimezoneFinder.timezone_at_land(): **file-based** and **in-memory** perform about the same (4.59ms vs 4.64ms, 1.1% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 385% faster (4.85x) than **TimezoneFinder.timezone_at()** (683µs vs 3.31ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 362% faster (4.62x) than **TimezoneFinder.timezone_at()** (716µs vs 3.31ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 2931% faster (30.3x) than **TimezoneFinder.timezone_at()** (85.2µs vs 2.58ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2144% faster (22.4x) than **TimezoneFinder.timezone_at()** (115µs vs 2.58ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 38% faster (1.38x) than **TimezoneFinder.timezone_at()** (10.5ms vs 14.5ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 37% faster (1.37x) than **TimezoneFinder.timezone_at()** (10.6ms vs 14.5ms)

* Ambiguous-shortcut points are 5.6x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (85.2µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (14.5ms) - 16949% faster (170x)



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
     - 1.13µs
     - 1.49µs
     - 6.66µs
     - 9.23µs
     - 1.41µs
     - 14.1µs
   * - on-land points
     - 1.20µs
     - 5.51µs
     - 6.86µs
     - 9.51µs
     - 1.80µs
     - 10.5µs
   * - unique-shortcut points
     - 1.10µs
     - 1.35µs
     - 1.52µs
     - 1.56µs
     - 1.13µs
     - 1.67µs
   * - ambiguous-shortcut points
     - 6.22µs
     - 7.07µs
     - 9.03µs
     - 11.8µs
     - 6.16µs
     - 15.1µs
