

Speed and Startup against tzfpy
===============================


**~1.28µs per lookup here against ~418ns for tzfpy 1.3.3** - 3.07x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

**For bulk lookups, ``timezone_names_at()`` answers the same 2,500 points in one call at ~240ns per point** - 1.74x faster than a loop of tzfpy calls, which has no batch API. See *Bulk Lookups* below, and :doc:`benchmark_results_batch_break_even` for the batch size from which batching pays.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 2.4454 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 418ns
     - 1.28µs
     - 1.08µs
     - 3.07x slower
   * - on-land points
     - 474ns
     - 1.56µs
     - 1.19µs
     - 3.30x slower
   * - unique-shortcut points
     - 378ns
     - 1.01µs
     - 1.02µs
     - 2.67x slower
   * - ambiguous-shortcut points
     - 1.08µs
     - 5.70µs
     - 2.20µs
     - 5.27x slower




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
     - 418ns
     - 240ns
     - 1.74x faster
   * - on-land points
     - 474ns
     - 487ns
     - 1.03x slower
   * - unique-shortcut points
     - 378ns
     - 43.2ns
     - 8.75x faster
   * - ambiguous-shortcut points
     - 1.08µs
     - 4.14µs
     - 3.83x slower




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
     - 14.5ms
     - 14.5ms
     - 295µs
     - 14.2ms
     - 16.1ms
     - 100
     - 5.70µs
     - 175k/s
   * - on-land points
     - 3.96ms
     - 3.95ms
     - 60.1µs
     - 3.91ms
     - 4.35ms
     - 100
     - 1.56µs
     - 640k/s
   * - random points
     - 3.25ms
     - 3.23ms
     - 43.9µs
     - 3.20ms
     - 3.48ms
     - 100
     - 1.28µs
     - 780k/s
   * - unique-shortcut points
     - 2.56ms
     - 2.55ms
     - 21.6µs
     - 2.52ms
     - 2.68ms
     - 100
     - 1.01µs
     - 990k/s




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
     - 10.5ms
     - 10.5ms
     - 231µs
     - 10.4ms
     - 11.9ms
     - 100
     - 4.14µs
     - 241k/s
   * - on-land points
     - 1.25ms
     - 1.24ms
     - 22.9µs
     - 1.22ms
     - 1.35ms
     - 100
     - 487ns
     - 2.05M/s
   * - random points
     - 623µs
     - 624µs
     - 13.9µs
     - 600µs
     - 677µs
     - 100
     - 240ns
     - 4.17M/s
   * - unique-shortcut points
     - 116µs
     - 111µs
     - 10.3µs
     - 108µs
     - 168µs
     - 100
     - 43.2ns
     - 23.1M/s




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
     - 5.55ms
     - 5.54ms
     - 32.4µs
     - 5.50ms
     - 5.70ms
     - 100
     - 2.20µs
     - 454k/s
   * - on-land points
     - 3.03ms
     - 3.02ms
     - 37.5µs
     - 2.98ms
     - 3.28ms
     - 100
     - 1.19µs
     - 839k/s
   * - random points
     - 2.75ms
     - 2.76ms
     - 32.2µs
     - 2.70ms
     - 2.87ms
     - 100
     - 1.08µs
     - 927k/s
   * - unique-shortcut points
     - 2.61ms
     - 2.60ms
     - 41.1µs
     - 2.54ms
     - 2.83ms
     - 100
     - 1.02µs
     - 984k/s




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
     - 2.80ms
     - 2.74ms
     - 204µs
     - 2.70ms
     - 4.24ms
     - 100
     - 1.08µs
     - 924k/s
   * - on-land points
     - 1.20ms
     - 1.19ms
     - 14.7µs
     - 1.18ms
     - 1.28ms
     - 100
     - 474ns
     - 2.11M/s
   * - random points
     - 1.06ms
     - 1.06ms
     - 9.72µs
     - 1.04ms
     - 1.10ms
     - 100
     - 418ns
     - 2.39M/s
   * - unique-shortcut points
     - 966µs
     - 960µs
     - 14.8µs
     - 946µs
     - 1.04ms
     - 100
     - 378ns
     - 2.64M/s




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
     - 26.4ms
     - 26.2ms
     - 463µs
     - 25.9ms
     - 27.7ms
     - 20
   * - timezonefinder, file-based
     - 201ms
     - 201ms
     - 3.09ms
     - 196ms
     - 208ms
     - 20
   * - timezonefinder, in-memory
     - 195ms
     - 193ms
     - 4.97ms
     - 189ms
     - 213ms
     - 20
   * - TimezoneFinderL
     - 179ms
     - 178ms
     - 3.99ms
     - 175ms
     - 189ms
     - 20
   * - tzfpy
     - 181ms
     - 181ms
     - 1.05ms
     - 180ms
     - 184ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 149ms to a first answer

* **tzfpy**: 154ms to a first answer

* **timezonefinder, in-memory**: 163ms to a first answer

* **timezonefinder, file-based**: 170ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
