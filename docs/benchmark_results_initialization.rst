

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
   :widths: 40 10 10 10 10 10 10

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
   * - TimezoneFinder, file-based
     - 377ms
     - 376ms
     - 8.02ms
     - 372ms
     - 417ms
     - 30
   * - TimezoneFinder, in-memory
     - 396ms
     - 396ms
     - 2.96ms
     - 393ms
     - 409ms
     - 30
   * - TimezoneFinderL, file-based
     - 373ms
     - 373ms
     - 1.38ms
     - 372ms
     - 378ms
     - 30
   * - TimezoneFinderL, in-memory
     - 374ms
     - 373ms
     - 1.68ms
     - 371ms
     - 377ms
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 5% faster (1.05x) than **in-memory** (377ms vs 396ms)

* TimezoneFinderL: **file-based** and **in-memory** perform about the same (373ms vs 374ms, 0.2% difference)

* Overall: fastest is **Initialization - TimezoneFinderL, file-based** (373ms), slowest is **Initialization - TimezoneFinder, in-memory** (396ms) - 6% faster (1.06x)
