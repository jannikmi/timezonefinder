

Timezone Finding Performance Benchmark
======================================




System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.13.11 (CPython)

**NumPy Version**: 2.2.6

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
     - 1.1e-04
     - 9k
   * - TimezoneFinder.certain_timezone_at()
     - 1.0e-04
     - 10k
   * - timezone_at_land()
     - 4.1e-06
     - 243k
   * - TimezoneFinder.timezone_at_land()
     - 4.1e-06
     - 245k
   * - timezone_at()
     - 3.8e-06
     - 266k
   * - TimezoneFinder.timezone_at()
     - 3.7e-06
     - 267k
   * - unique_timezone_at()
     - 6.2e-07
     - 1612k
   * - TimezoneFinder.unique_timezone_at()
     - 5.7e-07
     - 1744k
   * - TimezoneFinderL.unique_timezone_at()
     - 5.7e-07
     - 1744k
   * - TimezoneFinderL.timezone_at_land()
     - 8.0e-07
     - 1251k
   * - TimezoneFinderL.timezone_at()
     - 5.8e-07
     - 1738k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - certain_timezone_at()
     - 7.5e-05
     - 13k
   * - TimezoneFinder.certain_timezone_at()
     - 4.8e-04
     - 2k
   * - timezone_at_land()
     - 4.3e-06
     - 233k
   * - TimezoneFinder.timezone_at_land()
     - 4.0e-06
     - 249k
   * - timezone_at()
     - 3.8e-06
     - 266k
   * - TimezoneFinder.timezone_at()
     - 3.4e-06
     - 296k
   * - unique_timezone_at()
     - 9.0e-07
     - 1113k
   * - TimezoneFinder.unique_timezone_at()
     - 6.5e-07
     - 1546k
   * - TimezoneFinderL.unique_timezone_at()
     - 8.5e-07
     - 1182k
   * - TimezoneFinderL.timezone_at_land()
     - 1.1e-06
     - 884k
   * - TimezoneFinderL.timezone_at()
     - 5.9e-07
     - 1701k




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
     - 1.7e-03
     - 1k
   * - TimezoneFinder.timezone_at_land()
     - 3.2e-06
     - 315k
   * - TimezoneFinder.timezone_at()
     - 2.9e-06
     - 348k
   * - TimezoneFinder.unique_timezone_at()
     - 5.6e-07
     - 1793k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - TimezoneFinder.certain_timezone_at()
     - 7.6e-05
     - 13k
   * - TimezoneFinder.timezone_at_land()
     - 2.1e-06
     - 474k
   * - TimezoneFinder.timezone_at()
     - 1.8e-06
     - 564k
   * - TimezoneFinder.unique_timezone_at()
     - 5.4e-07
     - 1868k
