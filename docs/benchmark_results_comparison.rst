

Comparison against tzfpy
========================


**~1.16µs per lookup here against ~406ns for tzfpy 1.3.3** - 2.85x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

*Measured on Linux x86_64, Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 2.8000 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 406ns
     - 1.16µs
     - 1.00µs
     - 2.85x slower
   * - on-land points
     - 463ns
     - 1.51µs
     - 1.13µs
     - 3.26x slower
   * - unique-shortcut points
     - 354ns
     - 945ns
     - 946ns
     - 2.67x slower
   * - ambiguous-shortcut points
     - 1.05µs
     - 5.67µs
     - 2.11µs
     - 5.40x slower




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
     - 14.4ms
     - 14.4ms
     - 113µs
     - 14.2ms
     - 14.9ms
     - 100
     - 5.67µs
     - 176k/s
   * - on-land points
     - 3.80ms
     - 3.80ms
     - 31.5µs
     - 3.77ms
     - 3.94ms
     - 100
     - 1.51µs
     - 663k/s
   * - random points
     - 3.06ms
     - 2.92ms
     - 417µs
     - 2.89ms
     - 5.43ms
     - 100
     - 1.16µs
     - 864k/s
   * - unique-shortcut points
     - 2.40ms
     - 2.40ms
     - 20.9µs
     - 2.36ms
     - 2.53ms
     - 100
     - 945ns
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
     - 5.31ms
     - 5.31ms
     - 34.6µs
     - 5.27ms
     - 5.50ms
     - 100
     - 2.11µs
     - 475k/s
   * - on-land points
     - 2.84ms
     - 2.83ms
     - 19.3µs
     - 2.82ms
     - 2.93ms
     - 100
     - 1.13µs
     - 886k/s
   * - random points
     - 2.53ms
     - 2.52ms
     - 30.6µs
     - 2.51ms
     - 2.66ms
     - 100
     - 1.00µs
     - 996k/s
   * - unique-shortcut points
     - 2.38ms
     - 2.37ms
     - 20.5µs
     - 2.36ms
     - 2.47ms
     - 100
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
     - 2.73ms
     - 2.68ms
     - 131µs
     - 2.63ms
     - 3.37ms
     - 100
     - 1.05µs
     - 952k/s
   * - on-land points
     - 1.22ms
     - 1.18ms
     - 84.5µs
     - 1.16ms
     - 1.43ms
     - 100
     - 463ns
     - 2.16M/s
   * - random points
     - 1.03ms
     - 1.03ms
     - 24.8µs
     - 1.02ms
     - 1.24ms
     - 100
     - 406ns
     - 2.46M/s
   * - unique-shortcut points
     - 918µs
     - 898µs
     - 66.6µs
     - 885µs
     - 1.26ms
     - 100
     - 354ns
     - 2.82M/s




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
     - 24.8ms
     - 24.5ms
     - 1.07ms
     - 23.8ms
     - 28.3ms
     - 20
   * - timezonefinder, file-based
     - 189ms
     - 189ms
     - 1.35ms
     - 187ms
     - 193ms
     - 20
   * - timezonefinder, in-memory
     - 192ms
     - 192ms
     - 1.71ms
     - 189ms
     - 194ms
     - 20
   * - TimezoneFinderL
     - 178ms
     - 177ms
     - 4.96ms
     - 173ms
     - 197ms
     - 20
   * - tzfpy
     - 173ms
     - 173ms
     - 2.43ms
     - 170ms
     - 180ms
     - 20


Net of that baseline:

* **tzfpy**: 147ms to a first answer

* **TimezoneFinderL**: 149ms to a first answer

* **timezonefinder, file-based**: 164ms to a first answer

* **timezonefinder, in-memory**: 165ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
