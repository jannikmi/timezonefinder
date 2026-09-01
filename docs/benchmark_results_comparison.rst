

Comparison against tzfpy
========================


**~1.21µs per lookup here against ~307ns for tzfpy 1.3.3** - 3.95x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

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
     - 307ns
     - 1.21µs
     - 882ns
     - 3.95x slower
   * - on-land points
     - 358ns
     - 1.55µs
     - 908ns
     - 4.32x slower
   * - unique-shortcut points
     - 265ns
     - 824ns
     - 822ns
     - 3.11x slower
   * - ambiguous-shortcut points
     - 622ns
     - 4.62µs
     - 1.26µs
     - 7.43x slower




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
     - 13.1ms
     - 13.2ms
     - 676µs
     - 11.5ms
     - 14.7ms
     - 100
     - 4.62µs
     - 216k/s
   * - on-land points
     - 4.44ms
     - 4.39ms
     - 384µs
     - 3.87ms
     - 5.57ms
     - 229
     - 1.55µs
     - 647k/s
   * - random points
     - 3.57ms
     - 3.54ms
     - 341µs
     - 3.03ms
     - 4.40ms
     - 224
     - 1.21µs
     - 824k/s
   * - unique-shortcut points
     - 2.23ms
     - 2.21ms
     - 135µs
     - 2.06ms
     - 2.65ms
     - 406
     - 824ns
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
     - 3.55ms
     - 3.52ms
     - 291µs
     - 3.15ms
     - 4.37ms
     - 301
     - 1.26µs
     - 793k/s
   * - on-land points
     - 2.50ms
     - 2.48ms
     - 179µs
     - 2.27ms
     - 3.07ms
     - 424
     - 908ns
     - 1.10M/s
   * - random points
     - 2.48ms
     - 2.42ms
     - 368µs
     - 2.20ms
     - 8.60ms
     - 426
     - 882ns
     - 1.13M/s
   * - unique-shortcut points
     - 2.34ms
     - 2.24ms
     - 708µs
     - 2.05ms
     - 10.1ms
     - 387
     - 822ns
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
     - 2.03ms
     - 1.93ms
     - 441µs
     - 1.56ms
     - 4.24ms
     - 259
     - 622ns
     - 1.61M/s
   * - on-land points
     - 1.03ms
     - 970µs
     - 173µs
     - 896µs
     - 1.92ms
     - 490
     - 358ns
     - 2.79M/s
   * - random points
     - 885µs
     - 788µs
     - 193µs
     - 768µs
     - 1.57ms
     - 100
     - 307ns
     - 3.26M/s
   * - unique-shortcut points
     - 721µs
     - 694µs
     - 74.1µs
     - 662µs
     - 1.16ms
     - 943
     - 265ns
     - 3.77M/s




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
     - 29.5ms
     - 29.4ms
     - 1.22ms
     - 27.4ms
     - 32.0ms
     - 20
   * - timezonefinder, file-based
     - 146ms
     - 144ms
     - 6.48ms
     - 141ms
     - 167ms
     - 20
   * - timezonefinder, in-memory
     - 139ms
     - 138ms
     - 2.91ms
     - 134ms
     - 147ms
     - 20
   * - TimezoneFinderL
     - 130ms
     - 129ms
     - 2.88ms
     - 126ms
     - 136ms
     - 20
   * - tzfpy
     - 125ms
     - 125ms
     - 916µs
     - 123ms
     - 127ms
     - 20


Net of that baseline:

* **tzfpy**: 95.6ms to a first answer

* **TimezoneFinderL**: 98.2ms to a first answer

* **timezonefinder, in-memory**: 106ms to a first answer

* **timezonefinder, file-based**: 113ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
