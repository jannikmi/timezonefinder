Changelog
=========


1.5.5 (2016-06-03)
------------------

* using the newest version (2016d, May 2016) of the tz_world data from http://efele.net/maps/tz/world/
* holes in the polygons which are stored in the tz_world data are now correctly stored and handled
* rewrote the file_converter for storing the holes at the end of the timezone_data.bin
* added specific test cases for hole handling
* made some optimizations in the algorithms

1.5.4 (2016-04-26)
------------------

* using the newest version (2016b) of the tz_world from http://efele.net/maps/tz/world/
* rewrote the file_converter for parsing a .json created from the tz_worlds .shp
* had to temporarily fix one polygon manually which had the invalid TZID: 'America/Monterey' (should be 'America/Monterrey')
* had to make tests less strict because tzwhere still used the old data at the time and some results were simply different now


1.5.3 (2016-04-23)
------------------

* using 32-bit ints for storing the polygons now (instead of 64-bit): I calculated that the minimum accuracy (at the equator) is 1cm with the encoding being used. Tests passed.
* Benefits: 18MB file instead of 35MB, another 10-30% speed boost (depending on your hardware)


1.5.2 (2016-04-20)
------------------

* added python 2.7.6 support: replaced strings in unpack (unsupported by python 2.7.6 or earlier) with byte strings
* timezone names are now loaded from a separate file for better modularity


1.5.1 (2016-04-18)
------------------

* added python 2.7.8+ support:
    Therefore I had to change the tests a little bit (some operations were not supported). This only affects output.
    I also had to replace one part of the algorithms to prevent overflow in Python 2.7


1.5.0 (2016-04-12)
------------------

* automatically using optimized algorithms now (when numba is installed)
* added TimezoneFinder.using_numba() function to check if the import worked


1.4.0 (2016-04-07)
------------------

* Added the ``file_converter.py`` to the repository: It converts the .csv from pytzwhere to another ``.csv`` and this one into the used ``.bin``.
    Especially the shortcut computation and the boundary storage in there save a lot of reading and computation time, when deciding which timezone the coordinates are in.
    It will help to keep the package up to date, even when the timezone data should change in the future.

