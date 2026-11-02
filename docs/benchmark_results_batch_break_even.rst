

When Batched Lookups Pay
========================


**uniformly random points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``. Where it stops improving is **not established on this run**: the scalar baseline spread 26.1 % across rungs, above the 15 % this measurement needs before it can read an absolute quantity along the ladder.

**unique-shortcut points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``. Where it stops improving is **not established on this run**: the scalar baseline spread 26.4 % across rungs, above the 15 % this measurement needs before it can read an absolute quantity along the ladder.

*Measured on Linux x86_64, AMD EPYC 9V45 96-Core Processor @ 4.4355 GHz, Python 3.13.17, using the C extension (clang) point-in-polygon path.*

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
     - 1.01µs
     - 2.44µs
     - 0.41x
     - 0 of 61
     - slower
   * - 20
     - 1.01µs
     - 1.36µs
     - 0.74x
     - 0 of 61
     - slower
   * - 50
     - 975ns
     - 652ns
     - 1.50x
     - 61 of 61
     - faster
   * - 100
     - 966ns
     - 402ns
     - 2.40x
     - 61 of 61
     - faster
   * - 127
     - 953ns
     - 348ns
     - 2.74x
     - 61 of 61
     - faster
   * - 128
     - 936ns
     - 325ns
     - 2.88x
     - 61 of 61
     - faster
   * - 500
     - 842ns
     - 168ns
     - 5.01x
     - 61 of 61
     - faster
   * - 1,000
     - 942ns
     - 146ns
     - 6.44x
     - 61 of 61
     - faster
   * - 5,000
     - 811ns
     - 116ns
     - 6.98x
     - 61 of 61
     - faster
   * - 10,000
     - 803ns
     - 108ns
     - 7.40x
     - 61 of 61
     - faster
   * - 50,000
     - 979ns
     - 112ns
     - 8.70x
     - 61 of 61
     - faster
   * - 100,000
     - 899ns
     - 98.3ns
     - 9.15x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **26.1 %** across batch sizes from 10 up (limit 15 %) - too much to say where batching stops improving on this run.



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
     - 712ns
     - 2.05µs
     - 0.35x
     - 0 of 61
     - slower
   * - 20
     - 804ns
     - 1.12µs
     - 0.72x
     - 1 of 61
     - slower
   * - 50
     - 778ns
     - 480ns
     - 1.62x
     - 61 of 61
     - faster
   * - 100
     - 781ns
     - 265ns
     - 2.94x
     - 61 of 61
     - faster
   * - 127
     - 781ns
     - 212ns
     - 3.68x
     - 61 of 61
     - faster
   * - 128
     - 794ns
     - 199ns
     - 3.99x
     - 61 of 61
     - faster
   * - 500
     - 757ns
     - 59.9ns
     - 12.6x
     - 61 of 61
     - faster
   * - 1,000
     - 789ns
     - 37.3ns
     - 21.1x
     - 61 of 61
     - faster
   * - 5,000
     - 702ns
     - 16.4ns
     - 42.9x
     - 61 of 61
     - faster
   * - 10,000
     - 668ns
     - 13.8ns
     - 48.4x
     - 61 of 61
     - faster
   * - 50,000
     - 779ns
     - 11.9ns
     - 65.5x
     - 61 of 61
     - faster
   * - 100,000
     - 845ns
     - 11.3ns
     - 74.9x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **26.4 %** across batch sizes from 10 up (limit 15 %) - too much to say where batching stops improving on this run.

This page measures name-returning lookups. ``scripts/measure_batch_break_even.py --api ids`` compares ``timezone_ids_at()`` against a ``timezone_id_at()`` loop instead.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.17 (CPython)

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


**Rounds Per Rung**: 61

**Points Per Round**: ~80,000

**Coordinate Access**: memory mapped
