

Point-in-Polygon Acceleration Paths
===================================


**Numba JIT: 1.05x the C extension** on ``TimezoneFinder.timezone_at()`` over uniformly random points (slower).

**pure Python: 40.1x the C extension** on ``TimezoneFinder.timezone_at()`` over uniformly random points (slower).

*Measured on Linux x86_64, Intel(R) Xeon(R) Platinum 8370C CPU @ 2.8000 GHz, Python 3.13.16, across 2 environments on one machine.*

The three point-in-polygon implementations, measured against each other rather than across commits. ``timezonefinder/utils.py`` binds one of them at import time, so which one a process runs is decided by its environment: the C extension wherever it loaded, the Numba-compiled function where it did not and ``numba`` is importable, and the plain Python function where neither is available. The rows below are therefore measured by rebinding the kernel rather than by installing a different environment. See :doc:`benchmarking_methodology`.

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
     - 1.67ms
     - 2.70ms
     - 1.62x
     - 0 of 61
     - slower
   * - medium polygons
     - 1.83ms
     - 2.90ms
     - 1.59x
     - 0 of 61
     - slower
   * - large polygons
     - 3.63ms
     - 4.97ms
     - 1.37x
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
     - 1.67ms
     - 5.65ms
     - 3.38x
     - 0 of 15
     - slower
   * - medium polygons
     - 1.91ms
     - 153ms
     - 80.3x
     - 0 of 15
     - slower
   * - large polygons
     - 3.73ms
     - 435ms
     - 117x
     - 0 of 15
     - slower




What a caller actually pays
---------------------------


``TimezoneFinder.timezone_at()`` in memory, over the same committed point fixtures the other pages use. The kernel ratio above **bounds** these and does not predict them: the shortcut index answers a unique-shortcut query outright, so no point-in-polygon test runs at all and the two paths are measuring the same code.



Numba JIT against the C extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1
   :widths: 28 21 10 19 11 11

   * - Workload
     - C extension (clang)
     - Numba JIT
     - Relative to clang
     - Rounds won
     - Verdict
   * - random points
     - 2.87ms
     - 3.02ms
     - 1.05x
     - 3 of 61
     - slower
   * - unique-shortcut points
     - 2.49ms
     - 2.48ms
     - 1.00x
     - 38 of 61
     - unresolved
   * - ambiguous-shortcut points
     - 13.9ms
     - 15.7ms
     - 1.14x
     - 0 of 61
     - slower




pure Python against the C extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1
   :widths: 27 21 12 18 11 11

   * - Workload
     - C extension (clang)
     - pure Python
     - Relative to clang
     - Rounds won
     - Verdict
   * - random points
     - 2.95ms
     - 119ms
     - 40.1x
     - 0 of 15
     - slower
   * - unique-shortcut points
     - 2.44ms
     - 2.45ms
     - 1.00x
     - 4 of 15
     - unresolved
   * - ambiguous-shortcut points
     - 13.7ms
     - 3.48s
     - 254x
     - 0 of 15
     - slower




What installing Numba costs before any query
--------------------------------------------


Speed is only one consequence of installing the ``numba`` extra, and it is the only one the tables above can see: a paired comparison runs both candidates in one process, which has already imported whatever its environment holds. The rows below are therefore not paired - each is a fresh process that imports the package, constructs a default ``TimezoneFinder()`` and answers one query, measured by ``scripts/_startup_probe.py`` and reported as the median of its repetitions. Both environments hold the C extension and both *bind* it, so the two processes run the same kernel and differ in exactly one thing - whether Numba is installed beside it. The last column is therefore what the extra costs an installation that already has a working extension, and since the package imports Numba only where the JIT kernel is what answers queries, the honest answer is expected to be nothing: a row that shows otherwise means something reached into ``utils_numba`` on the way to a lookup again.



Resident memory
~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1
   :widths: 56 14 11 19

   * - Step
     - Plain install
     - With Numba
     - Cost of the extra
   * - added by ``import timezonefinder``
     - 4.63 MiB
     - 4.66 MiB
     - +32.0 KiB
   * - added by ``TimezoneFinder()``
     - 19.8 MiB
     - 19.9 MiB
     - +48.0 KiB
   * - added by the first query
     - 132 KiB
     - 128 KiB
     - -4.00 KiB
   * - **the whole process, once the first answer is out**
     - 37.7 MiB
     - 37.7 MiB
     - -24.0 KiB


Every row but the last is what that step added; the last is the whole process, which is the figure a container memory limit is set against. The difference is the Numba and ``llvmlite`` import plus the code it compiles, and it is paid per process - a worker pool pays it once per worker, and it does not shrink for ``TimezoneFinderL`` or for the memory-mapped default mode, because it is not boundary data (:doc:`benchmark_results_memory` measures that part).



Time to the first answer
~~~~~~~~~~~~~~~~~~~~~~~~



.. list-table::
   :header-rows: 1
   :widths: 48 17 13 22

   * - Step
     - Plain install
     - With Numba
     - Cost of the extra
   * - ``import timezonefinder``
     - 29.1ms
     - 28.2ms
     - -837µs
   * - ``TimezoneFinder()``
     - 111ms
     - 110ms
     - -897µs
   * - the first query
     - 60.9µs
     - 55.3µs
     - -5.64µs
   * - **the whole way to the first answer**
     - 140ms
     - 139ms
     - -1.74ms


Where there is a compilation at all it lands in the construction row rather than in the query one: ``timezonefinder/utils_numba.py`` declares eager signatures, so the kernels are compiled when that module is first imported, which constructing a finder triggers on an installation without the C extension. Numba caches that output on disk beside the installed package, so the figures here are the steady state - the median over repetitions discards the one process that compiled - and the *first* process in a fresh environment pays more. Where the installed package directory is read-only or thrown away between runs, every process pays it. Later queries are what the tables above measure; this is what a process pays before the first of them, and a short-lived process or a cold-started function pays it per invocation.



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
     - 1.67ms
     - 1.67ms
     - 0.2 %
     - yes
   * - medium
     - 1.83ms
     - 1.91ms
     - 4.4 %
     - **no**
   * - large
     - 3.63ms
     - 3.73ms
     - 2.6 %
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
     - 2.87ms
     - 2.95ms
     - 2.8 %
     - yes
   * - unique shortcut
     - 2.49ms
     - 2.44ms
     - 1.8 %
     - yes
   * - ambiguous shortcut
     - 13.9ms
     - 13.7ms
     - 1.2 %
     - yes


Two things move these rows. The first is ordinary run-to-run variation: the C kernel is the same compiled code in both runs, so wherever its two timings differ that is the floor for comparing anything *across* the two processes - and it is wider than the 3 % a paired comparison inside one process resolves, which is the whole reason this page does not divide one run into the other.

The second used to be specific to the Numba run and is not any more: ``timezonefinder/utils.py`` imports ``utils_numba`` only where the C extension is missing, so a process that merely *has* Numba installed no longer imports it - same kernel, same imports, same resident set as a plain install, which is what the section below now measures. What still differs is everything that reaches into ``utils_numba`` on purpose: the kernel rows on this page, and ``benchmarks/test_inside_polygon.py``'s ``*_python`` rows, which are JIT-compiled wherever Numba is installed.
