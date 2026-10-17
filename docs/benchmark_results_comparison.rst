

Comparison against tzfpy
========================


**~1.16µs per lookup here against ~403ns for tzfpy 1.3.3** - 2.88x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

*Measured on Linux x86_64, Intel(R) Xeon(R) Platinum 8370C CPU @ 2.7929 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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
     - 403ns
     - 1.16µs
     - 1.01µs
     - 2.88x slower
   * - on-land points
     - 464ns
     - 1.52µs
     - 1.13µs
     - 3.27x slower
   * - unique-shortcut points
     - 353ns
     - 953ns
     - 954ns
     - 2.70x slower
   * - ambiguous-shortcut points
     - 1.06µs
     - 5.39µs
     - 2.11µs
     - 5.08x slower




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
     - 14.3ms
     - 13.8ms
     - 1.46ms
     - 13.5ms
     - 21.1ms
     - 100
     - 5.39µs
     - 185k/s
   * - on-land points
     - 3.91ms
     - 3.89ms
     - 52.8µs
     - 3.80ms
     - 4.14ms
     - 100
     - 1.52µs
     - 658k/s
   * - random points
     - 2.93ms
     - 2.92ms
     - 40.5µs
     - 2.90ms
     - 3.15ms
     - 100
     - 1.16µs
     - 862k/s
   * - unique-shortcut points
     - 2.43ms
     - 2.42ms
     - 28.8µs
     - 2.38ms
     - 2.67ms
     - 100
     - 953ns
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
     - 5.33ms
     - 5.30ms
     - 121µs
     - 5.27ms
     - 6.20ms
     - 100
     - 2.11µs
     - 474k/s
   * - on-land points
     - 2.85ms
     - 2.84ms
     - 26.3µs
     - 2.83ms
     - 3.03ms
     - 100
     - 1.13µs
     - 884k/s
   * - random points
     - 2.57ms
     - 2.54ms
     - 101µs
     - 2.53ms
     - 3.37ms
     - 100
     - 1.01µs
     - 987k/s
   * - unique-shortcut points
     - 2.40ms
     - 2.39ms
     - 17.4µs
     - 2.39ms
     - 2.48ms
     - 100
     - 954ns
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
     - 2.69ms
     - 2.68ms
     - 56.2µs
     - 2.65ms
     - 3.21ms
     - 100
     - 1.06µs
     - 942k/s
   * - on-land points
     - 1.18ms
     - 1.18ms
     - 27.6µs
     - 1.16ms
     - 1.43ms
     - 100
     - 464ns
     - 2.15M/s
   * - random points
     - 1.02ms
     - 1.02ms
     - 24.1µs
     - 1.01ms
     - 1.23ms
     - 100
     - 403ns
     - 2.48M/s
   * - unique-shortcut points
     - 897µs
     - 892µs
     - 22.6µs
     - 881µs
     - 1.09ms
     - 100
     - 353ns
     - 2.84M/s




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
     - 23.3ms
     - 23.2ms
     - 447µs
     - 22.8ms
     - 25.0ms
     - 20
   * - timezonefinder, file-based
     - 184ms
     - 184ms
     - 2.09ms
     - 182ms
     - 192ms
     - 20
   * - timezonefinder, in-memory
     - 186ms
     - 186ms
     - 1.09ms
     - 184ms
     - 188ms
     - 20
   * - TimezoneFinderL
     - 171ms
     - 171ms
     - 1.39ms
     - 169ms
     - 174ms
     - 20
   * - tzfpy
     - 169ms
     - 169ms
     - 1.22ms
     - 168ms
     - 173ms
     - 20


Net of that baseline:

* **tzfpy**: 145ms to a first answer

* **TimezoneFinderL**: 146ms to a first answer

* **timezonefinder, file-based**: 159ms to a first answer

* **timezonefinder, in-memory**: 161ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
