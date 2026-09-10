

Comparison against tzfpy
========================


**~1.74µs per lookup here against ~419ns for tzfpy 1.3.3** - 4.16x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 2.4454 GHz, Python 3.13.15, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 419ns
     - 1.74µs
     - 1.43µs
     - 4.16x slower
   * - on-land points
     - 475ns
     - 2.15µs
     - 1.50µs
     - 4.52x slower
   * - unique-shortcut points
     - 343ns
     - 1.31µs
     - 1.32µs
     - 3.82x slower
   * - ambiguous-shortcut points
     - 903ns
     - 5.04µs
     - 2.17µs
     - 5.59x slower




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
     - 12.8ms
     - 12.7ms
     - 175µs
     - 12.6ms
     - 14.0ms
     - 100
     - 5.04µs
     - 198k/s
   * - on-land points
     - 5.54ms
     - 5.44ms
     - 211µs
     - 5.37ms
     - 6.32ms
     - 100
     - 2.15µs
     - 466k/s
   * - random points
     - 4.46ms
     - 4.43ms
     - 108µs
     - 4.36ms
     - 5.23ms
     - 100
     - 1.74µs
     - 573k/s
   * - unique-shortcut points
     - 3.33ms
     - 3.31ms
     - 51.0µs
     - 3.27ms
     - 3.69ms
     - 100
     - 1.31µs
     - 764k/s




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
     - 5.48ms
     - 5.46ms
     - 86.8µs
     - 5.42ms
     - 6.27ms
     - 100
     - 2.17µs
     - 461k/s
   * - on-land points
     - 3.81ms
     - 3.80ms
     - 54.5µs
     - 3.76ms
     - 4.15ms
     - 100
     - 1.50µs
     - 666k/s
   * - random points
     - 3.63ms
     - 3.64ms
     - 37.5µs
     - 3.56ms
     - 3.80ms
     - 100
     - 1.43µs
     - 701k/s
   * - unique-shortcut points
     - 3.33ms
     - 3.32ms
     - 35.7µs
     - 3.30ms
     - 3.45ms
     - 100
     - 1.32µs
     - 758k/s




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
     - 2.30ms
     - 2.28ms
     - 83.1µs
     - 2.26ms
     - 2.86ms
     - 100
     - 903ns
     - 1.11M/s
   * - on-land points
     - 1.20ms
     - 1.20ms
     - 17.5µs
     - 1.19ms
     - 1.31ms
     - 100
     - 475ns
     - 2.11M/s
   * - random points
     - 1.06ms
     - 1.06ms
     - 12.3µs
     - 1.05ms
     - 1.11ms
     - 100
     - 419ns
     - 2.39M/s
   * - unique-shortcut points
     - 876µs
     - 872µs
     - 11.6µs
     - 857µs
     - 933µs
     - 100
     - 343ns
     - 2.92M/s




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
     - 26.0ms
     - 26.0ms
     - 206µs
     - 25.7ms
     - 26.5ms
     - 20
   * - timezonefinder, file-based
     - 205ms
     - 204ms
     - 4.76ms
     - 201ms
     - 225ms
     - 20
   * - timezonefinder, in-memory
     - 199ms
     - 199ms
     - 2.40ms
     - 196ms
     - 208ms
     - 20
   * - TimezoneFinderL
     - 186ms
     - 186ms
     - 1.15ms
     - 184ms
     - 188ms
     - 20
   * - tzfpy
     - 180ms
     - 180ms
     - 2.57ms
     - 178ms
     - 188ms
     - 20


Net of that baseline:

* **tzfpy**: 152ms to a first answer

* **TimezoneFinderL**: 158ms to a first answer

* **timezonefinder, in-memory**: 171ms to a first answer

* **timezonefinder, file-based**: 176ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
