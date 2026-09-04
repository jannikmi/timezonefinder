

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~353ns per check on a small polygon, ~571ns on the largest** (1.62x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~22.6µs on the largest polygon (39.5x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

*Measured on Darwin arm64, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.



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
     - 56.5ms
     - 56.5ms
     - 388µs
     - 55.6ms
     - 57.2ms
     - 15
     - 44.3k/s
   * - medium polygons
     - 6.21ms
     - 6.19ms
     - 102µs
     - 6.07ms
     - 6.75ms
     - 132
     - 403k/s
   * - small polygons
     - 2.13ms
     - 2.10ms
     - 93.4µs
     - 2.02ms
     - 2.70ms
     - 411
     - 1.18M/s




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
     - 1.43ms
     - 1.39ms
     - 81.2µs
     - 1.36ms
     - 1.68ms
     - 571
     - 1.75M/s
   * - medium polygons
     - 962µs
     - 939µs
     - 53.8µs
     - 921µs
     - 1.21ms
     - 875
     - 2.60M/s
   * - small polygons
     - 883µs
     - 863µs
     - 45.0µs
     - 850µs
     - 1.11ms
     - 1013
     - 2.83M/s




bare kernel (Python, Numba if available)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



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
     - 12.3s
     - 12.3s
     - 57.8ms
     - 12.2s
     - 12.4s
     - 5
     - 204/s
   * - medium polygons
     - 792ms
     - 793ms
     - 1.51ms
     - 790ms
     - 794ms
     - 5
     - 3.15k/s
   * - small polygons
     - 28.6ms
     - 28.4ms
     - 376µs
     - 28.2ms
     - 29.8ms
     - 35
     - 87.6k/s




packed kernel (Python, Numba if available)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



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
     - 293ms
     - 294ms
     - 1.72ms
     - 291ms
     - 295ms
     - 5
     - 8.52k/s
   * - medium polygons
     - 89.4ms
     - 89.4ms
     - 258µs
     - 89.1ms
     - 90.0ms
     - 12
     - 27.9k/s
   * - small polygons
     - 4.72ms
     - 4.70ms
     - 104µs
     - 4.55ms
     - 4.98ms
     - 209
     - 529k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 141% faster (2.41x) than **bare kernel (C/clang)** (883µs vs 2.13ms)

* Medium polygons: **packed kernel (C/clang)** is 545% faster (6.45x) than **bare kernel (C/clang)** (962µs vs 6.21ms)

* Large polygons: **packed kernel (C/clang)** is 3852% faster (39.5x) than **bare kernel (C/clang)** (1.43ms vs 56.5ms)

**C against Python/Numba**, on the kernel a lookup reaches:

* Small polygons: **packed kernel (C/clang)** is 435% faster (5.35x) than **packed kernel (Python, Numba if available)** (883µs vs 4.72ms)

* Medium polygons: **packed kernel (C/clang)** is 9198% faster (93.0x) than **packed kernel (Python, Numba if available)** (962µs vs 89.4ms)

* Large polygons: **packed kernel (C/clang)** is 20432% faster (205x) than **packed kernel (Python, Numba if available)** (1.43ms vs 293ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (883µs), slowest is **packed kernel (Python, Numba if available) - large polygons** (293ms) - 33111% faster (332x)
