

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~285ns per check on a small polygon, ~22.5µs on the largest** (79.1x) - which is why this suite is stratified by vertex count instead of averaged.

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
     - 57.5ms
     - 57.5ms
     - 420µs
     - 56.8ms
     - 58.2ms
     - 17
     - 43.5k/s
   * - medium polygons
     - 6.31ms
     - 6.36ms
     - 301µs
     - 5.78ms
     - 7.00ms
     - 134
     - 396k/s
   * - small polygons
     - 2.58ms
     - 2.58ms
     - 185µs
     - 2.33ms
     - 3.07ms
     - 226
     - 969k/s




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
     - 56.2ms
     - 400µs
     - 55.6ms
     - 57.0ms
     - 18
     - 44.4k/s
   * - medium polygons
     - 4.56ms
     - 4.57ms
     - 255µs
     - 4.13ms
     - 5.31ms
     - 206
     - 548k/s
   * - small polygons
     - 712µs
     - 691µs
     - 45.9µs
     - 680µs
     - 876µs
     - 162
     - 3.51M/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


* Small polygons: **point-in-polygon (Python, Numba if available)** is 263% faster (3.63x) than **point-in-polygon (C/clang)** (712µs vs 2.58ms)

* Medium polygons: **point-in-polygon (Python, Numba if available)** is 38% faster (1.38x) than **point-in-polygon (C/clang)** (4.56ms vs 6.31ms)

* Large polygons: **point-in-polygon (Python, Numba if available)** is 2% faster (1.02x) than **point-in-polygon (C/clang)** (56.3ms vs 57.5ms)

* Overall: fastest is **point-in-polygon (Python, Numba if available) - small polygons** (712µs), slowest is **point-in-polygon (C/clang) - large polygons** (57.5ms) - 7982% faster (80.8x)
