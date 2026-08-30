

Timezone Finding Performance Benchmark
======================================


**~1.65µs per lookup, ~608k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

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
     - 16.0ms
     - 16.0ms
     - 415µs
     - 14.3ms
     - 16.7ms
     - 62
     - 6.38µs
     - 157k/s
   * - on-land points, in-memory
     - 5.23ms
     - 5.20ms
     - 345µs
     - 4.66ms
     - 6.06ms
     - 185
     - 2.09µs
     - 478k/s
   * - random points, in-memory
     - 4.12ms
     - 4.01ms
     - 853µs
     - 3.58ms
     - 13.2ms
     - 217
     - 1.65µs
     - 608k/s
   * - unique-shortcut points, in-memory
     - 2.56ms
     - 2.52ms
     - 147µs
     - 2.38ms
     - 3.77ms
     - 337
     - 1.02µs
     - 978k/s




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
     - 6.27ms
     - 6.27ms
     - 335µs
     - 5.66ms
     - 7.19ms
     - 142
     - 2.51µs
     - 399k/s




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
     - 17.4ms
     - 17.5ms
     - 631µs
     - 16.1ms
     - 18.7ms
     - 49
     - 6.98µs
     - 143k/s
   * - on-land points, file-based
     - 5.90ms
     - 5.64ms
     - 2.03ms
     - 5.12ms
     - 28.2ms
     - 144
     - 2.36µs
     - 424k/s
   * - random points, file-based
     - 4.24ms
     - 4.19ms
     - 304µs
     - 3.77ms
     - 5.17ms
     - 214
     - 1.70µs
     - 589k/s
   * - unique-shortcut points, file-based
     - 2.63ms
     - 2.52ms
     - 1.08ms
     - 2.37ms
     - 21.0ms
     - 364
     - 1.05µs
     - 950k/s




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
     - 6.74ms
     - 6.76ms
     - 263µs
     - 6.14ms
     - 7.35ms
     - 130
     - 2.69µs
     - 371k/s




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
     - 3.76ms
     - 3.75ms
     - 153µs
     - 3.52ms
     - 4.25ms
     - 272
     - 1.50µs
     - 665k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 3% faster (1.03x) than **file-based** (4.12ms vs 4.24ms)

* On-land points: **in-memory** is 13% faster (1.13x) than **file-based** (5.23ms vs 5.90ms)

* Unique-shortcut points: **in-memory** is 3% faster (1.03x) than **file-based** (2.56ms vs 2.63ms)

* Ambiguous-shortcut points: **in-memory** is 9% faster (1.09x) than **file-based** (16.0ms vs 17.4ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 7% faster (1.07x) than **file-based** (6.27ms vs 6.74ms)

* Ambiguous-shortcut points are 6.2x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, in-memory** (2.56ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (17.4ms) - 582% faster (6.82x)



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
     - 2.71µs
     - 10.5µs
     - 16.3µs
     - 1.60µs
     - 34.9µs
   * - on-land points
     - 1.04µs
     - 6.38µs
     - 10.5µs
     - 22.6µs
     - 2.12µs
     - 31.6µs
   * - unique-shortcut points
     - 1.00µs
     - 1.04µs
     - 1.08µs
     - 1.13µs
     - 992ns
     - 1.21µs
   * - ambiguous-shortcut points
     - 6.42µs
     - 10.1µs
     - 17.0µs
     - 30.3µs
     - 6.58µs
     - 32.4µs
