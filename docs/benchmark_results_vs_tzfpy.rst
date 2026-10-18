

Speed and Startup against tzfpy
===============================


**~1.30µs per lookup here against ~421ns for tzfpy 1.3.3** - 3.09x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

**For bulk lookups, ``timezone_names_at()`` answers the same 2,500 points in one call at ~264ns per point** - 1.60x faster than a loop of tzfpy calls, which has no batch API. See *Bulk Lookups* below, and :doc:`benchmark_results_batch_break_even` for the batch size from which batching pays.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2440 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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

**Timezone Data Version**: 2026e



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
     - 421ns
     - 1.30µs
     - 1.09µs
     - 3.09x slower
   * - on-land points
     - 475ns
     - 1.68µs
     - 1.22µs
     - 3.53x slower
   * - unique-shortcut points
     - 371ns
     - 1.03µs
     - 1.03µs
     - 2.78x slower
   * - ambiguous-shortcut points
     - 1.07µs
     - 5.68µs
     - 2.18µs
     - 5.32x slower




Bulk Lookups
~~~~~~~~~~~~


The same 2,500 points, answered by one ``timezone_names_at()`` call per pass instead of a ``timezone_at()`` loop - this package's API for answering many points at once. tzfpy has no batch API (its ``get_tzs()`` returns every zone at a single point), so its column is the same ``get_tz()`` loop as above. The coordinates are passed as ready ``float64`` arrays; converting Python lists costs extra. Batching pays only above a few dozen points per call and depends on the batch size: :doc:`benchmark_results_batch_break_even`.


.. list-table::
   :header-rows: 1
   :widths: 22 12 51 15

   * - Query points
     - tzfpy.get_tz()
     - TimezoneFinder.timezone_names_at() (in-memory), per point
     - vs tzfpy.get_tz()
   * - random points
     - 421ns
     - 264ns
     - 1.60x faster
   * - on-land points
     - 475ns
     - 562ns
     - 1.18x slower
   * - unique-shortcut points
     - 371ns
     - 42.8ns
     - 8.67x faster
   * - ambiguous-shortcut points
     - 1.07µs
     - 4.17µs
     - 3.91x slower




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
     - 14.5ms
     - 14.4ms
     - 267µs
     - 14.2ms
     - 15.9ms
     - 100
     - 5.68µs
     - 176k/s
   * - on-land points
     - 4.25ms
     - 4.25ms
     - 26.9µs
     - 4.20ms
     - 4.37ms
     - 100
     - 1.68µs
     - 596k/s
   * - random points
     - 3.30ms
     - 3.29ms
     - 42.5µs
     - 3.26ms
     - 3.59ms
     - 100
     - 1.30µs
     - 767k/s
   * - unique-shortcut points
     - 2.63ms
     - 2.63ms
     - 22.0µs
     - 2.57ms
     - 2.75ms
     - 100
     - 1.03µs
     - 971k/s




TimezoneFinder.timezone_names_at() (in-memory)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



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
     - 10.6ms
     - 10.6ms
     - 107µs
     - 10.4ms
     - 11.0ms
     - 100
     - 4.17µs
     - 240k/s
   * - on-land points
     - 1.44ms
     - 1.43ms
     - 31.2µs
     - 1.41ms
     - 1.58ms
     - 100
     - 562ns
     - 1.78M/s
   * - random points
     - 689µs
     - 687µs
     - 18.9µs
     - 660µs
     - 781µs
     - 100
     - 264ns
     - 3.79M/s
   * - unique-shortcut points
     - 113µs
     - 110µs
     - 6.84µs
     - 107µs
     - 134µs
     - 100
     - 42.8ns
     - 23.4M/s




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
     - 5.52ms
     - 5.49ms
     - 271µs
     - 5.45ms
     - 8.19ms
     - 100
     - 2.18µs
     - 459k/s
   * - on-land points
     - 3.13ms
     - 3.13ms
     - 27.5µs
     - 3.06ms
     - 3.24ms
     - 100
     - 1.22µs
     - 817k/s
   * - random points
     - 2.77ms
     - 2.76ms
     - 27.6µs
     - 2.73ms
     - 2.89ms
     - 100
     - 1.09µs
     - 915k/s
   * - unique-shortcut points
     - 2.63ms
     - 2.63ms
     - 19.9µs
     - 2.58ms
     - 2.71ms
     - 100
     - 1.03µs
     - 971k/s




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
     - 2.70ms
     - 111µs
     - 2.67ms
     - 3.54ms
     - 100
     - 1.07µs
     - 937k/s
   * - on-land points
     - 1.20ms
     - 1.20ms
     - 14.4µs
     - 1.19ms
     - 1.29ms
     - 100
     - 475ns
     - 2.11M/s
   * - random points
     - 1.07ms
     - 1.06ms
     - 14.2µs
     - 1.05ms
     - 1.14ms
     - 100
     - 421ns
     - 2.37M/s
   * - unique-shortcut points
     - 947µs
     - 942µs
     - 12.8µs
     - 928µs
     - 1.02ms
     - 100
     - 371ns
     - 2.70M/s




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
     - 26.8ms
     - 26.4ms
     - 927µs
     - 26.2ms
     - 30.0ms
     - 20
   * - timezonefinder, file-based
     - 196ms
     - 196ms
     - 1.06ms
     - 194ms
     - 198ms
     - 20
   * - timezonefinder, in-memory
     - 192ms
     - 191ms
     - 2.84ms
     - 188ms
     - 198ms
     - 20
   * - TimezoneFinderL
     - 182ms
     - 182ms
     - 3.97ms
     - 176ms
     - 192ms
     - 20
   * - tzfpy
     - 181ms
     - 181ms
     - 1.32ms
     - 180ms
     - 185ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 150ms to a first answer

* **tzfpy**: 153ms to a first answer

* **timezonefinder, in-memory**: 162ms to a first answer

* **timezonefinder, file-based**: 168ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
