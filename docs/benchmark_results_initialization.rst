

TimezoneFinder Initialization Performance Benchmark
===================================================




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


**Test Runs Per Configuration**: 50

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
     - 444.2
     - 0.444
   * - TimezoneFinder (In-Memory)
     - 460.9
     - 0.461
   * - TimezoneFinderL (File-Based)
     - 442.6
     - 0.443
   * - TimezoneFinderL (In-Memory)
     - 443.8
     - 0.444




Performance Analysis
--------------------


* **Fastest configuration**: TimezoneFinderL (File-Based) (442.6 ms)

* **Slowest configuration**: TimezoneFinder (In-Memory) (460.9 ms)

* **Performance difference**: 1.0x speedup


* **File-based mode** is 1.0x faster on average (443.4 ms vs 452.4 ms)

.. note::

   Initialization times may vary based on system I/O performance, available memory, and background system activity. In-memory mode loads all data into RAM during initialization, while file-based mode opens files but defers data loading.
