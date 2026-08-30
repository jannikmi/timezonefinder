

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~985ns per check on a small polygon, ~22.7µs on the largest** (23.0x) - which is why this suite is stratified by vertex count instead of averaged.

*Measured on Darwin arm64, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.14.2 (CPython)

**NumPy Version**: 2.3.5

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



Results
~~~~~~~




point-in-polygon (C/clang)
^^^^^^^^^^^^^^^^^^^^^^^^^^



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
     - 56.7ms
     - 56.8ms
     - 421µs
     - 55.7ms
     - 57.3ms
     - 17
     - 44.1k/s
   * - medium polygons
     - 6.01ms
     - 6.00ms
     - 231µs
     - 5.62ms
     - 6.57ms
     - 147
     - 416k/s
   * - small polygons
     - 2.46ms
     - 2.41ms
     - 122µs
     - 2.34ms
     - 2.90ms
     - 370
     - 1.02M/s




point-in-polygon (Python, Numba if available)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



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
     - 14.2s
     - 14.2s
     - 78.1ms
     - 14.1s
     - 14.3s
     - 5
     - 176/s
   * - medium polygons
     - 919ms
     - 919ms
     - 866µs
     - 917ms
     - 919ms
     - 5
     - 2.72k/s
   * - small polygons
     - 34.9ms
     - 34.8ms
     - 742µs
     - 33.3ms
     - 36.9ms
     - 29
     - 71.7k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


* Small polygons: **point-in-polygon (C/clang)** is 1316% faster (14.2x) than **point-in-polygon (Python, Numba if available)** (2.46ms vs 34.9ms)

* Medium polygons: **point-in-polygon (C/clang)** is 15191% faster (153x) than **point-in-polygon (Python, Numba if available)** (6.01ms vs 919ms)

* Large polygons: **point-in-polygon (C/clang)** is 24908% faster (250x) than **point-in-polygon (Python, Numba if available)** (56.7ms vs 14.2s)

* Overall: fastest is **point-in-polygon (C/clang) - small polygons** (2.46ms), slowest is **point-in-polygon (Python, Numba if available) - large polygons** (14.2s) - 575262% faster (5754x)
