

TimezoneFinder Memory Footprint
===============================




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


**C Implementation Available**: False

**Numba JIT Available**: True



Performance Optimizations
~~~~~~~~~~~~~~~~~~~~~~~~~


* ✗ Using pure Python point-in-polygon implementation

* ✓ Numba JIT compilation enabled



Benchmark Input Provenance
~~~~~~~~~~~~~~~~~~~~~~~~~~


**Fixture Version**: 2

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
     - 4.47 MiB
     - 4.47 MiB
     - 13.1 MiB
     - 13.2 MiB
   * - TimezoneFinder[file_based]
     - 4.77 MiB
     - 5.67 MiB
     - 13.6 MiB
     - 46.4 MiB
   * - TimezoneFinder[in_memory]
     - 67.8 MiB
     - 68.7 MiB
     - 76.6 MiB
     - 78.1 MiB




Summary
~~~~~~~


* Importing the package costs **95.7 MiB** of resident memory before any timezone data is touched.

* ``in_memory=True`` holds **68.7 MiB** on the heap against **5.67 MiB** for the default file-based mode (12.1x more). That is the price of the speedup documented in :doc:`benchmark_results_timezonefinding`.

* The file-based mode's resident set grows from **13.6 MiB** at construction to **46.4 MiB** once the workload has run, as the kernel faults in the mapped coordinate pages actually queried. Unlike the in-memory mode's allocation, these pages are reclaimable under memory pressure.

* ``TimezoneFinderL`` holds **4.47 MiB**: it consults only the shortcut index and loads no polygon data at all, which is why it takes no ``in_memory`` variant here.

.. note::

   These numbers describe the data structures this package builds, not a container sizing recommendation: add the interpreter and the import cost above, and note that RSS attribution of memory-mapped pages is platform-specific.
