

TimezoneFinder Initialization Performance Benchmark
===================================================


**~8.73ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~452µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

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
     - 8.73ms
     - 8.46ms
     - 1.23ms
     - 7.92ms
     - 13.3ms
     - 30
   * - TimezoneFinder, in-memory
     - 12.7ms
     - 12.6ms
     - 801µs
     - 11.8ms
     - 16.7ms
     - 30
   * - TimezoneFinderL, file-based
     - 452µs
     - 445µs
     - 19.0µs
     - 438µs
     - 527µs
     - 30
   * - TimezoneFinderL, in-memory
     - 458µs
     - 448µs
     - 25.9µs
     - 440µs
     - 538µs
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 45% faster (1.45x) than **in-memory** (8.73ms vs 12.7ms)

* TimezoneFinderL: **file-based** and **in-memory** perform about the same (452µs vs 458µs, 1.4% difference)

* Overall: fastest is **Initialization - TimezoneFinderL, file-based** (452µs), slowest is **Initialization - TimezoneFinder, in-memory** (12.7ms) - 2702% faster (28.0x)
