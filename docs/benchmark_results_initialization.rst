

TimezoneFinder Initialization Performance Benchmark
===================================================


**~9.86ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~324µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

*Measured on Linux x86_64, Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 2.8000 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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


**Fixture Version**: 4

**Timezone Data Version**: 2026d



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
     - 9.86ms
     - 9.88ms
     - 181µs
     - 9.56ms
     - 10.3ms
     - 30
   * - TimezoneFinder, in-memory
     - 9.61ms
     - 8.77ms
     - 3.87ms
     - 8.33ms
     - 29.6ms
     - 30
   * - TimezoneFinderL
     - 324µs
     - 303µs
     - 75.8µs
     - 290µs
     - 674µs
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **in-memory** is 3% faster (1.03x) than **file-based** (9.61ms vs 9.86ms)

* Overall: fastest is **Initialization - TimezoneFinderL** (324µs), slowest is **Initialization - TimezoneFinder, file-based** (9.86ms) - 2948% faster (30.5x)
