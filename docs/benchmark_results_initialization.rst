

TimezoneFinder Initialization Performance Benchmark
===================================================


**~8.74ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~459µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

*Measured on Darwin arm64, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.



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


**C Implementation Available**: True

**Numba JIT Available**: False



Performance Optimizations
~~~~~~~~~~~~~~~~~~~~~~~~~


* ✓ Compiled C extension for point-in-polygon operations

* ✗ Numba JIT compilation not available



Benchmark Input Provenance
~~~~~~~~~~~~~~~~~~~~~~~~~~


**Fixture Version**: 3

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
     - 8.74ms
     - 8.48ms
     - 1.22ms
     - 8.03ms
     - 13.7ms
     - 30
   * - TimezoneFinder, in-memory
     - 12.7ms
     - 12.6ms
     - 697µs
     - 12.0ms
     - 16.1ms
     - 30
   * - TimezoneFinderL, file-based
     - 459µs
     - 445µs
     - 35.4µs
     - 439µs
     - 585µs
     - 30
   * - TimezoneFinderL, in-memory
     - 472µs
     - 453µs
     - 48.4µs
     - 441µs
     - 624µs
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 45% faster (1.45x) than **in-memory** (8.74ms vs 12.7ms)

* TimezoneFinderL: **file-based** is 3% faster (1.03x) than **in-memory** (459µs vs 472µs)

* Overall: fastest is **Initialization - TimezoneFinderL, file-based** (459µs), slowest is **Initialization - TimezoneFinder, in-memory** (12.7ms) - 2654% faster (27.5x)
