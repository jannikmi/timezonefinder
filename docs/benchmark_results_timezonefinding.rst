

Timezone Finding Performance Benchmark
======================================


**~1.90µs per lookup, ~527k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

*Measured on Darwin arm64, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.



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


**C Implementation Available**: True

**Numba JIT Available**: False



Performance Optimizations
~~~~~~~~~~~~~~~~~~~~~~~~~


* ✓ Compiled C extension for point-in-polygon operations

* ✗ Numba JIT compilation not available



Benchmark Input Provenance
~~~~~~~~~~~~~~~~~~~~~~~~~~


**Fixture Version**: 3

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
     - 26.8ms
     - 26.8ms
     - 492µs
     - 25.7ms
     - 27.8ms
     - 37
     - 10.7µs
     - 93.4k/s
   * - on-land points, in-memory
     - 8.87ms
     - 8.84ms
     - 326µs
     - 8.24ms
     - 9.59ms
     - 118
     - 3.55µs
     - 282k/s
   * - random points, in-memory
     - 4.75ms
     - 4.68ms
     - 273µs
     - 4.32ms
     - 5.38ms
     - 200
     - 1.90µs
     - 527k/s
   * - unique-shortcut points, in-memory
     - 2.19ms
     - 2.17ms
     - 94.1µs
     - 2.08ms
     - 2.68ms
     - 413
     - 878ns
     - 1.14M/s




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
     - 9.55ms
     - 9.46ms
     - 343µs
     - 9.01ms
     - 10.6ms
     - 106
     - 3.82µs
     - 262k/s




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
     - 28.9ms
     - 28.9ms
     - 557µs
     - 27.8ms
     - 29.8ms
     - 34
     - 11.5µs
     - 86.6k/s
   * - on-land points, file-based
     - 9.26ms
     - 9.17ms
     - 377µs
     - 8.64ms
     - 10.3ms
     - 98
     - 3.70µs
     - 270k/s
   * - random points, file-based
     - 4.94ms
     - 4.85ms
     - 285µs
     - 4.52ms
     - 5.68ms
     - 180
     - 1.98µs
     - 506k/s
   * - unique-shortcut points, file-based
     - 2.19ms
     - 2.17ms
     - 89.0µs
     - 2.08ms
     - 2.53ms
     - 454
     - 877ns
     - 1.14M/s




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
     - 10.2ms
     - 10.1ms
     - 423µs
     - 9.42ms
     - 11.1ms
     - 89
     - 4.06µs
     - 246k/s




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
     - 3.33ms
     - 3.25ms
     - 225µs
     - 3.10ms
     - 4.16ms
     - 298
     - 1.33µs
     - 750k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 4% faster (1.04x) than **file-based** (4.75ms vs 4.94ms)

* On-land points: **in-memory** is 4% faster (1.04x) than **file-based** (8.87ms vs 9.26ms)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.19ms vs 2.19ms, 0.1% difference)

* Ambiguous-shortcut points: **in-memory** is 8% faster (1.08x) than **file-based** (26.8ms vs 28.9ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 6% faster (1.06x) than **file-based** (9.55ms vs 10.2ms)

* Ambiguous-shortcut points are 12.2x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, file-based** (2.19ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (28.9ms) - 1216% faster (13.2x)
