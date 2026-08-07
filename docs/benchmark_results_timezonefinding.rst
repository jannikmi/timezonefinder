

Timezone Finding Performance Benchmark
======================================


**~3.50µs per lookup, ~286k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

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
     - 24.6ms
     - 24.8ms
     - 702µs
     - 22.9ms
     - 25.6ms
     - 42
     - 9.84µs
     - 102k/s
   * - on-land points, in-memory
     - 14.8ms
     - 15.0ms
     - 491µs
     - 13.6ms
     - 15.5ms
     - 68
     - 5.93µs
     - 169k/s
   * - random points, in-memory
     - 8.74ms
     - 8.87ms
     - 408µs
     - 7.94ms
     - 9.39ms
     - 88
     - 3.50µs
     - 286k/s
   * - unique-shortcut points, in-memory
     - 2.80ms
     - 2.69ms
     - 230µs
     - 2.62ms
     - 3.58ms
     - 330
     - 1.12µs
     - 894k/s




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
     - 16.1ms
     - 586µs
     - 14.7ms
     - 16.9ms
     - 60
     - 6.37µs
     - 157k/s




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
     - 37.0ms
     - 37.2ms
     - 522µs
     - 36.0ms
     - 37.9ms
     - 26
     - 14.8µs
     - 67.5k/s
   * - on-land points, file-based
     - 20.4ms
     - 20.7ms
     - 651µs
     - 19.0ms
     - 21.6ms
     - 45
     - 8.16µs
     - 123k/s
   * - random points, file-based
     - 11.7ms
     - 11.9ms
     - 487µs
     - 10.7ms
     - 12.4ms
     - 75
     - 4.68µs
     - 214k/s
   * - unique-shortcut points, file-based
     - 2.74ms
     - 2.69ms
     - 166µs
     - 2.61ms
     - 3.59ms
     - 317
     - 1.10µs
     - 911k/s




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
     - 21.8ms
     - 21.9ms
     - 338µs
     - 20.9ms
     - 22.3ms
     - 43
     - 8.73µs
     - 115k/s




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
     - 3.31ms
     - 3.17ms
     - 328µs
     - 2.94ms
     - 4.41ms
     - 250
     - 1.32µs
     - 756k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 34% faster (1.34x) than **file-based** (8.74ms vs 11.7ms)

* On-land points: **in-memory** is 38% faster (1.38x) than **file-based** (14.8ms vs 20.4ms)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.74ms vs 2.80ms, 2.0% difference)

* Ambiguous-shortcut points: **in-memory** is 51% faster (1.51x) than **file-based** (24.6ms vs 37.0ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 37% faster (1.37x) than **file-based** (15.9ms vs 21.8ms)

* Ambiguous-shortcut points are 8.8x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, file-based** (2.74ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (37.0ms) - 1250% faster (13.5x)
