

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~293ns per check on a small polygon, ~22.3µs on the largest** (76.2x) - which is why this suite is stratified by vertex count instead of averaged.

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
     - 57.1ms
     - 57.1ms
     - 204µs
     - 56.7ms
     - 57.4ms
     - 18
     - 43.8k/s
   * - medium polygons
     - 6.17ms
     - 6.20ms
     - 216µs
     - 5.65ms
     - 6.72ms
     - 148
     - 405k/s
   * - small polygons
     - 2.55ms
     - 2.55ms
     - 131µs
     - 2.36ms
     - 2.88ms
     - 296
     - 979k/s




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
     - 55.9ms
     - 55.9ms
     - 211µs
     - 55.4ms
     - 56.1ms
     - 18
     - 44.7k/s
   * - medium polygons
     - 4.37ms
     - 4.38ms
     - 199µs
     - 4.00ms
     - 4.83ms
     - 221
     - 572k/s
   * - small polygons
     - 733µs
     - 715µs
     - 40.0µs
     - 708µs
     - 896µs
     - 184
     - 3.41M/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


* Small polygons: **point-in-polygon (Python, Numba if available)** is 248% faster (3.48x) than **point-in-polygon (C/clang)** (733µs vs 2.55ms)

* Medium polygons: **point-in-polygon (Python, Numba if available)** is 41% faster (1.41x) than **point-in-polygon (C/clang)** (4.37ms vs 6.17ms)

* Large polygons: **point-in-polygon (Python, Numba if available)** is 2% faster (1.02x) than **point-in-polygon (C/clang)** (55.9ms vs 57.1ms)

* Overall: fastest is **point-in-polygon (Python, Numba if available) - small polygons** (733µs), slowest is **point-in-polygon (C/clang) - large polygons** (57.1ms) - 7692% faster (77.9x)
