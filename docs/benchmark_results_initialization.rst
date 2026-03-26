

TimezoneFinder Initialization Performance Benchmark
===================================================




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


**Test Runs Per Configuration**: 100

**Algorithm Type**: Class Initialization

**Test Configurations**: TimezoneFinder and TimezoneFinderL with file-based and in-memory modes



Initialization Performance Results
----------------------------------



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Configuration
     - Average Time (ms)
     - Average Time (s)
   * - TimezoneFinder (File-Based)
     - 216.3
     - 0.216
   * - TimezoneFinder (In-Memory)
     - 218.9
     - 0.219
   * - TimezoneFinderL (File-Based)
     - 207.5
     - 0.208
   * - TimezoneFinderL (In-Memory)
     - 208.1
     - 0.208




Performance Analysis
--------------------


* **Fastest configuration**: TimezoneFinderL (File-Based) (207.5 ms)

* **Slowest configuration**: TimezoneFinder (In-Memory) (218.9 ms)

* **Performance difference**: 5% faster


* **File-based mode** is 1% faster (211.9 ms vs 213.5 ms)

.. note::

   Initialization times may vary based on system I/O performance, available memory, and background system activity. In-memory mode loads all data into RAM during initialization, while file-based mode opens files but defers data loading.
