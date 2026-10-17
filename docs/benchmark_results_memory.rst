

TimezoneFinder Memory Footprint
===============================


**~1.78 MiB** allocated in the default mode, **~32.4 MiB** with ``in_memory=True`` - the default maps the coordinate data instead of reading it, which is what keeps it viable in a constrained container.

*Measured on Linux x86_64, AMD EPYC 7763 64-Core Processor @ 3.2441 GHz, Python 3.13.16, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.



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


**Measurement Source**: scripts/measure_memory.py

**Workload Size**: 10,000

Every figure below is a **delta**, measured in a fresh subprocess per configuration against a baseline taken once the package is imported. The import itself dominates any of them and is reported separately: it is the cost of NumPy, paid once per process whichever finder you build.

``Heap`` is what ``tracemalloc`` accounts for - Python and NumPy allocations. ``RSS`` is the process resident set, which additionally counts memory-mapped pages. The two differ by design and the gap is the point: with ``in_memory=False`` the coordinate data is mapped rather than read, so it becomes resident only as the 10,000 lookups of the workload fault its pages in - which is why the ``after init`` and ``after workload`` columns are both shown.



Results
~~~~~~~



.. list-table::
   :header-rows: 1
   :widths: 28 16 21 15 20

   * - Configuration
     - Heap after init
     - Heap after workload
     - RSS after init
     - RSS after workload
   * - TimezoneFinderL
     - 534 KiB
     - 534 KiB
     - 588 KiB
     - 592 KiB
   * - TimezoneFinder[file_based]
     - 1.78 MiB
     - 1.78 MiB
     - 3.64 MiB
     - 17.9 MiB
   * - TimezoneFinder[in_memory]
     - 32.4 MiB
     - 32.4 MiB
     - 33.8 MiB
     - 33.9 MiB




Summary
~~~~~~~


* Importing the package costs **3.56 MiB** of resident memory before any timezone data is touched.

* ``in_memory=True`` holds **32.4 MiB** on the heap against **1.78 MiB** for the default file-based mode (18.1x more). That is the price of the speedup documented in :doc:`benchmark_results_timezonefinding`.

* The file-based mode's resident set grows from **3.64 MiB** at construction to **17.9 MiB** once the workload has run, as the kernel faults in the mapped coordinate pages actually queried. Unlike the in-memory mode's allocation, these pages are reclaimable under memory pressure.

* ``TimezoneFinderL`` holds **534 KiB**: it consults only the shortcut index and loads no polygon data at all, which is why it takes no ``in_memory`` variant here.

.. note::

   These numbers describe the data structures this package builds, not a container sizing recommendation: add the interpreter and the import cost above, and note that RSS attribution of memory-mapped pages is platform-specific.
