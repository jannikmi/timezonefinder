

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



Benchmark Input Provenance
~~~~~~~~~~~~~~~~~~~~~~~~~~


**Fixture Version**: 2

**Timezone Data Version**: 2026c



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
     - 397ms
     - 2.61ms
     - 394ms
     - 407ms
     - 30
   * - TimezoneFinder, in-memory
     - 433ms
     - 419ms
     - 35.2ms
     - 414ms
     - 552ms
     - 30
   * - TimezoneFinderL, file-based
     - 397ms
     - 396ms
     - 7.21ms
     - 393ms
     - 435ms
     - 30
   * - TimezoneFinderL, in-memory
     - 397ms
     - 396ms
     - 7.46ms
     - 390ms
     - 433ms
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 9% faster (1.09x) than **in-memory** (398ms vs 433ms)

* TimezoneFinderL: **in-memory** and **file-based** perform about the same (397ms vs 397ms, 0.1% difference)

* Overall: fastest is **Initialization - TimezoneFinderL, in-memory** (397ms), slowest is **Initialization - TimezoneFinder, in-memory** (433ms) - 9% faster (1.09x)
