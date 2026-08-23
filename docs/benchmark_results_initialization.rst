

TimezoneFinder Initialization Performance Benchmark
===================================================


**~8.28ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~463µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

*Measured on Darwin arm64, Python 3.14.2, using the Numba JIT point-in-polygon path.* Continuous integration tracks a different one - the C extension without Numba, what a plain ``pip install timezonefinder`` gives you - so these figures are not comparable to the trend chart. See :doc:`benchmarking_methodology`.



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


**C Implementation Available**: False

**Numba JIT Available**: True



Performance Optimizations
~~~~~~~~~~~~~~~~~~~~~~~~~


* ✗ Using pure Python point-in-polygon implementation

* ✓ Numba JIT compilation enabled



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
     - 8.28ms
     - 8.14ms
     - 1.06ms
     - 7.51ms
     - 13.7ms
     - 30
   * - TimezoneFinder, in-memory
     - 12.3ms
     - 12.3ms
     - 238µs
     - 11.5ms
     - 12.7ms
     - 30
   * - TimezoneFinderL, file-based
     - 463µs
     - 441µs
     - 48.4µs
     - 431µs
     - 631µs
     - 30
   * - TimezoneFinderL, in-memory
     - 465µs
     - 443µs
     - 50.2µs
     - 433µs
     - 629µs
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 48% faster (1.48x) than **in-memory** (8.28ms vs 12.3ms)

* TimezoneFinderL: **file-based** and **in-memory** perform about the same (463µs vs 465µs, 0.4% difference)

* Overall: fastest is **Initialization - TimezoneFinderL, file-based** (463µs), slowest is **Initialization - TimezoneFinder, in-memory** (12.3ms) - 2555% faster (26.5x)
