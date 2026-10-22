

When Batched Lookups Pay
========================


**uniformly random points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``, and stops improving beyond ~50,000 (8.00x the scalar loop, faster); from 100,000 points it is slower per point again.

**unique-shortcut points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``, and stops improving beyond ~50,000 (54.9x the scalar loop, faster); from 100,000 points it is slower per point again.

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 3.6982 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.*

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
     - 1.25µs
     - 3.20µs
     - 0.39x
     - 0 of 61
     - slower
   * - 20
     - 1.20µs
     - 1.81µs
     - 0.66x
     - 0 of 61
     - slower
   * - 50
     - 1.15µs
     - 866ns
     - 1.33x
     - 61 of 61
     - faster
   * - 100
     - 1.15µs
     - 540ns
     - 2.13x
     - 61 of 61
     - faster
   * - 127
     - 1.14µs
     - 467ns
     - 2.43x
     - 61 of 61
     - faster
   * - 128
     - 1.14µs
     - 445ns
     - 2.57x
     - 61 of 61
     - faster
   * - 500
     - 1.14µs
     - 236ns
     - 4.83x
     - 61 of 61
     - faster
   * - 1,000
     - 1.12µs
     - 201ns
     - 5.58x
     - 61 of 61
     - faster
   * - 5,000
     - 1.12µs
     - 166ns
     - 6.72x
     - 61 of 61
     - faster
   * - 10,000
     - 1.10µs
     - 157ns
     - 7.02x
     - 61 of 61
     - faster
   * - 50,000
     - 1.18µs
     - 147ns
     - 8.00x
     - 61 of 61
     - faster
   * - 100,000
     - 1.17µs
     - 156ns
     - 7.47x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **13.4 %** across batch sizes from 10 up (limit 15 %).



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
     - 965ns
     - 2.80µs
     - 0.34x
     - 0 of 61
     - slower
   * - 20
     - 944ns
     - 1.61µs
     - 0.59x
     - 0 of 61
     - slower
   * - 50
     - 929ns
     - 661ns
     - 1.41x
     - 61 of 61
     - faster
   * - 100
     - 924ns
     - 360ns
     - 2.57x
     - 61 of 61
     - faster
   * - 127
     - 918ns
     - 295ns
     - 3.11x
     - 61 of 61
     - faster
   * - 128
     - 933ns
     - 264ns
     - 3.53x
     - 61 of 61
     - faster
   * - 500
     - 946ns
     - 80.5ns
     - 11.8x
     - 61 of 61
     - faster
   * - 1,000
     - 915ns
     - 50.6ns
     - 18.1x
     - 61 of 61
     - faster
   * - 5,000
     - 921ns
     - 23.6ns
     - 39.0x
     - 61 of 61
     - faster
   * - 10,000
     - 908ns
     - 20.6ns
     - 44.1x
     - 61 of 61
     - faster
   * - 50,000
     - 947ns
     - 17.2ns
     - 54.9x
     - 61 of 61
     - faster
   * - 100,000
     - 969ns
     - 30.8ns
     - 31.4x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **6.7 %** across batch sizes from 10 up (limit 15 %).

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
