

Timezone Finding Performance Benchmark
======================================


**~1.33µs per lookup, ~752k/s** - ``TimezoneFinder.timezone_at()`` over uniformly random query points in memory, the workload closest to a real query mix.

This page describes one point-in-polygon implementation. The other two are measured against it in :doc:`benchmark_results_acceleration_paths` - which is where the ranking between them is stated, since it is a measurement that moves and a claim repeated in prose would not.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2287 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration records the ``min`` estimator for these rows: ``TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory``, ``TimezoneFinder.timezone_at() - random points, in-memory``, ``TimezoneFinder.timezone_at() - unique-shortcut points, in-memory``, ``TimezoneFinder.timezone_ids_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_ids_at() - random points, file-based``, ``TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - ambiguous-shortcut points, file-based``, ``TimezoneFinder.timezone_names_at() - random points, file-based``, ``TimezoneFinder.timezone_names_at() - unique-shortcut points, file-based``. This published table leads with ``Mean`` and includes the full suite, so its values answer a different question from the trend chart.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.16 (CPython)

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


**Fixture Version**: 4

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
     - 15.0ms
     - 15.1ms
     - 393µs
     - 14.3ms
     - 15.7ms
     - 15
     - 6.00µs
     - 167k/s
   * - on-land points, in-memory
     - 4.35ms
     - 4.30ms
     - 168µs
     - 4.24ms
     - 4.92ms
     - 15
     - 1.74µs
     - 575k/s
   * - random points, in-memory
     - 3.32ms
     - 3.25ms
     - 148µs
     - 3.22ms
     - 3.74ms
     - 15
     - 1.33µs
     - 752k/s
   * - unique-shortcut points, in-memory
     - 2.68ms
     - 2.65ms
     - 73.8µs
     - 2.63ms
     - 2.92ms
     - 15
     - 1.07µs
     - 934k/s




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
     - 4.68ms
     - 4.68ms
     - 36.2µs
     - 4.62ms
     - 4.75ms
     - 15
     - 1.87µs
     - 534k/s




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
     - 14.5ms
     - 14.3ms
     - 423µs
     - 14.2ms
     - 15.9ms
     - 15
     - 5.79µs
     - 173k/s
   * - on-land points, file-based
     - 4.34ms
     - 4.24ms
     - 176µs
     - 4.16ms
     - 4.68ms
     - 15
     - 1.73µs
     - 577k/s
   * - random points, file-based
     - 3.25ms
     - 3.23ms
     - 38.9µs
     - 3.22ms
     - 3.37ms
     - 15
     - 1.30µs
     - 769k/s
   * - unique-shortcut points, file-based
     - 2.65ms
     - 2.65ms
     - 13.0µs
     - 2.64ms
     - 2.67ms
     - 15
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
   * - file-based
     - 4.71ms
     - 4.71ms
     - 25.4µs
     - 4.67ms
     - 4.77ms
     - 15
     - 1.88µs
     - 531k/s




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
     - 10.6ms
     - 10.5ms
     - 172µs
     - 10.4ms
     - 11.1ms
     - 15
     - 4.22µs
     - 237k/s
   * - random points, file-based
     - 688µs
     - 680µs
     - 28.9µs
     - 659µs
     - 770µs
     - 15
     - 275ns
     - 3.63M/s
   * - unique-shortcut points, file-based
     - 86.5µs
     - 81.9µs
     - 11.0µs
     - 78.6µs
     - 120µs
     - 15
     - 34.6ns
     - 28.9M/s




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
     - 11.1ms
     - 10.9ms
     - 433µs
     - 10.6ms
     - 12.0ms
     - 15
     - 4.44µs
     - 225k/s
   * - random points, file-based
     - 700µs
     - 707µs
     - 16.8µs
     - 669µs
     - 722µs
     - 15
     - 280ns
     - 3.57M/s
   * - unique-shortcut points, file-based
     - 116µs
     - 111µs
     - 12.8µs
     - 109µs
     - 155µs
     - 15
     - 46.5ns
     - 21.5M/s




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
     - 5.66ms
     - 5.64ms
     - 55.1µs
     - 5.59ms
     - 5.81ms
     - 15
     - 2.26µs
     - 442k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**In-memory vs file-based** (``TimezoneFinder.timezone_at()``):

* Random points: **file-based** is 2% faster (1.02x) than **in-memory** (3.25ms vs 3.32ms)

* On-land points: **file-based** and **in-memory** perform about the same (4.34ms vs 4.35ms, 0.3% difference)

* Unique-shortcut points: **file-based** and **in-memory** perform about the same (2.65ms vs 2.68ms, 0.9% difference)

* Ambiguous-shortcut points: **file-based** is 4% faster (1.04x) than **in-memory** (14.5ms vs 15.0ms)

* TimezoneFinder.timezone_at_land(): **in-memory** and **file-based** perform about the same (4.68ms vs 4.71ms, 0.7% difference)

**Scalar vs batch lookups** (file-based):

* Random points, ids: **TimezoneFinder.timezone_ids_at()** is 372% faster (4.72x) than **TimezoneFinder.timezone_at()** (688µs vs 3.25ms)

* Random points, names: **TimezoneFinder.timezone_names_at()** is 364% faster (4.64x) than **TimezoneFinder.timezone_at()** (700µs vs 3.25ms)

* Unique-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 2967% faster (30.7x) than **TimezoneFinder.timezone_at()** (86.5µs vs 2.65ms)

* Unique-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 2180% faster (22.8x) than **TimezoneFinder.timezone_at()** (116µs vs 2.65ms)

* Ambiguous-shortcut points, ids: **TimezoneFinder.timezone_ids_at()** is 37% faster (1.37x) than **TimezoneFinder.timezone_at()** (10.6ms vs 14.5ms)

* Ambiguous-shortcut points, names: **TimezoneFinder.timezone_names_at()** is 31% faster (1.31x) than **TimezoneFinder.timezone_at()** (11.1ms vs 14.5ms)

* Ambiguous-shortcut points are 5.6x slower than unique-shortcut points (in-memory): a unique shortcut resolves directly from the index, while an ambiguous one falls through to the full point-in-polygon check.

* Overall: fastest is **TimezoneFinder.timezone_ids_at() - unique-shortcut points, file-based** (86.5µs), slowest is **TimezoneFinder.timezone_at() - ambiguous-shortcut points, in-memory** (15.0ms) - 17255% faster (174x)



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
     - 1.15µs
     - 1.59µs
     - 7.75µs
     - 12.1µs
     - 1.48µs
     - 18.0µs
   * - on-land points
     - 1.22µs
     - 6.00µs
     - 8.49µs
     - 12.3µs
     - 1.93µs
     - 14.3µs
   * - unique-shortcut points
     - 1.12µs
     - 1.43µs
     - 1.71µs
     - 1.83µs
     - 1.17µs
     - 1.88µs
   * - ambiguous-shortcut points
     - 6.72µs
     - 8.07µs
     - 10.8µs
     - 14.4µs
     - 6.71µs
     - 19.8µs
