

TimezoneFinder Initialization Performance Benchmark
===================================================


**~389ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~383ms** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

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


**Fixture Version**: 2

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
     - 389ms
     - 389ms
     - 8.86ms
     - 379ms
     - 417ms
     - 30
   * - TimezoneFinder, in-memory
     - 409ms
     - 408ms
     - 6.43ms
     - 402ms
     - 435ms
     - 30
   * - TimezoneFinderL, file-based
     - 383ms
     - 381ms
     - 5.88ms
     - 377ms
     - 394ms
     - 30
   * - TimezoneFinderL, in-memory
     - 381ms
     - 380ms
     - 3.26ms
     - 377ms
     - 391ms
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 5% faster (1.05x) than **in-memory** (389ms vs 409ms)

* TimezoneFinderL: **in-memory** and **file-based** perform about the same (381ms vs 383ms, 0.5% difference)

* Overall: fastest is **Initialization - TimezoneFinderL, in-memory** (381ms), slowest is **Initialization - TimezoneFinder, in-memory** (409ms) - 7% faster (1.07x)
