

TimezoneFinder Memory Footprint
===============================


**~2.24 MiB** allocated in the default mode, **~32.6 MiB** with ``in_memory=True`` - the default maps the coordinate data instead of reading it, which is what keeps it viable in a constrained container.

*Measured on Darwin arm64, Python 3.14.2, using the C extension (clang) point-in-polygon path.* This is the configuration continuous integration tracks - what a plain ``pip install timezonefinder`` gives you. See :doc:`benchmarking_methodology`.



System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.14.2 (CPython)

**NumPy Version**: 2.3.5

**Platform**: Darwin arm64

**Processor**: arm



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


**Fixture Version**: 3

**Timezone Data Version**: 2026c



Benchmark Configuration
~~~~~~~~~~~~~~~~~~~~~~~


**Measurement Source**: scripts/measure_memory.py

**Workload Size**: 10,000

Every figure below is a **delta**, measured in a fresh subprocess per configuration against a baseline taken once the package is imported. The import itself dominates any of them and is reported separately: it is the cost of NumPy and H3, paid once per process whichever finder you build.

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
     - 1.01 MiB
     - 1.01 MiB
     - 1.62 MiB
     - 1.69 MiB
   * - TimezoneFinder[file_based]
     - 2.24 MiB
     - 2.24 MiB
     - 3.77 MiB
     - 12.2 MiB
   * - TimezoneFinder[in_memory]
     - 32.6 MiB
     - 32.6 MiB
     - 33.7 MiB
     - 33.8 MiB




Summary
~~~~~~~


* Importing the package costs **16.8 MiB** of resident memory before any timezone data is touched.

* ``in_memory=True`` holds **32.6 MiB** on the heap against **2.24 MiB** for the default file-based mode (14.6x more). That is the price of the speedup documented in :doc:`benchmark_results_timezonefinding`.

* The file-based mode's resident set grows from **3.77 MiB** at construction to **12.2 MiB** once the workload has run, as the kernel faults in the mapped coordinate pages actually queried. Unlike the in-memory mode's allocation, these pages are reclaimable under memory pressure.

* ``TimezoneFinderL`` holds **1.01 MiB**: it consults only the shortcut index and loads no polygon data at all, which is why it takes no ``in_memory`` variant here.

.. note::

   These numbers describe the data structures this package builds, not a container sizing recommendation: add the interpreter and the import cost above, and note that RSS attribution of memory-mapped pages is platform-specific.
