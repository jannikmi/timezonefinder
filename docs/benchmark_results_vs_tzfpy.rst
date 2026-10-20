

Speed and Startup against tzfpy
===============================


**~646ns per lookup here against ~257ns for tzfpy 1.3.3** - 2.52x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

**For bulk lookups, ``timezone_names_at()`` answers the same 2,500 points in one call at ~126ns per point** - 2.03x faster than a loop of tzfpy calls, which has no batch API. See *Bulk Lookups* below, and :doc:`benchmark_results_batch_break_even` for the batch size from which batching pays.

*Measured on Linux x86_64, AMD EPYC 9V45 96-Core Processor @ 4.3482 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 257ns
     - 646ns
     - 564ns
     - 2.52x slower
   * - on-land points
     - 299ns
     - 817ns
     - 621ns
     - 2.73x slower
   * - unique-shortcut points
     - 236ns
     - 519ns
     - 527ns
     - 2.20x slower
   * - ambiguous-shortcut points
     - 779ns
     - 3.08µs
     - 1.17µs
     - 3.96x slower




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
     - 257ns
     - 126ns
     - 2.03x faster
   * - on-land points
     - 299ns
     - 258ns
     - 1.16x faster
   * - unique-shortcut points
     - 236ns
     - 20.6ns
     - 11.4x faster
   * - ambiguous-shortcut points
     - 779ns
     - 2.31µs
     - 2.96x slower




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
     - 7.86ms
     - 185µs
     - 7.71ms
     - 8.58ms
     - 100
     - 3.08µs
     - 324k/s
   * - on-land points
     - 2.11ms
     - 2.07ms
     - 108µs
     - 2.04ms
     - 2.76ms
     - 100
     - 817ns
     - 1.22M/s
   * - random points
     - 1.66ms
     - 1.64ms
     - 76.4µs
     - 1.61ms
     - 2.05ms
     - 100
     - 646ns
     - 1.55M/s
   * - unique-shortcut points
     - 1.38ms
     - 1.34ms
     - 99.4µs
     - 1.30ms
     - 1.91ms
     - 100
     - 519ns
     - 1.93M/s




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
     - 5.92ms
     - 5.86ms
     - 172µs
     - 5.77ms
     - 7.10ms
     - 100
     - 2.31µs
     - 433k/s
   * - on-land points
     - 663µs
     - 661µs
     - 13.2µs
     - 646µs
     - 747µs
     - 100
     - 258ns
     - 3.87M/s
   * - random points
     - 326µs
     - 322µs
     - 11.7µs
     - 316µs
     - 406µs
     - 100
     - 126ns
     - 7.92M/s
   * - unique-shortcut points
     - 52.5µs
     - 51.8µs
     - 2.27µs
     - 51.5µs
     - 64.6µs
     - 100
     - 20.6ns
     - 48.6M/s




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
     - 2.96ms
     - 2.95ms
     - 39.7µs
     - 2.91ms
     - 3.24ms
     - 100
     - 1.17µs
     - 858k/s
   * - on-land points
     - 1.59ms
     - 1.59ms
     - 28.6µs
     - 1.55ms
     - 1.76ms
     - 100
     - 621ns
     - 1.61M/s
   * - random points
     - 1.44ms
     - 1.42ms
     - 73.9µs
     - 1.41ms
     - 1.86ms
     - 100
     - 564ns
     - 1.77M/s
   * - unique-shortcut points
     - 1.33ms
     - 1.33ms
     - 9.53µs
     - 1.32ms
     - 1.37ms
     - 100
     - 527ns
     - 1.90M/s




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
     - 2.01ms
     - 1.98ms
     - 107µs
     - 1.95ms
     - 2.86ms
     - 100
     - 779ns
     - 1.28M/s
   * - on-land points
     - 765µs
     - 757µs
     - 30.1µs
     - 747µs
     - 986µs
     - 100
     - 299ns
     - 3.35M/s
   * - random points
     - 661µs
     - 657µs
     - 30.2µs
     - 642µs
     - 926µs
     - 100
     - 257ns
     - 3.89M/s
   * - unique-shortcut points
     - 605µs
     - 603µs
     - 12.8µs
     - 589µs
     - 700µs
     - 100
     - 236ns
     - 4.25M/s




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
     - 17.0ms
     - 16.9ms
     - 226µs
     - 16.8ms
     - 17.8ms
     - 20
   * - timezonefinder, file-based
     - 128ms
     - 126ms
     - 4.53ms
     - 122ms
     - 140ms
     - 20
   * - timezonefinder, in-memory
     - 129ms
     - 128ms
     - 1.62ms
     - 126ms
     - 133ms
     - 20
   * - TimezoneFinderL
     - 107ms
     - 107ms
     - 1.98ms
     - 105ms
     - 111ms
     - 20
   * - tzfpy
     - 127ms
     - 127ms
     - 915µs
     - 125ms
     - 129ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 88.6ms to a first answer

* **timezonefinder, file-based**: 105ms to a first answer

* **tzfpy**: 108ms to a first answer

* **timezonefinder, in-memory**: 109ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
