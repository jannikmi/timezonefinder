

Timezone Finding Performance Benchmark
======================================




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



Benchmark Configuration
~~~~~~~~~~~~~~~~~~~~~~~


**Benchmark Source**: pytest-benchmark

**Batch Size**: 1,000

Each benchmark times one pass over 1,000 fixed, committed query points (see benchmarks/conftest.py); rows below report seconds-per-batch. Divide by the batch size for seconds-per-query.



In-Memory Mode
~~~~~~~~~~~~~~




TimezoneFinder.timezone_at()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 14 14 14 14 14 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
   * - ambiguous-shortcut points, in-memory
     - 8.47e-03s
     - 8.44e-03s
     - 9.68e-05s
     - 8.38e-03s
     - 8.86e-03s
     - 114
   * - on-land points, in-memory
     - 4.56e-03s
     - 4.54e-03s
     - 5.59e-05s
     - 4.50e-03s
     - 4.97e-03s
     - 193
   * - random points, in-memory
     - 3.42e-03s
     - 3.41e-03s
     - 2.82e-05s
     - 3.39e-03s
     - 3.55e-03s
     - 182
   * - unique-shortcut points, in-memory
     - 1.06e-03s
     - 1.05e-03s
     - 1.46e-05s
     - 1.03e-03s
     - 1.21e-03s
     - 774




TimezoneFinder.timezone_at_land()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 14 14 14 14 14 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
   * - in-memory
     - 4.99e-03s
     - 4.97e-03s
     - 8.57e-05s
     - 4.93e-03s
     - 5.90e-03s
     - 188




File-Based Mode
~~~~~~~~~~~~~~~




TimezoneFinder.timezone_at()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 14 14 14 14 14 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
   * - ambiguous-shortcut points, file-based
     - 1.27e-02s
     - 1.27e-02s
     - 1.25e-04s
     - 1.26e-02s
     - 1.34e-02s
     - 68
   * - on-land points, file-based
     - 6.19e-03s
     - 6.18e-03s
     - 4.30e-05s
     - 6.15e-03s
     - 6.45e-03s
     - 128
   * - random points, file-based
     - 4.76e-03s
     - 4.76e-03s
     - 2.40e-05s
     - 4.74e-03s
     - 4.93e-03s
     - 154
   * - unique-shortcut points, file-based
     - 1.05e-03s
     - 1.05e-03s
     - 3.63e-05s
     - 1.03e-03s
     - 1.64e-03s
     - 818




TimezoneFinder.timezone_at_land()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 14 14 14 14 14 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
   * - file-based
     - 6.69e-03s
     - 6.67e-03s
     - 6.49e-05s
     - 6.63e-03s
     - 7.27e-03s
     - 119




TimezoneFinderL (heuristic-only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. note::

   TimezoneFinderL does not support in-memory mode; shortcuts are always loaded from disk.



TimezoneFinderL.timezone_at() (ambiguous-shortcut points)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 14 14 14 14 14 14 14

   * - Configuration
     - Mean
     - Median
     - StdDev
     - Min
     - Max
     - Rounds
   * - -
     - 1.18e-03s
     - 1.17e-03s
     - 3.39e-05s
     - 1.15e-03s
     - 1.59e-03s
     - 726
