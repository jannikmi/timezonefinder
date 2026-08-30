

Timezone Finding Performance Benchmark
======================================


**~1.63µs per lookup, ~614k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

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
     - 16.2ms
     - 16.3ms
     - 684µs
     - 14.9ms
     - 17.6ms
     - 60
     - 6.49µs
     - 154k/s
   * - on-land points, in-memory
     - 5.58ms
     - 5.40ms
     - 1.49ms
     - 4.69ms
     - 17.2ms
     - 187
     - 2.23µs
     - 448k/s
   * - random points, in-memory
     - 4.07ms
     - 4.05ms
     - 358µs
     - 3.57ms
     - 4.88ms
     - 200
     - 1.63µs
     - 614k/s
   * - unique-shortcut points, in-memory
     - 2.58ms
     - 2.57ms
     - 147µs
     - 2.37ms
     - 3.01ms
     - 373
     - 1.03µs
     - 971k/s




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
     - 6.52ms
     - 6.55ms
     - 458µs
     - 5.71ms
     - 7.81ms
     - 162
     - 2.61µs
     - 383k/s




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
     - 18.0ms
     - 17.9ms
     - 814µs
     - 16.5ms
     - 19.8ms
     - 49
     - 7.21µs
     - 139k/s
   * - on-land points, file-based
     - 5.83ms
     - 5.85ms
     - 425µs
     - 5.14ms
     - 6.84ms
     - 141
     - 2.33µs
     - 429k/s
   * - random points, file-based
     - 4.29ms
     - 4.24ms
     - 364µs
     - 3.75ms
     - 5.18ms
     - 207
     - 1.72µs
     - 582k/s
   * - unique-shortcut points, file-based
     - 2.57ms
     - 2.56ms
     - 155µs
     - 2.37ms
     - 3.17ms
     - 360
     - 1.03µs
     - 972k/s




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
     - 6.86ms
     - 6.86ms
     - 404µs
     - 6.12ms
     - 7.71ms
     - 117
     - 2.74µs
     - 365k/s




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
     - 3.86ms
     - 3.82ms
     - 232µs
     - 3.52ms
     - 4.48ms
     - 272
     - 1.54µs
     - 648k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** is 5% faster (1.05x) than **file-based** (4.07ms vs 4.29ms)

* On-land points: **in-memory** is 4% faster (1.04x) than **file-based** (5.58ms vs 5.83ms)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.57ms vs 2.58ms, 0.1% difference)

* Ambiguous-shortcut points: **in-memory** is 11% faster (1.11x) than **file-based** (16.2ms vs 18.0ms)

* TimezoneFinder.timezone_at_land(): **in-memory** is 5% faster (1.05x) than **file-based** (6.52ms vs 6.86ms)

* Ambiguous-shortcut points are 6.3x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_at() - unique-shortcut points, file-based** (2.57ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (18.0ms) - 601% faster (7.01x)



Per-Query Latency Distribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Every table above times one pass over a whole batch of points, so it says what a workload costs on average. This one times each query on its own, in the default memory-mapped mode, and reports the distribution: the slowest queries in this package cost tens of times the median, because a point falling in a very large boundary polygon is answered by one ray cast across that whole ring. A batch mean cannot show that, which is why both are published (``scripts/measure_query_latency.py``, ``make latency``).

5,000 queries per point class, each keeping its fastest of 3 passes.


.. list-table::
   :header-rows: 1
   :widths: 40 10 10 10 10 10 10

   * - Point class
     - p50
     - p90
     - p99
     - p99.9
     - mean
     - max
   * - random points
     - 1.04µs
     - 2.79µs
     - 10.8µs
     - 17.4µs
     - 1.67µs
     - 34.2µs
   * - on-land points
     - 1.04µs
     - 6.54µs
     - 10.5µs
     - 22.6µs
     - 2.15µs
     - 32.3µs
   * - unique-shortcut points
     - 1.00µs
     - 1.04µs
     - 1.13µs
     - 1.17µs
     - 1.01µs
     - 1.21µs
   * - ambiguous-shortcut points
     - 6.62µs
     - 10.1µs
     - 17.1µs
     - 30.8µs
     - 6.71µs
     - 32.5µs
