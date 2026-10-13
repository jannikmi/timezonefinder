

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~331ns per check on a small polygon, ~831ns on the largest** (2.51x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~22.0µs on the largest polygon (26.4x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

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
     - 54.9ms
     - 54.8ms
     - 545µs
     - 54.6ms
     - 56.8ms
     - 15
     - 45.5k/s
   * - medium polygons
     - 5.68ms
     - 5.66ms
     - 102µs
     - 5.50ms
     - 5.89ms
     - 15
     - 440k/s
   * - small polygons
     - 1.94ms
     - 1.92ms
     - 92.4µs
     - 1.88ms
     - 2.25ms
     - 15
     - 1.29M/s




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
     - 2.08ms
     - 1.59ms
     - 1.17ms
     - 1.30ms
     - 5.67ms
     - 15
     - 1.20M/s
   * - medium polygons
     - 875µs
     - 862µs
     - 27.6µs
     - 859µs
     - 938µs
     - 15
     - 2.86M/s
   * - small polygons
     - 827µs
     - 808µs
     - 40.8µs
     - 804µs
     - 958µs
     - 15
     - 3.02M/s




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
     - 11.8s
     - 11.8s
     - 24.1ms
     - 11.8s
     - 11.9s
     - 15
     - 211/s
   * - medium polygons
     - 743ms
     - 741ms
     - 5.59ms
     - 738ms
     - 752ms
     - 15
     - 3.36k/s
   * - small polygons
     - 25.4ms
     - 25.3ms
     - 423µs
     - 25.0ms
     - 26.4ms
     - 15
     - 98.6k/s




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
     - 270ms
     - 268ms
     - 5.92ms
     - 266ms
     - 287ms
     - 15
     - 9.25k/s
   * - medium polygons
     - 97.2ms
     - 90.3ms
     - 22.5ms
     - 84.6ms
     - 175ms
     - 15
     - 25.7k/s
   * - small polygons
     - 6.36ms
     - 5.16ms
     - 3.00ms
     - 4.62ms
     - 16.5ms
     - 15
     - 393k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 134% faster (2.34x) than **bare kernel (C/clang)** (827µs vs 1.94ms)

* Medium polygons: **packed kernel (C/clang)** is 549% faster (6.49x) than **bare kernel (C/clang)** (875µs vs 5.68ms)

* Large polygons: **packed kernel (C/clang)** is 2544% faster (26.4x) than **bare kernel (C/clang)** (2.08ms vs 54.9ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 669% faster (7.69x) than **packed kernel (pure Python)** (827µs vs 6.36ms)

* Medium polygons: **packed kernel (C/clang)** is 11013% faster (111x) than **packed kernel (pure Python)** (875µs vs 97.2ms)

* Large polygons: **packed kernel (C/clang)** is 12906% faster (130x) than **packed kernel (pure Python)** (2.08ms vs 270ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (827µs), slowest is **packed kernel (pure Python) - large polygons** (270ms) - 32592% faster (327x)
