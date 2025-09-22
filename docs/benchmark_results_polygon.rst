

Point-in-Polygon Algorithm Performance Benchmark
================================================




System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.12.1 (CPython)

**NumPy Version**: 2.2.6

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


**Test Queries**: 10,000

**Algorithm Type**: Point-in-Polygon

**Test Data Type**: Random polygons with random query points



Performance Results
-------------------



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Implementation
     - Average Time (s)
     - Throughput (queries/sec)
   * - pt_in_poly_clang
     - 8.5e-06
     - 1.2e+05
   * - pt_in_poly_python
     - 2.7e-06
     - 3.7e+05




Performance Summary
-------------------


Python implementation WITH Numba is 2.1x faster than the C implementation

.. note::

   Performance results may vary based on system configuration, compiler optimizations, and runtime conditions.
