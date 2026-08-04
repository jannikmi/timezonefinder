

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
     - 398ms
     - 396ms
     - 6.53ms
     - 391ms
     - 428ms
     - 30
   * - TimezoneFinder, in-memory
     - 418ms
     - 417ms
     - 6.81ms
     - 414ms
     - 453ms
     - 30
   * - TimezoneFinderL, file-based
     - 397ms
     - 394ms
     - 10.3ms
     - 392ms
     - 437ms
     - 30
   * - TimezoneFinderL, in-memory
     - 394ms
     - 394ms
     - 1.52ms
     - 391ms
     - 397ms
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 5% faster (1.05x) than **in-memory** (398ms vs 418ms)

* TimezoneFinderL: **in-memory** and **file-based** perform about the same (394ms vs 397ms, 0.8% difference)

* Overall: fastest is **Initialization - TimezoneFinderL, in-memory** (394ms), slowest is **Initialization - TimezoneFinder, in-memory** (418ms) - 6% faster (1.06x)
