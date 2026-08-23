

TimezoneFinder Memory Footprint
===============================


**~1.13 MiB** allocated in the default mode, **~62.1 MiB** with ``in_memory=True`` - the default maps the coordinate data instead of reading it, which is what keeps it viable in a constrained container.

*Measured on Darwin arm64, Python 3.14.2, using the Numba JIT point-in-polygon path.* Continuous integration tracks a different one - the C extension without Numba, what a plain ``pip install timezonefinder`` gives you - so these figures are not comparable to the trend chart. See :doc:`benchmarking_methodology`.



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
     - 176 KiB
     - 176 KiB
     - n/a
     - n/a
   * - TimezoneFinder[file_based]
     - 248 KiB
     - 1.13 MiB
     - 400 KiB
     - 32.4 MiB
   * - TimezoneFinder[in_memory]
     - 61.3 MiB
     - 62.1 MiB
     - 61.6 MiB
     - 63.1 MiB




Summary
~~~~~~~


* Importing the package costs **95.7 MiB** of resident memory before any timezone data is touched.

* ``in_memory=True`` holds **62.1 MiB** on the heap against **1.13 MiB** for the default file-based mode (55.2x more). That is the price of the speedup documented in :doc:`benchmark_results_timezonefinding`.

* The file-based mode's resident set grows from **400 KiB** at construction to **32.4 MiB** once the workload has run, as the kernel faults in the mapped coordinate pages actually queried. Unlike the in-memory mode's allocation, these pages are reclaimable under memory pressure.

* ``TimezoneFinderL`` holds **176 KiB**: it consults only the shortcut index and loads no polygon data at all, which is why it takes no ``in_memory`` variant here.

.. note::

   These numbers describe the data structures this package builds, not a container sizing recommendation: add the interpreter and the import cost above, and note that RSS attribution of memory-mapped pages is platform-specific.
