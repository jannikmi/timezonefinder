

TimezoneFinder Initialization Performance Benchmark
===================================================


**~14.1ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~287µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 3.9326 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration tracks none of the rows on this page. This published table leads with ``Mean`` and belongs to the full on-demand suite, while the trend chart records the ``min`` estimator for the smaller ``benchmark_core`` subset.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.16 (CPython)

**NumPy Version**: 2.5.2

**Platform**: Linux x86_64

**Processor**: x86_64



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


**Fixture Version**: 5

**Timezone Data Version**: 2026e



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
     - 14.1ms
     - 14.1ms
     - 303µs
     - 13.6ms
     - 15.1ms
     - 30
   * - TimezoneFinder, in-memory
     - 6.54ms
     - 5.53ms
     - 3.60ms
     - 5.35ms
     - 21.9ms
     - 30
   * - TimezoneFinderL
     - 287µs
     - 279µs
     - 19.4µs
     - 267µs
     - 357µs
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **in-memory** is 116% faster (2.16x) than **file-based** (6.54ms vs 14.1ms)

* Overall: fastest is **Initialization - TimezoneFinderL** (287µs), slowest is **Initialization - TimezoneFinder, file-based** (14.1ms) - 4823% faster (49.2x)
