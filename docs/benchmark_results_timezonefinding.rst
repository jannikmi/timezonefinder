

Timezone Finding Performance Benchmark
======================================




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
     - 28.1ms
     - 27.9ms
     - 1.21ms
     - 26.4ms
     - 31.4ms
     - 37
     - 11.3µs
     - 88.8k/s
   * - on-land points, in-memory
     - 16.6ms
     - 16.7ms
     - 360µs
     - 15.8ms
     - 17.4ms
     - 62
     - 6.66µs
     - 150k/s
   * - random points, in-memory
     - 9.57ms
     - 9.58ms
     - 316µs
     - 8.87ms
     - 10.2ms
     - 74
     - 3.83µs
     - 261k/s
   * - unique-shortcut points, in-memory
     - 3.02ms
     - 3.00ms
     - 236µs
     - 2.65ms
     - 3.85ms
     - 318
     - 1.21µs
     - 828k/s




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
     - 17.8ms
     - 17.9ms
     - 361µs
     - 17.1ms
     - 18.8ms
     - 58
     - 7.14µs
     - 140k/s




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
     - 39.6ms
     - 39.6ms
     - 473µs
     - 38.5ms
     - 40.4ms
     - 23
     - 15.8µs
     - 63.2k/s
   * - on-land points, file-based
     - 22.2ms
     - 22.3ms
     - 491µs
     - 20.9ms
     - 23.0ms
     - 39
     - 8.89µs
     - 113k/s
   * - random points, file-based
     - 12.7ms
     - 12.7ms
     - 397µs
     - 11.8ms
     - 13.4ms
     - 67
     - 5.07µs
     - 197k/s
   * - unique-shortcut points, file-based
     - 3.07ms
     - 3.04ms
     - 292µs
     - 2.62ms
     - 3.93ms
     - 331
     - 1.23µs
     - 815k/s




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
     - 23.5ms
     - 23.4ms
     - 523µs
     - 22.4ms
     - 24.6ms
     - 38
     - 9.38µs
     - 107k/s




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
     - 3.75ms
     - 3.72ms
     - 521µs
     - 2.94ms
     - 7.66ms
     - 226
     - 1.50µs
     - 666k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 33% faster (1.33x) than **file-based** (9.57ms vs 12.7ms)

* On-land points: **in-memory** is 34% faster (1.34x) than **file-based** (16.6ms vs 22.2ms)

* Unique-shortcut points: **in-memory** and **file-based** perform about the same (3.02ms vs 3.07ms, 1.6% difference)

* Ambiguous-shortcut points: **in-memory** is 41% faster (1.41x) than **file-based** (28.1ms vs 39.6ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 31% faster (1.31x) than **file-based** (17.8ms vs 23.5ms)

* Ambiguous-shortcut points are 9.3x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, in-memory** (3.02ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (39.6ms) - 1211% faster (13.1x)
