

Point-in-Polygon Algorithm Performance Benchmark
================================================




System Configuration
--------------------


* Python version: 3.12.1

* NumPy version: 2.2.6

* Numba enabled: True

* Test queries: 10,000



Performance Results
-------------------



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Implementation
     - Average Time (s)
     - Throughput (queries/sec)
   * - pt_in_poly_clang
     - 8.7e-06
     - 1.1e+05
   * - pt_in_poly_python
     - 2.8e-06
     - 3.6e+05




Performance Summary
-------------------


Python implementation WITH Numba is 2.2x faster than the C implementation

.. note::

   Performance results may vary based on system configuration, compiler optimizations, and runtime conditions.
