

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~620ns per check on a small polygon, ~1.43µs on the largest** (2.31x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~36.9µs on the largest polygon (25.8x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 2.8000 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 92.3ms
     - 92.2ms
     - 370µs
     - 91.8ms
     - 92.9ms
     - 15
     - 27.1k/s
   * - medium polygons
     - 10.4ms
     - 10.4ms
     - 50.3µs
     - 10.3ms
     - 10.4ms
     - 15
     - 241k/s
   * - small polygons
     - 4.60ms
     - 4.57ms
     - 125µs
     - 4.45ms
     - 4.92ms
     - 15
     - 543k/s




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
     - 3.58ms
     - 3.54ms
     - 87.7µs
     - 3.53ms
     - 3.87ms
     - 15
     - 699k/s
   * - medium polygons
     - 1.72ms
     - 1.72ms
     - 13.6µs
     - 1.71ms
     - 1.75ms
     - 15
     - 1.45M/s
   * - small polygons
     - 1.55ms
     - 1.55ms
     - 7.00µs
     - 1.54ms
     - 1.57ms
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
     - 16.4s
     - 16.3s
     - 118ms
     - 16.3s
     - 16.7s
     - 15
     - 153/s
   * - medium polygons
     - 1.03s
     - 1.03s
     - 1.88ms
     - 1.02s
     - 1.03s
     - 15
     - 2.44k/s
   * - small polygons
     - 36.3ms
     - 36.3ms
     - 81.5µs
     - 36.2ms
     - 36.4ms
     - 15
     - 68.9k/s




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
     - 476ms
     - 476ms
     - 1.70ms
     - 474ms
     - 480ms
     - 15
     - 5.25k/s
   * - medium polygons
     - 173ms
     - 173ms
     - 386µs
     - 172ms
     - 174ms
     - 15
     - 14.5k/s
   * - small polygons
     - 8.76ms
     - 8.76ms
     - 50.7µs
     - 8.68ms
     - 8.88ms
     - 15
     - 285k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 197% faster (2.97x) than **bare kernel (C/clang)** (1.55ms vs 4.60ms)

* Medium polygons: **packed kernel (C/clang)** is 504% faster (6.04x) than **bare kernel (C/clang)** (1.72ms vs 10.4ms)

* Large polygons: **packed kernel (C/clang)** is 2481% faster (25.8x) than **bare kernel (C/clang)** (3.58ms vs 92.3ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 466% faster (5.66x) than **packed kernel (pure Python)** (1.55ms vs 8.76ms)

* Medium polygons: **packed kernel (C/clang)** is 9947% faster (100x) than **packed kernel (pure Python)** (1.72ms vs 173ms)

* Large polygons: **packed kernel (C/clang)** is 13226% faster (133x) than **packed kernel (pure Python)** (3.58ms vs 476ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.55ms), slowest is **packed kernel (pure Python) - large polygons** (476ms) - 30654% faster (308x)
