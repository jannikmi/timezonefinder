

Timezone Finding Performance Benchmark
======================================


**~2.02µs per lookup, ~496k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

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
     - 26.3ms
     - 26.3ms
     - 321µs
     - 25.6ms
     - 26.9ms
     - 38
     - 10.5µs
     - 94.9k/s
   * - on-land points, in-memory
     - 9.03ms
     - 9.00ms
     - 206µs
     - 8.40ms
     - 9.52ms
     - 109
     - 3.61µs
     - 277k/s
   * - random points, in-memory
     - 5.04ms
     - 5.07ms
     - 180µs
     - 4.67ms
     - 5.53ms
     - 183
     - 2.02µs
     - 496k/s
   * - unique-shortcut points, in-memory
     - 2.65ms
     - 2.64ms
     - 90.9µs
     - 2.51ms
     - 3.07ms
     - 363
     - 1.06µs
     - 943k/s




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
     - 10.1ms
     - 10.1ms
     - 227µs
     - 9.64ms
     - 10.6ms
     - 99
     - 4.05µs
     - 247k/s




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
     - 28.1ms
     - 28.1ms
     - 338µs
     - 27.4ms
     - 28.8ms
     - 33
     - 11.2µs
     - 89.0k/s
   * - on-land points, file-based
     - 9.43ms
     - 9.38ms
     - 209µs
     - 8.84ms
     - 9.98ms
     - 90
     - 3.77µs
     - 265k/s
   * - random points, file-based
     - 5.21ms
     - 5.21ms
     - 187µs
     - 4.84ms
     - 5.73ms
     - 158
     - 2.08µs
     - 480k/s
   * - unique-shortcut points, file-based
     - 2.64ms
     - 2.63ms
     - 95.1µs
     - 2.51ms
     - 3.26ms
     - 337
     - 1.06µs
     - 946k/s




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
     - 10.5ms
     - 10.5ms
     - 228µs
     - 9.94ms
     - 11.1ms
     - 82
     - 4.21µs
     - 238k/s




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
     - 3.74ms
     - 3.75ms
     - 104µs
     - 3.57ms
     - 4.09ms
     - 254
     - 1.50µs
     - 669k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 3% faster (1.03x) than **file-based** (5.04ms vs 5.21ms)

* On-land points: **in-memory** is 4% faster (1.04x) than **file-based** (9.03ms vs 9.43ms)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.64ms vs 2.65ms, 0.4% difference)

* Ambiguous-shortcut points: **in-memory** is 7% faster (1.07x) than **file-based** (26.3ms vs 28.1ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 4% faster (1.04x) than **file-based** (10.1ms vs 10.5ms)

* Ambiguous-shortcut points are 9.9x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, file-based** (2.64ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (28.1ms) - 964% faster (10.6x)
