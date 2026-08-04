

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
     - 670µs
     - 142ms
     - 144ms
     - 7
     - 17.5k/s
   * - medium polygons
     - 14.5ms
     - 14.5ms
     - 455µs
     - 13.6ms
     - 15.3ms
     - 64
     - 173k/s
   * - small polygons
     - 4.08ms
     - 4.03ms
     - 353µs
     - 3.52ms
     - 4.94ms
     - 206
     - 613k/s




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
     - 64.4ms
     - 64.5ms
     - 468µs
     - 63.7ms
     - 65.1ms
     - 16
     - 38.8k/s
   * - medium polygons
     - 5.23ms
     - 5.27ms
     - 292µs
     - 4.64ms
     - 5.90ms
     - 180
     - 478k/s
   * - small polygons
     - 738µs
     - 724µs
     - 51.4µs
     - 690µs
     - 901µs
     - 30
     - 3.39M/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


* Small polygons: **point-in-polygon (Python, Numba if available)** is 453% faster (5.53x) than **point-in-polygon (C/clang)** (738µs vs 4.08ms)

* Medium polygons: **point-in-polygon (Python, Numba if available)** is 177% faster (2.77x) than **point-in-polygon (C/clang)** (5.23ms vs 14.5ms)

* Large polygons: **point-in-polygon (Python, Numba if available)** is 122% faster (2.22x) than **point-in-polygon (C/clang)** (64.4ms vs 143ms)

* Overall: fastest is **point-in-polygon (Python, Numba if available) - small polygons** (738µs), slowest is **point-in-polygon (C/clang) - large polygons** (143ms) - 19305% faster (194x)
