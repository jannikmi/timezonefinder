

Comparison against tzfpy
========================


**~636ns per lookup here against ~304ns for tzfpy 1.3.3** - 2.10x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

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
     - 304ns
     - 636ns
     - 564ns
     - 2.10x slower
   * - on-land points
     - 347ns
     - 787ns
     - 619ns
     - 2.27x slower
   * - unique-shortcut points
     - 281ns
     - 531ns
     - 535ns
     - 1.89x slower
   * - ambiguous-shortcut points
     - 746ns
     - 2.58µs
     - 1.05µs
     - 3.46x slower




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
     - 6.70ms
     - 6.55ms
     - 327µs
     - 6.45ms
     - 7.84ms
     - 100
     - 2.58µs
     - 388k/s
   * - on-land points
     - 2.02ms
     - 1.98ms
     - 99.5µs
     - 1.97ms
     - 2.58ms
     - 100
     - 787ns
     - 1.27M/s
   * - random points
     - 1.62ms
     - 1.60ms
     - 36.6µs
     - 1.59ms
     - 1.76ms
     - 100
     - 636ns
     - 1.57M/s
   * - unique-shortcut points
     - 1.36ms
     - 1.34ms
     - 52.1µs
     - 1.33ms
     - 1.66ms
     - 100
     - 531ns
     - 1.88M/s




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
     - 2.68ms
     - 2.66ms
     - 62.2µs
     - 2.63ms
     - 3.10ms
     - 100
     - 1.05µs
     - 951k/s
   * - on-land points
     - 1.76ms
     - 1.56ms
     - 928µs
     - 1.55ms
     - 8.62ms
     - 100
     - 619ns
     - 1.62M/s
   * - random points
     - 1.44ms
     - 1.42ms
     - 33.8µs
     - 1.41ms
     - 1.65ms
     - 100
     - 564ns
     - 1.77M/s
   * - unique-shortcut points
     - 1.36ms
     - 1.35ms
     - 34.0µs
     - 1.34ms
     - 1.54ms
     - 100
     - 535ns
     - 1.87M/s




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
     - 1.98ms
     - 1.89ms
     - 237µs
     - 1.86ms
     - 3.03ms
     - 100
     - 746ns
     - 1.34M/s
   * - on-land points
     - 899µs
     - 876µs
     - 61.9µs
     - 867µs
     - 1.20ms
     - 100
     - 347ns
     - 2.88M/s
   * - random points
     - 792µs
     - 771µs
     - 68.8µs
     - 759µs
     - 1.29ms
     - 100
     - 304ns
     - 3.29M/s
   * - unique-shortcut points
     - 706µs
     - 704µs
     - 7.58µs
     - 702µs
     - 746µs
     - 100
     - 281ns
     - 3.56M/s




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
     - 23.9ms
     - 23.8ms
     - 944µs
     - 22.7ms
     - 25.9ms
     - 20
   * - timezonefinder, file-based
     - 106ms
     - 105ms
     - 5.41ms
     - 98.5ms
     - 123ms
     - 20
   * - timezonefinder, in-memory
     - 102ms
     - 102ms
     - 2.23ms
     - 98.6ms
     - 106ms
     - 20
   * - TimezoneFinderL
     - 96.0ms
     - 95.7ms
     - 4.28ms
     - 89.5ms
     - 112ms
     - 20
   * - tzfpy
     - 116ms
     - 115ms
     - 4.29ms
     - 114ms
     - 134ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 66.9ms to a first answer

* **timezonefinder, file-based**: 75.8ms to a first answer

* **timezonefinder, in-memory**: 75.9ms to a first answer

* **tzfpy**: 91.3ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
