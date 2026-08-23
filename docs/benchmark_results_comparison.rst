

Comparison against tzfpy
========================


**~1.72µs per lookup here against ~313ns for tzfpy 1.3.3** - 5.47x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

*Measured on Darwin arm64, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.14.2 (CPython)

**NumPy Version**: 2.3.5

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
     - 313ns
     - 1.72µs
     - 865ns
     - 5.47x slower
   * - on-land points
     - 357ns
     - 3.40µs
     - 892ns
     - 9.51x slower
   * - unique-shortcut points
     - 273ns
     - 823ns
     - 814ns
     - 3.02x slower
   * - ambiguous-shortcut points
     - 626ns
     - 10.2µs
     - 1.22µs
     - 16.4x slower




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
     - 26.9ms
     - 26.7ms
     - 1.92ms
     - 25.6ms
     - 45.4ms
     - 100
     - 10.2µs
     - 97.7k/s
   * - on-land points
     - 10.1ms
     - 9.40ms
     - 2.94ms
     - 8.49ms
     - 32.5ms
     - 103
     - 3.40µs
     - 294k/s
   * - random points
     - 4.95ms
     - 4.88ms
     - 432µs
     - 4.29ms
     - 7.73ms
     - 151
     - 1.72µs
     - 583k/s
   * - unique-shortcut points
     - 2.23ms
     - 2.20ms
     - 132µs
     - 2.06ms
     - 2.74ms
     - 397
     - 823ns
     - 1.21M/s




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
     - 3.31ms
     - 3.24ms
     - 224µs
     - 3.05ms
     - 4.08ms
     - 261
     - 1.22µs
     - 819k/s
   * - on-land points
     - 2.38ms
     - 2.34ms
     - 136µs
     - 2.23ms
     - 3.06ms
     - 407
     - 892ns
     - 1.12M/s
   * - random points
     - 2.33ms
     - 2.27ms
     - 156µs
     - 2.16ms
     - 2.83ms
     - 356
     - 865ns
     - 1.16M/s
   * - unique-shortcut points
     - 2.14ms
     - 2.12ms
     - 89.2µs
     - 2.04ms
     - 2.46ms
     - 471
     - 814ns
     - 1.23M/s




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
     - 1.73ms
     - 1.67ms
     - 171µs
     - 1.56ms
     - 2.57ms
     - 319
     - 626ns
     - 1.60M/s
   * - on-land points
     - 960µs
     - 936µs
     - 78.9µs
     - 893µs
     - 1.64ms
     - 643
     - 357ns
     - 2.80M/s
   * - random points
     - 875µs
     - 837µs
     - 100µs
     - 784µs
     - 1.24ms
     - 100
     - 313ns
     - 3.19M/s
   * - unique-shortcut points
     - 721µs
     - 708µs
     - 40.1µs
     - 681µs
     - 939µs
     - 1010
     - 273ns
     - 3.67M/s




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
     - 27.3ms
     - 27.3ms
     - 1.26ms
     - 25.6ms
     - 31.4ms
     - 20
   * - timezonefinder, file-based
     - 135ms
     - 133ms
     - 11.9ms
     - 128ms
     - 184ms
     - 20
   * - timezonefinder, in-memory
     - 128ms
     - 128ms
     - 1.81ms
     - 125ms
     - 131ms
     - 20
   * - TimezoneFinderL
     - 116ms
     - 115ms
     - 2.03ms
     - 112ms
     - 120ms
     - 20
   * - tzfpy
     - 123ms
     - 122ms
     - 2.40ms
     - 121ms
     - 131ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 86.5ms to a first answer

* **tzfpy**: 95.2ms to a first answer

* **timezonefinder, in-memory**: 99.4ms to a first answer

* **timezonefinder, file-based**: 102ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
