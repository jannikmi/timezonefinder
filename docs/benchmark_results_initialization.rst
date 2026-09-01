

TimezoneFinder Initialization Performance Benchmark
===================================================


**~10.1ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~531µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

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
     - 10.1ms
     - 9.90ms
     - 998µs
     - 9.18ms
     - 14.8ms
     - 30
   * - TimezoneFinder, in-memory
     - 7.80ms
     - 7.72ms
     - 935µs
     - 6.40ms
     - 10.8ms
     - 30
   * - TimezoneFinderL, file-based
     - 531µs
     - 520µs
     - 66.5µs
     - 452µs
     - 665µs
     - 30
   * - TimezoneFinderL, in-memory
     - 508µs
     - 470µs
     - 74.5µs
     - 447µs
     - 725µs
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **in-memory** is 30% faster (1.30x) than **file-based** (7.80ms vs 10.1ms)

* TimezoneFinderL: **in-memory** is 4% faster (1.04x) than **file-based** (508µs vs 531µs)

* Overall: fastest is **Initialization - TimezoneFinderL, in-memory** (508µs), slowest is **Initialization - TimezoneFinder, file-based** (10.1ms) - 1892% faster (19.9x)
