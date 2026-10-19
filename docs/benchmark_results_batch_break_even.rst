

When Batched Lookups Pay
========================


**uniformly random points: batching starts paying between 50 and 100 points per call** for ``timezone_names_at()``. Where it stops improving is **not established on this run**: the scalar baseline spread 18.6 % across rungs, above the 15 % this measurement needs before it can read an absolute quantity along the ladder.

**unique-shortcut points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``, and stops improving beyond ~50,000 (48.1x the scalar loop, faster); from 100,000 points it is slower per point again.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 2.7473 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.*

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
     - 1.54µs
     - 5.01µs
     - 0.31x
     - 0 of 61
     - slower
   * - 20
     - 1.42µs
     - 2.85µs
     - 0.50x
     - 0 of 61
     - slower
   * - 50
     - 1.38µs
     - 1.39µs
     - 0.99x
     - 49 of 61
     - unresolved
   * - 100
     - 1.36µs
     - 864ns
     - 1.57x
     - 61 of 61
     - faster
   * - 127
     - 1.33µs
     - 736ns
     - 1.81x
     - 61 of 61
     - faster
   * - 128
     - 1.33µs
     - 706ns
     - 1.88x
     - 61 of 61
     - faster
   * - 500
     - 1.33µs
     - 347ns
     - 3.83x
     - 61 of 61
     - faster
   * - 1,000
     - 1.32µs
     - 285ns
     - 4.63x
     - 61 of 61
     - faster
   * - 5,000
     - 1.30µs
     - 220ns
     - 5.90x
     - 61 of 61
     - faster
   * - 10,000
     - 1.32µs
     - 199ns
     - 6.63x
     - 61 of 61
     - faster
   * - 50,000
     - 1.37µs
     - 189ns
     - 7.24x
     - 61 of 61
     - faster
   * - 100,000
     - 1.37µs
     - 194ns
     - 7.06x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **18.6 %** across batch sizes from 10 up (limit 15 %) - too much to say where batching stops improving on this run.



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
     - 1.11µs
     - 4.02µs
     - 0.28x
     - 0 of 61
     - slower
   * - 20
     - 1.09µs
     - 2.19µs
     - 0.50x
     - 0 of 61
     - slower
   * - 50
     - 1.08µs
     - 956ns
     - 1.13x
     - 61 of 61
     - faster
   * - 100
     - 1.06µs
     - 524ns
     - 2.02x
     - 61 of 61
     - faster
   * - 127
     - 1.05µs
     - 430ns
     - 2.44x
     - 61 of 61
     - faster
   * - 128
     - 1.05µs
     - 385ns
     - 2.72x
     - 61 of 61
     - faster
   * - 500
     - 1.05µs
     - 119ns
     - 8.82x
     - 61 of 61
     - faster
   * - 1,000
     - 1.04µs
     - 74.2ns
     - 14.0x
     - 61 of 61
     - faster
   * - 5,000
     - 1.06µs
     - 32.1ns
     - 33.1x
     - 61 of 61
     - faster
   * - 10,000
     - 1.04µs
     - 26.5ns
     - 39.0x
     - 61 of 61
     - faster
   * - 50,000
     - 1.08µs
     - 22.5ns
     - 48.1x
     - 61 of 61
     - faster
   * - 100,000
     - 1.09µs
     - 34.1ns
     - 31.9x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **7.2 %** across batch sizes from 10 up (limit 15 %).

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

**Timezone Data Version**: 2026d



Benchmark Configuration
~~~~~~~~~~~~~~~~~~~~~~~


**Rounds Per Rung**: 61

**Points Per Round**: ~80,000

**Coordinate Access**: memory mapped
