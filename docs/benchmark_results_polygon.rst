

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

Each benchmark times one pass over 1,000 fixed, committed (point, polygon) pairs drawn from a single polygon-size stratum, so the cost of the largest polygons isn't hidden behind an unweighted average.



Results
~~~~~~~




point-in-polygon (C/clang)
^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 14 14 14 14 14 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
   * - large polygons
     - 5.38e-02s
     - 5.38e-02s
     - 1.41e-04s
     - 5.37e-02s
     - 5.43e-02s
     - 18
   * - medium polygons
     - 5.59e-03s
     - 5.61e-03s
     - 1.20e-04s
     - 5.34e-03s
     - 6.23e-03s
     - 152
   * - small polygons
     - 1.42e-03s
     - 1.41e-03s
     - 2.62e-05s
     - 1.40e-03s
     - 1.83e-03s
     - 376




point-in-polygon (Python, Numba if available)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 14 14 14 14 14 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
   * - large polygons
     - 2.39e-02s
     - 2.39e-02s
     - 7.15e-05s
     - 2.38e-02s
     - 2.42e-02s
     - 42
   * - medium polygons
     - 1.93e-03s
     - 1.92e-03s
     - 4.06e-05s
     - 1.91e-03s
     - 2.12e-03s
     - 479
   * - small polygons
     - 2.80e-04s
     - 2.79e-04s
     - 3.09e-06s
     - 2.78e-04s
     - 3.01e-04s
     - 305
