

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~358ns per check on a small polygon, ~570ns on the largest** (1.59x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~22.9µs on the largest polygon (40.2x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Darwin arm64, Apple M1 Pro, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration tracks none of the rows on this page. This published table leads with ``Mean`` and belongs to the full on-demand suite, while the trend chart records the ``min`` estimator for the smaller ``benchmark_core`` subset.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.14.2 (CPython)

**NumPy Version**: 2.5.2

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
     - 57.3ms
     - 57.3ms
     - 182µs
     - 57.0ms
     - 57.7ms
     - 15
     - 43.6k/s
   * - medium polygons
     - 6.41ms
     - 6.39ms
     - 180µs
     - 6.13ms
     - 6.69ms
     - 15
     - 390k/s
   * - small polygons
     - 2.14ms
     - 2.13ms
     - 103µs
     - 2.01ms
     - 2.33ms
     - 15
     - 1.17M/s




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
     - 1.43ms
     - 1.39ms
     - 89.0µs
     - 1.36ms
     - 1.65ms
     - 15
     - 1.75M/s
   * - medium polygons
     - 939µs
     - 932µs
     - 18.6µs
     - 919µs
     - 982µs
     - 15
     - 2.66M/s
   * - small polygons
     - 895µs
     - 877µs
     - 43.4µs
     - 852µs
     - 1.00ms
     - 15
     - 2.79M/s




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
     - 12.4s
     - 12.4s
     - 63.6ms
     - 12.2s
     - 12.5s
     - 15
     - 202/s
   * - medium polygons
     - 804ms
     - 801ms
     - 7.68ms
     - 798ms
     - 827ms
     - 15
     - 3.11k/s
   * - small polygons
     - 29.4ms
     - 29.4ms
     - 317µs
     - 28.9ms
     - 30.0ms
     - 15
     - 85.1k/s




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
     - 296ms
     - 295ms
     - 2.13ms
     - 291ms
     - 299ms
     - 15
     - 8.46k/s
   * - medium polygons
     - 89.2ms
     - 89.1ms
     - 788µs
     - 87.9ms
     - 91.2ms
     - 15
     - 28.0k/s
   * - small polygons
     - 4.66ms
     - 4.67ms
     - 25.3µs
     - 4.62ms
     - 4.69ms
     - 15
     - 536k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 139% faster (2.39x) than **bare kernel (C/clang)** (895µs vs 2.14ms)

* Medium polygons: **packed kernel (C/clang)** is 583% faster (6.83x) than **bare kernel (C/clang)** (939µs vs 6.41ms)

* Large polygons: **packed kernel (C/clang)** is 3921% faster (40.2x) than **bare kernel (C/clang)** (1.43ms vs 57.3ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 421% faster (5.21x) than **packed kernel (pure Python)** (895µs vs 4.66ms)

* Medium polygons: **packed kernel (C/clang)** is 9402% faster (95.0x) than **packed kernel (pure Python)** (939µs vs 89.2ms)

* Large polygons: **packed kernel (C/clang)** is 20636% faster (207x) than **packed kernel (pure Python)** (1.43ms vs 296ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (895µs), slowest is **packed kernel (pure Python) - large polygons** (296ms) - 32946% faster (330x)
