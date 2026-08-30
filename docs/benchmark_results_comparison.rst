

Comparison against tzfpy
========================


**~1.44µs per lookup here against ~320ns for tzfpy 1.3.3** - 4.50x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

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
     - 1000ns
     - 4.50x slower
   * - on-land points
     - 362ns
     - 1.89µs
     - 1.04µs
     - 5.22x slower
   * - unique-shortcut points
     - 275ns
     - 951ns
     - 952ns
     - 3.46x slower
   * - ambiguous-shortcut points
     - 639ns
     - 6.00µs
     - 1.43µs
     - 9.39x slower




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
     - 16.5ms
     - 16.5ms
     - 574µs
     - 15.0ms
     - 17.7ms
     - 100
     - 6.00µs
     - 167k/s
   * - on-land points
     - 5.45ms
     - 5.48ms
     - 371µs
     - 4.72ms
     - 6.33ms
     - 176
     - 1.89µs
     - 530k/s
   * - random points
     - 4.15ms
     - 4.13ms
     - 307µs
     - 3.60ms
     - 4.99ms
     - 191
     - 1.44µs
     - 694k/s
   * - unique-shortcut points
     - 2.64ms
     - 2.62ms
     - 165µs
     - 2.38ms
     - 3.26ms
     - 373
     - 951ns
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
     - 4.06ms
     - 4.00ms
     - 299µs
     - 3.57ms
     - 5.55ms
     - 261
     - 1.43µs
     - 700k/s
   * - on-land points
     - 3.01ms
     - 2.86ms
     - 1.19ms
     - 2.60ms
     - 17.4ms
     - 326
     - 1.04µs
     - 961k/s
   * - random points
     - 2.84ms
     - 2.80ms
     - 208µs
     - 2.50ms
     - 3.50ms
     - 362
     - 1000ns
     - 1.00M/s
   * - unique-shortcut points
     - 2.76ms
     - 2.73ms
     - 234µs
     - 2.38ms
     - 3.81ms
     - 387
     - 952ns
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
     - 2.31ms
     - 2.27ms
     - 523µs
     - 1.60ms
     - 4.18ms
     - 262
     - 639ns
     - 1.57M/s
   * - on-land points
     - 1.17ms
     - 1.08ms
     - 261µs
     - 904µs
     - 2.33ms
     - 560
     - 362ns
     - 2.76M/s
   * - random points
     - 1.07ms
     - 967µs
     - 290µs
     - 801µs
     - 2.29ms
     - 100
     - 320ns
     - 3.12M/s
   * - unique-shortcut points
     - 801µs
     - 734µs
     - 137µs
     - 687µs
     - 1.56ms
     - 978
     - 275ns
     - 3.64M/s




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
     - 2.25ms
     - 32.6ms
     - 41.7ms
     - 20
   * - timezonefinder, file-based
     - 150ms
     - 146ms
     - 16.5ms
     - 142ms
     - 214ms
     - 20
   * - timezonefinder, in-memory
     - 148ms
     - 148ms
     - 2.48ms
     - 142ms
     - 153ms
     - 20
   * - TimezoneFinderL
     - 136ms
     - 136ms
     - 3.41ms
     - 130ms
     - 144ms
     - 20
   * - tzfpy
     - 136ms
     - 136ms
     - 2.66ms
     - 133ms
     - 143ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 97.8ms to a first answer

* **tzfpy**: 101ms to a first answer

* **timezonefinder, file-based**: 109ms to a first answer

* **timezonefinder, in-memory**: 109ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
