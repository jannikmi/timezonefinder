

Point-in-Polygon Algorithm Performance Benchmark
================================================


**~402ns per check on a small polygon, ~591ns on the largest** (1.47x) - the kernel a lookup reaches, which skips the parts of a ring a horizontal ray cannot cross and is therefore nearly flat in polygon size.

The same check over an unindexed coordinate array is ~22.9µs on the largest polygon (38.8x the packed cost) - which is what the stratification below is for, and what the latitude block index removed.

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
     - 57.3ms
     - 57.4ms
     - 466µs
     - 56.1ms
     - 57.9ms
     - 16
     - 43.7k/s
   * - medium polygons
     - 6.54ms
     - 6.52ms
     - 174µs
     - 6.20ms
     - 7.10ms
     - 141
     - 382k/s
   * - small polygons
     - 2.60ms
     - 2.55ms
     - 198µs
     - 2.35ms
     - 3.22ms
     - 334
     - 962k/s




packed kernel (C/clang)
^^^^^^^^^^^^^^^^^^^^^^^



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
     - 1.48ms
     - 1.47ms
     - 20.6µs
     - 1.45ms
     - 1.57ms
     - 612
     - 1.69M/s
   * - medium polygons
     - 1.05ms
     - 1.04ms
     - 17.0µs
     - 1.03ms
     - 1.13ms
     - 852
     - 2.38M/s
   * - small polygons
     - 1.00ms
     - 996µs
     - 24.3µs
     - 982µs
     - 1.14ms
     - 984
     - 2.49M/s




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
     - 14.2s
     - 14.2s
     - 16.6ms
     - 14.2s
     - 14.3s
     - 5
     - 176/s
   * - medium polygons
     - 943ms
     - 934ms
     - 16.6ms
     - 932ms
     - 970ms
     - 5
     - 2.65k/s
   * - small polygons
     - 34.8ms
     - 34.9ms
     - 389µs
     - 34.0ms
     - 35.5ms
     - 29
     - 71.8k/s




packed kernel (Python, Numba if available)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



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
     - 301ms
     - 301ms
     - 243µs
     - 301ms
     - 301ms
     - 5
     - 8.30k/s
   * - medium polygons
     - 88.2ms
     - 88.0ms
     - 511µs
     - 87.7ms
     - 89.4ms
     - 12
     - 28.3k/s
   * - small polygons
     - 4.78ms
     - 4.78ms
     - 41.8µs
     - 4.72ms
     - 5.09ms
     - 207
     - 523k/s




Performance Summary
~~~~~~~~~~~~~~~~~~~


**What the stored index and payload buy**, per polygon-size stratum - the same C predicate over the same pairs, reading the packed collection against reading a plain coordinate array with nothing in front of it:

* Small polygons: **packed kernel (C/clang)** is 159% faster (2.59x) than **bare kernel (C/clang)** (1.00ms vs 2.60ms)

* Medium polygons: **packed kernel (C/clang)** is 524% faster (6.24x) than **bare kernel (C/clang)** (1.05ms vs 6.54ms)

* Large polygons: **packed kernel (C/clang)** is 3779% faster (38.8x) than **bare kernel (C/clang)** (1.48ms vs 57.3ms)

**C against Python/Numba**, on the kernel a lookup reaches:

* Small polygons: **packed kernel (C/clang)** is 376% faster (4.76x) than **packed kernel (Python, Numba if available)** (1.00ms vs 4.78ms)

* Medium polygons: **packed kernel (C/clang)** is 8310% faster (84.1x) than **packed kernel (Python, Numba if available)** (1.05ms vs 88.2ms)

* Large polygons: **packed kernel (C/clang)** is 20294% faster (204x) than **packed kernel (Python, Numba if available)** (1.48ms vs 301ms)

* Overall: fastest is **packed kernel (C/clang) - small polygons** (1.00ms), slowest is **packed kernel (Python, Numba if available) - large polygons** (301ms) - 29869% faster (300x)
