

Speed and Startup against tzfpy
===============================


**~1.05µs per lookup here against ~333ns for tzfpy 1.3.3** - 3.14x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

**For bulk lookups, ``timezone_names_at()`` answers the same 2,500 points in one call at ~175ns per point** - 1.91x faster than a loop of tzfpy calls, which has no batch API. See *Bulk Lookups* below, and :doc:`benchmark_results_batch_break_even` for the batch size from which batching pays.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 3.6926 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

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


**Fixture Version**: 5

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
     - 333ns
     - 1.05µs
     - 945ns
     - 3.14x slower
   * - on-land points
     - 379ns
     - 1.28µs
     - 1.02µs
     - 3.39x slower
   * - unique-shortcut points
     - 299ns
     - 924ns
     - 906ns
     - 3.09x slower
   * - ambiguous-shortcut points
     - 878ns
     - 4.54µs
     - 1.81µs
     - 5.17x slower




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
     - 333ns
     - 175ns
     - 1.91x faster
   * - on-land points
     - 379ns
     - 365ns
     - 1.04x faster
   * - unique-shortcut points
     - 299ns
     - 29.8ns
     - 10.0x faster
   * - ambiguous-shortcut points
     - 878ns
     - 3.26µs
     - 3.71x slower




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
     - 11.5ms
     - 11.5ms
     - 172µs
     - 11.3ms
     - 12.7ms
     - 100
     - 4.54µs
     - 220k/s
   * - on-land points
     - 3.29ms
     - 3.26ms
     - 107µs
     - 3.21ms
     - 3.81ms
     - 100
     - 1.28µs
     - 780k/s
   * - random points
     - 2.72ms
     - 2.66ms
     - 157µs
     - 2.62ms
     - 3.50ms
     - 100
     - 1.05µs
     - 954k/s
   * - unique-shortcut points
     - 2.37ms
     - 2.34ms
     - 77.4µs
     - 2.31ms
     - 2.65ms
     - 100
     - 924ns
     - 1.08M/s




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
     - 8.49ms
     - 8.30ms
     - 768µs
     - 8.14ms
     - 13.7ms
     - 100
     - 3.26µs
     - 307k/s
   * - on-land points
     - 935µs
     - 934µs
     - 13.0µs
     - 912µs
     - 999µs
     - 100
     - 365ns
     - 2.74M/s
   * - random points
     - 455µs
     - 454µs
     - 11.4µs
     - 437µs
     - 501µs
     - 100
     - 175ns
     - 5.72M/s
   * - unique-shortcut points
     - 77.7µs
     - 76.2µs
     - 4.62µs
     - 74.5µs
     - 110µs
     - 100
     - 29.8ns
     - 33.6M/s




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
     - 4.62ms
     - 4.59ms
     - 110µs
     - 4.53ms
     - 5.03ms
     - 100
     - 1.81µs
     - 552k/s
   * - on-land points
     - 2.59ms
     - 2.59ms
     - 18.1µs
     - 2.55ms
     - 2.66ms
     - 100
     - 1.02µs
     - 979k/s
   * - random points
     - 2.41ms
     - 2.41ms
     - 23.8µs
     - 2.36ms
     - 2.51ms
     - 100
     - 945ns
     - 1.06M/s
   * - unique-shortcut points
     - 2.29ms
     - 2.29ms
     - 22.8µs
     - 2.27ms
     - 2.46ms
     - 100
     - 906ns
     - 1.10M/s




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
     - 2.27ms
     - 2.26ms
     - 58.8µs
     - 2.19ms
     - 2.48ms
     - 100
     - 878ns
     - 1.14M/s
   * - on-land points
     - 972µs
     - 965µs
     - 22.6µs
     - 946µs
     - 1.08ms
     - 100
     - 379ns
     - 2.64M/s
   * - random points
     - 859µs
     - 853µs
     - 17.2µs
     - 833µs
     - 934µs
     - 100
     - 333ns
     - 3.00M/s
   * - unique-shortcut points
     - 770µs
     - 766µs
     - 16.2µs
     - 747µs
     - 823µs
     - 100
     - 299ns
     - 3.35M/s




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
     - 21.7ms
     - 21.8ms
     - 455µs
     - 21.0ms
     - 22.7ms
     - 20
   * - timezonefinder, file-based
     - 155ms
     - 155ms
     - 1.87ms
     - 152ms
     - 161ms
     - 20
   * - timezonefinder, in-memory
     - 148ms
     - 148ms
     - 1.66ms
     - 145ms
     - 152ms
     - 20
   * - TimezoneFinderL
     - 135ms
     - 136ms
     - 1.58ms
     - 133ms
     - 140ms
     - 20
   * - tzfpy
     - 151ms
     - 151ms
     - 1.14ms
     - 150ms
     - 154ms
     - 20


Net of that baseline:

* **TimezoneFinderL**: 112ms to a first answer

* **timezonefinder, in-memory**: 124ms to a first answer

* **tzfpy**: 129ms to a first answer

* **timezonefinder, file-based**: 131ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** The two packages disagree on a small fraction of points, and a disagreement count on its own says nothing about which answer is right - settling that needs ground truth, which neither package carries. :doc:`alternatives` states the design difference instead of scoring it.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
