

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
     - 1.3e-04
     - 8k
   * - TimezoneFinder.certain_timezone_at()
     - 9.7e-05
     - 10k
   * - timezone_at_land()
     - 7.8e-06
     - 128k
   * - TimezoneFinder.timezone_at_land()
     - 7.9e-06
     - 127k
   * - timezone_at()
     - 7.9e-06
     - 127k
   * - TimezoneFinder.timezone_at()
     - 7.9e-06
     - 127k
   * - unique_timezone_at()
     - 1.3e-06
     - 747k
   * - TimezoneFinder.unique_timezone_at()
     - 1.2e-06
     - 847k
   * - TimezoneFinderL.unique_timezone_at()
     - 1.3e-06
     - 777k
   * - TimezoneFinderL.timezone_at_land()
     - 1.9e-06
     - 526k
   * - TimezoneFinderL.timezone_at()
     - 1.4e-06
     - 725k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - certain_timezone_at()
     - 9.3e-05
     - 11k
   * - TimezoneFinder.certain_timezone_at()
     - 9.0e-05
     - 11k
   * - timezone_at_land()
     - 5.3e-06
     - 187k
   * - TimezoneFinder.timezone_at_land()
     - 5.2e-06
     - 191k
   * - timezone_at()
     - 4.8e-06
     - 207k
   * - TimezoneFinder.timezone_at()
     - 4.8e-06
     - 209k
   * - unique_timezone_at()
     - 1.2e-06
     - 831k
   * - TimezoneFinder.unique_timezone_at()
     - 1.1e-06
     - 894k
   * - TimezoneFinderL.unique_timezone_at()
     - 1.1e-06
     - 873k
   * - TimezoneFinderL.timezone_at_land()
     - 1.6e-06
     - 610k
   * - TimezoneFinderL.timezone_at()
     - 1.2e-06
     - 861k




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
     - 5.8e-06
     - 173k
   * - TimezoneFinder.timezone_at()
     - 5.3e-06
     - 189k
   * - TimezoneFinder.unique_timezone_at()
     - 1.1e-06
     - 906k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - TimezoneFinder.certain_timezone_at()
     - 9.3e-05
     - 11k
   * - TimezoneFinder.timezone_at_land()
     - 3.9e-06
     - 257k
   * - TimezoneFinder.timezone_at()
     - 3.4e-06
     - 295k
   * - TimezoneFinder.unique_timezone_at()
     - 1.1e-06
     - 903k
