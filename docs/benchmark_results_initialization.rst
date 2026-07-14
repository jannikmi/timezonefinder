

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
     - 216.9
     - 0.217
   * - TimezoneFinder (In-Memory)
     - 225.0
     - 0.225
   * - TimezoneFinderL (File-Based)
     - 212.8
     - 0.213
   * - TimezoneFinderL (In-Memory)
     - 210.4
     - 0.210




Performance Analysis
--------------------


* **Fastest configuration**: TimezoneFinderL (In-Memory) (210.4 ms)

* **Slowest configuration**: TimezoneFinder (In-Memory) (225.0 ms)

* **Performance difference**: 6% faster


* **File-based mode** is 1% faster (214.9 ms vs 217.7 ms)

.. note::

   Initialization times may vary based on system I/O performance, available memory, and background system activity. In-memory mode loads all data into RAM during initialization, while file-based mode opens files but defers data loading.
