

Timezone Finding Performance Benchmark
======================================


**~3.40µs per lookup, ~294k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

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

**Batch Size**: 2,500

Each benchmark times one pass over 2,500 fixed, committed query points (see benchmarks/conftest.py). Mean/Median/StdDev/Min/Max below are for the full 2,500-query batch; Time/Query and Throughput divide and scale that out to a per-query figure.



In-Memory Mode
~~~~~~~~~~~~~~




TimezoneFinder.timezone_at()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 36 7 7 7 7 7 7 11 11

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query
     - Throughput
   * - ambiguous-shortcut points, in-memory
     - 24.9ms
     - 24.9ms
     - 381µs
     - 24.0ms
     - 25.7ms
     - 40
     - 9.96µs
     - 100k/s
   * - on-land points, in-memory
     - 14.6ms
     - 14.6ms
     - 333µs
     - 14.0ms
     - 15.3ms
     - 68
     - 5.85µs
     - 171k/s
   * - random points, in-memory
     - 8.51ms
     - 8.43ms
     - 314µs
     - 7.86ms
     - 9.47ms
     - 105
     - 3.40µs
     - 294k/s
   * - unique-shortcut points, in-memory
     - 2.75ms
     - 2.74ms
     - 97.1µs
     - 2.59ms
     - 3.01ms
     - 344
     - 1.10µs
     - 909k/s




TimezoneFinder.timezone_at_land()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 18 9 9 9 9 9 9 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query
     - Throughput
   * - in-memory
     - 15.9ms
     - 15.9ms
     - 337µs
     - 14.8ms
     - 16.5ms
     - 63
     - 6.34µs
     - 158k/s




File-Based Mode
~~~~~~~~~~~~~~~




TimezoneFinder.timezone_at()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 42 6 6 6 6 6 6 11 11

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query
     - Throughput
   * - ambiguous-shortcut points, file-based
     - 26.7ms
     - 26.7ms
     - 326µs
     - 25.7ms
     - 27.2ms
     - 35
     - 10.7µs
     - 93.8k/s
   * - on-land points, file-based
     - 15.5ms
     - 15.5ms
     - 315µs
     - 14.7ms
     - 16.1ms
     - 57
     - 6.18µs
     - 162k/s
   * - random points, file-based
     - 8.89ms
     - 8.83ms
     - 357µs
     - 8.21ms
     - 9.74ms
     - 90
     - 3.56µs
     - 281k/s
   * - unique-shortcut points, file-based
     - 2.75ms
     - 2.75ms
     - 103µs
     - 2.58ms
     - 3.08ms
     - 346
     - 1.10µs
     - 909k/s




TimezoneFinder.timezone_at_land()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 18 9 9 9 9 9 9 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query
     - Throughput
   * - file-based
     - 16.6ms
     - 16.6ms
     - 378µs
     - 15.6ms
     - 17.3ms
     - 53
     - 6.63µs
     - 151k/s




TimezoneFinderL (heuristic-only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. note::

   TimezoneFinderL does not support in-memory mode; shortcuts are always loaded from disk.



TimezoneFinderL.timezone_at() (ambiguous-shortcut points)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 18 9 9 9 9 9 9 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query
     - Throughput
   * - -
     - 3.84ms
     - 3.85ms
     - 109µs
     - 3.64ms
     - 4.13ms
     - 251
     - 1.54µs
     - 651k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 5% faster (1.05x) than **file-based** (8.51ms vs 8.89ms)

* On-land points: **in-memory** is 6% faster (1.06x) than **file-based** (14.6ms vs 15.5ms)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.75ms vs 2.75ms, 0.1% difference)

* Ambiguous-shortcut points: **in-memory** is 7% faster (1.07x) than **file-based** (24.9ms vs 26.7ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 5% faster (1.05x) than **file-based** (15.9ms vs 16.6ms)

* Ambiguous-shortcut points are 9.1x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, file-based** (2.75ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (26.7ms) - 869% faster (9.69x)
