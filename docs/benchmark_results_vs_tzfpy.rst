

Speed and Startup against tzfpy
===============================


**~758ns per lookup here against ~279ns for tzfpy 2.1.2** - 2.72x slower, over uniformly random query points answered by both packages in the same process on the same machine. That gap is what full-resolution boundary polygons cost; :doc:`alternatives` is where the trade is argued rather than measured.

**For bulk lookups, ``timezone_names_at()`` answers the same 2,500 points in one call at ~141ns per point** - 1.97x faster than a loop of tzfpy calls, which has no batch API. See *Bulk Lookups* below, and :doc:`benchmark_results_batch_break_even` for the batch size from which batching pays.

*Measured on Linux x86_64, Intel(R) Xeon(R) 6975P-C @ 3.8763 GHz, Python 3.13.18, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.

Continuous integration tracks none of the rows on this page. This published table leads with ``Mean`` and belongs to the full on-demand suite, while the trend chart records the ``min`` estimator for the smaller ``benchmark_core`` subset.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.18 (CPython)

**NumPy Version**: 2.5.2

**Platform**: Linux x86_64



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

**Timezone Data Version**: 2026f



Benchmark Configuration
~~~~~~~~~~~~~~~~~~~~~~~


**Benchmark Source**: pytest-benchmark

**Batch Size**: 2,500

**Tzfpy Version**: 2.1.2

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
     - 279ns
     - 758ns
     - 652ns
     - 2.72x slower
   * - on-land points
     - 335ns
     - 958ns
     - 719ns
     - 2.86x slower
   * - unique-shortcut points
     - 251ns
     - 625ns
     - 625ns
     - 2.48x slower
   * - ambiguous-shortcut points
     - 930ns
     - 3.67µs
     - 1.31µs
     - 3.95x slower




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
     - 279ns
     - 141ns
     - 1.97x faster
   * - on-land points
     - 335ns
     - 308ns
     - 1.09x faster
   * - unique-shortcut points
     - 251ns
     - 23.1ns
     - 10.9x faster
   * - ambiguous-shortcut points
     - 930ns
     - 2.90µs
     - 3.12x slower




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
     - 9.29ms
     - 9.28ms
     - 59.8µs
     - 9.18ms
     - 9.68ms
     - 100
     - 3.67µs
     - 272k/s
   * - on-land points
     - 2.48ms
     - 2.48ms
     - 24.7µs
     - 2.39ms
     - 2.60ms
     - 100
     - 958ns
     - 1.04M/s
   * - random points
     - 1.92ms
     - 1.92ms
     - 13.7µs
     - 1.90ms
     - 1.98ms
     - 100
     - 758ns
     - 1.32M/s
   * - unique-shortcut points
     - 1.59ms
     - 1.59ms
     - 13.0µs
     - 1.56ms
     - 1.63ms
     - 100
     - 625ns
     - 1.60M/s




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
     - 7.35ms
     - 7.34ms
     - 43.8µs
     - 7.26ms
     - 7.54ms
     - 100
     - 2.90µs
     - 345k/s
   * - on-land points
     - 806µs
     - 803µs
     - 18.0µs
     - 771µs
     - 892µs
     - 100
     - 308ns
     - 3.24M/s
   * - random points
     - 373µs
     - 373µs
     - 10.8µs
     - 353µs
     - 423µs
     - 100
     - 141ns
     - 7.08M/s
   * - unique-shortcut points
     - 61.0µs
     - 58.8µs
     - 4.58µs
     - 57.7µs
     - 82.0µs
     - 100
     - 23.1ns
     - 43.4M/s




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
     - 3.33ms
     - 3.32ms
     - 77.0µs
     - 3.28ms
     - 4.00ms
     - 100
     - 1.31µs
     - 763k/s
   * - on-land points
     - 1.84ms
     - 1.84ms
     - 21.2µs
     - 1.80ms
     - 1.93ms
     - 100
     - 719ns
     - 1.39M/s
   * - random points
     - 1.65ms
     - 1.65ms
     - 13.1µs
     - 1.63ms
     - 1.72ms
     - 100
     - 652ns
     - 1.53M/s
   * - unique-shortcut points
     - 1.59ms
     - 1.58ms
     - 21.9µs
     - 1.56ms
     - 1.69ms
     - 100
     - 625ns
     - 1.60M/s




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
     - 2.36ms
     - 2.35ms
     - 38.2µs
     - 2.33ms
     - 2.70ms
     - 100
     - 930ns
     - 1.07M/s
   * - on-land points
     - 868µs
     - 867µs
     - 14.0µs
     - 838µs
     - 960µs
     - 100
     - 335ns
     - 2.98M/s
   * - random points
     - 732µs
     - 721µs
     - 43.1µs
     - 697µs
     - 983µs
     - 100
     - 279ns
     - 3.59M/s
   * - unique-shortcut points
     - 644µs
     - 644µs
     - 10.6µs
     - 629µs
     - 702µs
     - 100
     - 251ns
     - 3.98M/s




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
     - 17.8ms
     - 17.7ms
     - 383µs
     - 17.5ms
     - 19.2ms
     - 20
   * - timezonefinder, file-based
     - 127ms
     - 126ms
     - 2.14ms
     - 125ms
     - 135ms
     - 20
   * - timezonefinder, in-memory
     - 134ms
     - 133ms
     - 2.58ms
     - 131ms
     - 141ms
     - 20
   * - TimezoneFinderL
     - 117ms
     - 116ms
     - 2.63ms
     - 116ms
     - 127ms
     - 20
   * - tzfpy
     - 58.9ms
     - 58.6ms
     - 948µs
     - 57.4ms
     - 61.7ms
     - 20


Net of that baseline:

* **tzfpy**: 39.9ms to a first answer

* **TimezoneFinderL**: 98.2ms to a first answer

* **timezonefinder, file-based**: 108ms to a first answer

* **timezonefinder, in-memory**: 113ms to a first answer



What This Page Does Not Measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


* **Accuracy.** This page times the two packages, not their answers. On uniformly drawn points they agree; near a border they differ, because tzfpy's simplified polygons move it, and :doc:`border_accuracy_vs_tzfpy` measures how often by distance from the border.

* **Memory footprint and distribution size.** :doc:`benchmark_results_memory` measures this package only: the harness behind it (``scripts/measure_memory.py``) constructs finders from this repository and has no tzfpy configuration.

* **Any other machine.** One CPU, one Python build, one acceleration path, all named above. The *ratio* survives a change of machine far better than the absolute numbers do, but neither is a promise - see :doc:`benchmarking_methodology`.
