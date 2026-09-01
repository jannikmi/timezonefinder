

Timezone Finding Performance Benchmark
======================================


**~1.39µs per lookup, ~722k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

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
     - 13.5ms
     - 13.4ms
     - 741µs
     - 12.2ms
     - 15.2ms
     - 74
     - 5.39µs
     - 186k/s
   * - on-land points, in-memory
     - 4.40ms
     - 4.35ms
     - 361µs
     - 3.92ms
     - 5.51ms
     - 195
     - 1.76µs
     - 568k/s
   * - random points, in-memory
     - 3.46ms
     - 3.44ms
     - 313µs
     - 3.08ms
     - 4.43ms
     - 249
     - 1.39µs
     - 722k/s
   * - unique-shortcut points, in-memory
     - 2.33ms
     - 2.32ms
     - 158µs
     - 2.12ms
     - 3.39ms
     - 379
     - 931ns
     - 1.07M/s




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
     - 5.46ms
     - 5.42ms
     - 471µs
     - 4.70ms
     - 7.10ms
     - 171
     - 2.19µs
     - 458k/s




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
     - 670µs
     - 11.9ms
     - 14.5ms
     - 68
     - 5.32µs
     - 188k/s
   * - on-land points, file-based
     - 4.45ms
     - 4.43ms
     - 326µs
     - 3.91ms
     - 5.64ms
     - 187
     - 1.78µs
     - 561k/s
   * - random points, file-based
     - 3.53ms
     - 3.43ms
     - 344µs
     - 3.09ms
     - 5.36ms
     - 218
     - 1.41µs
     - 708k/s
   * - unique-shortcut points, file-based
     - 2.29ms
     - 2.26ms
     - 153µs
     - 2.11ms
     - 2.91ms
     - 415
     - 917ns
     - 1.09M/s




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
     - 5.32ms
     - 5.18ms
     - 399µs
     - 4.74ms
     - 6.38ms
     - 154
     - 2.13µs
     - 470k/s




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
     - 10.7ms
     - 10.6ms
     - 604µs
     - 9.74ms
     - 12.4ms
     - 85
     - 4.28µs
     - 234k/s
   * - random points, file-based
     - 2.39ms
     - 2.34ms
     - 223µs
     - 2.11ms
     - 3.08ms
     - 320
     - 958ns
     - 1.04M/s
   * - unique-shortcut points, file-based
     - 1.31ms
     - 1.29ms
     - 91.7µs
     - 1.21ms
     - 1.82ms
     - 694
     - 525ns
     - 1.91M/s




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
     - 10.5ms
     - 10.3ms
     - 625µs
     - 9.45ms
     - 12.0ms
     - 88
     - 4.19µs
     - 239k/s
   * - random points, file-based
     - 2.33ms
     - 2.29ms
     - 150µs
     - 2.13ms
     - 2.93ms
     - 354
     - 931ns
     - 1.07M/s
   * - unique-shortcut points, file-based
     - 1.33ms
     - 1.31ms
     - 86.8µs
     - 1.24ms
     - 1.97ms
     - 686
     - 533ns
     - 1.88M/s




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
     - 3.52ms
     - 3.46ms
     - 241µs
     - 3.20ms
     - 4.51ms
     - 252
     - 1.41µs
     - 710k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** and **file-based** perform about the same (3.46ms vs 3.53ms, 1.9% difference)

* On-land points: **in-memory** and **file-based** perform about the same (4.40ms vs 4.45ms, 1.3% difference)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.29ms vs 2.33ms, 1.6% difference)

* Ambiguous-shortcut points: **file-based** and **in-memory** perform about the same (13.3ms vs 13.5ms, 1.2% difference)

* TimezoneFinder.timezone_at_land(): **file-based** is 3% faster (1.03x) than **in-memory** (5.32ms vs 5.46ms)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 47% faster (1.47x) than **TimezoneFinder.timezone_at()** (2.39ms vs 3.53ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 52% faster (1.52x) than **TimezoneFinder.timezone_at()** (2.33ms vs 3.53ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 75% faster (1.75x) than **TimezoneFinder.timezone_at()** (1.31ms vs 2.29ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 72% faster (1.72x) than **TimezoneFinder.timezone_at()** (1.33ms vs 2.29ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 24% faster (1.24x) than **TimezoneFinder.timezone_at()** (10.7ms vs 13.3ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 27% faster (1.27x) than **TimezoneFinder.timezone_at()** (10.5ms vs 13.3ms)

* Ambiguous-shortcut points are 5.8x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (1.31ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (13.5ms) - 927% faster (10.3x)



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
     - 2.50µs
     - 7.37µs
     - 13.5µs
     - 1.31µs
     - 25.3µs
   * - on-land points
     - 917ns
     - 4.50µs
     - 7.25µs
     - 17.5µs
     - 1.66µs
     - 25.3µs
   * - unique-shortcut points
     - 875ns
     - 917ns
     - 959ns
     - 1.00µs
     - 873ns
     - 1.04µs
   * - ambiguous-shortcut points
     - 4.42µs
     - 7.00µs
     - 13.1µs
     - 24.5µs
     - 4.79µs
     - 26.9µs
