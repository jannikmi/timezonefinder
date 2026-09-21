

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~654ns per check on a small polygon, ~1.21µs on the largest** (1.85x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~38.8µs on the largest polygon (32.0x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 2.8720 GHz, Python 3.13.15, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 97.0ms
     - 97.0ms
     - 252µs
     - 96.8ms
     - 97.8ms
     - 15
     - 25.8k/s
   * - medium polygons
     - 10.9ms
     - 10.9ms
     - 102µs
     - 10.8ms
     - 11.2ms
     - 15
     - 229k/s
   * - small polygons
     - 4.52ms
     - 4.51ms
     - 24.1µs
     - 4.49ms
     - 4.58ms
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
     - 3.03ms
     - 3.02ms
     - 21.5µs
     - 3.01ms
     - 3.08ms
     - 15
     - 824k/s
   * - medium polygons
     - 1.79ms
     - 1.79ms
     - 8.30µs
     - 1.77ms
     - 1.80ms
     - 15
     - 1.40M/s
   * - small polygons
     - 1.64ms
     - 1.64ms
     - 9.37µs
     - 1.62ms
     - 1.65ms
     - 15
     - 1.53M/s




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
     - 240ms
     - 18.7s
     - 19.4s
     - 15
     - 131/s
   * - medium polygons
     - 1.23s
     - 1.23s
     - 5.06ms
     - 1.22s
     - 1.24s
     - 15
     - 2.04k/s
   * - small polygons
     - 40.5ms
     - 40.5ms
     - 119µs
     - 40.3ms
     - 40.7ms
     - 15
     - 61.7k/s




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
     - 535ms
     - 535ms
     - 1.08ms
     - 533ms
     - 537ms
     - 15
     - 4.67k/s
   * - medium polygons
     - 133ms
     - 133ms
     - 338µs
     - 132ms
     - 133ms
     - 15
     - 18.8k/s
   * - small polygons
     - 11.3ms
     - 11.3ms
     - 69.1µs
     - 11.2ms
     - 11.4ms
     - 15
     - 221k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 176% faster (2.76x) than **bare kernel (C/clang)** (1.64ms vs 4.52ms)

* Medium polygons: **packed kernel (C/clang)** is 510% faster (6.10x) than **bare kernel (C/clang)** (1.79ms vs 10.9ms)

* Large polygons: **packed kernel (C/clang)** is 3099% faster (32.0x) than **bare kernel (C/clang)** (3.03ms vs 97.0ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 590% faster (6.90x) than **packed kernel (pure Python)** (1.64ms vs 11.3ms)

* Medium polygons: **packed kernel (C/clang)** is 7320% faster (74.2x) than **packed kernel (pure Python)** (1.79ms vs 133ms)

* Large polygons: **packed kernel (C/clang)** is 17539% faster (176x) than **packed kernel (pure Python)** (3.03ms vs 535ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.64ms), slowest is **packed kernel (pure Python) - large polygons** (535ms) - 32602% faster (327x)
