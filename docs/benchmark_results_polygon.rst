

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~618ns per check on a small polygon, ~1.40µs on the largest** (2.26x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check without that index is ~23.9µs on the largest polygon (17.1x the block-filtered cost) - which is what the stratification below is for, and what the latitude block index removed.

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
     - 59.7ms
     - 59.7ms
     - 502µs
     - 58.6ms
     - 60.7ms
     - 14
     - 41.9k/s
   * - medium polygons
     - 6.25ms
     - 6.25ms
     - 286µs
     - 5.59ms
     - 6.97ms
     - 99
     - 400k/s
   * - small polygons
     - 2.33ms
     - 2.30ms
     - 212µs
     - 2.03ms
     - 3.21ms
     - 399
     - 1.07M/s




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
     - 3.49ms
     - 3.49ms
     - 239µs
     - 3.11ms
     - 4.00ms
     - 279
     - 717k/s
   * - medium polygons
     - 2.77ms
     - 2.78ms
     - 192µs
     - 2.48ms
     - 3.19ms
     - 360
     - 901k/s
   * - small polygons
     - 2.71ms
     - 2.71ms
     - 181µs
     - 2.38ms
     - 3.10ms
     - 354
     - 924k/s




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
     - 12.7s
     - 12.7s
     - 182ms
     - 12.4s
     - 12.9s
     - 5
     - 197/s
   * - medium polygons
     - 821ms
     - 821ms
     - 2.27ms
     - 818ms
     - 823ms
     - 5
     - 3.05k/s
   * - small polygons
     - 30.5ms
     - 30.4ms
     - 450µs
     - 29.5ms
     - 31.4ms
     - 33
     - 81.8k/s




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
     - 137ms
     - 137ms
     - 608µs
     - 136ms
     - 138ms
     - 8
     - 18.2k/s
   * - medium polygons
     - 13.2ms
     - 13.3ms
     - 394µs
     - 12.4ms
     - 14.1ms
     - 74
     - 189k/s
   * - small polygons
     - 1.55ms
     - 1.53ms
     - 93.6µs
     - 1.41ms
     - 1.84ms
     - 578
     - 1.62M/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the block index buys**, per polygon-size stratum - the same C kernel over the same pairs, with and without the stored latitude ranges in front of it:

* Small polygons: **bare kernel (C/clang)** is 16% faster (1.16x) than **block-filtered kernel (C/clang)** (2.33ms vs 2.71ms)

* Medium polygons: **block-filtered kernel (C/clang)** is 125% faster (2.25x) than **bare kernel (C/clang)** (2.77ms vs 6.25ms)

* Large polygons: **block-filtered kernel (C/clang)** is 1611% faster (17.1x) than **bare kernel (C/clang)** (3.49ms vs 59.7ms)

**C against Python/Numba**, on the kernel a lookup reaches:

* Small polygons: **block-filtered kernel (Python, Numba if available)** is 75% faster (1.75x) than **block-filtered kernel (C/clang)** (1.55ms vs 2.71ms)

* Medium polygons: **block-filtered kernel (C/clang)** is 377% faster (4.77x) than **block-filtered kernel (Python, Numba if available)** (2.77ms vs 13.2ms)

* Large polygons: **block-filtered kernel (C/clang)** is 3830% faster (39.3x) than **block-filtered kernel (Python, Numba if available)** (3.49ms vs 137ms)

* Overall: fastest is **block-filtered kernel (Python, Numba if available) - small polygons** (1.55ms), slowest is **block-filtered kernel (Python, Numba if available) - large polygons** (137ms) - 8773% faster (88.7x)
