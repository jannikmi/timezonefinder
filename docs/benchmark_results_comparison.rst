

Comparison against tzfpy
========================


**~1.44µs per lookup here against ~320ns for tzfpy 1.3.3** - 4.49x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

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
     - 320ns
     - 1.44µs
     - 1.01µs
     - 4.49x slower
   * - on-land points
     - 370ns
     - 1.92µs
     - 1.04µs
     - 5.19x slower
   * - unique-shortcut points
     - 278ns
     - 954ns
     - 956ns
     - 3.43x slower
   * - ambiguous-shortcut points
     - 638ns
     - 6.19µs
     - 1.42µs
     - 9.71x slower




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
     - 17.2ms
     - 16.7ms
     - 3.09ms
     - 15.5ms
     - 39.0ms
     - 100
     - 6.19µs
     - 161k/s
   * - on-land points
     - 5.63ms
     - 5.65ms
     - 370µs
     - 4.81ms
     - 6.65ms
     - 166
     - 1.92µs
     - 520k/s
   * - random points
     - 4.26ms
     - 4.25ms
     - 319µs
     - 3.60ms
     - 5.16ms
     - 166
     - 1.44µs
     - 695k/s
   * - unique-shortcut points
     - 2.73ms
     - 2.69ms
     - 218µs
     - 2.38ms
     - 3.46ms
     - 368
     - 954ns
     - 1.05M/s




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
     - 4.00ms
     - 3.99ms
     - 234µs
     - 3.56ms
     - 4.68ms
     - 232
     - 1.42µs
     - 703k/s
   * - on-land points
     - 2.94ms
     - 2.92ms
     - 193µs
     - 2.61ms
     - 3.47ms
     - 315
     - 1.04µs
     - 958k/s
   * - random points
     - 2.90ms
     - 2.89ms
     - 209µs
     - 2.52ms
     - 3.54ms
     - 372
     - 1.01µs
     - 993k/s
   * - unique-shortcut points
     - 2.83ms
     - 2.73ms
     - 901µs
     - 2.39ms
     - 16.0ms
     - 352
     - 956ns
     - 1.05M/s




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
     - 2.32ms
     - 2.22ms
     - 627µs
     - 1.59ms
     - 4.61ms
     - 260
     - 638ns
     - 1.57M/s
   * - on-land points
     - 1.21ms
     - 1.12ms
     - 257µs
     - 926µs
     - 2.18ms
     - 507
     - 370ns
     - 2.70M/s
   * - random points
     - 1.04ms
     - 920µs
     - 261µs
     - 801µs
     - 1.71ms
     - 100
     - 320ns
     - 3.12M/s
   * - unique-shortcut points
     - 811µs
     - 745µs
     - 141µs
     - 695µs
     - 1.54ms
     - 873
     - 278ns
     - 3.60M/s




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
     - 34.6ms
     - 33.9ms
     - 2.59ms
     - 31.5ms
     - 41.5ms
     - 20
   * - timezonefinder, file-based
     - 146ms
     - 144ms
     - 13.4ms
     - 137ms
     - 200ms
     - 20
   * - timezonefinder, in-memory
     - 144ms
     - 144ms
     - 2.15ms
     - 141ms
     - 149ms
     - 20
   * - TimezoneFinderL
     - 133ms
     - 132ms
     - 4.17ms
     - 127ms
     - 142ms
     - 20
   * - tzfpy
     - 130ms
     - 129ms
     - 3.29ms
     - 126ms
     - 141ms
     - 20


Net of that baseline:

* **tzfpy**: 94.6ms to a first answer

* **TimezoneFinderL**: 95.7ms to a first answer

* **timezonefinder, file-based**: 105ms to a first answer

* **timezonefinder, in-memory**: 110ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
