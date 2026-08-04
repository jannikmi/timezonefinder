

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



Benchmark Configuration
~~~~~~~~~~~~~~~~~~~~~~~


**Benchmark Source**: pytest-benchmark

**Batch Size**: 1,000

Each benchmark times one pass over 1,000 fixed, committed query points (see benchmarks/conftest.py). Mean/Median/StdDev/Min/Max below are for the full 1,000-query batch; Time/Query and Throughput divide and scale that out to a per-query figure.



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
     - 8.47ms
     - 8.44ms
     - 96.8µs
     - 8.38ms
     - 8.86ms
     - 114
     - 8.47µs
     - 118k/s
   * - on-land points, in-memory
     - 4.56ms
     - 4.54ms
     - 55.9µs
     - 4.50ms
     - 4.97ms
     - 193
     - 4.56µs
     - 220k/s
   * - random points, in-memory
     - 3.42ms
     - 3.41ms
     - 28.2µs
     - 3.39ms
     - 3.55ms
     - 182
     - 3.42µs
     - 293k/s
   * - unique-shortcut points, in-memory
     - 1.06ms
     - 1.05ms
     - 14.6µs
     - 1.03ms
     - 1.21ms
     - 774
     - 1.06µs
     - 947k/s




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
     - 4.99ms
     - 4.97ms
     - 85.7µs
     - 4.93ms
     - 5.90ms
     - 188
     - 4.99µs
     - 200k/s




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
     - 12.7ms
     - 12.7ms
     - 125µs
     - 12.6ms
     - 13.4ms
     - 68
     - 12.7µs
     - 78.5k/s
   * - on-land points, file-based
     - 6.19ms
     - 6.18ms
     - 43.0µs
     - 6.15ms
     - 6.45ms
     - 128
     - 6.19µs
     - 161k/s
   * - random points, file-based
     - 4.76ms
     - 4.76ms
     - 24.0µs
     - 4.74ms
     - 4.93ms
     - 154
     - 4.76µs
     - 210k/s
   * - unique-shortcut points, file-based
     - 1.05ms
     - 1.05ms
     - 36.3µs
     - 1.03ms
     - 1.64ms
     - 818
     - 1.05µs
     - 948k/s




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
     - 6.69ms
     - 6.67ms
     - 64.9µs
     - 6.63ms
     - 7.27ms
     - 119
     - 6.69µs
     - 150k/s




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
     - 1.18ms
     - 1.17ms
     - 33.9µs
     - 1.15ms
     - 1.59ms
     - 726
     - 1.18µs
     - 850k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 28% faster (1.39x) than **file-based** (3.42ms vs 4.76ms)

* On-land points: **in-memory** is 26% faster (1.36x) than **file-based** (4.56ms vs 6.19ms)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (1.05ms vs 1.06ms, 0.1% difference)

* Ambiguous-shortcut points: **in-memory** is 33% faster (1.50x) than **file-based** (8.47ms vs 12.7ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 25% faster (1.34x) than **file-based** (4.99ms vs 6.69ms)

* Ambiguous-shortcut points are 8.0x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, file-based** (1.05ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (12.7ms) - 92% faster (12.1x)
