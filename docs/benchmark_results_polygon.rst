

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~641ns per check on a small polygon, ~1.49µs on the largest** (2.33x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check without that index is ~22.6µs on the largest polygon (15.1x the block-filtered cost) - which is what the stratification below is for, and what the latitude block index removed.

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

**Polygon Strata**: small / medium / large (by vertex count percentile)

Each benchmark times one pass over 2,500 fixed, committed (point, polygon) pairs drawn from a single polygon-size stratum, so the cost of the largest polygons isn't hidden behind an unweighted average. Mean/Median/StdDev/Min/Max are for the full 2,500-pair batch; Throughput is queries/second for that batch.

.. note::

   The point and the polygon in each pair are drawn independently, so many pairs put the point nowhere near the polygon. That does not matter for the bare kernel, which scans the whole ring either way, but it means a share of the block-filtered checks are rejections rather than scans - cheapest on the small stratum, where a rejection is most of what is left. A real lookup reaches this stage only after a bounding-box check has passed, so read the block-filtered figures as a floor and :doc:`benchmark_results_timezonefinding` for what a query actually pays.



Results
~~~~~~~




bare kernel (C/clang)
^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 24 10 10 10 10 10 10 16

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Throughput
   * - large polygons
     - 56.5ms
     - 56.5ms
     - 489µs
     - 55.6ms
     - 57.3ms
     - 18
     - 44.2k/s
   * - medium polygons
     - 6.02ms
     - 6.00ms
     - 270µs
     - 5.60ms
     - 6.69ms
     - 145
     - 416k/s
   * - small polygons
     - 2.50ms
     - 2.46ms
     - 135µs
     - 2.34ms
     - 2.88ms
     - 378
     - 998k/s




block-filtered kernel (C/clang)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 24 10 10 10 10 10 10 16

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Throughput
   * - large polygons
     - 3.74ms
     - 3.72ms
     - 96.5µs
     - 3.65ms
     - 4.57ms
     - 259
     - 669k/s
   * - medium polygons
     - 3.14ms
     - 3.10ms
     - 132µs
     - 3.02ms
     - 3.87ms
     - 317
     - 796k/s
   * - small polygons
     - 3.03ms
     - 2.97ms
     - 141µs
     - 2.90ms
     - 3.53ms
     - 331
     - 825k/s




bare kernel (Python, Numba if available)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 24 10 10 10 10 10 10 16

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Throughput
   * - large polygons
     - 14.1s
     - 14.1s
     - 126ms
     - 14.0s
     - 14.3s
     - 5
     - 177/s
   * - medium polygons
     - 916ms
     - 916ms
     - 1.99ms
     - 914ms
     - 919ms
     - 5
     - 2.73k/s
   * - small polygons
     - 35.1ms
     - 35.1ms
     - 741µs
     - 33.6ms
     - 36.7ms
     - 29
     - 71.3k/s




block-filtered kernel (Python, Numba if available)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 24 10 10 10 10 10 10 16

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
     - Throughput
   * - large polygons
     - 150ms
     - 150ms
     - 303µs
     - 150ms
     - 150ms
     - 7
     - 16.7k/s
   * - medium polygons
     - 15.8ms
     - 15.8ms
     - 246µs
     - 15.6ms
     - 16.9ms
     - 64
     - 158k/s
   * - small polygons
     - 1.60ms
     - 1.59ms
     - 30.2µs
     - 1.57ms
     - 1.79ms
     - 589
     - 1.56M/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the block index buys**, per polygon-size stratum - the same C kernel over the same pairs, with and without the stored latitude ranges in front of it:

* Small polygons: **bare kernel (C/clang)** is 21% faster (1.21x) than **block-filtered kernel (C/clang)** (2.50ms vs 3.03ms)

* Medium polygons: **block-filtered kernel (C/clang)** is 91% faster (1.91x) than **bare kernel (C/clang)** (3.14ms vs 6.02ms)

* Large polygons: **block-filtered kernel (C/clang)** is 1413% faster (15.1x) than **bare kernel (C/clang)** (3.74ms vs 56.5ms)

**C against Python/Numba**, on the kernel a lookup reaches:

* Small polygons: **block-filtered kernel (Python, Numba if available)** is 89% faster (1.89x) than **block-filtered kernel (C/clang)** (1.60ms vs 3.03ms)

* Medium polygons: **block-filtered kernel (C/clang)** is 404% faster (5.04x) than **block-filtered kernel (Python, Numba if available)** (3.14ms vs 15.8ms)

* Large polygons: **block-filtered kernel (C/clang)** is 3917% faster (40.2x) than **block-filtered kernel (Python, Numba if available)** (3.74ms vs 150ms)

* Overall: fastest is **block-filtered kernel (Python, Numba if available) - small polygons** (1.60ms), slowest is **block-filtered kernel (Python, Numba if available) - large polygons** (150ms) - 9258% faster (93.6x)
