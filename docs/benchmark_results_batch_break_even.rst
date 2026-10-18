

When Batched Lookups Pay
========================


**uniformly random points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``. Where it stops improving is **not established on this run**: the scalar baseline spread 23.5 % across rungs, above the 15 % this measurement needs before it can read an absolute quantity along the ladder.

**unique-shortcut points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``, and stops improving beyond ~50,000 (50.7x the scalar loop, faster); from 100,000 points it is slower per point again.

*Measured on Linux x86_64, INTEL(R) XEON(R) PLATINUM 8573C @ 2.3000 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.*

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
     - 1.51µs
     - 3.84µs
     - 0.39x
     - 0 of 61
     - slower
   * - 20
     - 1.35µs
     - 2.15µs
     - 0.63x
     - 0 of 61
     - slower
   * - 50
     - 1.33µs
     - 1.05µs
     - 1.26x
     - 61 of 61
     - faster
   * - 100
     - 1.30µs
     - 664ns
     - 1.95x
     - 61 of 61
     - faster
   * - 127
     - 1.30µs
     - 583ns
     - 2.23x
     - 61 of 61
     - faster
   * - 128
     - 1.29µs
     - 538ns
     - 2.40x
     - 61 of 61
     - faster
   * - 500
     - 1.25µs
     - 297ns
     - 4.22x
     - 61 of 61
     - faster
   * - 1,000
     - 1.26µs
     - 256ns
     - 4.90x
     - 61 of 61
     - faster
   * - 5,000
     - 1.25µs
     - 212ns
     - 5.87x
     - 61 of 61
     - faster
   * - 10,000
     - 1.22µs
     - 208ns
     - 5.88x
     - 61 of 61
     - faster
   * - 50,000
     - 1.25µs
     - 192ns
     - 6.53x
     - 61 of 61
     - faster
   * - 100,000
     - 1.26µs
     - 197ns
     - 6.39x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **23.5 %** across batch sizes from 10 up (limit 15 %) - too much to say where batching stops improving on this run.



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
     - 3.24µs
     - 0.34x
     - 0 of 61
     - slower
   * - 20
     - 1.12µs
     - 1.75µs
     - 0.64x
     - 0 of 61
     - slower
   * - 50
     - 1.04µs
     - 750ns
     - 1.39x
     - 61 of 61
     - faster
   * - 100
     - 1.03µs
     - 406ns
     - 2.53x
     - 61 of 61
     - faster
   * - 127
     - 1.04µs
     - 334ns
     - 3.11x
     - 61 of 61
     - faster
   * - 128
     - 1.03µs
     - 295ns
     - 3.49x
     - 61 of 61
     - faster
   * - 500
     - 1.01µs
     - 88.4ns
     - 11.4x
     - 61 of 61
     - faster
   * - 1,000
     - 1.00µs
     - 54.5ns
     - 18.4x
     - 61 of 61
     - faster
   * - 5,000
     - 1.01µs
     - 25.3ns
     - 39.9x
     - 61 of 61
     - faster
   * - 10,000
     - 989ns
     - 21.7ns
     - 45.6x
     - 61 of 61
     - faster
   * - 50,000
     - 1.02µs
     - 20.2ns
     - 50.7x
     - 61 of 61
     - faster
   * - 100,000
     - 1.01µs
     - 32.3ns
     - 31.1x
     - 61 of 61
     - faster


Check: the loop's per-point time, which should not depend on the batch size, varied **13.1 %** across batch sizes from 10 up (limit 15 %).

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

**Timezone Data Version**: 2026d



Benchmark Configuration
~~~~~~~~~~~~~~~~~~~~~~~


**Rounds Per Rung**: 61

**Points Per Round**: ~80,000

**Coordinate Access**: memory mapped
