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

Installing the optional ``numba`` dependency JIT-compiles the same routine, and it **takes precedence
over the C extension** when both are available:

.. code-block:: console

    pip install timezonefinder[numba]


.. code-block:: python

    TimezoneFinder.using_numba()  # returns True or False


**Taking precedence is a dispatch rule, not a speed claim** - and the two have been confused here
before, in this documentation. Which path is fastest is a measurement, it has changed as the kernels
and the data format changed, and it is not the same answer for every workload: a query the H3
shortcut index answers outright never reaches a point-in-polygon test at all, so no choice of kernel
moves it.

Read the answer off :doc:`benchmark_results_acceleration_paths`, which measures all three paths
against each other and is regenerated with the rest of the reports. Do not assume the accelerator you
installed is the faster one - check the page, for the workload you actually run.

Installing Numba also changes more than the point-in-polygon kernel: ``validate_coordinates`` then
calls two JIT-compiled scalar helpers rather than two plain comparisons, and every query pays that
before any geometry. That page measures it.

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
