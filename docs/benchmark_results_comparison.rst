

Comparison against tzfpy
========================


**~1.43µs per lookup here against ~318ns for tzfpy 1.3.3** - 4.50x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

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
     - 318ns
     - 1.43µs
     - 996ns
     - 4.50x slower
   * - on-land points
     - 359ns
     - 1.87µs
     - 1.04µs
     - 5.22x slower
   * - unique-shortcut points
     - 277ns
     - 947ns
     - 949ns
     - 3.41x slower
   * - ambiguous-shortcut points
     - 631ns
     - 5.76µs
     - 1.41µs
     - 9.12x slower




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
     - 16.3ms
     - 16.0ms
     - 2.02ms
     - 14.4ms
     - 32.9ms
     - 100
     - 5.76µs
     - 174k/s
   * - on-land points
     - 5.24ms
     - 5.13ms
     - 1.27ms
     - 4.69ms
     - 17.3ms
     - 187
     - 1.87µs
     - 533k/s
   * - random points
     - 3.97ms
     - 3.96ms
     - 241µs
     - 3.58ms
     - 4.67ms
     - 170
     - 1.43µs
     - 698k/s
   * - unique-shortcut points
     - 2.53ms
     - 2.50ms
     - 128µs
     - 2.37ms
     - 3.09ms
     - 388
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
     - 3.69ms
     - 3.62ms
     - 153µs
     - 3.51ms
     - 4.13ms
     - 272
     - 1.41µs
     - 712k/s
   * - on-land points
     - 2.70ms
     - 2.67ms
     - 78.3µs
     - 2.59ms
     - 2.98ms
     - 324
     - 1.04µs
     - 964k/s
   * - random points
     - 2.65ms
     - 2.58ms
     - 158µs
     - 2.49ms
     - 3.26ms
     - 319
     - 996ns
     - 1.00M/s
   * - unique-shortcut points
     - 2.49ms
     - 2.45ms
     - 111µs
     - 2.37ms
     - 2.89ms
     - 343
     - 949ns
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
     - 1.81ms
     - 1.70ms
     - 284µs
     - 1.58ms
     - 3.16ms
     - 280
     - 631ns
     - 1.58M/s
   * - on-land points
     - 939µs
     - 911µs
     - 62.0µs
     - 898µs
     - 1.40ms
     - 560
     - 359ns
     - 2.78M/s
   * - random points
     - 837µs
     - 805µs
     - 79.2µs
     - 795µs
     - 1.16ms
     - 100
     - 318ns
     - 3.15M/s
   * - unique-shortcut points
     - 717µs
     - 700µs
     - 39.7µs
     - 694µs
     - 979µs
     - 900
     - 277ns
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
     - 30.5ms
     - 29.9ms
     - 2.48ms
     - 29.2ms
     - 40.8ms
     - 20
   * - timezonefinder, file-based
     - 135ms
     - 133ms
     - 8.65ms
     - 127ms
     - 169ms
     - 20
   * - timezonefinder, in-memory
     - 137ms
     - 137ms
     - 2.93ms
     - 133ms
     - 144ms
     - 20
   * - TimezoneFinderL
     - 123ms
     - 123ms
     - 1.70ms
     - 120ms
     - 128ms
     - 20
   * - tzfpy
     - 126ms
     - 125ms
     - 5.04ms
     - 123ms
     - 146ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 90.7ms to a first answer

* **tzfpy**: 93.4ms to a first answer

* **timezonefinder, file-based**: 97.9ms to a first answer

* **timezonefinder, in-memory**: 104ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
