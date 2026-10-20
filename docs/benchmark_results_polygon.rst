

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~375ns per check on a small polygon, ~637ns on the largest** (1.70x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~19.1µs on the largest polygon (29.9x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 9V45 96-Core Processor @ 4.3482 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 47.7ms
     - 47.4ms
     - 825µs
     - 46.7ms
     - 49.3ms
     - 15
     - 52.4k/s
   * - medium polygons
     - 6.60ms
     - 6.54ms
     - 124µs
     - 6.43ms
     - 6.88ms
     - 15
     - 379k/s
   * - small polygons
     - 2.50ms
     - 2.48ms
     - 78.8µs
     - 2.45ms
     - 2.76ms
     - 15
     - 998k/s




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
     - 1.59ms
     - 1.59ms
     - 10.8µs
     - 1.58ms
     - 1.62ms
     - 15
     - 1.57M/s
   * - medium polygons
     - 1.04ms
     - 1.04ms
     - 7.03µs
     - 1.03ms
     - 1.06ms
     - 15
     - 2.40M/s
   * - small polygons
     - 937µs
     - 939µs
     - 8.52µs
     - 918µs
     - 952µs
     - 15
     - 2.67M/s




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
     - 9.64s
     - 9.60s
     - 106ms
     - 9.54s
     - 9.75s
     - 5
     - 259/s
   * - medium polygons
     - 670ms
     - 668ms
     - 9.37ms
     - 659ms
     - 693ms
     - 15
     - 3.73k/s
   * - small polygons
     - 20.7ms
     - 20.5ms
     - 426µs
     - 20.4ms
     - 21.8ms
     - 15
     - 121k/s




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
     - 275ms
     - 275ms
     - 2.65ms
     - 270ms
     - 281ms
     - 15
     - 9.10k/s
   * - medium polygons
     - 110ms
     - 110ms
     - 627µs
     - 109ms
     - 112ms
     - 15
     - 22.8k/s
   * - small polygons
     - 4.93ms
     - 4.92ms
     - 21.8µs
     - 4.91ms
     - 5.00ms
     - 15
     - 507k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 167% faster (2.67x) than **bare kernel (C/clang)** (937µs vs 2.50ms)

* Medium polygons: **packed kernel (C/clang)** is 535% faster (6.35x) than **bare kernel (C/clang)** (1.04ms vs 6.60ms)

* Large polygons: **packed kernel (C/clang)** is 2894% faster (29.9x) than **bare kernel (C/clang)** (1.59ms vs 47.7ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 426% faster (5.26x) than **packed kernel (pure Python)** (937µs vs 4.93ms)

* Medium polygons: **packed kernel (C/clang)** is 10451% faster (106x) than **packed kernel (pure Python)** (1.04ms vs 110ms)

* Large polygons: **packed kernel (C/clang)** is 17136% faster (172x) than **packed kernel (pure Python)** (1.59ms vs 275ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (937µs), slowest is **packed kernel (pure Python) - large polygons** (275ms) - 29225% faster (293x)
