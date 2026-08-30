

TimezoneFinder Initialization Performance Benchmark
===================================================


**~9.92ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~529µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

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
     - 9.92ms
     - 9.07ms
     - 2.61ms
     - 7.89ms
     - 17.7ms
     - 30
   * - TimezoneFinder, in-memory
     - 12.9ms
     - 13.0ms
     - 946µs
     - 10.5ms
     - 15.2ms
     - 30
   * - TimezoneFinderL, file-based
     - 529µs
     - 490µs
     - 110µs
     - 454µs
     - 907µs
     - 30
   * - TimezoneFinderL, in-memory
     - 502µs
     - 460µs
     - 99.1µs
     - 442µs
     - 843µs
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 30% faster (1.30x) than **in-memory** (9.92ms vs 12.9ms)

* TimezoneFinderL: **in-memory** is 5% faster (1.05x) than **file-based** (502µs vs 529µs)

* Overall: fastest is **Initialization - TimezoneFinderL, in-memory** (502µs), slowest is **Initialization - TimezoneFinder, in-memory** (12.9ms) - 2475% faster (25.8x)
