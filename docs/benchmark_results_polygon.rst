

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~854ns per check on a small polygon, ~23.0µs on the largest** (26.9x) - which is why this suite is stratified by vertex count instead of averaged.

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
     - 57.4ms
     - 57.5ms
     - 453µs
     - 56.2ms
     - 58.2ms
     - 17
     - 43.5k/s
   * - medium polygons
     - 6.03ms
     - 5.88ms
     - 1.40ms
     - 5.30ms
     - 20.5ms
     - 161
     - 415k/s
   * - small polygons
     - 2.13ms
     - 2.10ms
     - 101µs
     - 2.02ms
     - 2.52ms
     - 448
     - 1.17M/s




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
     - 12.4s
     - 12.3s
     - 51.4ms
     - 12.3s
     - 12.4s
     - 5
     - 202/s
   * - medium polygons
     - 801ms
     - 801ms
     - 2.00ms
     - 799ms
     - 804ms
     - 5
     - 3.12k/s
   * - small polygons
     - 29.6ms
     - 29.7ms
     - 527µs
     - 28.5ms
     - 31.2ms
     - 34
     - 84.3k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


* Small polygons: **point-in-polygon (C/clang)** is 1289% faster (13.9x) than **point-in-polygon (Python, Numba if available)** (2.13ms vs 29.6ms)

* Medium polygons: **point-in-polygon (C/clang)** is 13190% faster (133x) than **point-in-polygon (Python, Numba if available)** (6.03ms vs 801ms)

* Large polygons: **point-in-polygon (C/clang)** is 21414% faster (215x) than **point-in-polygon (Python, Numba if available)** (57.4ms vs 12.4s)

* Overall: fastest is **point-in-polygon (C/clang) - small polygons** (2.13ms), slowest is **point-in-polygon (Python, Numba if available) - large polygons** (12.4s) - 579120% faster (5792x)
