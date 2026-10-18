

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~695ns per check on a small polygon, ~1.19µs on the largest** (1.72x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~32.2µs on the largest polygon (26.9x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2440 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 80.4ms
     - 80.2ms
     - 425µs
     - 80.0ms
     - 81.5ms
     - 15
     - 31.1k/s
   * - medium polygons
     - 9.64ms
     - 9.64ms
     - 154µs
     - 9.44ms
     - 9.96ms
     - 15
     - 259k/s
   * - small polygons
     - 4.51ms
     - 4.40ms
     - 226µs
     - 4.34ms
     - 4.97ms
     - 15
     - 554k/s




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
     - 2.99ms
     - 2.98ms
     - 15.8µs
     - 2.97ms
     - 3.02ms
     - 15
     - 837k/s
   * - medium polygons
     - 1.87ms
     - 1.87ms
     - 12.2µs
     - 1.85ms
     - 1.90ms
     - 15
     - 1.34M/s
   * - small polygons
     - 1.74ms
     - 1.74ms
     - 7.73µs
     - 1.73ms
     - 1.75ms
     - 15
     - 1.44M/s




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
     - 21.2s
     - 21.4s
     - 420ms
     - 20.5s
     - 21.5s
     - 5
     - 118/s
   * - medium polygons
     - 1.25s
     - 1.25s
     - 3.62ms
     - 1.24s
     - 1.25s
     - 15
     - 2.01k/s
   * - small polygons
     - 39.9ms
     - 39.8ms
     - 241µs
     - 39.7ms
     - 40.6ms
     - 15
     - 62.6k/s




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
     - 528ms
     - 527ms
     - 3.03ms
     - 524ms
     - 534ms
     - 15
     - 4.74k/s
   * - medium polygons
     - 144ms
     - 144ms
     - 373µs
     - 143ms
     - 145ms
     - 15
     - 17.4k/s
   * - small polygons
     - 11.4ms
     - 11.4ms
     - 34.8µs
     - 11.4ms
     - 11.5ms
     - 15
     - 218k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 160% faster (2.60x) than **bare kernel (C/clang)** (1.74ms vs 4.51ms)

* Medium polygons: **packed kernel (C/clang)** is 416% faster (5.16x) than **bare kernel (C/clang)** (1.87ms vs 9.64ms)

* Large polygons: **packed kernel (C/clang)** is 2592% faster (26.9x) than **bare kernel (C/clang)** (2.99ms vs 80.4ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 558% faster (6.58x) than **packed kernel (pure Python)** (1.74ms vs 11.4ms)

* Medium polygons: **packed kernel (C/clang)** is 7606% faster (77.1x) than **packed kernel (pure Python)** (1.87ms vs 144ms)

* Large polygons: **packed kernel (C/clang)** is 17573% faster (177x) than **packed kernel (pure Python)** (2.99ms vs 528ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.74ms), slowest is **packed kernel (pure Python) - large polygons** (528ms) - 30249% faster (303x)
