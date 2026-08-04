

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
     - 9.34ms
     - 9.30ms
     - 297µs
     - 8.87ms
     - 10.1ms
     - 103
     - 9.34µs
     - 107k/s
   * - on-land points, in-memory
     - 4.90ms
     - 4.89ms
     - 192µs
     - 4.61ms
     - 5.35ms
     - 198
     - 4.90µs
     - 204k/s
   * - random points, in-memory
     - 3.80ms
     - 3.73ms
     - 263µs
     - 3.44ms
     - 4.51ms
     - 119
     - 3.80µs
     - 263k/s
   * - unique-shortcut points, in-memory
     - 1.15ms
     - 1.10ms
     - 123µs
     - 1.03ms
     - 1.60ms
     - 771
     - 1.15µs
     - 867k/s




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
     - 5.48ms
     - 5.46ms
     - 242µs
     - 5.01ms
     - 6.09ms
     - 185
     - 5.48µs
     - 182k/s




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
     - 13.8ms
     - 13.9ms
     - 292µs
     - 13.1ms
     - 14.5ms
     - 62
     - 13.8µs
     - 72.3k/s
   * - on-land points, file-based
     - 6.85ms
     - 6.81ms
     - 302µs
     - 6.33ms
     - 7.62ms
     - 122
     - 6.85µs
     - 146k/s
   * - random points, file-based
     - 5.27ms
     - 5.24ms
     - 264µs
     - 4.86ms
     - 6.15ms
     - 147
     - 5.27µs
     - 190k/s
   * - unique-shortcut points, file-based
     - 1.14ms
     - 1.09ms
     - 123µs
     - 1.03ms
     - 1.66ms
     - 722
     - 1.14µs
     - 874k/s




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
     - 7.26ms
     - 7.24ms
     - 237µs
     - 6.80ms
     - 7.86ms
     - 112
     - 7.26µs
     - 138k/s




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
     - 1.26ms
     - 1.20ms
     - 125µs
     - 1.16ms
     - 1.90ms
     - 640
     - 1.26µs
     - 793k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 39% faster (1.39x) than **file-based** (3.80ms vs 5.27ms)

* On-land points: **in-memory** is 40% faster (1.40x) than **file-based** (4.90ms vs 6.85ms)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (1.14ms vs 1.15ms, 0.8% difference)

* Ambiguous-shortcut points: **in-memory** is 48% faster (1.48x) than **file-based** (9.34ms vs 13.8ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 33% faster (1.33x) than **file-based** (5.48ms vs 7.26ms)

* Ambiguous-shortcut points are 8.1x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, file-based** (1.14ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (13.8ms) - 1109% faster (12.1x)
