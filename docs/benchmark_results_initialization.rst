

TimezoneFinder Initialization Performance Benchmark
===================================================




System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.14.2 (CPython)

**NumPy Version**: 2.4.4

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
     - 212.2
     - 0.212
   * - TimezoneFinder (In-Memory)
     - 218.9
     - 0.219
   * - TimezoneFinderL (File-Based)
     - 206.6
     - 0.207
   * - TimezoneFinderL (In-Memory)
     - 209.5
     - 0.209




Performance Analysis
--------------------


* **Fastest configuration**: TimezoneFinderL (File-Based) (206.6 ms)

* **Slowest configuration**: TimezoneFinder (In-Memory) (218.9 ms)

* **Performance difference**: 6% faster


* **File-based mode** is 2% faster (209.4 ms vs 214.2 ms)

.. note::

   Initialization times may vary based on system I/O performance, available memory, and background system activity. In-memory mode loads all data into RAM during initialization, while file-based mode opens files but defers data loading.
