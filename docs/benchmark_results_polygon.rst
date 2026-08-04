

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



Benchmark Configuration
~~~~~~~~~~~~~~~~~~~~~~~


**Benchmark Source**: pytest-benchmark

**Batch Size**: 1,000

**Polygon Strata**: small / medium / large (by vertex count percentile)

Each benchmark times one pass over 1,000 fixed, committed (point, polygon) pairs drawn from a single polygon-size stratum, so the cost of the largest polygons isn't hidden behind an unweighted average. Mean/Median/StdDev/Min/Max are for the full 1,000-pair batch; Throughput is queries/second for that batch.



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
     - 55.8ms
     - 55.6ms
     - 569µs
     - 55.1ms
     - 57.2ms
     - 18
     - 17.9k/s
   * - medium polygons
     - 5.77ms
     - 5.73ms
     - 258µs
     - 5.37ms
     - 6.35ms
     - 152
     - 173k/s
   * - small polygons
     - 1.50ms
     - 1.45ms
     - 117µs
     - 1.40ms
     - 1.93ms
     - 275
     - 666k/s




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
     - 25.2ms
     - 25.2ms
     - 281µs
     - 24.7ms
     - 25.7ms
     - 40
     - 39.7k/s
   * - medium polygons
     - 2.07ms
     - 2.03ms
     - 142µs
     - 1.91ms
     - 2.51ms
     - 436
     - 483k/s
   * - small polygons
     - 285µs
     - 278µs
     - 17.3µs
     - 277µs
     - 394µs
     - 157
     - 3.51M/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


* Small polygons: **point-in-polygon (Python, Numba if available)** is 427% faster (5.27x) than **point-in-polygon (C/clang)** (285µs vs 1.50ms)

* Medium polygons: **point-in-polygon (Python, Numba if available)** is 179% faster (2.79x) than **point-in-polygon (C/clang)** (2.07ms vs 5.77ms)

* Large polygons: **point-in-polygon (Python, Numba if available)** is 121% faster (2.21x) than **point-in-polygon (C/clang)** (25.2ms vs 55.8ms)

* Overall: fastest is **point-in-polygon (Python, Numba if available) - small polygons** (285µs), slowest is **point-in-polygon (C/clang) - large polygons** (55.8ms) - 19496% faster (196x)
