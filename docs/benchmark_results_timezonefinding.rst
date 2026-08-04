

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
     - 27.8ms
     - 27.7ms
     - 674µs
     - 26.6ms
     - 29.2ms
     - 38
     - 11.1µs
     - 89.8k/s
   * - on-land points, in-memory
     - 17.1ms
     - 17.2ms
     - 446µs
     - 16.1ms
     - 17.9ms
     - 60
     - 6.83µs
     - 146k/s
   * - random points, in-memory
     - 9.78ms
     - 9.74ms
     - 371µs
     - 9.15ms
     - 10.4ms
     - 16
     - 3.91µs
     - 256k/s
   * - unique-shortcut points, in-memory
     - 3.06ms
     - 3.04ms
     - 324µs
     - 2.61ms
     - 3.80ms
     - 286
     - 1.22µs
     - 818k/s




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
     - 18.2ms
     - 18.2ms
     - 409µs
     - 17.4ms
     - 19.0ms
     - 54
     - 7.28µs
     - 137k/s




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
     - 40.2ms
     - 40.3ms
     - 493µs
     - 39.1ms
     - 41.4ms
     - 24
     - 16.1µs
     - 62.1k/s
   * - on-land points, file-based
     - 22.7ms
     - 22.8ms
     - 541µs
     - 21.6ms
     - 23.5ms
     - 40
     - 9.08µs
     - 110k/s
   * - random points, file-based
     - 13.0ms
     - 13.0ms
     - 464µs
     - 11.9ms
     - 13.7ms
     - 65
     - 5.19µs
     - 193k/s
   * - unique-shortcut points, file-based
     - 3.08ms
     - 3.06ms
     - 320µs
     - 2.61ms
     - 3.94ms
     - 283
     - 1.23µs
     - 812k/s




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
     - 25.0ms
     - 24.1ms
     - 6.13ms
     - 23.0ms
     - 61.2ms
     - 37
     - 10.0µs
     - 99.9k/s




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
     - 3.65ms
     - 3.58ms
     - 525µs
     - 2.96ms
     - 6.68ms
     - 223
     - 1.46µs
     - 685k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 33% faster (1.33x) than **file-based** (9.78ms vs 13.0ms)

* On-land points: **in-memory** is 33% faster (1.33x) than **file-based** (17.1ms vs 22.7ms)

* Unique-shortcut points: **in-memory** and **file-based** perform about the same (3.06ms vs 3.08ms, 0.8% difference)

* Ambiguous-shortcut points: **in-memory** is 45% faster (1.45x) than **file-based** (27.8ms vs 40.2ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 38% faster (1.38x) than **file-based** (18.2ms vs 25.0ms)

* Ambiguous-shortcut points are 9.1x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, in-memory** (3.06ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (40.2ms) - 1216% faster (13.2x)
