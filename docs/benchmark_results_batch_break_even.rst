

When Batched Lookups Pay
========================


**uniformly random points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``. Where it stops improving is **not established on this run**: the scalar baseline spread 16.7 % across rungs, above the 15 % this measurement needs before it can read an absolute quantity along the ladder.

**unique-shortcut points: batching starts paying between 20 and 50 points per call** for ``timezone_names_at()``, and had not stopped improving at the top of the ladder.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 2.4454 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.*

``timezone_names_at()`` amortises validation, the integer scaling and the shortcut table read over a whole batch, and the cell arithmetic vectorises with it and still resolves ambiguous points one at a time. So it is faster per point than calling ``timezone_at()`` in a loop only once the batch is large enough to pay back its own fixed cost. This page is where that happens, and where growing the batch further stops helping. See :doc:`benchmarking_methodology`.

.. note::

   Nothing on this page is on the continuous-integration trend chart, which tracks one fixed batch size. These are on-demand measurements, taken by ``make batch-break-even``. Both answers move with the machine *and* with the workload, so read them as this configuration's, and run the script on your own coordinates to get yours.



How this is measured
--------------------


Each row below is one paired comparison: a ``timezone_at()`` loop over N points against a single ``timezone_names_at()`` call on the same N points, with the same draw handed to both candidates, the order alternating round by round, and two estimators reported so that a difference neither can demonstrate reads as ``unresolved`` rather than as a number (``benchmarks/candidate_comparison.py``).

Every rung times the same amount of work - about 80,000 points per round, whatever the batch size - so the rungs are comparable to each other, and both answers are read off the ratio *within* a rung rather than off absolute times across rungs, which is what keeps drift over the run out of the curve. Points are drawn without replacement inside a batch: a repeated coordinate would be answered from the batch's own cell lookup and would flatter exactly the effect being measured.

The ladder runs well past where either curve levels off, because where batching stops improving can only be read from rungs *beyond* it: a ladder that ends on the knee cannot tell a plateau from a curve still falling. Its top rungs need more points than the committed benchmark fixtures hold, so each fixture is extended with points drawn by the fixture generator's own sampler and classified by its own rule - the same population, not merely the same label.

The coordinate arrays are prepared before the clock starts, in the contiguous ``float64`` form the batch API takes without copying. A caller holding Python lists pays one conversion per axis per call on top of what these rows show.

**The two answers do not survive a noisy machine equally well.** Where batching starts paying is a comparison *within* one rung, so drift over the run cancels out of it and it reproduces. Where it stops improving is the batched call's per-point time compared *across* rungs, which drift moves directly - so it is quoted only when the control below certifies that the ladder measured one thing, and withheld when it does not.



The sweep
---------


.. image:: batch_break_even_sweep.svg

The upper panel is the best-round speed-up; the lower one is the share of rounds the batched call won, which assumes nothing about how the noise is distributed. A difference is believed only where both agree, so the shaded band - where the crossing lies - is exactly where the upper panel passes 1.0 and the lower one passes one half. Hollow markers are rungs neither estimator resolves. An arrow marks where a curve stops improving, and is drawn only when the control certifies the run, the same rule the headline follows.

The dotted rule at 128 is not a measurement artefact: ``ZoneNames.names_of`` converts ids to names with a Python loop below that size and a numpy gather at or above it, so the per-point cost steps there.



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
   * - 1
     - 1.86µs
     - 38.5µs
     - 0.05x
     - 0 of 61
     - slower
   * - 10
     - 1.45µs
     - 5.17µs
     - 0.28x
     - 0 of 61
     - slower
   * - 20
     - 1.49µs
     - 3.02µs
     - 0.49x
     - 0 of 61
     - slower
   * - 50
     - 1.57µs
     - 1.50µs
     - 1.05x
     - 61 of 61
     - faster
   * - 100
     - 1.57µs
     - 948ns
     - 1.65x
     - 61 of 61
     - faster
   * - 127
     - 1.55µs
     - 818ns
     - 1.90x
     - 61 of 61
     - faster
   * - 128
     - 1.39µs
     - 743ns
     - 1.87x
     - 61 of 61
     - faster
   * - 500
     - 1.36µs
     - 385ns
     - 3.54x
     - 61 of 61
     - faster
   * - 1,000
     - 1.36µs
     - 315ns
     - 4.31x
     - 61 of 61
     - faster
   * - 2,000
     - 1.35µs
     - 284ns
     - 4.75x
     - 61 of 61
     - faster
   * - 5,000
     - 1.47µs
     - 254ns
     - 5.81x
     - 61 of 61
     - faster
   * - 10,000
     - 1.47µs
     - 246ns
     - 5.98x
     - 61 of 61
     - faster
   * - 20,000
     - 1.52µs
     - 246ns
     - 6.19x
     - 61 of 61
     - faster


The crossing is reported as the interval (20, 50] rather than as a number, because that is all a ladder of discrete sizes can establish. The rungs inside it read ``no difference`` or ``unresolved`` by construction: that is what it means for the crossing to be in there, not a defect in the run.

Control: the scalar loop answers the same points at every rung, so its per-point time should not depend on the batch size. Across the 12 rungs at or above N=10 it spread **16.7 %** (1.35µs to 1.57µs), against a 15 % threshold - **above the threshold**, so read the curve with suspicion and re-measure on a quieter machine. It is published as the reader's check and is never divided into anything. The smaller rungs are excluded because the harness's own per-batch cost lands on them divided by a very small N.



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
     - 1.51µs
     - 36.5µs
     - 0.04x
     - 0 of 61
     - slower
   * - 10
     - 1.16µs
     - 4.17µs
     - 0.28x
     - 0 of 61
     - slower
   * - 20
     - 1.15µs
     - 2.26µs
     - 0.51x
     - 0 of 61
     - slower
   * - 50
     - 1.06µs
     - 959ns
     - 1.10x
     - 61 of 61
     - faster
   * - 100
     - 1.07µs
     - 530ns
     - 2.02x
     - 61 of 61
     - faster
   * - 127
     - 1.06µs
     - 432ns
     - 2.45x
     - 61 of 61
     - faster
   * - 128
     - 1.06µs
     - 387ns
     - 2.74x
     - 61 of 61
     - faster
   * - 500
     - 1.05µs
     - 120ns
     - 8.77x
     - 61 of 61
     - faster
   * - 1,000
     - 1.07µs
     - 74.4ns
     - 14.3x
     - 61 of 61
     - faster
   * - 2,000
     - 1.05µs
     - 48.8ns
     - 21.6x
     - 61 of 61
     - faster
   * - 5,000
     - 1.06µs
     - 31.8ns
     - 33.2x
     - 61 of 61
     - faster
   * - 10,000
     - 1.05µs
     - 26.0ns
     - 40.5x
     - 61 of 61
     - faster
   * - 20,000
     - 1.05µs
     - 23.2ns
     - 45.1x
     - 61 of 61
     - faster


The crossing is reported as the interval (20, 50] rather than as a number, because that is all a ladder of discrete sizes can establish. The rungs inside it read ``no difference`` or ``unresolved`` by construction: that is what it means for the crossing to be in there, not a defect in the run.

Control: the scalar loop answers the same points at every rung, so its per-point time should not depend on the batch size. Across the 12 rungs at or above N=10 it spread **10.9 %** (1.05µs to 1.16µs), against a 15 % threshold - so the ladder measured one thing. It is published as the reader's check and is never divided into anything. The smaller rungs are excluded because the harness's own per-batch cost lands on them divided by a very small N.



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

**Points Per Round**: ~80,000

**Coordinate Access**: memory mapped
