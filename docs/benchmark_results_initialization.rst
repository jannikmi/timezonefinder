

TimezoneFinder Initialization Performance Benchmark
===================================================


**~8.78ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~471µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

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
     - 8.78ms
     - 8.11ms
     - 2.35ms
     - 7.69ms
     - 18.7ms
     - 30
   * - TimezoneFinder, in-memory
     - 12.1ms
     - 12.2ms
     - 513µs
     - 10.4ms
     - 12.8ms
     - 30
   * - TimezoneFinderL, file-based
     - 471µs
     - 459µs
     - 48.6µs
     - 424µs
     - 630µs
     - 30
   * - TimezoneFinderL, in-memory
     - 457µs
     - 429µs
     - 54.5µs
     - 421µs
     - 627µs
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 38% faster (1.38x) than **in-memory** (8.78ms vs 12.1ms)

* TimezoneFinderL: **in-memory** is 3% faster (1.03x) than **file-based** (457µs vs 471µs)

* Overall: fastest is **Initialization - TimezoneFinderL, in-memory** (457µs), slowest is **Initialization - TimezoneFinder, in-memory** (12.1ms) - 2557% faster (26.6x)
