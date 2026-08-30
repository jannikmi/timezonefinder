

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~1.03µs per check on a small polygon, ~23.4µs on the largest** (22.7x) - which is why this suite is stratified by vertex count instead of averaged.

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
     - 58.5ms
     - 58.3ms
     - 641µs
     - 57.2ms
     - 59.6ms
     - 17
     - 42.8k/s
   * - medium polygons
     - 6.27ms
     - 6.27ms
     - 297µs
     - 5.64ms
     - 6.93ms
     - 145
     - 399k/s
   * - small polygons
     - 2.58ms
     - 2.56ms
     - 167µs
     - 2.34ms
     - 3.12ms
     - 374
     - 970k/s




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
     - 15.0s
     - 14.7s
     - 562ms
     - 14.5s
     - 15.9s
     - 5
     - 167/s
   * - medium polygons
     - 956ms
     - 957ms
     - 4.76ms
     - 950ms
     - 960ms
     - 5
     - 2.62k/s
   * - small polygons
     - 35.6ms
     - 35.5ms
     - 445µs
     - 34.9ms
     - 36.9ms
     - 29
     - 70.3k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


* Small polygons: **point-in-polygon (C/clang)** is 1279% faster (13.8x) than **point-in-polygon (Python, Numba if available)** (2.58ms vs 35.6ms)

* Medium polygons: **point-in-polygon (C/clang)** is 15152% faster (153x) than **point-in-polygon (Python, Numba if available)** (6.27ms vs 956ms)

* Large polygons: **point-in-polygon (C/clang)** is 25584% faster (257x) than **point-in-polygon (Python, Numba if available)** (58.5ms vs 15.0s)

* Overall: fastest is **point-in-polygon (C/clang) - small polygons** (2.58ms), slowest is **point-in-polygon (Python, Numba if available) - large polygons** (15.0s) - 582125% faster (5822x)
