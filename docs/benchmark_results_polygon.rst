

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
     - 57.3ms
     - 57.4ms
     - 612µs
     - 56.1ms
     - 58.3ms
     - 18
     - 43.6k/s
   * - medium polygons
     - 6.35ms
     - 6.37ms
     - 299µs
     - 5.80ms
     - 6.98ms
     - 147
     - 394k/s
   * - small polygons
     - 2.54ms
     - 2.47ms
     - 185µs
     - 2.35ms
     - 3.33ms
     - 291
     - 982k/s




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
     - 55.7ms
     - 55.6ms
     - 711µs
     - 54.7ms
     - 57.1ms
     - 19
     - 44.9k/s
   * - medium polygons
     - 4.30ms
     - 4.22ms
     - 209µs
     - 4.11ms
     - 5.11ms
     - 204
     - 582k/s
   * - small polygons
     - 692µs
     - 683µs
     - 20.9µs
     - 679µs
     - 789µs
     - 188
     - 3.61M/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


* Small polygons: **point-in-polygon (Python, Numba if available)** is 268% faster (3.68x) than **point-in-polygon (C/clang)** (692µs vs 2.54ms)

* Medium polygons: **point-in-polygon (Python, Numba if available)** is 48% faster (1.48x) than **point-in-polygon (C/clang)** (4.30ms vs 6.35ms)

* Large polygons: **point-in-polygon (Python, Numba if available)** is 3% faster (1.03x) than **point-in-polygon (C/clang)** (55.7ms vs 57.3ms)

* Overall: fastest is **point-in-polygon (Python, Numba if available) - small polygons** (692µs), slowest is **point-in-polygon (C/clang) - large polygons** (57.3ms) - 8186% faster (82.9x)
