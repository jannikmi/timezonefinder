

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~711ns per check on a small polygon, ~1.21µs on the largest** (1.70x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~32.1µs on the largest polygon (26.6x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2287 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 80.3ms
     - 80.2ms
     - 203µs
     - 80.1ms
     - 80.8ms
     - 15
     - 31.1k/s
   * - medium polygons
     - 10.3ms
     - 10.3ms
     - 54.4µs
     - 10.2ms
     - 10.4ms
     - 15
     - 243k/s
   * - small polygons
     - 4.92ms
     - 4.94ms
     - 79.4µs
     - 4.80ms
     - 5.03ms
     - 15
     - 508k/s




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
     - 3.01ms
     - 3.01ms
     - 28.7µs
     - 2.98ms
     - 3.09ms
     - 15
     - 830k/s
   * - medium polygons
     - 1.92ms
     - 1.91ms
     - 24.4µs
     - 1.90ms
     - 1.98ms
     - 15
     - 1.30M/s
   * - small polygons
     - 1.78ms
     - 1.78ms
     - 6.31µs
     - 1.77ms
     - 1.79ms
     - 15
     - 1.41M/s




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
     - 20.1s
     - 20.1s
     - 166ms
     - 19.9s
     - 20.4s
     - 15
     - 124/s
   * - medium polygons
     - 1.28s
     - 1.28s
     - 9.01ms
     - 1.26s
     - 1.29s
     - 15
     - 1.95k/s
   * - small polygons
     - 43.6ms
     - 43.7ms
     - 206µs
     - 43.4ms
     - 43.9ms
     - 15
     - 57.3k/s




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
     - 517ms
     - 516ms
     - 3.59ms
     - 512ms
     - 525ms
     - 15
     - 4.84k/s
   * - medium polygons
     - 186ms
     - 186ms
     - 597µs
     - 185ms
     - 187ms
     - 15
     - 13.5k/s
   * - small polygons
     - 9.26ms
     - 9.23ms
     - 67.9µs
     - 9.20ms
     - 9.41ms
     - 15
     - 270k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 177% faster (2.77x) than **bare kernel (C/clang)** (1.78ms vs 4.92ms)

* Medium polygons: **packed kernel (C/clang)** is 436% faster (5.36x) than **bare kernel (C/clang)** (1.92ms vs 10.3ms)

* Large polygons: **packed kernel (C/clang)** is 2564% faster (26.6x) than **bare kernel (C/clang)** (3.01ms vs 80.3ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 421% faster (5.21x) than **packed kernel (pure Python)** (1.78ms vs 9.26ms)

* Medium polygons: **packed kernel (C/clang)** is 9574% faster (96.7x) than **packed kernel (pure Python)** (1.92ms vs 186ms)

* Large polygons: **packed kernel (C/clang)** is 17044% faster (171x) than **packed kernel (pure Python)** (3.01ms vs 517ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.78ms), slowest is **packed kernel (pure Python) - large polygons** (517ms) - 28970% faster (291x)
