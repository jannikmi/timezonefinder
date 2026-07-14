

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
     - 1.2e-04
     - 8k
   * - TimezoneFinder.certain_timezone_at()
     - 7.8e-05
     - 13k
   * - timezone_at_land()
     - 4.7e-06
     - 214k
   * - TimezoneFinder.timezone_at_land()
     - 4.6e-06
     - 218k
   * - timezone_at()
     - 4.3e-06
     - 232k
   * - TimezoneFinder.timezone_at()
     - 4.3e-06
     - 234k
   * - unique_timezone_at()
     - 7.0e-07
     - 1425k
   * - TimezoneFinder.unique_timezone_at()
     - 6.4e-07
     - 1566k
   * - TimezoneFinderL.unique_timezone_at()
     - 6.6e-07
     - 1521k
   * - TimezoneFinderL.timezone_at_land()
     - 9.7e-07
     - 1032k
   * - TimezoneFinderL.timezone_at()
     - 6.9e-07
     - 1459k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - certain_timezone_at()
     - 8.5e-05
     - 12k
   * - TimezoneFinder.certain_timezone_at()
     - 7.4e-05
     - 13k
   * - timezone_at_land()
     - 3.3e-06
     - 302k
   * - TimezoneFinder.timezone_at_land()
     - 3.3e-06
     - 307k
   * - timezone_at()
     - 2.9e-06
     - 342k
   * - TimezoneFinder.timezone_at()
     - 2.9e-06
     - 342k
   * - unique_timezone_at()
     - 6.8e-07
     - 1462k
   * - TimezoneFinder.unique_timezone_at()
     - 6.4e-07
     - 1573k
   * - TimezoneFinderL.unique_timezone_at()
     - 6.8e-07
     - 1472k
   * - TimezoneFinderL.timezone_at_land()
     - 1.0e-06
     - 966k
   * - TimezoneFinderL.timezone_at()
     - 7.1e-07
     - 1411k




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
     - 7.2e-05
     - 14k
   * - TimezoneFinder.timezone_at_land()
     - 3.5e-06
     - 289k
   * - TimezoneFinder.timezone_at()
     - 3.1e-06
     - 323k
   * - TimezoneFinder.unique_timezone_at()
     - 6.3e-07
     - 1598k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - TimezoneFinder.certain_timezone_at()
     - 6.1e-05
     - 16k
   * - TimezoneFinder.timezone_at_land()
     - 2.4e-06
     - 415k
   * - TimezoneFinder.timezone_at()
     - 2.1e-06
     - 487k
   * - TimezoneFinder.unique_timezone_at()
     - 6.3e-07
     - 1577k
