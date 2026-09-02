

Comparison against tzfpy
========================


**~1.18µs per lookup here against ~305ns for tzfpy 1.3.3** - 3.86x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

*Measured on Darwin arm64, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.



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
     - 305ns
     - 1.18µs
     - 832ns
     - 3.86x slower
   * - on-land points
     - 351ns
     - 1.52µs
     - 865ns
     - 4.33x slower
   * - unique-shortcut points
     - 266ns
     - 781ns
     - 782ns
     - 2.94x slower
   * - ambiguous-shortcut points
     - 622ns
     - 4.66µs
     - 1.24µs
     - 7.50x slower




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
     - 12.1ms
     - 11.9ms
     - 484µs
     - 11.7ms
     - 14.0ms
     - 100
     - 4.66µs
     - 215k/s
   * - on-land points
     - 3.95ms
     - 3.91ms
     - 170µs
     - 3.80ms
     - 5.24ms
     - 218
     - 1.52µs
     - 658k/s
   * - random points
     - 3.09ms
     - 3.04ms
     - 171µs
     - 2.94ms
     - 3.84ms
     - 278
     - 1.18µs
     - 850k/s
   * - unique-shortcut points
     - 2.02ms
     - 2.00ms
     - 63.6µs
     - 1.95ms
     - 2.45ms
     - 452
     - 781ns
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
     - 3.30ms
     - 3.21ms
     - 215µs
     - 3.10ms
     - 4.01ms
     - 295
     - 1.24µs
     - 806k/s
   * - on-land points
     - 2.24ms
     - 2.22ms
     - 74.0µs
     - 2.16ms
     - 2.71ms
     - 414
     - 865ns
     - 1.16M/s
   * - random points
     - 2.16ms
     - 2.14ms
     - 80.0µs
     - 2.08ms
     - 2.79ms
     - 426
     - 832ns
     - 1.20M/s
   * - unique-shortcut points
     - 2.12ms
     - 2.02ms
     - 475µs
     - 1.95ms
     - 7.99ms
     - 473
     - 782ns
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
     - 1.71ms
     - 1.62ms
     - 183µs
     - 1.55ms
     - 2.47ms
     - 260
     - 622ns
     - 1.61M/s
   * - on-land points
     - 920µs
     - 898µs
     - 66.2µs
     - 877µs
     - 1.43ms
     - 581
     - 351ns
     - 2.85M/s
   * - random points
     - 801µs
     - 782µs
     - 48.4µs
     - 763µs
     - 983µs
     - 100
     - 305ns
     - 3.28M/s
   * - unique-shortcut points
     - 694µs
     - 676µs
     - 47.7µs
     - 664µs
     - 1.17ms
     - 1011
     - 266ns
     - 3.76M/s




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
     - 27.2ms
     - 27.3ms
     - 659µs
     - 26.2ms
     - 28.8ms
     - 20
   * - timezonefinder, file-based
     - 136ms
     - 135ms
     - 4.13ms
     - 128ms
     - 145ms
     - 20
   * - timezonefinder, in-memory
     - 129ms
     - 127ms
     - 7.90ms
     - 123ms
     - 159ms
     - 20
   * - TimezoneFinderL
     - 119ms
     - 119ms
     - 3.84ms
     - 114ms
     - 125ms
     - 20
   * - tzfpy
     - 122ms
     - 121ms
     - 3.79ms
     - 118ms
     - 136ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 87.5ms to a first answer

* **tzfpy**: 92.0ms to a first answer

* **timezonefinder, in-memory**: 96.8ms to a first answer

* **timezonefinder, file-based**: 102ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
