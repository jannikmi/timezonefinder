

Timezone Finding Performance Benchmark
======================================




System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.14.2 (CPython)

**NumPy Version**: 2.4.4

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


**Test Queries**: 10,000

**Algorithm Type**: Timezone Finding

**Test Modes**: File-based and In-memory

**Query Types**: On-land points and Random points



File-Based Mode
~~~~~~~~~~~~~~~




Results for 'on land points' (points included in a land timezone)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - certain_timezone_at()
     - 1.3e-04
     - 8k
   * - TimezoneFinder.certain_timezone_at()
     - 9.6e-05
     - 10k
   * - timezone_at_land()
     - 4.5e-06
     - 221k
   * - TimezoneFinder.timezone_at_land()
     - 4.7e-06
     - 213k
   * - timezone_at()
     - 4.3e-06
     - 235k
   * - TimezoneFinder.timezone_at()
     - 4.7e-06
     - 211k
   * - unique_timezone_at()
     - 7.3e-07
     - 1369k
   * - TimezoneFinder.unique_timezone_at()
     - 6.6e-07
     - 1519k
   * - TimezoneFinderL.unique_timezone_at()
     - 6.6e-07
     - 1521k
   * - TimezoneFinderL.timezone_at_land()
     - 9.8e-07
     - 1021k
   * - TimezoneFinderL.timezone_at()
     - 6.8e-07
     - 1470k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - certain_timezone_at()
     - 1.3e-04
     - 8k
   * - TimezoneFinder.certain_timezone_at()
     - 6.7e-05
     - 15k
   * - timezone_at_land()
     - 3.1e-06
     - 320k
   * - TimezoneFinder.timezone_at_land()
     - 3.1e-06
     - 327k
   * - timezone_at()
     - 2.8e-06
     - 360k
   * - TimezoneFinder.timezone_at()
     - 2.7e-06
     - 370k
   * - unique_timezone_at()
     - 6.8e-07
     - 1463k
   * - TimezoneFinder.unique_timezone_at()
     - 6.6e-07
     - 1520k
   * - TimezoneFinderL.unique_timezone_at()
     - 6.6e-07
     - 1509k
   * - TimezoneFinderL.timezone_at_land()
     - 9.6e-07
     - 1046k
   * - TimezoneFinderL.timezone_at()
     - 6.8e-07
     - 1460k




In-Memory Mode
~~~~~~~~~~~~~~


.. note::

   Global functions and TimezoneFinderL do not support in-memory mode.



Results for 'on land points' (points included in a land timezone)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - TimezoneFinder.certain_timezone_at()
     - 9.2e-05
     - 11k
   * - TimezoneFinder.timezone_at_land()
     - 3.3e-06
     - 299k
   * - TimezoneFinder.timezone_at()
     - 3.0e-06
     - 335k
   * - TimezoneFinder.unique_timezone_at()
     - 6.4e-07
     - 1569k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - TimezoneFinder.certain_timezone_at()
     - 1.3e-04
     - 8k
   * - TimezoneFinder.timezone_at_land()
     - 2.5e-06
     - 405k
   * - TimezoneFinder.timezone_at()
     - 2.0e-06
     - 497k
   * - TimezoneFinder.unique_timezone_at()
     - 6.7e-07
     - 1484k
