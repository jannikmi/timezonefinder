

Speed and Startup against tzfpy
===============================


**~1.06µs per lookup here against ~349ns for tzfpy 1.3.3** - 3.03x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

**For bulk lookups, ``timezone_names_at()`` answers the same 2,500 points in one call at ~200ns per point** - 1.75x faster than a loop of tzfpy calls, which has no batch API. See *Bulk Lookups* below, and :doc:`benchmark_results_batch_break_even` for the batch size from which batching pays.

*Measured on Linux x86_64, INTEL(R) XEON(R) PLATINUM 8573C @ 3.1028 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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


**Fixture Version**: 4

**Timezone Data Version**: 2026d



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
     - 349ns
     - 1.06µs
     - 910ns
     - 3.03x slower
   * - on-land points
     - 405ns
     - 1.37µs
     - 1.02µs
     - 3.38x slower
   * - unique-shortcut points
     - 315ns
     - 863ns
     - 846ns
     - 2.74x slower
   * - ambiguous-shortcut points
     - 1.10µs
     - 4.78µs
     - 1.78µs
     - 4.36x slower




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
     - 349ns
     - 200ns
     - 1.75x faster
   * - on-land points
     - 405ns
     - 444ns
     - 1.09x slower
   * - unique-shortcut points
     - 315ns
     - 31.3ns
     - 10.1x faster
   * - ambiguous-shortcut points
     - 1.10µs
     - 3.43µs
     - 3.13x slower




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
     - 12.4ms
     - 12.3ms
     - 368µs
     - 12.0ms
     - 14.0ms
     - 100
     - 4.78µs
     - 209k/s
   * - on-land points
     - 3.59ms
     - 3.57ms
     - 132µs
     - 3.42ms
     - 4.27ms
     - 100
     - 1.37µs
     - 731k/s
   * - random points
     - 2.84ms
     - 2.76ms
     - 276µs
     - 2.64ms
     - 4.13ms
     - 100
     - 1.06µs
     - 947k/s
   * - unique-shortcut points
     - 2.29ms
     - 2.26ms
     - 144µs
     - 2.16ms
     - 3.09ms
     - 100
     - 863ns
     - 1.16M/s




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
     - 8.93ms
     - 8.93ms
     - 155µs
     - 8.58ms
     - 9.53ms
     - 100
     - 3.43µs
     - 291k/s
   * - on-land points
     - 1.16ms
     - 1.15ms
     - 50.3µs
     - 1.11ms
     - 1.43ms
     - 100
     - 444ns
     - 2.25M/s
   * - random points
     - 523µs
     - 520µs
     - 16.3µs
     - 499µs
     - 612µs
     - 100
     - 200ns
     - 5.01M/s
   * - unique-shortcut points
     - 84.0µs
     - 82.6µs
     - 5.00µs
     - 78.3µs
     - 103µs
     - 100
     - 31.3ns
     - 31.9M/s




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
     - 4.59ms
     - 4.60ms
     - 85.3µs
     - 4.44ms
     - 4.83ms
     - 100
     - 1.78µs
     - 563k/s
   * - on-land points
     - 2.64ms
     - 2.62ms
     - 77.2µs
     - 2.54ms
     - 3.02ms
     - 100
     - 1.02µs
     - 983k/s
   * - random points
     - 2.35ms
     - 2.34ms
     - 56.9µs
     - 2.27ms
     - 2.70ms
     - 100
     - 910ns
     - 1.10M/s
   * - unique-shortcut points
     - 2.19ms
     - 2.18ms
     - 51.3µs
     - 2.12ms
     - 2.36ms
     - 100
     - 846ns
     - 1.18M/s




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
     - 2.83ms
     - 2.81ms
     - 93.3µs
     - 2.74ms
     - 3.47ms
     - 100
     - 1.10µs
     - 913k/s
   * - on-land points
     - 1.06ms
     - 1.05ms
     - 45.4µs
     - 1.01ms
     - 1.27ms
     - 100
     - 405ns
     - 2.47M/s
   * - random points
     - 926µs
     - 916µs
     - 54.0µs
     - 872µs
     - 1.24ms
     - 100
     - 349ns
     - 2.87M/s
   * - unique-shortcut points
     - 820µs
     - 806µs
     - 37.6µs
     - 789µs
     - 1.08ms
     - 100
     - 315ns
     - 3.17M/s




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
     - 24.3ms
     - 24.2ms
     - 645µs
     - 23.4ms
     - 25.8ms
     - 20
   * - timezonefinder, file-based
     - 188ms
     - 188ms
     - 2.12ms
     - 185ms
     - 194ms
     - 20
   * - timezonefinder, in-memory
     - 188ms
     - 188ms
     - 2.04ms
     - 186ms
     - 194ms
     - 20
   * - TimezoneFinderL
     - 172ms
     - 172ms
     - 829µs
     - 171ms
     - 174ms
     - 20
   * - tzfpy
     - 177ms
     - 177ms
     - 845µs
     - 175ms
     - 179ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 147ms to a first answer

* **tzfpy**: 152ms to a first answer

* **timezonefinder, file-based**: 162ms to a first answer

* **timezonefinder, in-memory**: 162ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
