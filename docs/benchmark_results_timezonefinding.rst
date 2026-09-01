

Timezone Finding Performance Benchmark
======================================


**~1.39µs per lookup, ~720k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

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
     - 12.4ms
     - 12.3ms
     - 420µs
     - 12.2ms
     - 14.3ms
     - 72
     - 4.98µs
     - 201k/s
   * - on-land points, in-memory
     - 4.50ms
     - 4.36ms
     - 276µs
     - 4.26ms
     - 5.36ms
     - 202
     - 1.80µs
     - 555k/s
   * - random points, in-memory
     - 3.47ms
     - 3.45ms
     - 113µs
     - 3.39ms
     - 4.38ms
     - 250
     - 1.39µs
     - 720k/s
   * - unique-shortcut points, in-memory
     - 2.45ms
     - 2.44ms
     - 57.7µs
     - 2.38ms
     - 2.92ms
     - 367
     - 979ns
     - 1.02M/s




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
     - 5.33ms
     - 5.32ms
     - 101µs
     - 5.23ms
     - 6.38ms
     - 173
     - 2.13µs
     - 469k/s




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
     - 12.4ms
     - 12.3ms
     - 303µs
     - 12.2ms
     - 14.5ms
     - 71
     - 4.94µs
     - 202k/s
   * - on-land points, file-based
     - 4.32ms
     - 4.31ms
     - 48.5µs
     - 4.25ms
     - 4.58ms
     - 201
     - 1.73µs
     - 578k/s
   * - random points, file-based
     - 3.56ms
     - 3.48ms
     - 211µs
     - 3.38ms
     - 4.53ms
     - 259
     - 1.42µs
     - 702k/s
   * - unique-shortcut points, file-based
     - 2.48ms
     - 2.45ms
     - 104µs
     - 2.37ms
     - 3.01ms
     - 388
     - 993ns
     - 1.01M/s




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
     - 5.33ms
     - 5.33ms
     - 38.9µs
     - 5.25ms
     - 5.53ms
     - 165
     - 2.13µs
     - 469k/s




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
     - 10.1ms
     - 10.0ms
     - 304µs
     - 9.91ms
     - 11.5ms
     - 89
     - 4.06µs
     - 246k/s
   * - random points, file-based
     - 2.29ms
     - 2.28ms
     - 27.8µs
     - 2.24ms
     - 2.44ms
     - 362
     - 915ns
     - 1.09M/s
   * - unique-shortcut points, file-based
     - 1.30ms
     - 1.29ms
     - 19.7µs
     - 1.27ms
     - 1.40ms
     - 709
     - 518ns
     - 1.93M/s




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
     - 10.1ms
     - 10.1ms
     - 229µs
     - 9.97ms
     - 11.4ms
     - 88
     - 4.05µs
     - 247k/s
   * - random points, file-based
     - 2.31ms
     - 2.30ms
     - 38.4µs
     - 2.25ms
     - 2.55ms
     - 331
     - 923ns
     - 1.08M/s
   * - unique-shortcut points, file-based
     - 1.32ms
     - 1.31ms
     - 23.3µs
     - 1.29ms
     - 1.54ms
     - 698
     - 526ns
     - 1.90M/s




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
     - 3.60ms
     - 3.59ms
     - 66.1µs
     - 3.52ms
     - 4.27ms
     - 269
     - 1.44µs
     - 695k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 3% faster (1.03x) than **file-based** (3.47ms vs 3.56ms)

* On-land points: **file-based** is 4% faster (1.04x) than **in-memory** (4.32ms vs 4.50ms)

* Unique-shortcut points: **in-memory** and **file-based** perform about the same (2.45ms vs 2.48ms, 1.4% difference)

* Ambiguous-shortcut points: **file-based** and **in-memory** perform about the same (12.4ms vs 12.4ms, 0.7% difference)

* TimezoneFinder.timezone_at_land(): **in-memory** and **file-based** perform about the same (5.33ms vs 5.33ms, 0.0% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 56% faster (1.56x) than **TimezoneFinder.timezone_at()** (2.29ms vs 3.56ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 54% faster (1.54x) than **TimezoneFinder.timezone_at()** (2.31ms vs 3.56ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 91% faster (1.91x) than **TimezoneFinder.timezone_at()** (1.30ms vs 2.48ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 89% faster (1.89x) than **TimezoneFinder.timezone_at()** (1.32ms vs 2.48ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 22% faster (1.22x) than **TimezoneFinder.timezone_at()** (10.1ms vs 12.4ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 22% faster (1.22x) than **TimezoneFinder.timezone_at()** (10.1ms vs 12.4ms)

* Ambiguous-shortcut points are 5.1x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (1.30ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (12.4ms) - 860% faster (9.60x)



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
     - 1.00µs
     - 2.67µs
     - 8.00µs
     - 14.2µs
     - 1.41µs
     - 29.2µs
   * - on-land points
     - 1.04µs
     - 4.50µs
     - 7.42µs
     - 20.6µs
     - 1.76µs
     - 29.7µs
   * - unique-shortcut points
     - 1.00µs
     - 1.04µs
     - 1.08µs
     - 1.13µs
     - 993ns
     - 1.17µs
   * - ambiguous-shortcut points
     - 4.46µs
     - 7.33µs
     - 14.8µs
     - 28.5µs
     - 4.98µs
     - 29.8µs
