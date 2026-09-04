

Point-in-Polygon Acceleration Paths
===================================


**Numba JIT: 1.02x the C extension** on ``TimezoneFinder.timezone_at()`` over uniformly random points (unresolved).

**pure Python: 40.9x the C extension** on ``TimezoneFinder.timezone_at()`` over uniformly random points (slower).

*Measured on Linux x86_64, AMD EPYC 9V74 80-Core Processor @ 2.5961 GHz, Python 3.13.15, across 2 environments on one machine.*

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
     - 1.62ms
     - 2.70ms
     - 1.66x
     - 0 of 61
     - slower
   * - medium polygons
     - 1.76ms
     - 2.89ms
     - 1.65x
     - 0 of 61
     - slower
   * - large polygons
     - 3.00ms
     - 4.81ms
     - 1.60x
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
     - 1.61ms
     - 5.75ms
     - 3.57x
     - 0 of 15
     - slower
   * - medium polygons
     - 1.85ms
     - 139ms
     - 75.4x
     - 0 of 15
     - slower
   * - large polygons
     - 3.11ms
     - 463ms
     - 149x
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
     - 6.13ms
     - 6.25ms
     - 1.02x
     - 1 of 61
     - unresolved
   * - unique-shortcut points
     - 4.36ms
     - 4.38ms
     - 1.00x
     - 30 of 61
     - no difference
   * - ambiguous-shortcut points
     - 23.0ms
     - 24.4ms
     - 1.06x
     - 0 of 61
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
     - 5.50ms
     - 225ms
     - 40.9x
     - 0 of 15
     - slower
   * - unique-shortcut points
     - 3.46ms
     - 3.44ms
     - 0.99x
     - 9 of 15
     - no difference
   * - ambiguous-shortcut points
     - 21.6ms
     - 2.73s
     - 126x
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
     - 1.62ms
     - 1.61ms
     - 0.7 %
     - yes
   * - medium
     - 1.76ms
     - 1.85ms
     - 5.3 %
     - **no**
   * - large
     - 3.00ms
     - 3.11ms
     - 3.5 %
     - **no**




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
     - 6.13ms
     - 5.50ms
     - 11.6 %
     - **no**
   * - unique shortcut
     - 4.36ms
     - 3.46ms
     - 26.2 %
     - **no**
   * - ambiguous shortcut
     - 23.0ms
     - 21.6ms
     - 6.3 %
     - **no**


Two things move these rows. The first is ordinary run-to-run variation: the C kernel is the same compiled code in both runs, so wherever its two timings differ that is the floor for comparing anything *across* the two processes - and it is wider than the 3 % a paired comparison inside one process resolves, which is the whole reason this page does not divide one run into the other.

The second is specific to the Numba run: **installing Numba changes more than the point-in-polygon kernel**. ``utils.validate_coordinates`` calls two ``njit``-compiled scalar helpers when Numba is importable and two plain comparisons when it is not, and every query pays that on the way in, before any geometry. So a C-extension lookup measured beside Numba is not quite the C-extension lookup a plain install runs - and the effect is largest on the unique-shortcut rows, where validation is most of the query and no polygon is ever tested.
