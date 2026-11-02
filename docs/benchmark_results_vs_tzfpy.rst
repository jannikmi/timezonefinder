

Speed and Startup against tzfpy
===============================


**~621ns per lookup here against ~242ns for tzfpy 1.3.3** - 2.57x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

**For bulk lookups, ``timezone_names_at()`` answers the same 2,500 points in one call at ~118ns per point** - 2.05x faster than a loop of tzfpy calls, which has no batch API. See *Bulk Lookups* below, and :doc:`benchmark_results_batch_break_even` for the batch size from which batching pays.

*Measured on Linux x86_64, AMD EPYC 9V45 96-Core Processor @ 4.2918 GHz, Python 3.13.17, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration tracks none of the rows on this page. This published table leads with ``Mean`` and belongs to the full on-demand suite, while the trend chart records the ``min`` estimator for the smaller ``benchmark_core`` subset.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.17 (CPython)

**NumPy Version**: 2.5.2

**Platform**: Linux x86_64



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


**Fixture Version**: 5

**Timezone Data Version**: 2026f



Benchmark Configuration
~~~~~~~~~~~~~~~~~~~~~~~


**Benchmark Source**: pytest-benchmark

**Batch Size**: 2,500

**Tzfpy Version**: 1.3.3

Both packages answer the **same committed query points** (see benchmarks/conftest.py) in the same process, so the ratios below are a measurement rather than two figures from two machines set side by side. Each is called through its own API - ``timezone_at(lng=, lat=)`` and ``get_tz(lng, lat)`` - with no adapter frame on either side, which at these per-query times would itself be worth tens of percent.

.. note::

   The two packages are not answering quite the same question. This one stores the boundary polygons exactly as the source dataset provides them; tzfpy simplifies them. ``TimezoneFinderL`` is measured alongside as the closest thing in this package to the same bargain - it answers from the shortcut index alone and does not read polygon data at all. A speed ratio between different accuracy classes is a price, not a verdict.



Lookup Throughput
~~~~~~~~~~~~~~~~~


Per-query time, derived from one pass over 2,500 points. The last column states this package against tzfpy, computed from these measurements at render time rather than asserted.

Every figure in this section is the **min** over the measured rounds, not the mean - the estimator this project tracks everywhere, and the only fair one here. Both packages run the identical batch every round, so a slow round is the machine rather than the library; and because tzfpy's rounds are the shorter ones, that noise lands on its mean hardest. Scoring a competitor on the estimator that flatters this package would not be a measurement. The mean, median and spread of every round are in the full statistics below.


.. list-table::
   :header-rows: 1
   :widths: 20 11 32 23 14

   * - Query points
     - tzfpy.get_tz()
     - TimezoneFinder.timezone_at() (in-memory)
     - TimezoneFinderL.timezone_at()
     - vs tzfpy.get_tz()
   * - random points
     - 242ns
     - 621ns
     - 562ns
     - 2.57x slower
   * - on-land points
     - 274ns
     - 776ns
     - 601ns
     - 2.83x slower
   * - unique-shortcut points
     - 217ns
     - 510ns
     - 532ns
     - 2.35x slower
   * - ambiguous-shortcut points
     - 706ns
     - 2.99µs
     - 1.11µs
     - 4.23x slower




Bulk Lookups
~~~~~~~~~~~~


The same 2,500 points, answered by one ``timezone_names_at()`` call per pass instead of a ``timezone_at()`` loop - this package's API for answering many points at once. tzfpy has no batch API (its ``get_tzs()`` returns every zone at a single point), so its column is the same ``get_tz()`` loop as above. The coordinates are passed as ready ``float64`` arrays; converting Python lists costs extra. Batching pays only above a few dozen points per call and depends on the batch size: :doc:`benchmark_results_batch_break_even`.


.. list-table::
   :header-rows: 1
   :widths: 22 12 51 15

   * - Query points
     - tzfpy.get_tz()
     - TimezoneFinder.timezone_names_at() (in-memory), per point
     - vs tzfpy.get_tz()
   * - random points
     - 242ns
     - 118ns
     - 2.05x faster
   * - on-land points
     - 274ns
     - 249ns
     - 1.10x faster
   * - unique-shortcut points
     - 217ns
     - 20.4ns
     - 10.6x faster
   * - ambiguous-shortcut points
     - 706ns
     - 2.17µs
     - 3.07x slower




Full Statistics
~~~~~~~~~~~~~~~




TimezoneFinder.timezone_at() (in-memory)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 30 6 6 6 6 6 6 17 17

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query (min)
     - Throughput (min)
   * - ambiguous-shortcut points
     - 7.94ms
     - 7.99ms
     - 289µs
     - 7.47ms
     - 8.58ms
     - 100
     - 2.99µs
     - 335k/s
   * - on-land points
     - 1.99ms
     - 1.99ms
     - 36.3µs
     - 1.94ms
     - 2.22ms
     - 100
     - 776ns
     - 1.29M/s
   * - random points
     - 1.61ms
     - 1.60ms
     - 41.9µs
     - 1.55ms
     - 1.74ms
     - 100
     - 621ns
     - 1.61M/s
   * - unique-shortcut points
     - 1.32ms
     - 1.32ms
     - 17.1µs
     - 1.27ms
     - 1.39ms
     - 100
     - 510ns
     - 1.96M/s




TimezoneFinder.timezone_names_at() (in-memory)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 30 6 6 6 6 6 6 17 17

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query (min)
     - Throughput (min)
   * - ambiguous-shortcut points
     - 5.66ms
     - 5.67ms
     - 167µs
     - 5.43ms
     - 6.71ms
     - 100
     - 2.17µs
     - 461k/s
   * - on-land points
     - 637µs
     - 635µs
     - 17.2µs
     - 622µs
     - 779µs
     - 100
     - 249ns
     - 4.02M/s
   * - random points
     - 307µs
     - 301µs
     - 34.5µs
     - 295µs
     - 628µs
     - 100
     - 118ns
     - 8.48M/s
   * - unique-shortcut points
     - 52.0µs
     - 51.3µs
     - 2.18µs
     - 51.0µs
     - 64.6µs
     - 100
     - 20.4ns
     - 49.0M/s




TimezoneFinderL.timezone_at()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 30 6 6 6 6 6 6 17 17

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query (min)
     - Throughput (min)
   * - ambiguous-shortcut points
     - 2.86ms
     - 2.87ms
     - 51.4µs
     - 2.78ms
     - 2.99ms
     - 100
     - 1.11µs
     - 900k/s
   * - on-land points
     - 1.55ms
     - 1.55ms
     - 24.3µs
     - 1.50ms
     - 1.71ms
     - 100
     - 601ns
     - 1.66M/s
   * - random points
     - 1.45ms
     - 1.43ms
     - 77.9µs
     - 1.40ms
     - 2.00ms
     - 100
     - 562ns
     - 1.78M/s
   * - unique-shortcut points
     - 1.35ms
     - 1.34ms
     - 9.50µs
     - 1.33ms
     - 1.40ms
     - 100
     - 532ns
     - 1.88M/s




tzfpy.get_tz()
^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 30 6 6 6 6 6 6 17 17

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Time/Query (min)
     - Throughput (min)
   * - ambiguous-shortcut points
     - 2.12ms
     - 1.79ms
     - 742µs
     - 1.77ms
     - 4.94ms
     - 100
     - 706ns
     - 1.42M/s
   * - on-land points
     - 708µs
     - 698µs
     - 38.6µs
     - 686µs
     - 951µs
     - 100
     - 274ns
     - 3.65M/s
   * - random points
     - 619µs
     - 615µs
     - 28.0µs
     - 605µs
     - 856µs
     - 100
     - 242ns
     - 4.13M/s
   * - unique-shortcut points
     - 664µs
     - 560µs
     - 192µs
     - 542µs
     - 1.30ms
     - 100
     - 217ns
     - 4.61M/s




Time to First Answer
~~~~~~~~~~~~~~~~~~~~


Wall clock of a fresh ``python -c`` that imports one package and answers exactly one lookup. This is the honest form of a *startup time* row, because the two packages spend that time in completely different places: this one imports NumPy and builds its index when a finder is constructed, while tzfpy imports in about a millisecond and deserialises its index inside the **first query**. Timing construction alone would score the second as free.

Every row includes interpreter startup, which the baseline row measures on its own. Process launch has a floor and a long, noisy tail, so the bullets below are again the **min** over the rounds; the mean of a row here can sit tens of percent above its own median, and reading a ranking off it would be reading the scheduler.


.. list-table::
   :header-rows: 1
   :widths: 40 10 10 10 10 10 10

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
   * - bare interpreter (baseline)
     - 16.8ms
     - 16.8ms
     - 347µs
     - 16.5ms
     - 18.0ms
     - 20
   * - timezonefinder, file-based
     - 124ms
     - 124ms
     - 5.79ms
     - 116ms
     - 137ms
     - 20
   * - timezonefinder, in-memory
     - 138ms
     - 138ms
     - 5.97ms
     - 128ms
     - 147ms
     - 20
   * - TimezoneFinderL
     - 114ms
     - 113ms
     - 8.34ms
     - 104ms
     - 138ms
     - 20
   * - tzfpy
     - 127ms
     - 125ms
     - 8.92ms
     - 120ms
     - 163ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 88.0ms to a first answer

* **timezonefinder, file-based**: 99.1ms to a first answer

* **tzfpy**: 104ms to a first answer

* **timezonefinder, in-memory**: 111ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
