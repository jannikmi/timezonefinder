

Timezone Finding Performance Benchmark
======================================


**~3.83µs per lookup, ~261k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

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
     - 25.0ms
     - 25.1ms
     - 439µs
     - 23.9ms
     - 25.7ms
     - 41
     - 10.0µs
     - 99.9k/s
   * - on-land points, in-memory
     - 15.3ms
     - 15.2ms
     - 902µs
     - 14.3ms
     - 21.6ms
     - 68
     - 6.11µs
     - 164k/s
   * - random points, in-memory
     - 9.56ms
     - 8.90ms
     - 3.12ms
     - 8.16ms
     - 27.4ms
     - 85
     - 3.83µs
     - 261k/s
   * - unique-shortcut points, in-memory
     - 3.01ms
     - 2.98ms
     - 284µs
     - 2.62ms
     - 3.83ms
     - 282
     - 1.20µs
     - 830k/s




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
     - 16.2ms
     - 16.2ms
     - 430µs
     - 15.2ms
     - 17.0ms
     - 62
     - 6.47µs
     - 154k/s




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
     - 27.0ms
     - 26.9ms
     - 546µs
     - 26.1ms
     - 28.2ms
     - 34
     - 10.8µs
     - 92.7k/s
   * - on-land points, file-based
     - 16.0ms
     - 15.8ms
     - 768µs
     - 15.0ms
     - 20.6ms
     - 54
     - 6.39µs
     - 156k/s
   * - random points, file-based
     - 8.97ms
     - 8.81ms
     - 335µs
     - 8.59ms
     - 9.93ms
     - 94
     - 3.59µs
     - 279k/s
   * - unique-shortcut points, file-based
     - 3.04ms
     - 3.00ms
     - 276µs
     - 2.61ms
     - 3.83ms
     - 314
     - 1.22µs
     - 823k/s




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
     - 17.2ms
     - 17.3ms
     - 486µs
     - 16.2ms
     - 17.9ms
     - 50
     - 6.87µs
     - 146k/s




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
     - 3.39ms
     - 3.38ms
     - 303µs
     - 2.93ms
     - 4.13ms
     - 303
     - 1.36µs
     - 737k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **file-based** is 7% faster (1.07x) than **in-memory** (8.97ms vs 9.56ms)

* On-land points: **in-memory** is 5% faster (1.05x) than **file-based** (15.3ms vs 16.0ms)

* Unique-shortcut points: **in-memory** and **file-based** perform about the same (3.01ms vs 3.04ms, 0.9% difference)

* Ambiguous-shortcut points: **in-memory** is 8% faster (1.08x) than **file-based** (25.0ms vs 27.0ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 6% faster (1.06x) than **file-based** (16.2ms vs 17.2ms)

* Ambiguous-shortcut points are 8.3x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, in-memory** (3.01ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (27.0ms) - 795% faster (8.95x)
