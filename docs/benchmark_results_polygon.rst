

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~703ns per check on a small polygon, ~1.21µs on the largest** (1.72x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~32.0µs on the largest polygon (26.5x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2420 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration tracks none of the rows on this page. This published table leads with ``Mean`` and belongs to the full on-demand suite, while the trend chart records the ``min`` estimator for the smaller ``benchmark_core`` subset.



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

**Timezone Data Version**: 2026d



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
     - 80.0ms
     - 80.0ms
     - 494µs
     - 79.7ms
     - 81.7ms
     - 15
     - 31.2k/s
   * - medium polygons
     - 9.63ms
     - 9.62ms
     - 74.6µs
     - 9.52ms
     - 9.78ms
     - 15
     - 259k/s
   * - small polygons
     - 4.39ms
     - 4.38ms
     - 57.8µs
     - 4.31ms
     - 4.51ms
     - 15
     - 570k/s




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
     - 3.02ms
     - 2.99ms
     - 53.7µs
     - 2.99ms
     - 3.15ms
     - 15
     - 827k/s
   * - medium polygons
     - 1.90ms
     - 1.90ms
     - 6.45µs
     - 1.89ms
     - 1.91ms
     - 15
     - 1.32M/s
   * - small polygons
     - 1.76ms
     - 1.76ms
     - 8.82µs
     - 1.74ms
     - 1.78ms
     - 15
     - 1.42M/s




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
     - 20.6s
     - 20.6s
     - 179ms
     - 20.3s
     - 20.8s
     - 5
     - 121/s
   * - medium polygons
     - 1.28s
     - 1.28s
     - 4.51ms
     - 1.27s
     - 1.29s
     - 15
     - 1.95k/s
   * - small polygons
     - 42.2ms
     - 41.9ms
     - 507µs
     - 41.7ms
     - 43.2ms
     - 15
     - 59.3k/s




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
     - 532ms
     - 531ms
     - 2.42ms
     - 528ms
     - 537ms
     - 15
     - 4.70k/s
   * - medium polygons
     - 191ms
     - 191ms
     - 566µs
     - 190ms
     - 192ms
     - 15
     - 13.1k/s
   * - small polygons
     - 9.43ms
     - 9.43ms
     - 27.4µs
     - 9.36ms
     - 9.49ms
     - 15
     - 265k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 150% faster (2.50x) than **bare kernel (C/clang)** (1.76ms vs 4.39ms)

* Medium polygons: **packed kernel (C/clang)** is 407% faster (5.07x) than **bare kernel (C/clang)** (1.90ms vs 9.63ms)

* Large polygons: **packed kernel (C/clang)** is 2548% faster (26.5x) than **bare kernel (C/clang)** (3.02ms vs 80.0ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 436% faster (5.36x) than **packed kernel (pure Python)** (1.76ms vs 9.43ms)

* Medium polygons: **packed kernel (C/clang)** is 9931% faster (100x) than **packed kernel (pure Python)** (1.90ms vs 191ms)

* Large polygons: **packed kernel (C/clang)** is 17481% faster (176x) than **packed kernel (pure Python)** (3.02ms vs 532ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.76ms), slowest is **packed kernel (pure Python) - large polygons** (532ms) - 30139% faster (302x)
