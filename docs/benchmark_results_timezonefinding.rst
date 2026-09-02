

Timezone Finding Performance Benchmark
======================================


**~1.37µs per lookup, ~730k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

*Measured on Darwin arm64, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.



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
     - 13.3ms
     - 13.3ms
     - 477µs
     - 11.9ms
     - 14.2ms
     - 77
     - 5.32µs
     - 188k/s
   * - on-land points, in-memory
     - 4.19ms
     - 4.14ms
     - 302µs
     - 3.81ms
     - 4.89ms
     - 204
     - 1.68µs
     - 596k/s
   * - random points, in-memory
     - 3.42ms
     - 3.41ms
     - 270µs
     - 2.99ms
     - 4.11ms
     - 276
     - 1.37µs
     - 730k/s
   * - unique-shortcut points, in-memory
     - 2.13ms
     - 2.10ms
     - 103µs
     - 1.99ms
     - 2.57ms
     - 408
     - 851ns
     - 1.17M/s




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
     - 4.45ms
     - 4.38ms
     - 299µs
     - 4.07ms
     - 5.13ms
     - 203
     - 1.78µs
     - 562k/s




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
     - 13.3ms
     - 13.4ms
     - 527µs
     - 11.9ms
     - 14.4ms
     - 70
     - 5.32µs
     - 188k/s
   * - on-land points, file-based
     - 4.38ms
     - 4.41ms
     - 300µs
     - 3.80ms
     - 5.07ms
     - 184
     - 1.75µs
     - 571k/s
   * - random points, file-based
     - 3.37ms
     - 3.33ms
     - 256µs
     - 2.99ms
     - 4.08ms
     - 264
     - 1.35µs
     - 742k/s
   * - unique-shortcut points, file-based
     - 2.13ms
     - 2.09ms
     - 122µs
     - 1.99ms
     - 2.83ms
     - 436
     - 851ns
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
     - 4.56ms
     - 4.49ms
     - 343µs
     - 4.09ms
     - 5.60ms
     - 175
     - 1.82µs
     - 548k/s




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
     - 10.6ms
     - 407µs
     - 9.75ms
     - 11.5ms
     - 82
     - 4.21µs
     - 237k/s
   * - random points, file-based
     - 2.21ms
     - 2.18ms
     - 150µs
     - 2.02ms
     - 2.82ms
     - 359
     - 884ns
     - 1.13M/s
   * - unique-shortcut points, file-based
     - 1.17ms
     - 1.14ms
     - 71.6µs
     - 1.10ms
     - 1.53ms
     - 763
     - 467ns
     - 2.14M/s




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
     - 10.7ms
     - 10.9ms
     - 422µs
     - 9.61ms
     - 11.3ms
     - 87
     - 4.30µs
     - 233k/s
   * - random points, file-based
     - 2.23ms
     - 2.21ms
     - 140µs
     - 2.03ms
     - 2.68ms
     - 339
     - 894ns
     - 1.12M/s
   * - unique-shortcut points, file-based
     - 1.19ms
     - 1.16ms
     - 71.3µs
     - 1.12ms
     - 1.47ms
     - 714
     - 476ns
     - 2.10M/s




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
     - 3.48ms
     - 3.45ms
     - 254µs
     - 3.11ms
     - 4.20ms
     - 303
     - 1.39µs
     - 718k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **file-based** and **in-memory** perform about the same (3.37ms vs 3.42ms, 1.6% difference)

* On-land points: **in-memory** is 4% faster (1.04x) than **file-based** (4.19ms vs 4.38ms)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.13ms vs 2.13ms, 0.0% difference)

* Ambiguous-shortcut points: **in-memory** and **file-based** perform about the same (13.3ms vs 13.3ms, 0.1% difference)

* TimezoneFinder.timezone_at_land(): **in-memory** is 3% faster (1.03x) than **file-based** (4.45ms vs 4.56ms)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 52% faster (1.52x) than **TimezoneFinder.timezone_at()** (2.21ms vs 3.37ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 51% faster (1.51x) than **TimezoneFinder.timezone_at()** (2.23ms vs 3.37ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 82% faster (1.82x) than **TimezoneFinder.timezone_at()** (1.17ms vs 2.13ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 79% faster (1.79x) than **TimezoneFinder.timezone_at()** (1.19ms vs 2.13ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 26% faster (1.26x) than **TimezoneFinder.timezone_at()** (10.5ms vs 13.3ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 24% faster (1.24x) than **TimezoneFinder.timezone_at()** (10.7ms vs 13.3ms)

* Ambiguous-shortcut points are 6.2x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (1.17ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (13.3ms) - 1039% faster (11.4x)



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
     - 875ns
     - 2.50µs
     - 7.58µs
     - 13.4µs
     - 1.32µs
     - 27.5µs
   * - on-land points
     - 875ns
     - 4.33µs
     - 7.17µs
     - 17.5µs
     - 1.60µs
     - 26.6µs
   * - unique-shortcut points
     - 833ns
     - 875ns
     - 917ns
     - 959ns
     - 829ns
     - 1.04µs
   * - ambiguous-shortcut points
     - 4.29µs
     - 6.96µs
     - 13.1µs
     - 24.5µs
     - 4.72µs
     - 25.8µs
