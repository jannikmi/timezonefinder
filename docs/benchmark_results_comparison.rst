

Comparison against tzfpy
========================


**~1.30µs per lookup here against ~418ns for tzfpy 1.3.3** - 3.11x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2420 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 418ns
     - 1.30µs
     - 1.11µs
     - 3.11x slower
   * - on-land points
     - 473ns
     - 1.67µs
     - 1.21µs
     - 3.54x slower
   * - unique-shortcut points
     - 368ns
     - 1.03µs
     - 1.06µs
     - 2.81x slower
   * - ambiguous-shortcut points
     - 1.06µs
     - 5.74µs
     - 2.22µs
     - 5.41x slower




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
     - 14.8ms
     - 14.8ms
     - 245µs
     - 14.4ms
     - 16.0ms
     - 100
     - 5.74µs
     - 174k/s
   * - on-land points
     - 4.29ms
     - 4.27ms
     - 116µs
     - 4.18ms
     - 5.25ms
     - 100
     - 1.67µs
     - 598k/s
   * - random points
     - 3.37ms
     - 3.30ms
     - 340µs
     - 3.25ms
     - 6.29ms
     - 100
     - 1.30µs
     - 769k/s
   * - unique-shortcut points
     - 2.63ms
     - 2.62ms
     - 36.0µs
     - 2.58ms
     - 2.85ms
     - 100
     - 1.03µs
     - 967k/s




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
     - 5.62ms
     - 5.60ms
     - 45.8µs
     - 5.56ms
     - 5.88ms
     - 100
     - 2.22µs
     - 450k/s
   * - on-land points
     - 3.20ms
     - 3.09ms
     - 440µs
     - 3.02ms
     - 5.74ms
     - 100
     - 1.21µs
     - 827k/s
   * - random points
     - 2.79ms
     - 2.78ms
     - 38.6µs
     - 2.76ms
     - 3.02ms
     - 100
     - 1.11µs
     - 905k/s
   * - unique-shortcut points
     - 2.66ms
     - 2.65ms
     - 25.2µs
     - 2.64ms
     - 2.78ms
     - 100
     - 1.06µs
     - 947k/s




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
     - 2.71ms
     - 2.69ms
     - 79.1µs
     - 2.65ms
     - 3.28ms
     - 100
     - 1.06µs
     - 942k/s
   * - on-land points
     - 1.20ms
     - 1.19ms
     - 21.3µs
     - 1.18ms
     - 1.32ms
     - 100
     - 473ns
     - 2.11M/s
   * - random points
     - 1.06ms
     - 1.05ms
     - 17.3µs
     - 1.04ms
     - 1.18ms
     - 100
     - 418ns
     - 2.39M/s
   * - unique-shortcut points
     - 938µs
     - 934µs
     - 13.2µs
     - 921µs
     - 1.03ms
     - 100
     - 368ns
     - 2.71M/s




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
     - 26.1ms
     - 26.0ms
     - 388µs
     - 25.7ms
     - 27.5ms
     - 20
   * - timezonefinder, file-based
     - 214ms
     - 196ms
     - 65.9ms
     - 191ms
     - 490ms
     - 20
   * - timezonefinder, in-memory
     - 189ms
     - 189ms
     - 1.69ms
     - 186ms
     - 193ms
     - 20
   * - TimezoneFinderL
     - 177ms
     - 177ms
     - 2.09ms
     - 174ms
     - 182ms
     - 20
   * - tzfpy
     - 180ms
     - 180ms
     - 1.30ms
     - 178ms
     - 182ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 148ms to a first answer

* **tzfpy**: 152ms to a first answer

* **timezonefinder, in-memory**: 161ms to a first answer

* **timezonefinder, file-based**: 166ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
