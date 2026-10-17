

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~622ns per check on a small polygon, ~1.48µs on the largest** (2.38x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~36.6µs on the largest polygon (24.7x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, Intel(R) Xeon(R) Platinum 8370C CPU @ 2.7929 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 91.4ms
     - 91.2ms
     - 735µs
     - 91.1ms
     - 94.0ms
     - 15
     - 27.3k/s
   * - medium polygons
     - 9.94ms
     - 9.93ms
     - 60.4µs
     - 9.86ms
     - 10.1ms
     - 15
     - 251k/s
   * - small polygons
     - 4.22ms
     - 4.17ms
     - 123µs
     - 4.02ms
     - 4.54ms
     - 15
     - 592k/s




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
     - 3.70ms
     - 3.72ms
     - 34.5µs
     - 3.61ms
     - 3.73ms
     - 15
     - 675k/s
   * - medium polygons
     - 1.72ms
     - 1.72ms
     - 8.79µs
     - 1.71ms
     - 1.75ms
     - 15
     - 1.45M/s
   * - small polygons
     - 1.55ms
     - 1.55ms
     - 14.6µs
     - 1.54ms
     - 1.60ms
     - 15
     - 1.61M/s




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
     - 16.5s
     - 16.5s
     - 21.7ms
     - 16.5s
     - 16.6s
     - 5
     - 151/s
   * - medium polygons
     - 1.04s
     - 1.03s
     - 11.2ms
     - 1.03s
     - 1.06s
     - 15
     - 2.41k/s
   * - small polygons
     - 36.7ms
     - 36.7ms
     - 246µs
     - 36.2ms
     - 37.2ms
     - 15
     - 68.2k/s




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
     - 474ms
     - 474ms
     - 1.42ms
     - 472ms
     - 476ms
     - 15
     - 5.27k/s
   * - medium polygons
     - 173ms
     - 173ms
     - 320µs
     - 172ms
     - 173ms
     - 15
     - 14.5k/s
   * - small polygons
     - 8.73ms
     - 8.72ms
     - 36.1µs
     - 8.68ms
     - 8.80ms
     - 15
     - 286k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 172% faster (2.72x) than **bare kernel (C/clang)** (1.55ms vs 4.22ms)

* Medium polygons: **packed kernel (C/clang)** is 477% faster (5.77x) than **bare kernel (C/clang)** (1.72ms vs 9.94ms)

* Large polygons: **packed kernel (C/clang)** is 2368% faster (24.7x) than **bare kernel (C/clang)** (3.70ms vs 91.4ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 461% faster (5.61x) than **packed kernel (pure Python)** (1.55ms vs 8.73ms)

* Medium polygons: **packed kernel (C/clang)** is 9927% faster (100x) than **packed kernel (pure Python)** (1.72ms vs 173ms)

* Large polygons: **packed kernel (C/clang)** is 12695% faster (128x) than **packed kernel (pure Python)** (3.70ms vs 474ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.55ms), slowest is **packed kernel (pure Python) - large polygons** (474ms) - 30383% faster (305x)
