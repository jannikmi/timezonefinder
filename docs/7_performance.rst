.. _performance:

Performance
===========

This page collects the measured numbers and the two knobs that move them. For *why* the lookup is
shaped the way it is, see :doc:`architecture`.


.. _speed-tests:

Benchmark Results
-----------------

.. note::

   All performance reports are generated automatically and may vary based on hardware configuration and dataset version.

The tables below are a snapshot, measured once per data update. For how the timings develop over time, see the `benchmark trend chart <https://jannikmi.github.io/timezonefinder/dev/bench/>`__, which CI appends to on every push to ``master``. It tracks the default installation (C extension, no Numba) on GitHub-hosted runners, so its absolute numbers are not comparable to the tables here.

:doc:`benchmarking_methodology` documents how all of these numbers are produced and what they can and cannot tell you - in particular why two CI runs are not comparable to each other, and where every alert threshold comes from.


Timezone Finding
~~~~~~~~~~~~~~~~

See :doc:`benchmark_results_timezonefinding` for a comprehensive performance comparison between all timezone finding functions, auto-generated from the ``benchmarks/test_timezone_finding.py`` pytest-benchmark suite (``make reports``)

That page ends with the **per-query latency distribution** - p50 through p99.9, measured one query at a time by ``scripts/measure_query_latency.py`` (``make latency``). Read it if you have a latency budget rather than a throughput target: the tables above it time a whole batch, and a batch mean cannot say what the slowest lookups cost.



Batch Lookups
~~~~~~~~~~~~~

See :doc:`benchmark_results_batch_break_even` for the batch size at which ``timezone_names_at()`` starts beating a loop of ``timezone_at()`` calls, and the size beyond which a larger batch buys nothing more - auto-generated from the ``scripts/measure_batch_break_even.py`` sweep (``make batch-break-even``).

Both numbers depend on your hardware *and* on your coordinates, because points sharing an H3 cell are answered together: that page carries the figures for uniformly random points on one machine, and the script takes ``--points your.csv`` to measure yours.


Point in Polygon Checks
~~~~~~~~~~~~~~~~~~~~~~~

See :doc:`benchmark_results_polygon` for detailed point-in-polygon algorithm performance comparison between C and Python implementations, auto-generated from the ``benchmarks/test_inside_polygon.py`` pytest-benchmark suite (``make reports``)


Initialization Time
~~~~~~~~~~~~~~~~~~~

See :doc:`benchmark_results_initialization` for detailed TimezoneFinder initialization performance comparison across different classes and modes, auto-generated from the ``benchmarks/test_initialization.py`` pytest-benchmark suite (``make reports``)


Memory Footprint
~~~~~~~~~~~~~~~~

See :doc:`benchmark_results_memory` for the measured footprint of each class and mode, auto-generated from the ``scripts/measure_memory.py`` harness (``make reports``). Memory is measured separately from the suites above rather than by ``pytest-benchmark``, which times code and would have its timings distorted by the allocation tracking.


Comparison against tzfpy
~~~~~~~~~~~~~~~~~~~~~~~~

See :doc:`benchmark_results_comparison` for a head-to-head measurement against `tzfpy <https://github.com/ringsaturn/tzfpy>`__ - both packages answering the same committed query points in the same process on the same machine - auto-generated from the ``benchmarks/test_comparison.py`` pytest-benchmark suite (``make reports``). :doc:`alternatives` is where the trade-off those numbers price is argued.


C extension
-----------

During installation ``timezonefinder`` automatically tries to compile a C extension implementing the
time critical point in polygon check, which requires a Clang compiler. If that fails - no compiler,
a broken ``cffi`` installation - the package falls back to the pure Python implementation, which is
correct and substantially slower. How much slower depends on polygon size and on how often a query
reaches the geometry at all, so it is measured rather than quoted here:
:doc:`benchmark_results_acceleration_paths` carries the current figures.

To check which implementation is active:

.. code-block:: python

    TimezoneFinder.using_clang_pip()  # returns True or False


Numba
-----

Installing the optional ``numba`` dependency JIT-compiles the same routine, as the **fallback for an
installation that has no C extension**:

.. code-block:: console

    pip install timezonefinder[numba]


.. code-block:: python

    TimezoneFinder.using_numba()  # is Numba compiling this process's helpers?
    TimezoneFinder.using_clang_pip()  # is the C extension what a lookup runs?


The C extension wins wherever it loaded, and the JIT kernel runs only where it did not. Numba used
to take precedence whenever it was importable - an ordering that predates both the extension and the
packed payload the kernels read today, and that :doc:`benchmark_results_acceleration_paths` has since
measured backwards: the JIT kernel is slower than the extension on every polygon size and never
faster on a whole lookup. Where no compiler is available the ordering never mattered, and that is the
case the extra still serves; there its rival is the pure-Python fallback, which the same page
measures in orders of magnitude rather than percent.

The two methods above therefore answer different questions: ``using_numba()`` says Numba is
installed and compiling this process's helper functions, ``using_clang_pip()`` says which kernel a
lookup actually reaches. On an installation holding both, both are ``True``.

**Which path is fastest remains a measurement**, not a property of the dispatch - it has moved as the
kernels and the data format moved, and it is not one answer for every workload, since a query the H3
shortcut index answers outright never reaches a point-in-polygon test at all. Read it off
:doc:`benchmark_results_acceleration_paths`, which is regenerated with the rest of the reports.

**And where it is not the kernel, it now costs nothing.** ``timezonefinder.utils`` imports
``utils_numba`` only in the branch a missing extension takes, and that import is what pulls in Numba -
its signatures are eager, so importing the module compiles it. An installation whose extension loaded
therefore never imports Numba however thoroughly it is installed: same resident memory as a plain
install, no compilation pause, and the footprints on :doc:`benchmark_results_memory` describe the
whole process again.

Where the JIT kernel *is* what answers queries, that cost is real and is what the extra buys the
lookup with: Numba and its LLVM toolchain add more resident memory than the whole packaged boundary
dataset, and the kernels compile when the first finder is constructed. Numba caches the compiled code
beside the installed package, so a read-only or ephemeral installation directory pays that
compilation on every start.

All three implementations compute identical results; they only differ in speed. :doc:`architecture`
explains why the choice is made once at import time and what follows from that - most importantly
that they are separate code paths whose timings must never be compared to each other under one
benchmark name.


In memory mode
--------------

To speed up the computations at the cost of memory consumption and initialisation time, pass ``in_memory=True`` during initialisation.
This causes all binary files to be read into memory.

.. code-block:: python

    tf = TimezoneFinder(in_memory=True)


By default the coordinate data is memory mapped instead, so only the pages a lookup actually touches become resident - which is what keeps the default mode viable in a memory-constrained container. See :doc:`benchmark_results_memory` for the measured cost of each mode.
