

Point-in-Polygon Algorithm Performance Benchmark
================================================




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
     - 143ms
     - 143ms
     - 861µs
     - 141ms
     - 144ms
     - 7
     - 17.5k/s
   * - medium polygons
     - 14.4ms
     - 14.5ms
     - 453µs
     - 13.4ms
     - 15.3ms
     - 65
     - 173k/s
   * - small polygons
     - 3.95ms
     - 3.90ms
     - 335µs
     - 3.46ms
     - 4.77ms
     - 178
     - 633k/s




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
     - 63.0ms
     - 63.2ms
     - 1.16ms
     - 60.9ms
     - 64.9ms
     - 16
     - 39.7k/s
   * - medium polygons
     - 5.10ms
     - 5.10ms
     - 261µs
     - 4.62ms
     - 5.78ms
     - 193
     - 490k/s
   * - small polygons
     - 748µs
     - 717µs
     - 69.2µs
     - 690µs
     - 1.01ms
     - 151
     - 3.34M/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


* Small polygons: **point-in-polygon (Python, Numba if available)** is 428% faster (5.28x) than **point-in-polygon (C/clang)** (748µs vs 3.95ms)

* Medium polygons: **point-in-polygon (Python, Numba if available)** is 183% faster (2.83x) than **point-in-polygon (C/clang)** (5.10ms vs 14.4ms)

* Large polygons: **point-in-polygon (Python, Numba if available)** is 126% faster (2.26x) than **point-in-polygon (C/clang)** (63.0ms vs 143ms)

* Overall: fastest is **point-in-polygon (Python, Numba if available) - small polygons** (748µs), slowest is **point-in-polygon (C/clang) - large polygons** (143ms) - 18965% faster (191x)
