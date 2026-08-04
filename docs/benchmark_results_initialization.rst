

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
     - 391ms
     - 392ms
     - 3.43ms
     - 384ms
     - 396ms
     - 30
   * - TimezoneFinder, in-memory
     - 410ms
     - 410ms
     - 4.09ms
     - 403ms
     - 426ms
     - 30
   * - TimezoneFinderL, file-based
     - 389ms
     - 388ms
     - 9.14ms
     - 382ms
     - 435ms
     - 30
   * - TimezoneFinderL, in-memory
     - 388ms
     - 388ms
     - 2.94ms
     - 382ms
     - 393ms
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 5% faster (1.05x) than **in-memory** (391ms vs 410ms)

* TimezoneFinderL: **in-memory** and **file-based** perform about the same (388ms vs 389ms, 0.2% difference)

* Overall: fastest is **Initialization - TimezoneFinderL, in-memory** (388ms), slowest is **Initialization - TimezoneFinder, in-memory** (410ms) - 6% faster (1.06x)
