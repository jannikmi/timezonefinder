

Point-in-Polygon Acceleration Paths
===================================


**Numba JIT: 1.03x the C extension** on ``TimezoneFinder.timezone_at()`` over uniformly random points (slower).

**pure Python: 40.7x the C extension** on ``TimezoneFinder.timezone_at()`` over uniformly random points (slower).

*Measured on Darwin arm64, Apple M1 Pro, Python 3.14.2, across 2 environments on one machine.*

The three point-in-polygon implementations, measured against each other rather than across commits. ``timezonefinder/utils.py`` binds one of them at import time, so which one a process runs is decided by its environment: Numba when it is importable, the C extension when it is not but the extension loaded, and the plain Python function when neither is available. See :doc:`benchmarking_methodology`.

.. note::

   Nothing on this page is on the continuous-integration trend chart, which tracks the C extension alone - what a plain ``pip install timezonefinder`` runs. These are on-demand measurements, taken by ``make acceleration-paths``.



How this is measured
--------------------


Numba and pure Python are one source decorated or not, so **no process holds both**: what a process does hold is the C extension plus whichever of the two its environment produced. Each row below is therefore a paired comparison inside one process - the same random draw handed to both candidates, the order alternating round by round, and two estimators reported so that a difference neither can demonstrate reads as ``unresolved`` rather than as a number (``benchmarks/candidate_comparison.py``).

That also fixes what this page will **not** do: divide one environment's column into the other's. Two runs in two processes can alternate nothing and share no draw, so a Numba-against-pure-Python ratio taken that way would rest on the single estimator this repository has already been misled by (:doc:`benchmarking_methodology`). The two measured pairs are published; the third ratio is not derived from them.



The kernel a lookup reaches
---------------------------


``PolygonArray.pip`` over the packed payload, one pass over 2,500 committed (point, ring) pairs per round, split by polygon size so the largest rings are not hidden behind an average over a mostly-small population.



Numba JIT against the C extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1
   :widths: 19 25 12 22 13 9

   * - Workload
     - C extension (clang)
     - Numba JIT
     - Relative to clang
     - Rounds won
     - Verdict
   * - small polygons
     - 912µs
     - 1.71ms
     - 1.87x
     - 0 of 61
     - slower
   * - medium polygons
     - 973µs
     - 1.80ms
     - 1.85x
     - 0 of 61
     - slower
   * - large polygons
     - 1.41ms
     - 2.68ms
     - 1.89x
     - 0 of 61
     - slower




pure Python against the C extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1
   :widths: 19 23 14 22 13 9

   * - Workload
     - C extension (clang)
     - pure Python
     - Relative to clang
     - Rounds won
     - Verdict
   * - small polygons
     - 923µs
     - 3.73ms
     - 4.04x
     - 0 of 15
     - slower
   * - medium polygons
     - 1.03ms
     - 82.1ms
     - 79.5x
     - 0 of 15
     - slower
   * - large polygons
     - 1.46ms
     - 285ms
     - 196x
     - 0 of 15
     - slower




What a caller actually pays
---------------------------


``TimezoneFinder.timezone_at()`` in memory, over the same committed point fixtures the other pages use. The kernel ratio above **bounds** these and does not predict them: the H3 shortcut index answers a unique-shortcut query outright, so no point-in-polygon test runs at all and the two paths are measuring the same code.



Numba JIT against the C extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1
   :widths: 27 20 10 18 11 14

   * - Workload
     - C extension (clang)
     - Numba JIT
     - Relative to clang
     - Rounds won
     - Verdict
   * - random points
     - 3.14ms
     - 3.24ms
     - 1.03x
     - 21 of 61
     - slower
   * - unique-shortcut points
     - 2.16ms
     - 2.19ms
     - 1.01x
     - 36 of 61
     - no difference
   * - ambiguous-shortcut points
     - 12.4ms
     - 13.1ms
     - 1.06x
     - 5 of 61
     - slower




pure Python against the C extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1
   :widths: 25 20 12 18 11 14

   * - Workload
     - C extension (clang)
     - pure Python
     - Relative to clang
     - Rounds won
     - Verdict
   * - random points
     - 3.08ms
     - 125ms
     - 40.7x
     - 0 of 15
     - slower
   * - unique-shortcut points
     - 2.01ms
     - 1.99ms
     - 0.99x
     - 8 of 15
     - no difference
   * - ambiguous-shortcut points
     - 12.7ms
     - 1.55s
     - 122x
     - 0 of 15
     - slower




How comparable the two runs are
-------------------------------


Both runs measure the C extension, so its two timings are the same quantity measured twice and their spread says how much of the gap between the tables above is the environment rather than the point-in-polygon path. Published rather than used as a gate, because nothing here divides one run into the other.



The kernel a lookup reaches
~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1
   :widths: 10 34 36 8 12

   * - Workload
     - clang, in the Numba JIT run
     - clang, in the pure Python run
     - Spread
     - Within 3 %
   * - small
     - 912µs
     - 923µs
     - 1.2 %
     - yes
   * - medium
     - 973µs
     - 1.03ms
     - 6.0 %
     - **no**
   * - large
     - 1.41ms
     - 1.46ms
     - 2.9 %
     - yes




What a caller actually pays
~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1
   :widths: 20 30 32 7 11

   * - Workload
     - clang, in the Numba JIT run
     - clang, in the pure Python run
     - Spread
     - Within 3 %
   * - random
     - 3.14ms
     - 3.08ms
     - 1.7 %
     - yes
   * - unique shortcut
     - 2.16ms
     - 2.01ms
     - 7.7 %
     - **no**
   * - ambiguous shortcut
     - 12.4ms
     - 12.7ms
     - 2.2 %
     - yes


Two things move these rows. The first is ordinary run-to-run variation: the C kernel is the same compiled code in both runs, so wherever its two timings differ that is the floor for comparing anything *across* the two processes - and it is wider than the 3 % a paired comparison inside one process resolves, which is the whole reason this page does not divide one run into the other.

The second is specific to the Numba run: **installing Numba changes more than the point-in-polygon kernel**. ``utils.validate_coordinates`` calls two ``njit``-compiled scalar helpers when Numba is importable and two plain comparisons when it is not, and every query pays that on the way in, before any geometry. So a C-extension lookup measured beside Numba is not quite the C-extension lookup a plain install runs - and the effect is largest on the unique-shortcut rows, where validation is most of the query and no polygon is ever tested.
