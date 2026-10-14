

When Batched Lookups Pay
========================


**uniformly random points: batching starts paying between 50 and 100 points per call** for ``timezone_names_at()``, and stops improving beyond ~2,000 (4.84x the scalar loop, faster).

**unique-shortcut points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``, and had not stopped improving at the top of the ladder.

*Measured on Linux x86_64, Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz @ 2.7304 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.*

``timezone_names_at()`` amortises validation, the integer scaling and the shortcut table read over a whole batch, and the cell arithmetic vectorises with it and still resolves ambiguous points one at a time. So it is faster per point than calling ``timezone_at()`` in a loop only once the batch is large enough to pay back its own fixed cost. This page is where that happens, and where growing the batch further stops helping. See :doc:`benchmarking_methodology`.

.. note::

   Nothing on this page is on the continuous-integration trend chart, which tracks one fixed batch size. These are on-demand measurements, taken by ``make batch-break-even``. Both answers move with the machine *and* with the workload, so read them as this configuration's, and run the script on your own coordinates to get yours.



How this is measured
--------------------


Each row below is one paired comparison: a ``timezone_at()`` loop over N points against a single ``timezone_names_at()`` call on the same N points, with the same draw handed to both candidates, the order alternating round by round, and two estimators reported so that a difference neither can demonstrate reads as ``unresolved`` rather than as a number (``benchmarks/candidate_comparison.py``).

Every rung times the same amount of work - about 25,000 points per round, whatever the batch size - so the rungs are comparable to each other, and both answers are read off the ratio *within* a rung rather than off absolute times across rungs, which is what keeps drift over the run out of the curve. Points are drawn without replacement inside a batch: a repeated coordinate would be answered from the batch's own cell lookup and would flatter exactly the effect being measured.

The coordinate arrays are prepared before the clock starts, in the contiguous ``float64`` form the batch API takes without copying. A caller holding Python lists pays one conversion per axis per call on top of what these rows show.

**The two answers do not survive a noisy machine equally well.** Where batching starts paying is a comparison *within* one rung, so drift over the run cancels out of it and it reproduces. Where it stops improving is the batched call's per-point time compared *across* rungs, which drift moves directly - so it is quoted only when the control below certifies that the ladder measured one thing, and withheld when it does not.



The sweep
---------


.. image:: batch_break_even_sweep.svg

The upper panel is the best-round speed-up; the lower one is the share of rounds the batched call won, which assumes nothing about how the noise is distributed. A difference is believed only where both agree, so the shaded band - where the crossing lies - is exactly where the upper panel passes 1.0 and the lower one passes one half. Hollow markers are rungs neither estimator resolves.

The dotted rule at 128 is not a measurement artefact: ``ZoneNames.names_of`` converts ids to names with a Python loop below that size and a numpy gather at or above it, so the per-point cost steps there.



Batch size against speed-up, uniformly random points
----------------------------------------------------



.. list-table::
   :header-rows: 1
   :widths: 10 29 30 8 10 13

   * - Batch size
     - timezone_at() loop, per point
     - timezone_names_at(), per point
     - Speed-up
     - Rounds won
     - Verdict
   * - 1
     - 1.50µs
     - 35.7µs
     - 0.04x
     - 0 of 61
     - slower
   * - 2
     - 1.43µs
     - 18.0µs
     - 0.08x
     - 0 of 61
     - slower
   * - 5
     - 1.36µs
     - 8.24µs
     - 0.16x
     - 0 of 61
     - slower
   * - 10
     - 1.32µs
     - 4.65µs
     - 0.28x
     - 0 of 61
     - slower
   * - 20
     - 1.27µs
     - 2.64µs
     - 0.48x
     - 0 of 61
     - slower
   * - 50
     - 1.26µs
     - 1.28µs
     - 0.99x
     - 29 of 61
     - no difference
   * - 100
     - 1.23µs
     - 788ns
     - 1.56x
     - 61 of 61
     - faster
   * - 127
     - 1.23µs
     - 674ns
     - 1.82x
     - 61 of 61
     - faster
   * - 128
     - 1.24µs
     - 644ns
     - 1.93x
     - 61 of 61
     - faster
   * - 200
     - 1.22µs
     - 498ns
     - 2.46x
     - 61 of 61
     - faster
   * - 500
     - 1.22µs
     - 339ns
     - 3.62x
     - 61 of 61
     - faster
   * - 1,000
     - 1.21µs
     - 280ns
     - 4.32x
     - 61 of 61
     - faster
   * - 2,000
     - 1.24µs
     - 256ns
     - 4.84x
     - 61 of 61
     - faster
   * - 5,000
     - 1.22µs
     - 246ns
     - 4.94x
     - 61 of 61
     - faster


The crossing is reported as the interval (50, 100] rather than as a number, because that is all a ladder of discrete sizes can establish. The rungs inside it read ``no difference`` or ``unresolved`` by construction: that is what it means for the crossing to be in there, not a defect in the run.

Control: the scalar loop answers the same points at every rung, so its per-point time should not depend on the batch size. Across the 11 rungs at or above N=10 it spread **8.7 %** (1.21µs to 1.32µs), against a 15 % threshold - so the ladder measured one thing. It is published as the reader's check and is never divided into anything. The smaller rungs are excluded because the harness's own per-batch cost lands on them divided by a very small N.



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
   * - 1
     - 1.14µs
     - 34.1µs
     - 0.03x
     - 0 of 61
     - slower
   * - 2
     - 1.06µs
     - 16.7µs
     - 0.06x
     - 0 of 61
     - slower
   * - 5
     - 1.02µs
     - 7.20µs
     - 0.14x
     - 0 of 61
     - slower
   * - 10
     - 997ns
     - 3.95µs
     - 0.25x
     - 0 of 61
     - slower
   * - 20
     - 981ns
     - 2.14µs
     - 0.46x
     - 0 of 61
     - slower
   * - 50
     - 963ns
     - 913ns
     - 1.06x
     - 58 of 61
     - faster
   * - 100
     - 957ns
     - 487ns
     - 1.96x
     - 61 of 61
     - faster
   * - 127
     - 954ns
     - 396ns
     - 2.41x
     - 61 of 61
     - faster
   * - 128
     - 955ns
     - 363ns
     - 2.63x
     - 61 of 61
     - faster
   * - 200
     - 954ns
     - 242ns
     - 3.95x
     - 61 of 61
     - faster
   * - 500
     - 948ns
     - 108ns
     - 8.75x
     - 61 of 61
     - faster
   * - 1,000
     - 947ns
     - 66.3ns
     - 14.3x
     - 61 of 61
     - faster
   * - 2,000
     - 945ns
     - 43.0ns
     - 22.0x
     - 61 of 61
     - faster


The crossing is reported as the interval (20, 50] rather than as a number, because that is all a ladder of discrete sizes can establish. The rungs inside it read ``no difference`` or ``unresolved`` by construction: that is what it means for the crossing to be in there, not a defect in the run.

Control: the scalar loop answers the same points at every rung, so its per-point time should not depend on the batch size. Across the 10 rungs at or above N=10 it spread **5.5 %** (945ns to 997ns), against a 15 % threshold - so the ladder measured one thing. It is published as the reader's check and is never divided into anything. The smaller rungs are excluded because the harness's own per-batch cost lands on them divided by a very small N.



What this does not say
----------------------


**Both answers are properties of the workload, not only of the library.** The batch path answers every point that falls in one shortcut cell from a single lookup, so a clustered stream - a delivery round, a city, a sensor network - amortises sooner than the uniformly random points measured here, which share almost nothing. Random points are the conservative case.

They are also properties of this machine and this acceleration path. ``scripts/measure_batch_break_even.py`` takes ``--points your.csv`` (two columns, ``lng,lat``) and reports the same two numbers for your coordinates on your hardware, which is the only way to get the answer that applies to you.

This page measures name-returning lookups. ``scripts/measure_batch_break_even.py --api ids`` runs the corresponding like-for-like comparison of ``timezone_ids_at()`` against a ``timezone_id_at()`` loop, with the per-point name conversion absent from both sides.



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

**Points Per Round**: ~25,000

**Coordinate Access**: memory mapped
