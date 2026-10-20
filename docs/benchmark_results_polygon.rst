

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~494ns per check on a small polygon, ~913ns on the largest** (1.85x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~31.3µs on the largest polygon (34.3x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 3.9326 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 78.3ms
     - 77.7ms
     - 1.23ms
     - 77.5ms
     - 80.8ms
     - 15
     - 31.9k/s
   * - medium polygons
     - 9.15ms
     - 9.11ms
     - 95.5µs
     - 9.08ms
     - 9.46ms
     - 15
     - 273k/s
   * - small polygons
     - 3.27ms
     - 3.27ms
     - 25.4µs
     - 3.24ms
     - 3.34ms
     - 15
     - 764k/s




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
     - 2.28ms
     - 2.29ms
     - 16.6µs
     - 2.26ms
     - 2.32ms
     - 15
     - 1.09M/s
   * - medium polygons
     - 1.38ms
     - 1.37ms
     - 19.5µs
     - 1.36ms
     - 1.43ms
     - 15
     - 1.82M/s
   * - small polygons
     - 1.24ms
     - 1.24ms
     - 8.09µs
     - 1.22ms
     - 1.25ms
     - 15
     - 2.02M/s




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
     - 14.7s
     - 14.7s
     - 83.0ms
     - 14.6s
     - 14.8s
     - 5
     - 170/s
   * - medium polygons
     - 1.04s
     - 1.02s
     - 41.7ms
     - 999ms
     - 1.11s
     - 15
     - 2.41k/s
   * - small polygons
     - 31.9ms
     - 32.1ms
     - 969µs
     - 29.5ms
     - 32.8ms
     - 15
     - 78.4k/s




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
     - 384ms
     - 384ms
     - 16.4ms
     - 365ms
     - 413ms
     - 15
     - 6.51k/s
   * - medium polygons
     - 138ms
     - 138ms
     - 1.72ms
     - 137ms
     - 144ms
     - 15
     - 18.1k/s
   * - small polygons
     - 6.28ms
     - 6.25ms
     - 67.4µs
     - 6.20ms
     - 6.44ms
     - 15
     - 398k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 165% faster (2.65x) than **bare kernel (C/clang)** (1.24ms vs 3.27ms)

* Medium polygons: **packed kernel (C/clang)** is 564% faster (6.64x) than **bare kernel (C/clang)** (1.38ms vs 9.15ms)

* Large polygons: **packed kernel (C/clang)** is 3330% faster (34.3x) than **bare kernel (C/clang)** (2.28ms vs 78.3ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 408% faster (5.08x) than **packed kernel (pure Python)** (1.24ms vs 6.28ms)

* Medium polygons: **packed kernel (C/clang)** is 9950% faster (100x) than **packed kernel (pure Python)** (1.38ms vs 138ms)

* Large polygons: **packed kernel (C/clang)** is 16723% faster (168x) than **packed kernel (pure Python)** (2.28ms vs 384ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.24ms), slowest is **packed kernel (pure Python) - large polygons** (384ms) - 30985% faster (311x)
