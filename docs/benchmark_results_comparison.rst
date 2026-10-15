

Comparison against tzfpy
========================


**~1.30µs per lookup here against ~422ns for tzfpy 1.3.3** - 3.09x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2287 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 422ns
     - 1.30µs
     - 1.12µs
     - 3.09x slower
   * - on-land points
     - 476ns
     - 1.68µs
     - 1.23µs
     - 3.52x slower
   * - unique-shortcut points
     - 372ns
     - 1.02µs
     - 1.05µs
     - 2.74x slower
   * - ambiguous-shortcut points
     - 1.10µs
     - 6.17µs
     - 2.27µs
     - 5.58x slower




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
     - 16.1ms
     - 16.0ms
     - 536µs
     - 15.4ms
     - 20.0ms
     - 100
     - 6.17µs
     - 162k/s
   * - on-land points
     - 4.46ms
     - 4.39ms
     - 284µs
     - 4.19ms
     - 6.09ms
     - 100
     - 1.68µs
     - 596k/s
   * - random points
     - 3.34ms
     - 3.31ms
     - 77.5µs
     - 3.26ms
     - 3.67ms
     - 100
     - 1.30µs
     - 767k/s
   * - unique-shortcut points
     - 2.61ms
     - 2.60ms
     - 47.6µs
     - 2.55ms
     - 2.95ms
     - 100
     - 1.02µs
     - 980k/s




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
     - 5.89ms
     - 5.89ms
     - 145µs
     - 5.68ms
     - 6.71ms
     - 100
     - 2.27µs
     - 440k/s
   * - on-land points
     - 3.15ms
     - 3.10ms
     - 199µs
     - 3.07ms
     - 4.56ms
     - 100
     - 1.23µs
     - 816k/s
   * - random points
     - 2.89ms
     - 2.86ms
     - 90.4µs
     - 2.79ms
     - 3.29ms
     - 100
     - 1.12µs
     - 896k/s
   * - unique-shortcut points
     - 2.68ms
     - 2.66ms
     - 54.3µs
     - 2.64ms
     - 3.07ms
     - 100
     - 1.05µs
     - 948k/s




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
     - 3.13ms
     - 2.95ms
     - 490µs
     - 2.76ms
     - 5.20ms
     - 100
     - 1.10µs
     - 905k/s
   * - on-land points
     - 1.24ms
     - 1.20ms
     - 140µs
     - 1.19ms
     - 2.06ms
     - 100
     - 476ns
     - 2.10M/s
   * - random points
     - 1.08ms
     - 1.07ms
     - 27.7µs
     - 1.05ms
     - 1.23ms
     - 100
     - 422ns
     - 2.37M/s
   * - unique-shortcut points
     - 952µs
     - 947µs
     - 16.5µs
     - 930µs
     - 1.02ms
     - 100
     - 372ns
     - 2.69M/s




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
     - 29.4ms
     - 29.3ms
     - 1.09ms
     - 27.2ms
     - 31.1ms
     - 20
   * - timezonefinder, file-based
     - 210ms
     - 207ms
     - 8.16ms
     - 202ms
     - 231ms
     - 20
   * - timezonefinder, in-memory
     - 198ms
     - 198ms
     - 2.06ms
     - 193ms
     - 202ms
     - 20
   * - TimezoneFinderL
     - 188ms
     - 188ms
     - 2.63ms
     - 184ms
     - 195ms
     - 20
   * - tzfpy
     - 190ms
     - 190ms
     - 3.87ms
     - 182ms
     - 199ms
     - 20


Net of that baseline:

* **tzfpy**: 155ms to a first answer

* **TimezoneFinderL**: 157ms to a first answer

* **timezonefinder, in-memory**: 166ms to a first answer

* **timezonefinder, file-based**: 175ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
