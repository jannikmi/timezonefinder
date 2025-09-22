

Timezone Finding Performance Benchmark
======================================




System Configuration
--------------------


**C Implementation**: False


**Numba JIT**: True


**Test Queries**: 100



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
     - 4.6e-03
     - 0k
   * - TimezoneFinder.certain_timezone_at()
     - 1.6e-04
     - 6k
   * - timezone_at_land()
     - 7.1e-06
     - 140k
   * - TimezoneFinder.timezone_at_land()
     - 6.6e-06
     - 152k
   * - timezone_at()
     - 6.0e-06
     - 168k
   * - TimezoneFinder.timezone_at()
     - 5.8e-06
     - 172k
   * - unique_timezone_at()
     - 9.6e-07
     - 1046k
   * - TimezoneFinder.unique_timezone_at()
     - 8.5e-07
     - 1172k
   * - TimezoneFinderL.unique_timezone_at()
     - 2.5e-06
     - 405k
   * - TimezoneFinderL.timezone_at_land()
     - 1.5e-06
     - 662k
   * - TimezoneFinderL.timezone_at()
     - 8.9e-07
     - 1125k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - certain_timezone_at()
     - 1.8e-04
     - 6k
   * - TimezoneFinder.certain_timezone_at()
     - 1.3e-04
     - 8k
   * - timezone_at_land()
     - 8.3e-06
     - 121k
   * - TimezoneFinder.timezone_at_land()
     - 7.4e-06
     - 136k
   * - timezone_at()
     - 6.6e-06
     - 151k
   * - TimezoneFinder.timezone_at()
     - 6.5e-06
     - 155k
   * - unique_timezone_at()
     - 9.5e-07
     - 1054k
   * - TimezoneFinder.unique_timezone_at()
     - 8.5e-07
     - 1171k
   * - TimezoneFinderL.unique_timezone_at()
     - 1.5e-06
     - 657k
   * - TimezoneFinderL.timezone_at_land()
     - 1.5e-06
     - 668k
   * - TimezoneFinderL.timezone_at()
     - 9.0e-07
     - 1114k




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
     - 1.4e-04
     - 7k
   * - TimezoneFinder.timezone_at_land()
     - 5.4e-06
     - 184k
   * - TimezoneFinder.timezone_at()
     - 4.6e-06
     - 218k
   * - TimezoneFinder.unique_timezone_at()
     - 8.8e-07
     - 1134k




Results for random points (anywhere on earth)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Function Name
     - Seconds/Query
     - Points/Second
   * - TimezoneFinder.certain_timezone_at()
     - 1.6e-04
     - 6k
   * - TimezoneFinder.timezone_at_land()
     - 7.4e-06
     - 135k
   * - TimezoneFinder.timezone_at()
     - 5.3e-06
     - 188k
   * - TimezoneFinder.unique_timezone_at()
     - 1.2e-06
     - 811k
