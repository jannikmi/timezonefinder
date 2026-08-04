

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
     - 53.8ms
     - 53.8ms
     - 141µs
     - 53.7ms
     - 54.3ms
     - 18
     - 18.6k/s
   * - medium polygons
     - 5.59ms
     - 5.61ms
     - 120µs
     - 5.34ms
     - 6.23ms
     - 152
     - 179k/s
   * - small polygons
     - 1.42ms
     - 1.41ms
     - 26.2µs
     - 1.40ms
     - 1.83ms
     - 376
     - 705k/s




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
     - 23.9ms
     - 23.9ms
     - 71.5µs
     - 23.8ms
     - 24.2ms
     - 42
     - 41.8k/s
   * - medium polygons
     - 1.93ms
     - 1.92ms
     - 40.6µs
     - 1.91ms
     - 2.12ms
     - 479
     - 517k/s
   * - small polygons
     - 280µs
     - 279µs
     - 3.09µs
     - 278µs
     - 301µs
     - 305
     - 3.57M/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


* Small polygons: **point-in-polygon (Python, Numba if available)** is 80% faster (5.07x) than **point-in-polygon (C/clang)** (280µs vs 1.42ms)

* Medium polygons: **point-in-polygon (Python, Numba if available)** is 65% faster (2.89x) than **point-in-polygon (C/clang)** (1.93ms vs 5.59ms)

* Large polygons: **point-in-polygon (Python, Numba if available)** is 56% faster (2.25x) than **point-in-polygon (C/clang)** (23.9ms vs 53.8ms)

* Overall: fastest is **point-in-polygon (Python, Numba if available) - small polygons** (280µs), slowest is **point-in-polygon (C/clang) - large polygons** (53.8ms) - 99% faster (192x)
