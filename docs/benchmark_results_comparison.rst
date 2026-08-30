

Comparison against tzfpy
========================


**~1.43µs per lookup here against ~313ns for tzfpy 1.3.3** - 4.56x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

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
     - 1.43µs
     - 997ns
     - 4.56x slower
   * - on-land points
     - 359ns
     - 1.88µs
     - 1.04µs
     - 5.25x slower
   * - unique-shortcut points
     - 274ns
     - 947ns
     - 946ns
     - 3.45x slower
   * - ambiguous-shortcut points
     - 632ns
     - 5.72µs
     - 1.41µs
     - 9.05x slower




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
     - 15.8ms
     - 15.9ms
     - 589µs
     - 14.3ms
     - 17.1ms
     - 100
     - 5.72µs
     - 175k/s
   * - on-land points
     - 5.26ms
     - 5.13ms
     - 1.11ms
     - 4.71ms
     - 18.9ms
     - 184
     - 1.88µs
     - 531k/s
   * - random points
     - 3.93ms
     - 3.86ms
     - 285µs
     - 3.57ms
     - 5.10ms
     - 187
     - 1.43µs
     - 700k/s
   * - unique-shortcut points
     - 2.54ms
     - 2.46ms
     - 374µs
     - 2.37ms
     - 6.94ms
     - 372
     - 947ns
     - 1.06M/s




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
     - 3.79ms
     - 3.78ms
     - 166µs
     - 3.52ms
     - 4.24ms
     - 268
     - 1.41µs
     - 709k/s
   * - on-land points
     - 2.70ms
     - 2.68ms
     - 84.3µs
     - 2.60ms
     - 3.06ms
     - 357
     - 1.04µs
     - 963k/s
   * - random points
     - 2.69ms
     - 2.63ms
     - 177µs
     - 2.49ms
     - 3.31ms
     - 376
     - 997ns
     - 1.00M/s
   * - unique-shortcut points
     - 2.46ms
     - 2.43ms
     - 87.7µs
     - 2.36ms
     - 2.92ms
     - 403
     - 946ns
     - 1.06M/s




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
     - 1.80ms
     - 1.74ms
     - 251µs
     - 1.58ms
     - 3.06ms
     - 321
     - 632ns
     - 1.58M/s
   * - on-land points
     - 935µs
     - 909µs
     - 66.7µs
     - 896µs
     - 1.35ms
     - 570
     - 359ns
     - 2.79M/s
   * - random points
     - 838µs
     - 794µs
     - 81.1µs
     - 783µs
     - 1.14ms
     - 100
     - 313ns
     - 3.19M/s
   * - unique-shortcut points
     - 726µs
     - 699µs
     - 71.5µs
     - 685µs
     - 1.89ms
     - 837
     - 274ns
     - 3.65M/s




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
     - 30.5ms
     - 30.0ms
     - 2.56ms
     - 28.7ms
     - 40.8ms
     - 20
   * - timezonefinder, file-based
     - 139ms
     - 135ms
     - 15.6ms
     - 129ms
     - 200ms
     - 20
   * - timezonefinder, in-memory
     - 137ms
     - 137ms
     - 2.42ms
     - 130ms
     - 140ms
     - 20
   * - TimezoneFinderL
     - 123ms
     - 123ms
     - 2.14ms
     - 118ms
     - 127ms
     - 20
   * - tzfpy
     - 124ms
     - 124ms
     - 2.02ms
     - 121ms
     - 127ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 89.3ms to a first answer

* **tzfpy**: 92.2ms to a first answer

* **timezonefinder, file-based**: 100ms to a first answer

* **timezonefinder, in-memory**: 101ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
