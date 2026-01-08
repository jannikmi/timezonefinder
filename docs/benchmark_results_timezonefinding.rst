

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
     - 1.0e-04
     - 10k
   * - TimezoneFinder.certain_timezone_at()
     - 9.7e-05
     - 10k
   * - timezone_at_land()
     - 4.3e-06
     - 231k
   * - TimezoneFinder.timezone_at_land()
     - 4.3e-06
     - 231k
   * - timezone_at()
     - 4.1e-06
     - 247k
   * - TimezoneFinder.timezone_at()
     - 4.0e-06
     - 247k
   * - unique_timezone_at()
     - 6.3e-07
     - 1584k
   * - TimezoneFinder.unique_timezone_at()
     - 5.8e-07
     - 1722k
   * - TimezoneFinderL.unique_timezone_at()
     - 5.9e-07
     - 1694k
   * - TimezoneFinderL.timezone_at_land()
     - 8.8e-07
     - 1134k
   * - TimezoneFinderL.timezone_at()
     - 6.1e-07
     - 1646k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - certain_timezone_at()
     - 1.2e-04
     - 8k
   * - TimezoneFinder.certain_timezone_at()
     - 7.3e-05
     - 14k
   * - timezone_at_land()
     - 3.1e-06
     - 326k
   * - TimezoneFinder.timezone_at_land()
     - 3.0e-06
     - 330k
   * - timezone_at()
     - 2.7e-06
     - 365k
   * - TimezoneFinder.timezone_at()
     - 2.7e-06
     - 369k
   * - unique_timezone_at()
     - 6.1e-07
     - 1653k
   * - TimezoneFinder.unique_timezone_at()
     - 5.6e-07
     - 1773k
   * - TimezoneFinderL.unique_timezone_at()
     - 5.9e-07
     - 1687k
   * - TimezoneFinderL.timezone_at_land()
     - 8.8e-07
     - 1140k
   * - TimezoneFinderL.timezone_at()
     - 6.1e-07
     - 1652k




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
     - 3.1e-06
     - 318k
   * - TimezoneFinder.timezone_at()
     - 2.8e-06
     - 354k
   * - TimezoneFinder.unique_timezone_at()
     - 5.7e-07
     - 1755k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - TimezoneFinder.certain_timezone_at()
     - 7.0e-05
     - 14k
   * - TimezoneFinder.timezone_at_land()
     - 2.2e-06
     - 447k
   * - TimezoneFinder.timezone_at()
     - 1.9e-06
     - 524k
   * - TimezoneFinder.unique_timezone_at()
     - 5.7e-07
     - 1757k
