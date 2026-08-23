

TimezoneFinder Initialization Performance Benchmark
===================================================


**~7.98ms** to construct a ``TimezoneFinder`` in the default file-based mode, **~211µs** for ``TimezoneFinderL``. This is paid once per process - build one instance and reuse it rather than constructing per lookup.

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
     - 7.98ms
     - 7.75ms
     - 937µs
     - 7.43ms
     - 12.7ms
     - 30
   * - TimezoneFinder, in-memory
     - 11.9ms
     - 12.1ms
     - 792µs
     - 10.1ms
     - 13.6ms
     - 30
   * - TimezoneFinderL, file-based
     - 211µs
     - 198µs
     - 37.5µs
     - 193µs
     - 379µs
     - 30
   * - TimezoneFinderL, in-memory
     - 212µs
     - 201µs
     - 31.2µs
     - 194µs
     - 351µs
     - 30




Performance Summary
~~~~~~~~~~~~~~~~~~~


* TimezoneFinder: **file-based** is 50% faster (1.50x) than **in-memory** (7.98ms vs 11.9ms)

* TimezoneFinderL: **file-based** and **in-memory** perform about the same (211µs vs 212µs, 0.3% difference)

* Overall: fastest is **Initialization - TimezoneFinderL, file-based** (211µs), slowest is **Initialization - TimezoneFinder, in-memory** (11.9ms) - 5546% faster (56.5x)
