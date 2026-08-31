

Comparison against tzfpy
========================


**~1.31µs per lookup here against ~314ns for tzfpy 1.3.3** - 4.16x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

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
     - 314ns
     - 1.31µs
     - 883ns
     - 4.16x slower
   * - on-land points
     - 353ns
     - 1.76µs
     - 917ns
     - 4.98x slower
   * - unique-shortcut points
     - 273ns
     - 840ns
     - 824ns
     - 3.08x slower
   * - ambiguous-shortcut points
     - 627ns
     - 5.75µs
     - 1.29µs
     - 9.17x slower




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
     - 15.8ms
     - 578µs
     - 14.4ms
     - 17.5ms
     - 100
     - 5.75µs
     - 174k/s
   * - on-land points
     - 5.32ms
     - 5.21ms
     - 1.17ms
     - 4.39ms
     - 17.4ms
     - 202
     - 1.76µs
     - 569k/s
   * - random points
     - 3.86ms
     - 3.88ms
     - 329µs
     - 3.27ms
     - 4.60ms
     - 173
     - 1.31µs
     - 765k/s
   * - unique-shortcut points
     - 2.33ms
     - 2.30ms
     - 168µs
     - 2.10ms
     - 3.12ms
     - 437
     - 840ns
     - 1.19M/s




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
     - 3.74ms
     - 3.73ms
     - 308µs
     - 3.23ms
     - 4.50ms
     - 293
     - 1.29µs
     - 774k/s
   * - on-land points
     - 2.63ms
     - 2.61ms
     - 198µs
     - 2.29ms
     - 3.19ms
     - 390
     - 917ns
     - 1.09M/s
   * - random points
     - 2.59ms
     - 2.60ms
     - 220µs
     - 2.21ms
     - 3.40ms
     - 383
     - 883ns
     - 1.13M/s
   * - unique-shortcut points
     - 2.28ms
     - 2.24ms
     - 155µs
     - 2.06ms
     - 2.73ms
     - 420
     - 824ns
     - 1.21M/s




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
     - 2.06ms
     - 1.76ms
     - 563µs
     - 1.57ms
     - 3.70ms
     - 262
     - 627ns
     - 1.59M/s
   * - on-land points
     - 1.02ms
     - 931µs
     - 203µs
     - 882µs
     - 1.88ms
     - 508
     - 353ns
     - 2.84M/s
   * - random points
     - 927µs
     - 897µs
     - 155µs
     - 785µs
     - 1.51ms
     - 100
     - 314ns
     - 3.19M/s
   * - unique-shortcut points
     - 760µs
     - 719µs
     - 105µs
     - 683µs
     - 1.36ms
     - 688
     - 273ns
     - 3.66M/s




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
     - 30.4ms
     - 29.9ms
     - 2.97ms
     - 27.7ms
     - 42.2ms
     - 20
   * - timezonefinder, file-based
     - 151ms
     - 150ms
     - 9.38ms
     - 141ms
     - 187ms
     - 20
   * - timezonefinder, in-memory
     - 149ms
     - 149ms
     - 1.94ms
     - 147ms
     - 154ms
     - 20
   * - TimezoneFinderL
     - 160ms
     - 152ms
     - 26.3ms
     - 131ms
     - 242ms
     - 20
   * - tzfpy
     - 128ms
     - 127ms
     - 4.54ms
     - 124ms
     - 146ms
     - 20


Net of that baseline:

* **tzfpy**: 96.5ms to a first answer

* **TimezoneFinderL**: 103ms to a first answer

* **timezonefinder, file-based**: 113ms to a first answer

* **timezonefinder, in-memory**: 119ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
