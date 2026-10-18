

TimezoneFinder Initialization Performance Benchmark
===================================================


**~14.3ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~364µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2440 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 14.3ms
     - 14.3ms
     - 158µs
     - 14.1ms
     - 14.7ms
     - 30
   * - TimezoneFinder, in-memory
     - 6.18ms
     - 6.03ms
     - 607µs
     - 5.90ms
     - 9.30ms
     - 30
   * - TimezoneFinderL
     - 364µs
     - 357µs
     - 22.0µs
     - 340µs
     - 425µs
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **in-memory** is 132% faster (2.32x) than **file-based** (6.18ms vs 14.3ms)

* Overall: fastest is **Initialization - TimezoneFinderL** (364µs), slowest is **Initialization - TimezoneFinder, file-based** (14.3ms) - 3841% faster (39.4x)
