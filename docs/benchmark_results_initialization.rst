

TimezoneFinder Initialization Performance Benchmark
===================================================


**~8.67ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~159µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

*Measured on Linux x86_64, AMD EPYC 9V45 96-Core Processor @ 4.2918 GHz, Python 3.13.17, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration tracks none of the rows on this page. This published table leads with ``Mean`` and belongs to the full on-demand suite, while the trend chart records the ``min`` estimator for the smaller ``benchmark_core`` subset.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.17 (CPython)

**NumPy Version**: 2.5.2

**Platform**: Linux x86_64



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

**Timezone Data Version**: 2026f



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
     - 8.67ms
     - 8.63ms
     - 218µs
     - 8.42ms
     - 9.58ms
     - 30
   * - TimezoneFinder, in-memory
     - 4.26ms
     - 3.20ms
     - 3.94ms
     - 3.03ms
     - 21.9ms
     - 30
   * - TimezoneFinderL
     - 159µs
     - 150µs
     - 28.5µs
     - 145µs
     - 293µs
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **in-memory** is 103% faster (2.03x) than **file-based** (4.26ms vs 8.67ms)

* Overall: fastest is **Initialization - TimezoneFinderL** (159µs), slowest is **Initialization - TimezoneFinder, file-based** (8.67ms) - 5342% faster (54.4x)
