

Comparison against tzfpy
========================


**~2.17µs per lookup here against ~435ns for tzfpy 1.3.3** - 4.98x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 2.8701 GHz, Python 3.13.15, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration tracks none of the rows on this page. This published table leads with ``Mean`` and belongs to the full on-demand suite, while the trend chart records the ``min`` estimator for the smaller ``benchmark_core`` subset.



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
     - 435ns
     - 2.17µs
     - 1.50µs
     - 4.98x slower
   * - on-land points
     - 477ns
     - 2.84µs
     - 1.55µs
     - 5.95x slower
   * - unique-shortcut points
     - 349ns
     - 1.42µs
     - 1.40µs
     - 4.07x slower
   * - ambiguous-shortcut points
     - 958ns
     - 8.90µs
     - 2.23µs
     - 9.29x slower




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
     - 22.5ms
     - 22.5ms
     - 131µs
     - 22.3ms
     - 23.2ms
     - 100
     - 8.90µs
     - 112k/s
   * - on-land points
     - 7.19ms
     - 7.18ms
     - 51.9µs
     - 7.10ms
     - 7.35ms
     - 100
     - 2.84µs
     - 352k/s
   * - random points
     - 5.53ms
     - 5.50ms
     - 114µs
     - 5.42ms
     - 6.35ms
     - 100
     - 2.17µs
     - 461k/s
   * - unique-shortcut points
     - 3.62ms
     - 3.60ms
     - 96.7µs
     - 3.56ms
     - 4.43ms
     - 100
     - 1.42µs
     - 703k/s




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
     - 5.72ms
     - 5.70ms
     - 132µs
     - 5.58ms
     - 6.15ms
     - 100
     - 2.23µs
     - 448k/s
   * - on-land points
     - 3.90ms
     - 3.90ms
     - 21.9µs
     - 3.87ms
     - 3.99ms
     - 100
     - 1.55µs
     - 646k/s
   * - random points
     - 3.80ms
     - 3.79ms
     - 32.9µs
     - 3.76ms
     - 3.97ms
     - 100
     - 1.50µs
     - 665k/s
   * - unique-shortcut points
     - 3.54ms
     - 3.54ms
     - 20.8µs
     - 3.50ms
     - 3.61ms
     - 100
     - 1.40µs
     - 713k/s




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
     - 2.47ms
     - 2.46ms
     - 87.2µs
     - 2.39ms
     - 3.25ms
     - 100
     - 958ns
     - 1.04M/s
   * - on-land points
     - 1.23ms
     - 1.22ms
     - 25.9µs
     - 1.19ms
     - 1.36ms
     - 100
     - 477ns
     - 2.10M/s
   * - random points
     - 1.11ms
     - 1.11ms
     - 21.9µs
     - 1.09ms
     - 1.22ms
     - 100
     - 435ns
     - 2.30M/s
   * - unique-shortcut points
     - 902µs
     - 898µs
     - 19.1µs
     - 873µs
     - 980µs
     - 100
     - 349ns
     - 2.86M/s




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
     - 28.9ms
     - 28.8ms
     - 794µs
     - 27.9ms
     - 30.4ms
     - 20
   * - timezonefinder, file-based
     - 209ms
     - 208ms
     - 2.59ms
     - 204ms
     - 215ms
     - 20
   * - timezonefinder, in-memory
     - 199ms
     - 199ms
     - 2.19ms
     - 196ms
     - 204ms
     - 20
   * - TimezoneFinderL
     - 189ms
     - 188ms
     - 2.83ms
     - 184ms
     - 197ms
     - 20
   * - tzfpy
     - 194ms
     - 194ms
     - 1.46ms
     - 192ms
     - 196ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 156ms to a first answer

* **tzfpy**: 164ms to a first answer

* **timezonefinder, in-memory**: 168ms to a first answer

* **timezonefinder, file-based**: 176ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
