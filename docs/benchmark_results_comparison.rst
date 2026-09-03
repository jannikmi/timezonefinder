

Comparison against tzfpy
========================


**~1.19µs per lookup here against ~310ns for tzfpy 1.3.3** - 3.83x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

*Measured on Darwin arm64, Apple M1 Pro, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration tracks none of the rows on this page. This published table leads with ``Mean`` and belongs to the full on-demand suite, while the trend chart records the ``min`` estimator for the smaller ``benchmark_core`` subset.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.14.2 (CPython)

**NumPy Version**: 2.5.2

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
     - 310ns
     - 1.19µs
     - 834ns
     - 3.83x slower
   * - on-land points
     - 358ns
     - 1.53µs
     - 869ns
     - 4.28x slower
   * - unique-shortcut points
     - 270ns
     - 782ns
     - 783ns
     - 2.90x slower
   * - ambiguous-shortcut points
     - 628ns
     - 4.76µs
     - 1.23µs
     - 7.58x slower




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
     - 13.2ms
     - 13.3ms
     - 480µs
     - 11.9ms
     - 14.2ms
     - 100
     - 4.76µs
     - 210k/s
   * - on-land points
     - 4.30ms
     - 4.27ms
     - 286µs
     - 3.83ms
     - 4.94ms
     - 100
     - 1.53µs
     - 653k/s
   * - random points
     - 3.29ms
     - 3.19ms
     - 265µs
     - 2.97ms
     - 3.96ms
     - 100
     - 1.19µs
     - 843k/s
   * - unique-shortcut points
     - 2.08ms
     - 2.03ms
     - 119µs
     - 1.95ms
     - 2.46ms
     - 100
     - 782ns
     - 1.28M/s




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
     - 3.32ms
     - 3.21ms
     - 230µs
     - 3.08ms
     - 3.98ms
     - 100
     - 1.23µs
     - 812k/s
   * - on-land points
     - 2.30ms
     - 2.25ms
     - 114µs
     - 2.17ms
     - 2.56ms
     - 100
     - 869ns
     - 1.15M/s
   * - random points
     - 2.30ms
     - 2.27ms
     - 163µs
     - 2.08ms
     - 2.60ms
     - 100
     - 834ns
     - 1.20M/s
   * - unique-shortcut points
     - 2.07ms
     - 2.03ms
     - 106µs
     - 1.96ms
     - 2.49ms
     - 100
     - 783ns
     - 1.28M/s




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
     - 1.81ms
     - 1.71ms
     - 253µs
     - 1.57ms
     - 2.91ms
     - 100
     - 628ns
     - 1.59M/s
   * - on-land points
     - 946µs
     - 920µs
     - 65.7µs
     - 895µs
     - 1.21ms
     - 100
     - 358ns
     - 2.79M/s
   * - random points
     - 843µs
     - 803µs
     - 90.0µs
     - 775µs
     - 1.31ms
     - 100
     - 310ns
     - 3.22M/s
   * - unique-shortcut points
     - 720µs
     - 698µs
     - 59.9µs
     - 674µs
     - 935µs
     - 100
     - 270ns
     - 3.71M/s




Time to First Answer
~~~~~~~~~~~~~~~~~~~~


Wall clock of a fresh ``python -c`` that imports one package and answers exactly one lookup. This is the honest form of a *startup time* row, because the two packages spend that time in completely different places: this one imports NumPy and H3 and builds its index when a finder is constructed, while tzfpy imports in about a millisecond and deserialises its index inside the **first query**. Timing construction alone would score the second as free.

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
     - 28.4ms
     - 28.3ms
     - 879µs
     - 27.0ms
     - 31.6ms
     - 20
   * - timezonefinder, file-based
     - 140ms
     - 140ms
     - 2.38ms
     - 137ms
     - 146ms
     - 20
   * - timezonefinder, in-memory
     - 136ms
     - 136ms
     - 1.24ms
     - 134ms
     - 138ms
     - 20
   * - TimezoneFinderL
     - 126ms
     - 125ms
     - 1.71ms
     - 124ms
     - 129ms
     - 20
   * - tzfpy
     - 123ms
     - 123ms
     - 979µs
     - 122ms
     - 126ms
     - 20


Net of that baseline:

* **tzfpy**: 94.8ms to a first answer

* **TimezoneFinderL**: 96.5ms to a first answer

* **timezonefinder, in-memory**: 107ms to a first answer

* **timezonefinder, file-based**: 110ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
