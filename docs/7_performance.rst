
.. _speed-tests:

Speed Test Results
-------------------

obtained on MacBook Pro (15-inch, 2017), 2,8 GHz Intel Core i7 with ``scripts/check_speed.py`` and timezonefinder version ``6.1.0``

::

    Speed Tests:
    10000 'on land points' (points included in a land timezone)
    using C implementation: True
    using Numba: False

    function name                       | s/query    | pts/s
    --------------------------------------------------
    TimezoneFinder.timezone_at()        | 1.0e-04    | 1.0e+04
    TimezoneFinder.timezone_at_land()   | 7.6e-05    | 1.3e+04
    TimezoneFinderL.timezone_at()       | 6.1e-06    | 1.6e+05
    TimezoneFinderL.timezone_at_land()  | 7.6e-06    | 1.3e+05


    Speed Tests:
    10000 random points (anywhere on earth)
    using C implementation: True
    using Numba: False

    function name                       | s/query    | pts/s
    --------------------------------------------------
    TimezoneFinder.timezone_at()        | 7.9e-05    | 1.3e+04
    TimezoneFinder.timezone_at_land()   | 8.2e-05    | 1.2e+04
    TimezoneFinderL.timezone_at()       | 6.1e-06    | 1.6e+05
    TimezoneFinderL.timezone_at_land()  | 8.0e-06    | 1.3e+05
