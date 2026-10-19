

Speed and Startup against tzfpy
===============================


**~982ns per lookup here against ~352ns for tzfpy 1.3.3** - 2.79x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

**For bulk lookups, ``timezone_names_at()`` answers the same 2,500 points in one call at ~169ns per point** - 2.08x faster than a loop of tzfpy calls, which has no batch API. See *Bulk Lookups* below, and :doc:`benchmark_results_batch_break_even` for the batch size from which batching pays.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 3.9326 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration tracks none of the rows on this page. This published table leads with ``Mean`` and belongs to the full on-demand suite, while the trend chart records the ``min`` estimator for the smaller ``benchmark_core`` subset.



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


**Fixture Version**: 5

**Timezone Data Version**: 2026e



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
     - 352ns
     - 982ns
     - 871ns
     - 2.79x slower
   * - on-land points
     - 395ns
     - 1.21µs
     - 941ns
     - 3.06x slower
   * - unique-shortcut points
     - 317ns
     - 824ns
     - 817ns
     - 2.60x slower
   * - ambiguous-shortcut points
     - 948ns
     - 4.27µs
     - 1.71µs
     - 4.50x slower




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
     - 352ns
     - 169ns
     - 2.08x faster
   * - on-land points
     - 395ns
     - 355ns
     - 1.11x faster
   * - unique-shortcut points
     - 317ns
     - 29.2ns
     - 10.8x faster
   * - ambiguous-shortcut points
     - 948ns
     - 3.16µs
     - 3.33x slower




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
     - 11.0ms
     - 10.9ms
     - 274µs
     - 10.7ms
     - 12.7ms
     - 100
     - 4.27µs
     - 234k/s
   * - on-land points
     - 3.08ms
     - 3.06ms
     - 142µs
     - 3.02ms
     - 4.39ms
     - 100
     - 1.21µs
     - 827k/s
   * - random points
     - 2.53ms
     - 2.51ms
     - 131µs
     - 2.46ms
     - 3.59ms
     - 100
     - 982ns
     - 1.02M/s
   * - unique-shortcut points
     - 2.08ms
     - 2.08ms
     - 15.1µs
     - 2.06ms
     - 2.16ms
     - 100
     - 824ns
     - 1.21M/s




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
     - 8.14ms
     - 8.12ms
     - 178µs
     - 7.90ms
     - 9.32ms
     - 100
     - 3.16µs
     - 316k/s
   * - on-land points
     - 914µs
     - 908µs
     - 20.6µs
     - 888µs
     - 1.05ms
     - 100
     - 355ns
     - 2.82M/s
   * - random points
     - 442µs
     - 439µs
     - 16.0µs
     - 423µs
     - 512µs
     - 100
     - 169ns
     - 5.91M/s
   * - unique-shortcut points
     - 75.8µs
     - 74.3µs
     - 4.32µs
     - 73.1µs
     - 99.8µs
     - 100
     - 29.2ns
     - 34.2M/s




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
     - 4.34ms
     - 4.31ms
     - 97.2µs
     - 4.27ms
     - 4.84ms
     - 100
     - 1.71µs
     - 586k/s
   * - on-land points
     - 2.39ms
     - 2.38ms
     - 23.4µs
     - 2.35ms
     - 2.51ms
     - 100
     - 941ns
     - 1.06M/s
   * - random points
     - 2.21ms
     - 2.20ms
     - 35.5µs
     - 2.18ms
     - 2.40ms
     - 100
     - 871ns
     - 1.15M/s
   * - unique-shortcut points
     - 2.07ms
     - 2.06ms
     - 19.3µs
     - 2.04ms
     - 2.17ms
     - 100
     - 817ns
     - 1.22M/s




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
     - 2.45ms
     - 2.44ms
     - 57.7µs
     - 2.37ms
     - 2.61ms
     - 100
     - 948ns
     - 1.05M/s
   * - on-land points
     - 1.02ms
     - 1.01ms
     - 24.0µs
     - 987µs
     - 1.11ms
     - 100
     - 395ns
     - 2.53M/s
   * - random points
     - 915µs
     - 912µs
     - 27.0µs
     - 880µs
     - 1.11ms
     - 100
     - 352ns
     - 2.84M/s
   * - unique-shortcut points
     - 810µs
     - 807µs
     - 11.4µs
     - 792µs
     - 854µs
     - 100
     - 317ns
     - 3.16M/s




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
     - 21.8ms
     - 21.6ms
     - 489µs
     - 21.2ms
     - 23.2ms
     - 20
   * - timezonefinder, file-based
     - 157ms
     - 155ms
     - 5.60ms
     - 153ms
     - 179ms
     - 20
   * - timezonefinder, in-memory
     - 165ms
     - 164ms
     - 3.29ms
     - 162ms
     - 175ms
     - 20
   * - TimezoneFinderL
     - 147ms
     - 147ms
     - 2.48ms
     - 141ms
     - 151ms
     - 20
   * - tzfpy
     - 157ms
     - 157ms
     - 811µs
     - 156ms
     - 159ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 120ms to a first answer

* **timezonefinder, file-based**: 132ms to a first answer

* **tzfpy**: 135ms to a first answer

* **timezonefinder, in-memory**: 140ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
