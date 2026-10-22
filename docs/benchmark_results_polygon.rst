

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~498ns per check on a small polygon, ~918ns on the largest** (1.84x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~30.9µs on the largest polygon (33.7x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 3.6926 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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


**Fixture Version**: 5

**Timezone Data Version**: 2026e



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
     - 77.2ms
     - 77.2ms
     - 94.0µs
     - 77.1ms
     - 77.4ms
     - 15
     - 32.4k/s
   * - medium polygons
     - 8.87ms
     - 8.85ms
     - 40.7µs
     - 8.82ms
     - 8.96ms
     - 15
     - 282k/s
   * - small polygons
     - 3.30ms
     - 3.25ms
     - 112µs
     - 3.23ms
     - 3.63ms
     - 15
     - 759k/s




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
     - 2.30ms
     - 2.29ms
     - 16.1µs
     - 2.28ms
     - 2.34ms
     - 15
     - 1.09M/s
   * - medium polygons
     - 1.35ms
     - 1.35ms
     - 12.1µs
     - 1.34ms
     - 1.39ms
     - 15
     - 1.85M/s
   * - small polygons
     - 1.24ms
     - 1.24ms
     - 12.6µs
     - 1.23ms
     - 1.27ms
     - 15
     - 2.01M/s




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
     - 16.4s
     - 16.4s
     - 51.4ms
     - 16.4s
     - 16.5s
     - 5
     - 152/s
   * - medium polygons
     - 1.11s
     - 1.11s
     - 7.10ms
     - 1.11s
     - 1.14s
     - 15
     - 2.25k/s
   * - small polygons
     - 34.1ms
     - 33.9ms
     - 540µs
     - 33.7ms
     - 35.8ms
     - 15
     - 73.4k/s




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
     - 375ms
     - 376ms
     - 3.74ms
     - 367ms
     - 378ms
     - 15
     - 6.67k/s
   * - medium polygons
     - 138ms
     - 137ms
     - 1.95ms
     - 137ms
     - 145ms
     - 15
     - 18.1k/s
   * - small polygons
     - 6.26ms
     - 6.25ms
     - 54.4µs
     - 6.21ms
     - 6.43ms
     - 15
     - 399k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 165% faster (2.65x) than **bare kernel (C/clang)** (1.24ms vs 3.30ms)

* Medium polygons: **packed kernel (C/clang)** is 554% faster (6.54x) than **bare kernel (C/clang)** (1.35ms vs 8.87ms)

* Large polygons: **packed kernel (C/clang)** is 3265% faster (33.7x) than **bare kernel (C/clang)** (2.30ms vs 77.2ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 403% faster (5.03x) than **packed kernel (pure Python)** (1.24ms vs 6.26ms)

* Medium polygons: **packed kernel (C/clang)** is 10091% faster (102x) than **packed kernel (pure Python)** (1.35ms vs 138ms)

* Large polygons: **packed kernel (C/clang)** is 16218% faster (163x) than **packed kernel (pure Python)** (2.30ms vs 375ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.24ms), slowest is **packed kernel (pure Python) - large polygons** (375ms) - 30005% faster (301x)
