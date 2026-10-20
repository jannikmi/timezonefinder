

When Batched Lookups Pay
========================


**uniformly random points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``, and stops improving beyond ~50,000 (8.74x the scalar loop, faster); from 100,000 points it is slower per point again.

**unique-shortcut points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``. Where it stops improving is **not established on this run**: the scalar baseline spread 24.5 % across rungs, above the 15 % this measurement needs before it can read an absolute quantity along the ladder.

*Measured on Linux x86_64, AMD EPYC 9V45 96-Core Processor @ 4.2325 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.*

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
     - 887ns
     - 2.44µs
     - 0.36x
     - 0 of 61
     - slower
   * - 20
     - 913ns
     - 1.38µs
     - 0.66x
     - 0 of 61
     - slower
   * - 50
     - 894ns
     - 655ns
     - 1.36x
     - 61 of 61
     - faster
   * - 100
     - 901ns
     - 404ns
     - 2.23x
     - 61 of 61
     - faster
   * - 127
     - 911ns
     - 353ns
     - 2.58x
     - 61 of 61
     - faster
   * - 128
     - 883ns
     - 330ns
     - 2.68x
     - 61 of 61
     - faster
   * - 500
     - 875ns
     - 171ns
     - 5.12x
     - 61 of 61
     - faster
   * - 1,000
     - 906ns
     - 150ns
     - 6.05x
     - 61 of 61
     - faster
   * - 5,000
     - 916ns
     - 126ns
     - 7.27x
     - 61 of 61
     - faster
   * - 10,000
     - 911ns
     - 121ns
     - 7.56x
     - 61 of 61
     - faster
   * - 50,000
     - 988ns
     - 113ns
     - 8.74x
     - 61 of 61
     - faster
   * - 100,000
     - 963ns
     - 128ns
     - 7.53x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **12.9 %** across batch sizes from 10 up (limit 15 %).



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
     - 824ns
     - 2.22µs
     - 0.37x
     - 0 of 61
     - slower
   * - 20
     - 807ns
     - 1.19µs
     - 0.68x
     - 0 of 61
     - slower
   * - 50
     - 861ns
     - 516ns
     - 1.67x
     - 61 of 61
     - faster
   * - 100
     - 806ns
     - 279ns
     - 2.89x
     - 61 of 61
     - faster
   * - 127
     - 777ns
     - 229ns
     - 3.39x
     - 61 of 61
     - faster
   * - 128
     - 726ns
     - 204ns
     - 3.57x
     - 61 of 61
     - faster
   * - 500
     - 692ns
     - 61.6ns
     - 11.2x
     - 61 of 61
     - faster
   * - 1,000
     - 724ns
     - 38.0ns
     - 19.1x
     - 61 of 61
     - faster
   * - 5,000
     - 773ns
     - 16.6ns
     - 46.5x
     - 61 of 61
     - faster
   * - 10,000
     - 700ns
     - 14.1ns
     - 49.6x
     - 61 of 61
     - faster
   * - 50,000
     - 726ns
     - 12.0ns
     - 60.3x
     - 61 of 61
     - faster
   * - 100,000
     - 723ns
     - 22.7ns
     - 31.9x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **24.5 %** across batch sizes from 10 up (limit 15 %) - too much to say where batching stops improving on this run.

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
