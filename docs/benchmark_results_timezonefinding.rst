

Timezone Finding Performance Benchmark
======================================


**~1.85µs per lookup, ~541k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

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
     - 16.8ms
     - 16.7ms
     - 697µs
     - 14.9ms
     - 19.1ms
     - 59
     - 6.72µs
     - 149k/s
   * - on-land points, in-memory
     - 5.61ms
     - 5.65ms
     - 473µs
     - 4.69ms
     - 7.22ms
     - 180
     - 2.24µs
     - 446k/s
   * - random points, in-memory
     - 4.62ms
     - 4.40ms
     - 1.15ms
     - 3.56ms
     - 15.9ms
     - 205
     - 1.85µs
     - 541k/s
   * - unique-shortcut points, in-memory
     - 2.65ms
     - 2.62ms
     - 193µs
     - 2.37ms
     - 3.39ms
     - 358
     - 1.06µs
     - 942k/s




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
     - 6.79ms
     - 6.79ms
     - 489µs
     - 5.77ms
     - 8.75ms
     - 143
     - 2.72µs
     - 368k/s




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
     - 18.8ms
     - 18.6ms
     - 1.11ms
     - 16.2ms
     - 22.0ms
     - 51
     - 7.53µs
     - 133k/s
   * - on-land points, file-based
     - 6.00ms
     - 6.00ms
     - 335µs
     - 5.13ms
     - 6.84ms
     - 140
     - 2.40µs
     - 416k/s
   * - random points, file-based
     - 4.29ms
     - 4.26ms
     - 354µs
     - 3.77ms
     - 5.22ms
     - 183
     - 1.72µs
     - 582k/s
   * - unique-shortcut points, file-based
     - 2.61ms
     - 2.60ms
     - 156µs
     - 2.37ms
     - 3.23ms
     - 300
     - 1.04µs
     - 959k/s




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
     - 7.33ms
     - 7.07ms
     - 1.99ms
     - 6.30ms
     - 23.5ms
     - 70
     - 2.93µs
     - 341k/s




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
     - 4.02ms
     - 3.97ms
     - 344µs
     - 3.56ms
     - 7.60ms
     - 251
     - 1.61µs
     - 621k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **file-based** is 8% faster (1.08x) than **in-memory** (4.29ms vs 4.62ms)

* On-land points: **in-memory** is 7% faster (1.07x) than **file-based** (5.61ms vs 6.00ms)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.61ms vs 2.65ms, 1.8% difference)

* Ambiguous-shortcut points: **in-memory** is 12% faster (1.12x) than **file-based** (16.8ms vs 18.8ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 8% faster (1.08x) than **file-based** (6.79ms vs 7.33ms)

* Ambiguous-shortcut points are 6.3x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, file-based** (2.61ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (18.8ms) - 622% faster (7.22x)



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
     - 1.08µs
     - 2.71µs
     - 10.8µs
     - 18.3µs
     - 1.67µs
     - 35.3µs
   * - on-land points
     - 1.04µs
     - 6.29µs
     - 10.0µs
     - 23.0µs
     - 2.09µs
     - 31.4µs
   * - unique-shortcut points
     - 1.00µs
     - 1.04µs
     - 1.08µs
     - 1.13µs
     - 988ns
     - 1.17µs
   * - ambiguous-shortcut points
     - 6.33µs
     - 9.83µs
     - 16.9µs
     - 30.2µs
     - 6.50µs
     - 32.1µs
