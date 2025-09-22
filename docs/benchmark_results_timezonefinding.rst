

Timezone Finding Performance Benchmark
======================================




System Status
-------------




Python Environment
~~~~~~~~~~~~~~~~~~


**Python Version**: 3.12.1 (CPython)

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
     - 2.0e-04
     - 5k
   * - TimezoneFinder.certain_timezone_at()
     - 1.5e-04
     - 7k
   * - timezone_at_land()
     - 7.1e-06
     - 141k
   * - TimezoneFinder.timezone_at_land()
     - 7.0e-06
     - 142k
   * - timezone_at()
     - 6.6e-06
     - 151k
   * - TimezoneFinder.timezone_at()
     - 6.8e-06
     - 147k
   * - unique_timezone_at()
     - 9.9e-07
     - 1012k
   * - TimezoneFinder.unique_timezone_at()
     - 9.3e-07
     - 1072k
   * - TimezoneFinderL.unique_timezone_at()
     - 9.3e-07
     - 1073k
   * - TimezoneFinderL.timezone_at_land()
     - 1.4e-06
     - 722k
   * - TimezoneFinderL.timezone_at()
     - 9.4e-07
     - 1062k




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
     - 1.2e-04
     - 8k
   * - timezone_at_land()
     - 5.2e-06
     - 194k
   * - TimezoneFinder.timezone_at_land()
     - 5.4e-06
     - 186k
   * - timezone_at()
     - 4.7e-06
     - 213k
   * - TimezoneFinder.timezone_at()
     - 4.6e-06
     - 216k
   * - unique_timezone_at()
     - 1.0e-06
     - 1003k
   * - TimezoneFinder.unique_timezone_at()
     - 9.4e-07
     - 1066k
   * - TimezoneFinderL.unique_timezone_at()
     - 9.6e-07
     - 1044k
   * - TimezoneFinderL.timezone_at_land()
     - 1.4e-06
     - 705k
   * - TimezoneFinderL.timezone_at()
     - 9.6e-07
     - 1047k




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
     - 1.5e-04
     - 7k
   * - TimezoneFinder.timezone_at_land()
     - 5.5e-06
     - 183k
   * - TimezoneFinder.timezone_at()
     - 5.0e-06
     - 201k
   * - TimezoneFinder.unique_timezone_at()
     - 9.1e-07
     - 1103k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - TimezoneFinder.certain_timezone_at()
     - 1.1e-04
     - 9k
   * - TimezoneFinder.timezone_at_land()
     - 3.8e-06
     - 264k
   * - TimezoneFinder.timezone_at()
     - 3.2e-06
     - 309k
   * - TimezoneFinder.unique_timezone_at()
     - 9.2e-07
     - 1089k
