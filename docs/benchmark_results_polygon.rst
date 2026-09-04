

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~621ns per check on a small polygon, ~1.16µs on the largest** (1.87x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~38.9µs on the largest polygon (33.4x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 2.8701 GHz, Python 3.13.15, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration tracks none of the rows on this page. This published table leads with ``Mean`` and belongs to the full on-demand suite, while the trend chart records the ``min`` estimator for the smaller ``benchmark_core`` subset.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.15 (CPython)

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
     - 97.1ms
     - 97.1ms
     - 72.4µs
     - 97.0ms
     - 97.3ms
     - 15
     - 25.7k/s
   * - medium polygons
     - 11.6ms
     - 11.6ms
     - 96.0µs
     - 11.5ms
     - 11.8ms
     - 15
     - 216k/s
   * - small polygons
     - 4.48ms
     - 4.42ms
     - 120µs
     - 4.39ms
     - 4.78ms
     - 15
     - 559k/s




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
     - 2.91ms
     - 2.91ms
     - 19.3µs
     - 2.89ms
     - 2.96ms
     - 15
     - 859k/s
   * - medium polygons
     - 1.71ms
     - 1.70ms
     - 28.1µs
     - 1.68ms
     - 1.77ms
     - 15
     - 1.46M/s
   * - small polygons
     - 1.55ms
     - 1.55ms
     - 14.1µs
     - 1.54ms
     - 1.59ms
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
     - 18.5s
     - 18.5s
     - 155ms
     - 18.3s
     - 18.8s
     - 15
     - 135/s
   * - medium polygons
     - 1.25s
     - 1.28s
     - 42.5ms
     - 1.20s
     - 1.30s
     - 15
     - 1.99k/s
   * - small polygons
     - 46.3ms
     - 46.2ms
     - 271µs
     - 45.9ms
     - 46.7ms
     - 15
     - 54.0k/s




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
     - 504ms
     - 504ms
     - 2.02ms
     - 501ms
     - 509ms
     - 15
     - 4.96k/s
   * - medium polygons
     - 159ms
     - 158ms
     - 1.66ms
     - 158ms
     - 164ms
     - 15
     - 15.7k/s
   * - small polygons
     - 8.47ms
     - 8.38ms
     - 328µs
     - 8.30ms
     - 9.62ms
     - 15
     - 295k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 188% faster (2.88x) than **bare kernel (C/clang)** (1.55ms vs 4.48ms)

* Medium polygons: **packed kernel (C/clang)** is 579% faster (6.79x) than **bare kernel (C/clang)** (1.71ms vs 11.6ms)

* Large polygons: **packed kernel (C/clang)** is 3237% faster (33.4x) than **bare kernel (C/clang)** (2.91ms vs 97.1ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 445% faster (5.45x) than **packed kernel (pure Python)** (1.55ms vs 8.47ms)

* Medium polygons: **packed kernel (C/clang)** is 9220% faster (93.2x) than **packed kernel (pure Python)** (1.71ms vs 159ms)

* Large polygons: **packed kernel (C/clang)** is 17204% faster (173x) than **packed kernel (pure Python)** (2.91ms vs 504ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.55ms), slowest is **packed kernel (pure Python) - large polygons** (504ms) - 32322% faster (324x)
