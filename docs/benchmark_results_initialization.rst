

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


**Benchmark Source**: pytest-benchmark

Each round constructs one fresh instance (cold construction); `benchmark.pedantic(..., warmup_rounds=0)` disables pytest-benchmark's usual calibration warmup so it cannot touch the on-disk data ahead of the measured rounds (see benchmarks/test_initialization.py).



Results
~~~~~~~




Initialization
^^^^^^^^^^^^^^



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
   * - TimezoneFinder, file-based
     - 3.77e-01s
     - 3.76e-01s
     - 8.02e-03s
     - 3.72e-01s
     - 4.17e-01s
     - 30
   * - TimezoneFinder, in-memory
     - 3.96e-01s
     - 3.96e-01s
     - 2.96e-03s
     - 3.93e-01s
     - 4.09e-01s
     - 30
   * - TimezoneFinderL, file-based
     - 3.73e-01s
     - 3.73e-01s
     - 1.38e-03s
     - 3.72e-01s
     - 3.78e-01s
     - 30
   * - TimezoneFinderL, in-memory
     - 3.74e-01s
     - 3.73e-01s
     - 1.68e-03s
     - 3.71e-01s
     - 3.77e-01s
     - 30




Performance Analysis
~~~~~~~~~~~~~~~~~~~~


* **Fastest configuration**: Initialization - TimezoneFinderL, file-based

* **Slowest configuration**: Initialization - TimezoneFinder, in-memory
