

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
     - 1.1e-04
     - 9k
   * - TimezoneFinder.certain_timezone_at()
     - 8.6e-05
     - 12k
   * - timezone_at_land()
     - 4.4e-06
     - 225k
   * - TimezoneFinder.timezone_at_land()
     - 4.4e-06
     - 230k
   * - timezone_at()
     - 4.2e-06
     - 241k
   * - TimezoneFinder.timezone_at()
     - 4.1e-06
     - 245k
   * - unique_timezone_at()
     - 6.2e-07
     - 1613k
   * - TimezoneFinder.unique_timezone_at()
     - 5.7e-07
     - 1767k
   * - TimezoneFinderL.unique_timezone_at()
     - 5.7e-07
     - 1752k
   * - TimezoneFinderL.timezone_at_land()
     - 8.5e-07
     - 1183k
   * - TimezoneFinderL.timezone_at()
     - 6.0e-07
     - 1672k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - certain_timezone_at()
     - 7.0e-05
     - 14k
   * - TimezoneFinder.certain_timezone_at()
     - 6.9e-05
     - 14k
   * - timezone_at_land()
     - 3.2e-06
     - 315k
   * - TimezoneFinder.timezone_at_land()
     - 3.1e-06
     - 323k
   * - timezone_at()
     - 2.9e-06
     - 350k
   * - TimezoneFinder.timezone_at()
     - 2.8e-06
     - 360k
   * - unique_timezone_at()
     - 6.3e-07
     - 1575k
   * - TimezoneFinder.unique_timezone_at()
     - 5.7e-07
     - 1743k
   * - TimezoneFinderL.unique_timezone_at()
     - 5.7e-07
     - 1747k
   * - TimezoneFinderL.timezone_at_land()
     - 8.6e-07
     - 1157k
   * - TimezoneFinderL.timezone_at()
     - 6.0e-07
     - 1654k




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
     - 6.4e-05
     - 16k
   * - TimezoneFinder.timezone_at_land()
     - 3.6e-06
     - 281k
   * - TimezoneFinder.timezone_at()
     - 3.2e-06
     - 310k
   * - TimezoneFinder.unique_timezone_at()
     - 6.2e-07
     - 1616k




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
     - 2.3e-06
     - 433k
   * - TimezoneFinder.timezone_at()
     - 2.0e-06
     - 497k
   * - TimezoneFinder.unique_timezone_at()
     - 5.8e-07
     - 1731k
