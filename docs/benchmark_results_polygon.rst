

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~284ns per check on a small polygon, ~22.5µs on the largest** (79.4x) - which is why this suite is stratified by vertex count instead of averaged.

*Measured on Darwin arm64, Python 3.14.2, using the Numba JIT point-in-polygon path.* Continuous integration tracks a different one - the C extension without Numba, what a plain ``pip install timezonefinder`` gives you - so these figures are not comparable to the trend chart. See :doc:`benchmarking_methodology`.



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


**C Implementation Available**: False

**Numba JIT Available**: True



Performance Optimizations
~~~~~~~~~~~~~~~~~~~~~~~~~


* ✗ Using pure Python point-in-polygon implementation

* ✓ Numba JIT compilation enabled



Benchmark Input Provenance
~~~~~~~~~~~~~~~~~~~~~~~~~~


**Fixture Version**: 2

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
     - 57.6ms
     - 57.6ms
     - 299µs
     - 57.1ms
     - 58.1ms
     - 17
     - 43.4k/s
   * - medium polygons
     - 6.30ms
     - 6.22ms
     - 288µs
     - 5.79ms
     - 6.96ms
     - 143
     - 397k/s
   * - small polygons
     - 2.59ms
     - 2.56ms
     - 147µs
     - 2.39ms
     - 3.01ms
     - 238
     - 965k/s




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
     - 56.3ms
     - 56.4ms
     - 291µs
     - 55.8ms
     - 56.9ms
     - 18
     - 44.4k/s
   * - medium polygons
     - 4.51ms
     - 4.45ms
     - 264µs
     - 4.11ms
     - 5.22ms
     - 191
     - 555k/s
   * - small polygons
     - 710µs
     - 695µs
     - 40.2µs
     - 681µs
     - 883µs
     - 156
     - 3.52M/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


* Small polygons: **point-in-polygon (Python, Numba if available)** is 265% faster (3.65x) than **point-in-polygon (C/clang)** (710µs vs 2.59ms)

* Medium polygons: **point-in-polygon (Python, Numba if available)** is 40% faster (1.40x) than **point-in-polygon (C/clang)** (4.51ms vs 6.30ms)

* Large polygons: **point-in-polygon (Python, Numba if available)** is 2% faster (1.02x) than **point-in-polygon (C/clang)** (56.3ms vs 57.6ms)

* Overall: fastest is **point-in-polygon (Python, Numba if available) - small polygons** (710µs), slowest is **point-in-polygon (C/clang) - large polygons** (57.6ms) - 8013% faster (81.1x)
