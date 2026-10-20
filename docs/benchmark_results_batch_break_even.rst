

When Batched Lookups Pay
========================


**uniformly random points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``, and stops improving beyond ~10,000 (7.45x the scalar loop, faster).

**unique-shortcut points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``, and stops improving beyond ~50,000 (57.7x the scalar loop, faster); from 100,000 points it is slower per point again.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 3.6891 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.*

``timezone_names_at()`` spreads its fixed cost per call over the whole batch, so it beats a ``timezone_at()`` loop only above some batch size, and stops getting faster per point at a larger one. Both depend on the machine and on how clustered the coordinates are - points sharing a shortcut cell are answered together, so a clustered stream pays off sooner than the uniformly random points measured here. Run ``scripts/measure_batch_break_even.py --points your.csv`` (columns ``lng,lat``) to measure your own. How the sweep is taken: :doc:`benchmarking_methodology`.



The sweep
---------


.. image:: batch_break_even_sweep.svg

Speed-up of one batched call over the loop on the same points. The shaded band is where batching starts paying, an arrow marks where it stops improving, and hollow markers are batch sizes with no clear winner. The dotted line at 128 is where ``ZoneNames.names_of`` switches from a Python loop to a numpy gather.



Batch size against speed-up, uniformly random points
----------------------------------------------------



.. list-table::
   :header-rows: 1
   :widths: 11 31 31 9 11 7

   * - Batch size
     - timezone_at() loop, per point
     - timezone_names_at(), per point
     - Speed-up
     - Rounds won
     - Verdict
   * - 10
     - 1.24µs
     - 3.22µs
     - 0.38x
     - 0 of 61
     - slower
   * - 20
     - 1.18µs
     - 1.81µs
     - 0.65x
     - 0 of 61
     - slower
   * - 50
     - 1.17µs
     - 863ns
     - 1.36x
     - 61 of 61
     - faster
   * - 100
     - 1.15µs
     - 539ns
     - 2.13x
     - 61 of 61
     - faster
   * - 127
     - 1.17µs
     - 473ns
     - 2.47x
     - 61 of 61
     - faster
   * - 128
     - 1.17µs
     - 441ns
     - 2.65x
     - 61 of 61
     - faster
   * - 500
     - 1.15µs
     - 234ns
     - 4.91x
     - 61 of 61
     - faster
   * - 1,000
     - 1.14µs
     - 200ns
     - 5.69x
     - 61 of 61
     - faster
   * - 5,000
     - 1.13µs
     - 166ns
     - 6.80x
     - 61 of 61
     - faster
   * - 10,000
     - 1.14µs
     - 153ns
     - 7.45x
     - 61 of 61
     - faster
   * - 50,000
     - 1.21µs
     - 148ns
     - 8.20x
     - 61 of 61
     - faster
   * - 100,000
     - 1.21µs
     - 154ns
     - 7.89x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **9.4 %** across batch sizes from 10 up (limit 15 %).



Batch size against speed-up, unique-shortcut points
---------------------------------------------------



.. list-table::
   :header-rows: 1
   :widths: 11 31 31 9 11 7

   * - Batch size
     - timezone_at() loop, per point
     - timezone_names_at(), per point
     - Speed-up
     - Rounds won
     - Verdict
   * - 10
     - 1.01µs
     - 2.81µs
     - 0.36x
     - 0 of 61
     - slower
   * - 20
     - 994ns
     - 1.53µs
     - 0.65x
     - 0 of 61
     - slower
   * - 50
     - 984ns
     - 664ns
     - 1.48x
     - 61 of 61
     - faster
   * - 100
     - 973ns
     - 363ns
     - 2.68x
     - 61 of 61
     - faster
   * - 127
     - 969ns
     - 298ns
     - 3.25x
     - 61 of 61
     - faster
   * - 128
     - 963ns
     - 265ns
     - 3.63x
     - 61 of 61
     - faster
   * - 500
     - 960ns
     - 81.1ns
     - 11.8x
     - 61 of 61
     - faster
   * - 1,000
     - 951ns
     - 51.0ns
     - 18.6x
     - 61 of 61
     - faster
   * - 5,000
     - 954ns
     - 23.8ns
     - 40.1x
     - 61 of 61
     - faster
   * - 10,000
     - 951ns
     - 20.5ns
     - 46.3x
     - 61 of 61
     - faster
   * - 50,000
     - 999ns
     - 17.3ns
     - 57.7x
     - 61 of 61
     - faster
   * - 100,000
     - 1.00µs
     - 27.9ns
     - 35.9x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **6.1 %** across batch sizes from 10 up (limit 15 %).

This page measures name-returning lookups. ``scripts/measure_batch_break_even.py --api ids`` compares ``timezone_ids_at()`` against a ``timezone_id_at()`` loop instead.



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


**Rounds Per Rung**: 61

**Points Per Round**: ~80,000

**Coordinate Access**: memory mapped
