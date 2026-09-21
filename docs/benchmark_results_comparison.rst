

Comparison against tzfpy
========================


**~1.83µs per lookup here against ~439ns for tzfpy 1.3.3** - 4.17x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 2.8720 GHz, Python 3.13.15, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration tracks none of the rows on this page. This published table leads with ``Mean`` and belongs to the full on-demand suite, while the trend chart records the ``min`` estimator for the smaller ``benchmark_core`` subset.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.15 (CPython)

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


**Fixture Version**: 3

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
     - 439ns
     - 1.83µs
     - 1.53µs
     - 4.17x slower
   * - on-land points
     - 491ns
     - 2.22µs
     - 1.57µs
     - 4.53x slower
   * - unique-shortcut points
     - 356ns
     - 1.40µs
     - 1.42µs
     - 3.94x slower
   * - ambiguous-shortcut points
     - 947ns
     - 5.02µs
     - 2.25µs
     - 5.31x slower




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
     - 12.7ms
     - 12.7ms
     - 186µs
     - 12.6ms
     - 14.2ms
     - 100
     - 5.02µs
     - 199k/s
   * - on-land points
     - 5.62ms
     - 5.61ms
     - 43.6µs
     - 5.56ms
     - 5.85ms
     - 100
     - 2.22µs
     - 450k/s
   * - random points
     - 4.62ms
     - 4.62ms
     - 38.5µs
     - 4.58ms
     - 4.83ms
     - 100
     - 1.83µs
     - 546k/s
   * - unique-shortcut points
     - 3.53ms
     - 3.52ms
     - 23.8µs
     - 3.50ms
     - 3.68ms
     - 100
     - 1.40µs
     - 714k/s




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
     - 5.68ms
     - 5.68ms
     - 38.2µs
     - 5.62ms
     - 5.81ms
     - 100
     - 2.25µs
     - 445k/s
   * - on-land points
     - 3.96ms
     - 3.96ms
     - 25.6µs
     - 3.93ms
     - 4.05ms
     - 100
     - 1.57µs
     - 636k/s
   * - random points
     - 3.86ms
     - 3.85ms
     - 28.6µs
     - 3.83ms
     - 4.00ms
     - 100
     - 1.53µs
     - 653k/s
   * - unique-shortcut points
     - 3.58ms
     - 3.57ms
     - 25.9µs
     - 3.55ms
     - 3.69ms
     - 100
     - 1.42µs
     - 705k/s




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
     - 2.41ms
     - 2.41ms
     - 31.4µs
     - 2.37ms
     - 2.59ms
     - 100
     - 947ns
     - 1.06M/s
   * - on-land points
     - 1.26ms
     - 1.25ms
     - 22.4µs
     - 1.23ms
     - 1.35ms
     - 100
     - 491ns
     - 2.04M/s
   * - random points
     - 1.13ms
     - 1.12ms
     - 31.3µs
     - 1.10ms
     - 1.29ms
     - 100
     - 439ns
     - 2.28M/s
   * - unique-shortcut points
     - 914µs
     - 912µs
     - 13.4µs
     - 889µs
     - 972µs
     - 100
     - 356ns
     - 2.81M/s




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
     - 28.3ms
     - 28.4ms
     - 572µs
     - 27.4ms
     - 29.1ms
     - 20
   * - timezonefinder, file-based
     - 202ms
     - 202ms
     - 1.35ms
     - 200ms
     - 205ms
     - 20
   * - timezonefinder, in-memory
     - 197ms
     - 197ms
     - 2.40ms
     - 195ms
     - 206ms
     - 20
   * - TimezoneFinderL
     - 182ms
     - 181ms
     - 1.44ms
     - 180ms
     - 184ms
     - 20
   * - tzfpy
     - 195ms
     - 195ms
     - 1.49ms
     - 193ms
     - 200ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 153ms to a first answer

* **tzfpy**: 166ms to a first answer

* **timezonefinder, in-memory**: 168ms to a first answer

* **timezonefinder, file-based**: 173ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
