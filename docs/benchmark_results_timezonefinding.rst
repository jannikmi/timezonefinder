

Timezone Finding Performance Benchmark
======================================


**~1.47µs per lookup, ~681k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

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
     - 14.8ms
     - 14.3ms
     - 827µs
     - 14.1ms
     - 17.0ms
     - 61
     - 5.91µs
     - 169k/s
   * - on-land points, in-memory
     - 4.86ms
     - 4.80ms
     - 222µs
     - 4.69ms
     - 6.04ms
     - 187
     - 1.95µs
     - 514k/s
   * - random points, in-memory
     - 3.67ms
     - 3.64ms
     - 134µs
     - 3.58ms
     - 4.53ms
     - 188
     - 1.47µs
     - 681k/s
   * - unique-shortcut points, in-memory
     - 2.44ms
     - 2.42ms
     - 63.7µs
     - 2.37ms
     - 3.06ms
     - 371
     - 975ns
     - 1.03M/s




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
     - 6.15ms
     - 5.79ms
     - 1.36ms
     - 5.68ms
     - 21.1ms
     - 158
     - 2.46µs
     - 406k/s




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
     - 16.4ms
     - 16.3ms
     - 531µs
     - 16.0ms
     - 18.1ms
     - 49
     - 6.57µs
     - 152k/s
   * - on-land points, file-based
     - 5.21ms
     - 5.18ms
     - 141µs
     - 5.10ms
     - 6.12ms
     - 160
     - 2.08µs
     - 480k/s
   * - random points, file-based
     - 3.83ms
     - 3.81ms
     - 123µs
     - 3.74ms
     - 4.76ms
     - 231
     - 1.53µs
     - 652k/s
   * - unique-shortcut points, file-based
     - 2.43ms
     - 2.42ms
     - 52.4µs
     - 2.37ms
     - 3.01ms
     - 389
     - 971ns
     - 1.03M/s




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
     - 6.30ms
     - 6.23ms
     - 204µs
     - 6.16ms
     - 7.36ms
     - 136
     - 2.52µs
     - 397k/s




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
     - 85.8µs
     - 3.51ms
     - 4.15ms
     - 272
     - 1.44µs
     - 693k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 4% faster (1.04x) than **file-based** (3.67ms vs 3.83ms)

* On-land points: **in-memory** is 7% faster (1.07x) than **file-based** (4.86ms vs 5.21ms)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.43ms vs 2.44ms, 0.4% difference)

* Ambiguous-shortcut points: **in-memory** is 11% faster (1.11x) than **file-based** (14.8ms vs 16.4ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 2% faster (1.02x) than **file-based** (6.15ms vs 6.30ms)

* Ambiguous-shortcut points are 6.1x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, file-based** (2.43ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (16.4ms) - 576% faster (6.76x)



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
     - 9.96µs
     - 16.3µs
     - 1.56µs
     - 31.5µs
   * - on-land points
     - 1.04µs
     - 6.62µs
     - 10.8µs
     - 23.4µs
     - 2.17µs
     - 32.0µs
   * - unique-shortcut points
     - 1.00µs
     - 1.04µs
     - 1.08µs
     - 1.13µs
     - 989ns
     - 1.17µs
   * - ambiguous-shortcut points
     - 6.38µs
     - 9.88µs
     - 17.0µs
     - 30.7µs
     - 6.50µs
     - 32.2µs
