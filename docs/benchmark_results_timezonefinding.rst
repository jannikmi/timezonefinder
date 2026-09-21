

Timezone Finding Performance Benchmark
======================================


**~1.81µs per lookup, ~552k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 2.8720 GHz, Python 3.13.15, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration records the ``min`` estimator for these rows: ``TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory``, ``TimezoneFinder.timezone_at() - random points, in-memory``, ``TimezoneFinder.timezone_at() - unique-shortcut points, in-memory``, ``TimezoneFinder.timezone_ids_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_ids_at() - random points, file-based``, ``TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - random points, file-based``, ``TimezoneFinder.timezone_names_at() - unique-shortcut points, file-based``. This published table leads with ``Mean`` and includes the full suite, so its values answer a different question from the trend chart.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.15 (CPython)

**NumPy Version**: 2.5.2

**Platform**: Linux x86_64

**Processor**: x86_64



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

**Timezone Data Version**: 2026d



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
     - 12.6ms
     - 12.6ms
     - 95.3µs
     - 12.5ms
     - 12.8ms
     - 15
     - 5.04µs
     - 198k/s
   * - on-land points, in-memory
     - 5.60ms
     - 5.58ms
     - 78.4µs
     - 5.53ms
     - 5.85ms
     - 15
     - 2.24µs
     - 447k/s
   * - random points, in-memory
     - 4.53ms
     - 4.52ms
     - 35.6µs
     - 4.50ms
     - 4.62ms
     - 15
     - 1.81µs
     - 552k/s
   * - unique-shortcut points, in-memory
     - 3.52ms
     - 3.51ms
     - 32.0µs
     - 3.48ms
     - 3.60ms
     - 15
     - 1.41µs
     - 711k/s




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
     - 6.09ms
     - 6.07ms
     - 44.6µs
     - 6.00ms
     - 6.17ms
     - 15
     - 2.44µs
     - 411k/s




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
     - 61.4µs
     - 12.6ms
     - 12.8ms
     - 15
     - 5.07µs
     - 197k/s
   * - on-land points, file-based
     - 5.64ms
     - 5.63ms
     - 36.8µs
     - 5.61ms
     - 5.76ms
     - 15
     - 2.26µs
     - 443k/s
   * - random points, file-based
     - 4.55ms
     - 4.54ms
     - 29.5µs
     - 4.51ms
     - 4.62ms
     - 15
     - 1.82µs
     - 549k/s
   * - unique-shortcut points, file-based
     - 3.52ms
     - 3.51ms
     - 46.5µs
     - 3.48ms
     - 3.67ms
     - 15
     - 1.41µs
     - 710k/s




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
     - 6.06ms
     - 6.04ms
     - 38.3µs
     - 6.01ms
     - 6.15ms
     - 15
     - 2.42µs
     - 413k/s




TimezoneFinder.timezone_ids_at()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



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
     - 10.4ms
     - 10.4ms
     - 65.8µs
     - 10.3ms
     - 10.6ms
     - 15
     - 4.16µs
     - 240k/s
   * - random points, file-based
     - 2.78ms
     - 2.76ms
     - 46.8µs
     - 2.73ms
     - 2.89ms
     - 15
     - 1.11µs
     - 900k/s
   * - unique-shortcut points, file-based
     - 1.77ms
     - 1.76ms
     - 37.5µs
     - 1.72ms
     - 1.86ms
     - 15
     - 708ns
     - 1.41M/s




TimezoneFinder.timezone_names_at()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



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
     - 10.5ms
     - 10.4ms
     - 110µs
     - 10.4ms
     - 10.7ms
     - 15
     - 4.19µs
     - 239k/s
   * - random points, file-based
     - 2.83ms
     - 2.82ms
     - 44.3µs
     - 2.77ms
     - 2.91ms
     - 15
     - 1.13µs
     - 882k/s
   * - unique-shortcut points, file-based
     - 1.80ms
     - 1.79ms
     - 32.5µs
     - 1.75ms
     - 1.87ms
     - 15
     - 718ns
     - 1.39M/s




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
     - 5.69ms
     - 5.65ms
     - 128µs
     - 5.59ms
     - 6.06ms
     - 15
     - 2.28µs
     - 439k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **in-memory** and **file-based** perform about the same (4.53ms vs 4.55ms, 0.4% difference)

* On-land points: **in-memory** and **file-based** perform about the same (5.60ms vs 5.64ms, 0.8% difference)

* Unique-shortcut points: **in-memory** and **file-based** perform about the same (3.52ms vs 3.52ms, 0.2% difference)

* Ambiguous-shortcut points: **in-memory** and **file-based** perform about the same (12.6ms vs 12.7ms, 0.6% difference)

* TimezoneFinder.timezone_at_land(): **file-based** and **in-memory** perform about the same (6.06ms vs 6.09ms, 0.5% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 64% faster (1.64x) than **TimezoneFinder.timezone_at()** (2.78ms vs 4.55ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 61% faster (1.61x) than **TimezoneFinder.timezone_at()** (2.83ms vs 4.55ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 99% faster (1.99x) than **TimezoneFinder.timezone_at()** (1.77ms vs 3.52ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 96% faster (1.96x) than **TimezoneFinder.timezone_at()** (1.80ms vs 3.52ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 22% faster (1.22x) than **TimezoneFinder.timezone_at()** (10.4ms vs 12.7ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 21% faster (1.21x) than **TimezoneFinder.timezone_at()** (10.5ms vs 12.7ms)

* Ambiguous-shortcut points are 3.6x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the H3 index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (1.77ms), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, file-based** (12.7ms) - 616% faster (7.16x)



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
     - 1.50µs
     - 3.36µs
     - 6.57µs
     - 9.67µs
     - 1.89µs
     - 11.4µs
   * - on-land points
     - 1.49µs
     - 5.57µs
     - 7.00µs
     - 9.81µs
     - 2.26µs
     - 15.7µs
   * - unique-shortcut points
     - 1.46µs
     - 1.53µs
     - 1.59µs
     - 1.66µs
     - 1.46µs
     - 1.74µs
   * - ambiguous-shortcut points
     - 5.40µs
     - 6.33µs
     - 8.83µs
     - 14.7µs
     - 5.07µs
     - 25.4µs
