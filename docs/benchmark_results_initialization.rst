

TimezoneFinder Initialization Performance Benchmark
===================================================


**~11.4ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~690µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

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
     - 11.4ms
     - 10.0ms
     - 4.58ms
     - 8.63ms
     - 30.9ms
     - 30
   * - TimezoneFinder, in-memory
     - 13.7ms
     - 12.8ms
     - 4.04ms
     - 10.0ms
     - 30.8ms
     - 30
   * - TimezoneFinderL, file-based
     - 690µs
     - 520µs
     - 312µs
     - 464µs
     - 1.54ms
     - 30
   * - TimezoneFinderL, in-memory
     - 653µs
     - 498µs
     - 398µs
     - 450µs
     - 2.36ms
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 20% faster (1.20x) than **in-memory** (11.4ms vs 13.7ms)

* TimezoneFinderL: **in-memory** is 6% faster (1.06x) than **file-based** (653µs vs 690µs)

* Overall: fastest is **Initialization - TimezoneFinderL, in-memory** (653µs), slowest is **Initialization - TimezoneFinder, in-memory** (13.7ms) - 1993% faster (20.9x)
