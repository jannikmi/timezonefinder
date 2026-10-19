

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~704ns per check on a small polygon, ~1.20µs on the largest** (1.70x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~33.3µs on the largest polygon (27.8x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 2.4454 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 83.2ms
     - 82.6ms
     - 2.10ms
     - 82.4ms
     - 90.8ms
     - 15
     - 30.0k/s
   * - medium polygons
     - 10.8ms
     - 10.7ms
     - 285µs
     - 10.3ms
     - 11.2ms
     - 15
     - 232k/s
   * - small polygons
     - 4.32ms
     - 4.31ms
     - 55.6µs
     - 4.28ms
     - 4.50ms
     - 15
     - 579k/s




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
     - 2.99ms
     - 7.23µs
     - 2.97ms
     - 3.00ms
     - 15
     - 836k/s
   * - medium polygons
     - 1.90ms
     - 1.90ms
     - 6.06µs
     - 1.89ms
     - 1.91ms
     - 15
     - 1.32M/s
   * - small polygons
     - 1.76ms
     - 1.75ms
     - 30.1µs
     - 1.74ms
     - 1.86ms
     - 15
     - 1.42M/s




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
     - 20.5s
     - 20.5s
     - 170ms
     - 20.3s
     - 20.7s
     - 5
     - 122/s
   * - medium polygons
     - 1.42s
     - 1.41s
     - 19.5ms
     - 1.38s
     - 1.44s
     - 15
     - 1.76k/s
   * - small polygons
     - 43.3ms
     - 42.9ms
     - 684µs
     - 42.7ms
     - 44.9ms
     - 15
     - 57.8k/s




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
     - 521ms
     - 525ms
     - 7.40ms
     - 510ms
     - 529ms
     - 15
     - 4.80k/s
   * - medium polygons
     - 187ms
     - 187ms
     - 672µs
     - 186ms
     - 188ms
     - 15
     - 13.4k/s
   * - small polygons
     - 9.29ms
     - 9.27ms
     - 48.4µs
     - 9.22ms
     - 9.38ms
     - 15
     - 269k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 146% faster (2.46x) than **bare kernel (C/clang)** (1.76ms vs 4.32ms)

* Medium polygons: **packed kernel (C/clang)** is 468% faster (5.68x) than **bare kernel (C/clang)** (1.90ms vs 10.8ms)

* Large polygons: **packed kernel (C/clang)** is 2684% faster (27.8x) than **bare kernel (C/clang)** (2.99ms vs 83.2ms)

**The C extension against pure Python**, on the kernel a lookup reaches. Which of the two interpreted implementations these rows describe is decided by the measuring environment, not by the benchmark - see :doc:`benchmark_results_acceleration_paths`, which measures all three against each other:

* Small polygons: **packed kernel (C/clang)** is 428% faster (5.28x) than **packed kernel (pure Python)** (1.76ms vs 9.29ms)

* Medium polygons: **packed kernel (C/clang)** is 9758% faster (98.6x) than **packed kernel (pure Python)** (1.90ms vs 187ms)

* Large polygons: **packed kernel (C/clang)** is 17315% faster (174x) than **packed kernel (pure Python)** (2.99ms vs 521ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.76ms), slowest is **packed kernel (pure Python) - large polygons** (521ms) - 29504% faster (296x)
