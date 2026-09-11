

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~708ns per check on a small polygon, ~1.22µs on the largest** (1.72x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~32.3µs on the largest polygon (26.6x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 2.4454 GHz, Python 3.13.15, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 80.9ms
     - 80.7ms
     - 408µs
     - 80.5ms
     - 82.0ms
     - 15
     - 30.9k/s
   * - medium polygons
     - 9.85ms
     - 9.85ms
     - 98.9µs
     - 9.68ms
     - 10.0ms
     - 15
     - 254k/s
   * - small polygons
     - 4.27ms
     - 4.25ms
     - 62.9µs
     - 4.23ms
     - 4.49ms
     - 15
     - 586k/s




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
     - 3.04ms
     - 3.03ms
     - 22.0µs
     - 3.02ms
     - 3.10ms
     - 15
     - 822k/s
   * - medium polygons
     - 1.92ms
     - 1.92ms
     - 9.45µs
     - 1.91ms
     - 1.95ms
     - 15
     - 1.30M/s
   * - small polygons
     - 1.77ms
     - 1.77ms
     - 12.6µs
     - 1.75ms
     - 1.80ms
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
     - 19.1s
     - 19.1s
     - 111ms
     - 18.9s
     - 19.3s
     - 15
     - 131/s
   * - medium polygons
     - 1.26s
     - 1.27s
     - 18.8ms
     - 1.22s
     - 1.28s
     - 15
     - 1.98k/s
   * - small polygons
     - 45.6ms
     - 45.6ms
     - 153µs
     - 45.3ms
     - 45.8ms
     - 15
     - 54.8k/s




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
     - 544ms
     - 543ms
     - 2.56ms
     - 540ms
     - 550ms
     - 15
     - 4.60k/s
   * - medium polygons
     - 177ms
     - 177ms
     - 562µs
     - 177ms
     - 178ms
     - 15
     - 14.1k/s
   * - small polygons
     - 9.35ms
     - 9.36ms
     - 50.4µs
     - 9.26ms
     - 9.41ms
     - 15
     - 267k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 141% faster (2.41x) than **bare kernel (C/clang)** (1.77ms vs 4.27ms)

* Medium polygons: **packed kernel (C/clang)** is 412% faster (5.12x) than **bare kernel (C/clang)** (1.92ms vs 9.85ms)

* Large polygons: **packed kernel (C/clang)** is 2559% faster (26.6x) than **bare kernel (C/clang)** (3.04ms vs 80.9ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 428% faster (5.28x) than **packed kernel (pure Python)** (1.77ms vs 9.35ms)

* Medium polygons: **packed kernel (C/clang)** is 9119% faster (92.2x) than **packed kernel (pure Python)** (1.92ms vs 177ms)

* Large polygons: **packed kernel (C/clang)** is 17782% faster (179x) than **packed kernel (pure Python)** (3.04ms vs 544ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.77ms), slowest is **packed kernel (pure Python) - large polygons** (544ms) - 30634% faster (307x)
