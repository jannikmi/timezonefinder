

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

**Test Data Type**: Random timezone boundary polygons with random query points

**Polygon Source**: TimezoneFinder's timezone boundary dataset



Test Methodology
----------------


**Polygons Used**: Random timezone boundary polygons from TimezoneFinder's dataset

**Query Points**: Random geographic coordinates (longitude, latitude)

**Test Process**: Each test iteration selects a random polygon from the timezone boundary dataset and a random query point, then measures the time to determine if the point lies within the polygon

**Polygon Characteristics**: Real-world timezone boundaries with varying complexity, from simple rectangular shapes to highly detailed coastlines and political boundaries



Performance Results
-------------------



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Implementation
     - Average Time (s)
     - Throughput (queries/sec)
   * - pt_in_poly_clang
     - 7.7e-06
     - 1.3e+05
   * - pt_in_poly_python
     - 2.6e-06
     - 3.9e+05




Performance Summary
-------------------


Python implementation WITH Numba is 2.0x faster than the C implementation

.. note::

   Performance results may vary based on system configuration, compiler optimizations, runtime conditions, and the complexity of the randomly selected timezone boundary polygons used in each test run.
