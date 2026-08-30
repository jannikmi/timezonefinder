

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~679ns per check on a small polygon, ~1.68µs on the largest** (2.48x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check without that index is ~23.1µs on the largest polygon (13.7x the block-filtered cost) - which is what the stratification below is for, and what the latitude block index removed.

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
     - 57.8ms
     - 57.8ms
     - 492µs
     - 56.9ms
     - 58.7ms
     - 17
     - 43.2k/s
   * - medium polygons
     - 6.23ms
     - 6.25ms
     - 281µs
     - 5.64ms
     - 6.85ms
     - 147
     - 401k/s
   * - small polygons
     - 2.61ms
     - 2.58ms
     - 189µs
     - 2.34ms
     - 3.58ms
     - 368
     - 956k/s




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
     - 4.21ms
     - 4.16ms
     - 339µs
     - 3.76ms
     - 7.73ms
     - 244
     - 594k/s
   * - medium polygons
     - 3.53ms
     - 3.42ms
     - 446µs
     - 3.01ms
     - 6.49ms
     - 280
     - 709k/s
   * - small polygons
     - 3.24ms
     - 3.22ms
     - 147µs
     - 2.92ms
     - 3.95ms
     - 305
     - 772k/s




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
     - 14.9s
     - 14.9s
     - 510ms
     - 14.4s
     - 15.5s
     - 5
     - 167/s
   * - medium polygons
     - 958ms
     - 957ms
     - 2.16ms
     - 955ms
     - 960ms
     - 5
     - 2.61k/s
   * - small polygons
     - 35.4ms
     - 35.4ms
     - 645µs
     - 34.1ms
     - 37.1ms
     - 28
     - 70.6k/s




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
     - 154ms
     - 154ms
     - 1.87ms
     - 152ms
     - 158ms
     - 7
     - 16.2k/s
   * - medium polygons
     - 14.8ms
     - 14.7ms
     - 313µs
     - 14.2ms
     - 15.8ms
     - 66
     - 169k/s
   * - small polygons
     - 1.70ms
     - 1.66ms
     - 165µs
     - 1.50ms
     - 3.07ms
     - 525
     - 1.47M/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the block index buys**, per polygon-size stratum - the same C kernel over the same pairs, with and without the stored latitude ranges in front of it:

* Small polygons: **bare kernel (C/clang)** is 24% faster (1.24x) than **block-filtered kernel (C/clang)** (2.61ms vs 3.24ms)

* Medium polygons: **block-filtered kernel (C/clang)** is 77% faster (1.77x) than **bare kernel (C/clang)** (3.53ms vs 6.23ms)

* Large polygons: **block-filtered kernel (C/clang)** is 1273% faster (13.7x) than **bare kernel (C/clang)** (4.21ms vs 57.8ms)

**C against Python/Numba**, on the kernel a lookup reaches:

* Small polygons: **block-filtered kernel (Python, Numba if available)** is 91% faster (1.91x) than **block-filtered kernel (C/clang)** (1.70ms vs 3.24ms)

* Medium polygons: **block-filtered kernel (C/clang)** is 320% faster (4.20x) than **block-filtered kernel (Python, Numba if available)** (3.53ms vs 14.8ms)

* Large polygons: **block-filtered kernel (C/clang)** is 3563% faster (36.6x) than **block-filtered kernel (Python, Numba if available)** (4.21ms vs 154ms)

* Overall: fastest is **block-filtered kernel (Python, Numba if available) - small polygons** (1.70ms), slowest is **block-filtered kernel (Python, Numba if available) - large polygons** (154ms) - 8986% faster (90.9x)
