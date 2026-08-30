

TimezoneFinder Initialization Performance Benchmark
===================================================


**~11.2ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~539µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

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
     - 11.2ms
     - 9.32ms
     - 5.02ms
     - 8.21ms
     - 28.8ms
     - 30
   * - TimezoneFinder, in-memory
     - 13.4ms
     - 13.4ms
     - 783µs
     - 12.1ms
     - 16.9ms
     - 30
   * - TimezoneFinderL, file-based
     - 539µs
     - 515µs
     - 107µs
     - 443µs
     - 882µs
     - 30
   * - TimezoneFinderL, in-memory
     - 521µs
     - 495µs
     - 89.6µs
     - 446µs
     - 846µs
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 19% faster (1.19x) than **in-memory** (11.2ms vs 13.4ms)

* TimezoneFinderL: **in-memory** is 3% faster (1.03x) than **file-based** (521µs vs 539µs)

* Overall: fastest is **Initialization - TimezoneFinderL, in-memory** (521µs), slowest is **Initialization - TimezoneFinder, in-memory** (13.4ms) - 2466% faster (25.7x)
