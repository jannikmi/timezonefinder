

Point-in-Polygon Acceleration Paths
===================================


**Numba JIT: 1.04x the C extension** on ``TimezoneFinder.timezone_at()`` over uniformly random points (slower).

**pure Python: 34.1x the C extension** on ``TimezoneFinder.timezone_at()`` over uniformly random points (slower).

*Measured on Darwin arm64, Apple M1 Pro, Python 3.14.2, across 2 environments on one machine.*

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
     - 869µs
     - 1.65ms
     - 1.90x
     - 0 of 61
     - slower
   * - medium polygons
     - 917µs
     - 1.74ms
     - 1.89x
     - 0 of 61
     - slower
   * - large polygons
     - 1.31ms
     - 2.58ms
     - 1.96x
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
     - 862µs
     - 2.73ms
     - 3.17x
     - 0 of 15
     - slower
   * - medium polygons
     - 949µs
     - 72.4ms
     - 76.3x
     - 0 of 15
     - slower
   * - large polygons
     - 1.37ms
     - 246ms
     - 180x
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
     - 1.60ms
     - 1.67ms
     - 1.04x
     - 8 of 61
     - slower
   * - unique-shortcut points
     - 1.43ms
     - 1.43ms
     - 1.00x
     - 22 of 61
     - unresolved
   * - ambiguous-shortcut points
     - 6.72ms
     - 8.08ms
     - 1.20x
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
     - 1.62ms
     - 55.1ms
     - 34.1x
     - 0 of 15
     - slower
   * - unique-shortcut points
     - 1.38ms
     - 1.39ms
     - 1.00x
     - 6 of 15
     - no difference
   * - ambiguous-shortcut points
     - 6.97ms
     - 1.64s
     - 235x
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
     - 2.97 MiB
     - 3.25 MiB
     - +288 KiB
   * - added by ``TimezoneFinder()``
     - 15.0 MiB
     - 15.1 MiB
     - +64.0 KiB
   * - added by the first query
     - 80.0 KiB
     - 80.0 KiB
     - 0 B
   * - **the whole process, once the first answer is out**
     - 40.3 MiB
     - 40.4 MiB
     - +112 KiB


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
     - 9.18ms
     - 8.68ms
     - -504µs
   * - ``TimezoneFinder()``
     - 61.5ms
     - 55.3ms
     - -6.17ms
   * - the first query
     - 60.4µs
     - 40.1µs
     - -20.3µs
   * - **the whole way to the first answer**
     - 70.7ms
     - 64.0ms
     - -6.69ms


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
     - 869µs
     - 862µs
     - 0.8 %
     - yes
   * - medium
     - 917µs
     - 949µs
     - 3.5 %
     - **no**
   * - large
     - 1.31ms
     - 1.37ms
     - 4.4 %
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
     - 1.60ms
     - 1.62ms
     - 0.8 %
     - yes
   * - unique shortcut
     - 1.43ms
     - 1.38ms
     - 3.3 %
     - **no**
   * - ambiguous shortcut
     - 6.72ms
     - 6.97ms
     - 3.7 %
     - **no**


Two things move these rows. The first is ordinary run-to-run variation: the C kernel is the same compiled code in both runs, so wherever its two timings differ that is the floor for comparing anything *across* the two processes - and it is wider than the 3 % a paired comparison inside one process resolves, which is the whole reason this page does not divide one run into the other.

The second used to be specific to the Numba run and is not any more: ``timezonefinder/utils.py`` imports ``utils_numba`` only where the C extension is missing, so a process that merely *has* Numba installed no longer imports it - same kernel, same imports, same resident set as a plain install, which is what the section below now measures. What still differs is everything that reaches into ``utils_numba`` on purpose: the kernel rows on this page, and ``benchmarks/test_inside_polygon.py``'s ``*_python`` rows, which are JIT-compiled wherever Numba is installed.
