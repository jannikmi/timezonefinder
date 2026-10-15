

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~689ns per check on a small polygon, ~1.17µs on the largest** (1.70x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~32.0µs on the largest polygon (27.2x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2441 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 79.9ms
     - 79.9ms
     - 159µs
     - 79.7ms
     - 80.2ms
     - 15
     - 31.3k/s
   * - medium polygons
     - 9.85ms
     - 9.90ms
     - 127µs
     - 9.67ms
     - 10.0ms
     - 15
     - 254k/s
   * - small polygons
     - 4.34ms
     - 4.33ms
     - 30.8µs
     - 4.30ms
     - 4.40ms
     - 15
     - 576k/s




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
     - 2.94ms
     - 2.92ms
     - 36.4µs
     - 2.91ms
     - 3.05ms
     - 15
     - 852k/s
   * - medium polygons
     - 1.84ms
     - 1.84ms
     - 7.38µs
     - 1.82ms
     - 1.85ms
     - 15
     - 1.36M/s
   * - small polygons
     - 1.72ms
     - 1.72ms
     - 23.6µs
     - 1.71ms
     - 1.81ms
     - 15
     - 1.45M/s




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
     - 125ms
     - 20.4s
     - 20.8s
     - 15
     - 121/s
   * - medium polygons
     - 1.27s
     - 1.27s
     - 4.31ms
     - 1.26s
     - 1.28s
     - 15
     - 1.97k/s
   * - small polygons
     - 43.0ms
     - 43.0ms
     - 481µs
     - 42.1ms
     - 43.8ms
     - 15
     - 58.2k/s




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
     - 519ms
     - 518ms
     - 2.97ms
     - 515ms
     - 526ms
     - 15
     - 4.82k/s
   * - medium polygons
     - 185ms
     - 185ms
     - 780µs
     - 184ms
     - 186ms
     - 15
     - 13.5k/s
   * - small polygons
     - 9.22ms
     - 9.21ms
     - 29.7µs
     - 9.18ms
     - 9.31ms
     - 15
     - 271k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 152% faster (2.52x) than **bare kernel (C/clang)** (1.72ms vs 4.34ms)

* Medium polygons: **packed kernel (C/clang)** is 435% faster (5.35x) than **bare kernel (C/clang)** (1.84ms vs 9.85ms)

* Large polygons: **packed kernel (C/clang)** is 2622% faster (27.2x) than **bare kernel (C/clang)** (2.94ms vs 79.9ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 435% faster (5.35x) than **packed kernel (pure Python)** (1.72ms vs 9.22ms)

* Medium polygons: **packed kernel (C/clang)** is 9960% faster (101x) than **packed kernel (pure Python)** (1.84ms vs 185ms)

* Large polygons: **packed kernel (C/clang)** is 17573% faster (177x) than **packed kernel (pure Python)** (2.94ms vs 519ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.72ms), slowest is **packed kernel (pure Python) - large polygons** (519ms) - 29996% faster (301x)
