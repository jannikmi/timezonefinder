

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~598ns per check on a small polygon, ~1.01µs on the largest** (1.70x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~37.5µs on the largest polygon (37.0x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, INTEL(R) XEON(R) PLATINUM 8573C @ 3.1028 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 93.8ms
     - 93.6ms
     - 1.01ms
     - 92.5ms
     - 96.3ms
     - 15
     - 26.7k/s
   * - medium polygons
     - 9.20ms
     - 9.15ms
     - 342µs
     - 8.74ms
     - 10.1ms
     - 15
     - 272k/s
   * - small polygons
     - 3.54ms
     - 3.53ms
     - 103µs
     - 3.46ms
     - 3.88ms
     - 15
     - 705k/s




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
     - 2.54ms
     - 2.53ms
     - 35.5µs
     - 2.47ms
     - 2.59ms
     - 15
     - 986k/s
   * - medium polygons
     - 1.64ms
     - 1.62ms
     - 63.0µs
     - 1.59ms
     - 1.85ms
     - 15
     - 1.52M/s
   * - small polygons
     - 1.50ms
     - 1.48ms
     - 29.2µs
     - 1.46ms
     - 1.56ms
     - 15
     - 1.67M/s




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
     - 16.3s
     - 16.2s
     - 43.7ms
     - 16.2s
     - 16.3s
     - 5
     - 154/s
   * - medium polygons
     - 1.02s
     - 1.02s
     - 2.57ms
     - 1.02s
     - 1.03s
     - 15
     - 2.45k/s
   * - small polygons
     - 34.5ms
     - 34.5ms
     - 261µs
     - 34.1ms
     - 35.0ms
     - 15
     - 72.4k/s




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
     - 431ms
     - 431ms
     - 1.64ms
     - 429ms
     - 435ms
     - 15
     - 5.79k/s
   * - medium polygons
     - 148ms
     - 147ms
     - 3.58ms
     - 145ms
     - 160ms
     - 15
     - 16.9k/s
   * - small polygons
     - 7.40ms
     - 7.39ms
     - 150µs
     - 7.21ms
     - 7.71ms
     - 15
     - 338k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 137% faster (2.37x) than **bare kernel (C/clang)** (1.50ms vs 3.54ms)

* Medium polygons: **packed kernel (C/clang)** is 460% faster (5.60x) than **bare kernel (C/clang)** (1.64ms vs 9.20ms)

* Large polygons: **packed kernel (C/clang)** is 3598% faster (37.0x) than **bare kernel (C/clang)** (2.54ms vs 93.8ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 395% faster (4.95x) than **packed kernel (pure Python)** (1.50ms vs 7.40ms)

* Medium polygons: **packed kernel (C/clang)** is 8906% faster (90.1x) than **packed kernel (pure Python)** (1.64ms vs 148ms)

* Large polygons: **packed kernel (C/clang)** is 16911% faster (170x) than **packed kernel (pure Python)** (2.54ms vs 431ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.50ms), slowest is **packed kernel (pure Python) - large polygons** (431ms) - 28749% faster (288x)
