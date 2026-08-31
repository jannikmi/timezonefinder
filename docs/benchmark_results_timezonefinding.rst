

Timezone Finding Performance Benchmark
======================================


**~1.56µs per lookup, ~640k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

*Measured on Darwin arm64, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.14.2 (CPython)

**NumPy Version**: 2.3.5

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
     - 15.8ms
     - 15.7ms
     - 1.00ms
     - 13.8ms
     - 19.6ms
     - 61
     - 6.34µs
     - 158k/s
   * - on-land points, in-memory
     - 5.12ms
     - 5.11ms
     - 462µs
     - 4.38ms
     - 6.27ms
     - 192
     - 2.05µs
     - 489k/s
   * - random points, in-memory
     - 3.90ms
     - 3.89ms
     - 375µs
     - 3.27ms
     - 4.73ms
     - 224
     - 1.56µs
     - 640k/s
   * - unique-shortcut points, in-memory
     - 2.36ms
     - 2.32ms
     - 206µs
     - 2.11ms
     - 3.56ms
     - 379
     - 945ns
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
   * - in-memory
     - 6.09ms
     - 6.12ms
     - 517µs
     - 5.18ms
     - 7.24ms
     - 157
     - 2.44µs
     - 411k/s




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
     - 17.9ms
     - 17.9ms
     - 810µs
     - 16.3ms
     - 19.6ms
     - 47
     - 7.14µs
     - 140k/s
   * - on-land points, file-based
     - 5.71ms
     - 5.69ms
     - 480µs
     - 4.84ms
     - 6.82ms
     - 147
     - 2.28µs
     - 438k/s
   * - random points, file-based
     - 4.22ms
     - 4.11ms
     - 1.12ms
     - 3.49ms
     - 15.4ms
     - 225
     - 1.69µs
     - 592k/s
   * - unique-shortcut points, file-based
     - 2.37ms
     - 2.32ms
     - 204µs
     - 2.11ms
     - 3.24ms
     - 432
     - 948ns
     - 1.05M/s




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
     - 6.70ms
     - 6.74ms
     - 556µs
     - 5.74ms
     - 7.91ms
     - 124
     - 2.68µs
     - 373k/s




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
     - 15.5ms
     - 15.1ms
     - 2.81ms
     - 13.2ms
     - 29.8ms
     - 60
     - 6.19µs
     - 162k/s
   * - random points, file-based
     - 2.81ms
     - 2.81ms
     - 250µs
     - 2.47ms
     - 3.37ms
     - 238
     - 1.12µs
     - 890k/s
   * - unique-shortcut points, file-based
     - 1.33ms
     - 1.28ms
     - 109µs
     - 1.21ms
     - 1.69ms
     - 691
     - 531ns
     - 1.88M/s




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
     - 15.2ms
     - 15.2ms
     - 837µs
     - 13.5ms
     - 16.8ms
     - 62
     - 6.08µs
     - 165k/s
   * - random points, file-based
     - 2.86ms
     - 2.86ms
     - 265µs
     - 2.50ms
     - 3.49ms
     - 269
     - 1.15µs
     - 873k/s
   * - unique-shortcut points, file-based
     - 1.36ms
     - 1.32ms
     - 111µs
     - 1.23ms
     - 1.77ms
     - 655
     - 542ns
     - 1.84M/s




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
     - 3.78ms
     - 3.77ms
     - 320µs
     - 3.25ms
     - 4.64ms
     - 298
     - 1.51µs
     - 662k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 8% faster (1.08x) than **file-based** (3.90ms vs 4.22ms)

* On-land points: **in-memory** is 12% faster (1.12x) than **file-based** (5.12ms vs 5.71ms)

* Unique-shortcut points: **in-memory** and **file-based** perform about the same (2.36ms vs 2.37ms, 0.3% difference)

* Ambiguous-shortcut points: **in-memory** is 13% faster (1.13x) than **file-based** (15.8ms vs 17.9ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 10% faster (1.10x) than **file-based** (6.09ms vs 6.70ms)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 50% faster (1.50x) than **TimezoneFinder.timezone_at()** (2.81ms vs 4.22ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 47% faster (1.47x) than **TimezoneFinder.timezone_at()** (2.86ms vs 4.22ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 79% faster (1.79x) than **TimezoneFinder.timezone_at()** (1.33ms vs 2.37ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 75% faster (1.75x) than **TimezoneFinder.timezone_at()** (1.36ms vs 2.37ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 15% faster (1.15x) than **TimezoneFinder.timezone_at()** (15.5ms vs 17.9ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 18% faster (1.18x) than **TimezoneFinder.timezone_at()** (15.2ms vs 17.9ms)

* Ambiguous-shortcut points are 6.7x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (1.33ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (17.9ms) - 1246% faster (13.5x)



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
     - 916ns
     - 2.58µs
     - 9.67µs
     - 15.3µs
     - 1.48µs
     - 27.2µs
   * - on-land points
     - 917ns
     - 6.37µs
     - 10.2µs
     - 19.2µs
     - 2.01µs
     - 27.5µs
   * - unique-shortcut points
     - 875ns
     - 958ns
     - 1.04µs
     - 1.08µs
     - 880ns
     - 1.17µs
   * - ambiguous-shortcut points
     - 6.33µs
     - 9.25µs
     - 15.2µs
     - 26.2µs
     - 6.33µs
     - 27.8µs
