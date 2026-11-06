

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~352ns per check on a small polygon, ~626ns on the largest** (1.78x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~19.0µs on the largest polygon (30.3x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 9V45 96-Core Processor @ 4.2918 GHz, Python 3.13.17, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration tracks none of the rows on this page. This published table leads with ``Mean`` and belongs to the full on-demand suite, while the trend chart records the ``min`` estimator for the smaller ``benchmark_core`` subset.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.17 (CPython)

**NumPy Version**: 2.5.2

**Platform**: Linux x86_64



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


**Fixture Version**: 5

**Timezone Data Version**: 2026f



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
     - 47.4ms
     - 47.4ms
     - 426µs
     - 46.9ms
     - 48.2ms
     - 15
     - 52.7k/s
   * - medium polygons
     - 6.19ms
     - 6.12ms
     - 165µs
     - 6.05ms
     - 6.67ms
     - 15
     - 404k/s
   * - small polygons
     - 2.98ms
     - 2.65ms
     - 924µs
     - 2.28ms
     - 5.52ms
     - 15
     - 839k/s




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
     - 1.56ms
     - 1.55ms
     - 41.1µs
     - 1.53ms
     - 1.67ms
     - 15
     - 1.60M/s
   * - medium polygons
     - 946µs
     - 943µs
     - 10.1µs
     - 939µs
     - 979µs
     - 15
     - 2.64M/s
   * - small polygons
     - 881µs
     - 874µs
     - 21.7µs
     - 857µs
     - 926µs
     - 15
     - 2.84M/s




bare kernel (pure Python)
^^^^^^^^^^^^^^^^^^^^^^^^^



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
     - 9.76s
     - 9.74s
     - 101ms
     - 9.65s
     - 9.91s
     - 5
     - 256/s
   * - medium polygons
     - 668ms
     - 663ms
     - 17.1ms
     - 645ms
     - 700ms
     - 15
     - 3.75k/s
   * - small polygons
     - 21.8ms
     - 21.9ms
     - 470µs
     - 21.1ms
     - 22.5ms
     - 15
     - 115k/s




packed kernel (pure Python)
^^^^^^^^^^^^^^^^^^^^^^^^^^^



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
     - 259ms
     - 258ms
     - 3.18ms
     - 254ms
     - 267ms
     - 15
     - 9.67k/s
   * - medium polygons
     - 96.0ms
     - 96.2ms
     - 1.86ms
     - 93.4ms
     - 98.9ms
     - 15
     - 26.0k/s
   * - small polygons
     - 4.10ms
     - 4.09ms
     - 24.9µs
     - 4.06ms
     - 4.14ms
     - 15
     - 610k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 239% faster (3.39x) than **bare kernel (C/clang)** (881µs vs 2.98ms)

* Medium polygons: **packed kernel (C/clang)** is 555% faster (6.55x) than **bare kernel (C/clang)** (946µs vs 6.19ms)

* Large polygons: **packed kernel (C/clang)** is 2932% faster (30.3x) than **bare kernel (C/clang)** (1.56ms vs 47.4ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 365% faster (4.65x) than **packed kernel (pure Python)** (881µs vs 4.10ms)

* Medium polygons: **packed kernel (C/clang)** is 10046% faster (101x) than **packed kernel (pure Python)** (946µs vs 96.0ms)

* Large polygons: **packed kernel (C/clang)** is 16427% faster (165x) than **packed kernel (pure Python)** (1.56ms vs 259ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (881µs), slowest is **packed kernel (pure Python) - large polygons** (259ms) - 29265% faster (294x)
