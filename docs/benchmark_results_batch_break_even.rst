

When Batched Lookups Pay
========================


**uniformly random points: batching starts paying between 50 and 100 points per call** for ``timezone_names_at()``. Where it stops improving is **not established on this run**: the scalar baseline spread 15.6 % across rungs, above the 15 % this measurement needs before it can read an absolute quantity along the ladder.

**unique-shortcut points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``, and stops improving beyond ~50,000 (51.2x the scalar loop, faster); from 100,000 points it is slower per point again.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 2.4454 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.*

``timezone_names_at()`` spreads its fixed cost per call over the whole batch, so it beats a ``timezone_at()`` loop only above some batch size, and stops getting faster per point at a larger one. Both depend on the machine and on how clustered the coordinates are - points sharing a shortcut cell are answered together, so a clustered stream pays off sooner than the uniformly random points measured here. Run ``scripts/measure_batch_break_even.py --points your.csv`` (columns ``lng,lat``) to measure your own. How the sweep is taken: :doc:`benchmarking_methodology`.



The sweep
---------


.. image:: batch_break_even_sweep.svg

Speed-up of one batched call over the loop on the same points. The shaded band is where batching starts paying, an arrow marks where it stops improving, and hollow markers are batch sizes with no clear winner. The dotted line at 128 is where ``ZoneNames.names_of`` switches from a Python loop to a numpy gather.



Batch size against speed-up, uniformly random points
----------------------------------------------------



.. list-table::
   :header-rows: 1
   :widths: 10 30 32 8 10 10

   * - Batch size
     - timezone_at() loop, per point
     - timezone_names_at(), per point
     - Speed-up
     - Rounds won
     - Verdict
   * - 10
     - 1.58µs
     - 5.20µs
     - 0.30x
     - 0 of 61
     - slower
   * - 20
     - 1.44µs
     - 2.97µs
     - 0.49x
     - 0 of 61
     - slower
   * - 50
     - 1.40µs
     - 1.45µs
     - 0.97x
     - 26 of 61
     - unresolved
   * - 100
     - 1.39µs
     - 903ns
     - 1.53x
     - 61 of 61
     - faster
   * - 127
     - 1.40µs
     - 788ns
     - 1.77x
     - 61 of 61
     - faster
   * - 128
     - 1.40µs
     - 759ns
     - 1.84x
     - 61 of 61
     - faster
   * - 500
     - 1.38µs
     - 392ns
     - 3.53x
     - 61 of 61
     - faster
   * - 1,000
     - 1.39µs
     - 324ns
     - 4.28x
     - 61 of 61
     - faster
   * - 5,000
     - 1.37µs
     - 257ns
     - 5.34x
     - 61 of 61
     - faster
   * - 10,000
     - 1.36µs
     - 238ns
     - 5.72x
     - 61 of 61
     - faster
   * - 50,000
     - 1.43µs
     - 221ns
     - 6.47x
     - 61 of 61
     - faster
   * - 100,000
     - 1.44µs
     - 232ns
     - 6.21x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **15.6 %** across batch sizes from 10 up (limit 15 %) - too much to say where batching stops improving on this run.



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
     - 1.14µs
     - 4.18µs
     - 0.27x
     - 0 of 61
     - slower
   * - 20
     - 1.13µs
     - 2.23µs
     - 0.51x
     - 0 of 61
     - slower
   * - 50
     - 1.09µs
     - 962ns
     - 1.13x
     - 61 of 61
     - faster
   * - 100
     - 1.08µs
     - 526ns
     - 2.06x
     - 61 of 61
     - faster
   * - 127
     - 1.10µs
     - 432ns
     - 2.55x
     - 61 of 61
     - faster
   * - 128
     - 1.11µs
     - 390ns
     - 2.84x
     - 61 of 61
     - faster
   * - 500
     - 1.08µs
     - 119ns
     - 9.10x
     - 61 of 61
     - faster
   * - 1,000
     - 1.07µs
     - 73.8ns
     - 14.5x
     - 61 of 61
     - faster
   * - 5,000
     - 1.06µs
     - 31.8ns
     - 33.5x
     - 61 of 61
     - faster
   * - 10,000
     - 1.07µs
     - 26.0ns
     - 41.2x
     - 61 of 61
     - faster
   * - 50,000
     - 1.10µs
     - 21.5ns
     - 51.2x
     - 61 of 61
     - faster
   * - 100,000
     - 1.11µs
     - 37.1ns
     - 29.8x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **7.3 %** across batch sizes from 10 up (limit 15 %).

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


**Fixture Version**: 4

**Timezone Data Version**: 2026e



Benchmark Configuration
~~~~~~~~~~~~~~~~~~~~~~~


**Rounds Per Rung**: 61

**Points Per Round**: ~80,000

**Coordinate Access**: memory mapped
