

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~356ns per check on a small polygon, ~578ns on the largest** (1.62x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~24.0µs on the largest polygon (41.5x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

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

**Polygon Strata**: small / medium / large (by vertex count percentile)

Each benchmark times one pass over 2,500 fixed, committed (point, polygon) pairs drawn from a single polygon-size stratum, so the cost of the largest polygons isn't hidden behind an unweighted average. Mean/Median/StdDev/Min/Max are for the full 2,500-pair batch; Throughput is queries/second for that batch.

.. note::

   The point and the polygon in each pair are drawn independently, so many pairs put the point nowhere near the polygon. That does not matter for the bare kernel, which scans the whole ring either way, but it means a share of the block-filtered checks are rejections rather than scans - cheapest on the small stratum, where a rejection is most of what is left. A real lookup reaches this stage only after a bounding-box check has passed, so read the block-filtered figures as a floor and :doc:`benchmark_results_timezonefinding` for what a query actually pays.



Results
~~~~~~~




bare kernel (C/clang)
^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 24 10 10 10 10 10 10 16

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Throughput
   * - large polygons
     - 60.0ms
     - 57.2ms
     - 7.14ms
     - 56.3ms
     - 82.9ms
     - 16
     - 41.7k/s
   * - medium polygons
     - 6.34ms
     - 6.32ms
     - 309µs
     - 5.90ms
     - 8.35ms
     - 153
     - 395k/s
   * - small polygons
     - 2.12ms
     - 2.10ms
     - 144µs
     - 1.94ms
     - 2.60ms
     - 430
     - 1.18M/s




packed kernel (C/clang)
^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 24 10 10 10 10 10 10 16

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Throughput
   * - large polygons
     - 1.44ms
     - 1.42ms
     - 90.7µs
     - 1.35ms
     - 1.90ms
     - 616
     - 1.73M/s
   * - medium polygons
     - 974µs
     - 953µs
     - 67.6µs
     - 918µs
     - 1.32ms
     - 877
     - 2.57M/s
   * - small polygons
     - 891µs
     - 870µs
     - 59.1µs
     - 844µs
     - 1.36ms
     - 1094
     - 2.81M/s




bare kernel (Python, Numba if available)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 24 10 10 10 10 10 10 16

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Throughput
   * - large polygons
     - 12.7s
     - 12.7s
     - 481ms
     - 12.3s
     - 13.5s
     - 5
     - 196/s
   * - medium polygons
     - 793ms
     - 792ms
     - 2.65ms
     - 791ms
     - 796ms
     - 5
     - 3.15k/s
   * - small polygons
     - 30.8ms
     - 29.7ms
     - 3.89ms
     - 28.6ms
     - 47.8ms
     - 33
     - 81.2k/s




packed kernel (Python, Numba if available)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 24 10 10 10 10 10 10 16

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Throughput
   * - large polygons
     - 302ms
     - 301ms
     - 3.12ms
     - 300ms
     - 307ms
     - 5
     - 8.27k/s
   * - medium polygons
     - 92.4ms
     - 92.4ms
     - 503µs
     - 91.4ms
     - 93.4ms
     - 11
     - 27.1k/s
   * - small polygons
     - 4.91ms
     - 4.89ms
     - 145µs
     - 4.62ms
     - 5.28ms
     - 193
     - 510k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 138% faster (2.38x) than **bare kernel (C/clang)** (891µs vs 2.12ms)

* Medium polygons: **packed kernel (C/clang)** is 551% faster (6.51x) than **bare kernel (C/clang)** (974µs vs 6.34ms)

* Large polygons: **packed kernel (C/clang)** is 4051% faster (41.5x) than **bare kernel (C/clang)** (1.44ms vs 60.0ms)

**C against Python/Numba**, on the kernel a lookup reaches:

* Small polygons: **packed kernel (C/clang)** is 451% faster (5.51x) than **packed kernel (Python, Numba if available)** (891µs vs 4.91ms)

* Medium polygons: **packed kernel (C/clang)** is 9387% faster (94.9x) than **packed kernel (Python, Numba if available)** (974µs vs 92.4ms)

* Large polygons: **packed kernel (C/clang)** is 20811% faster (209x) than **packed kernel (Python, Numba if available)** (1.44ms vs 302ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (891µs), slowest is **packed kernel (Python, Numba if available) - large polygons** (302ms) - 33806% faster (339x)
