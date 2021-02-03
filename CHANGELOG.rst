Changelog
=========


TODOs:
document class attributes
create variables for used dtype for each type of data (polygon address, coordinate...)
more "intelligent" binary file creation settings: name, dtype etc. combined


5.1.1 (2021-02-03)
------------------

* BUGFIX: get_geometry() now also works for the last zone
* add get_geometry() tests
* black code style
* pre-commit checks

5.1.0 (2021-01-14)
------------------

* update the command line interface. the package can now directly be called with ``timezonefinder``
* added the new query functions to the command line interface (to match the online API)


5.0.0 (2020-12-23)
------------------

MAJOR CHANGES:

Due to multiple user requests the ocean timezones ("Etc/GMT+-XX") are now included in the data files per default. fix #88. Since ocean timezones span the whole globe, now every point lies within a timezone!

API changes:
* added ``timezone_at_land()``: replaces the previous ``timezone_at()`` and returns ``None`` in case of a matched ocean timezone.

* deprecated ``certain_timezone_at()``. only meaningful in the case of timezone data WITHOUT oceans. Has equal results as  ``timezone_at()``, but is more expensive to use.
* also looking a single closest timezone boundary with ``closest_timezone_at()`` is not really meaningful, since every point lies within a zone!
* refactored tests. new test cases for ocean timezones


4.5.0 (2020-11-06)
------------------

BUGFIX: handle output destination for data files correctly in file_converter.py (FIX #107)

* updated the data to `2020d <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2020d>`__
* disable a test case for an Uzbek enclave. tests fail at this coordinate, possibly a bug. issue filed here: https://github.com/evansiroky/timezone-boundary-builder/issues/94
* update parse_data.sh script to properly handle new data format


4.4.1 (2020-08-04)
------------------

BUGFIX: a longitude of 180 equals -180 (not 0.0 as previously implemented)


4.4.0 (2020-05-14)
------------------

* added new class TimezonefinderL for using JUST shortcuts (without timezone polygon data)
* therefore included the most common timezone of each shortcut stored in the binary file ``shortcuts_direct_id.bin``
* introduced typing
* included API documentation
* read hole registry directly from json, ``hole_poly_ids.bin`` not required any more
* added the ``parse_data.sh`` shell script for downloading the latest timezone data, also with oceans


improvements of file_converter.py:

* added command line arguments for specifying the input and output directories
* read binary names from ``global_settings.py``
* read data types from ``global_settings.py``
* use with statement for writing binaries
* automatically detect overflow for each data type in use
* cleanup code, remove redundancies, improve codestyle
* fixing #101: make imports work for local and remote execution




4.3.1 (2020-04-29)
------------------

* BUGFIX #99: include the correct timezone_names.json in build
* wheel specific for the supported python versions (3.6, 3.7, 3.8)

4.3.0 (2020-04-28)
------------------

* updated the data to `2020a <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2020a>`__
* added "extra" simplifying the installation of Numba
* added minimal required python version
* added minimal required version of the dependencies
* simplified and updated settings (e.g. reading current version from file)
* also testing python 3.8 now
* loading version from file

4.2.0 (2019-12-15)
------------------

* added option to specify the location of the binary data files to use. making it possible to easily point to own compiled data. also load timezone names json from this location
* make timezone names a class attribute (instead of a global variable)
* simplify code for opening and closing multiple binary files
* added tests for a specified path to the data
* testing multiple python3 versions automatically
* pinned new requirements
* importlib_resources removed from the dependencies
* added a documentation at: https://timezonefinder.readthedocs.io/en/latest/
* added contribution guidelines


4.1.0 (2019-07-07)
------------------

* updated the data to `2019b <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2019b>`__
* added description of using vectorized input in readme



4.0.3 (2019-06-23)
------------------

* clarification of readme: referenced latest `timezonefinderL` release, better rst headlines, updated shield.io banner syntax
* clarification of speedup times (exponential notation)
* removed `six` and py2 dependency from tests
* minor updates to publishing routine
* minor improvement in timezone_at(): conversion coordinates to int later only when required


4.0.2 (2019-04-01)
------------------

* updated the data to `2019a <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2019a>`__


4.0.1 (2019-03-12)
------------------

* BUGFIX: fixing #77 (missing dependency in setup.py)


4.0.0 (2019-03-12)
------------------

* ATTENTION: Dropped Python2 support (#72)! `six` dependency no longer required.
* BUGFIX: fixing #74 (broken py3 with numba support)
* added `in_memory`-mode (adapted unit tests to test both modes, added speed tests and explanation to readme)
* use of timeit in speed tests for more accurate results
* dropped use of kwargs_only decorator (can be implemented directly with python3)

3.4.2 (2019-01-15)
------------------

* BUGFIX: fixing #70 (broken py2.7 with numba support)
* added automatic tox tests for py2.7 py3 environments with numba installed
* fixed coverage report

3.4.1 (2019-01-13)
------------------

* added test cases for the Numba helpers (#55)
* added more polygon tests to test the function inside_polygon()
* added global data type definitions (format strings) to ``global_settings.py``
* removed tzwhere completely from the main tests (no comparison any more).
* removed code drafts for ahead of time compilation (#40)

3.4.0 (2019-01-06)
------------------

* updated the data to `2018i <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2018i>`__
* introduced ``global_settings.py`` to globally define settings and get rid of "magic numbers".


3.3.0 (2018-11-17)
------------------

* updated the data to `2018g <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2018g>`__



3.2.1 (2018-10-30)
------------------

* ATTENTION: the package ``importlib_resources`` is now required
* fixing automatic Conda build by exchanging ``pkg_resources.resource_stream`` with ``importlib_resources.open_binary``
* added tests for overflow in helpers.py/inside_polygon()


3.2.0 (2018-10-23)
------------------

* ATTENTION: the package `kwargs_only <https://github.com/adamchainz/kwargs-only>`__ is not a requirement any more!
* fixing #63 (kwargs_only not in conda) enabling automatic conda forge builds by directly providing the kwargs_only functionality again
* added example.py with the code examples from the readme
* fixing #62 (overflow happening because of using numpy.int32): forcing int64 type conversion



3.1.0 (2018-09-27)
------------------

* fixing typo in requirements.txt
* updated publishing routine: reminder to include all direct dependencies and to compile the requirements.txt with python 2 (pip-tools)


3.0.2 (2018-09-26)
------------------

* ATTENTION: the package `kwargs_only <https://github.com/adamchainz/kwargs-only>`__ is now required! This functionality has previously been implemented by the author directly within this package, but some code features got deprecated.
* updated build/testing/publishing routine
* fixing issue #61 (six dependency not listed in setup.py)
* no more default arguments for timezone_at() and certain_timezone_at()
* no more comparison to (py-)tzwhere in the tests (test_it.py)
* updated requirements.txt (removed tzwhere and dependencies)
* prepared helpers_test.py for also testing helpers_numba.py
* exchanged deprecated inspect.getargspec() into .getfullargspec() in functional.py


3.0.1 (2018-05-30)
------------------

* fixing minor issue #58 (readme not rendering in pyPI)


3.0.0 (2018-05-17)
------------------

* ATTENTION: the package six is now required! (was necessary because of the new testing routine. improves compatibility standards)
* updated build/testing/publishing routine
* updated the data to `2018d <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2018d>`__
* fixing minor issue #52 (shortcuts being out of bounds for extreme coordinate values)
* the list of polygon ids in each shortcut is sorted after freq. of appearance of their zone id.
    this is critical for ruling out zones faster (as soon as just polygons of one zone are left this zone can be returned)
* using argparse package now for parsing the command line arguments
* added option of choosing between functions timezone_at() and certain_timezone_at() on the command line with flag -f
* the timezone names are now being stored in a readable JSON file
* adjusted the main test cases
* corrections and clarifications in the readme and code comments


2.1.2 (2017-11-20)
------------------

* bugfix: possibly uninitialized variable in closest_timezone_at()


2.1.1 (2017-11-20)
------------------

* updated the data to `2017c <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2017c>`__
* minor improvements in code style and readme
* include publishing routine script


2.1.0 (2017-05-19)
------------------

* updated the data to `2017a <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2017a>`__ (tz_world is not being maintained any more)
* the file_converter has been updated to parse the new format of .json files
* the new data is much bigger (based on OSM Data, +40MB). I am sorry for this but its still better than small outdated data!
* in case size and speed matter more you than actuality, you can still check out older versions of timezonefinder(L)
* the new timezone polygons are not limited to the coastlines, but they are including some large parts of the sea. This makes the results of closest_timezone_at() somewhat meaningless (as with timezonefinderL).
* the polygons can not be simplified much more and as a consequence timezonefinderL is not being updated any more.
* simplification functions (used for compiling the data for timezonefinderL) have been deleted from the file_converter
* the readme has been updated to inform about this major change
* some tests have been temporarily disabled (with tzwhere still using a very old version of tz_world, a comparison does not make too much sense atm)

2.0.1 (2017-04-08)
------------------

* added missing package data entries (2.0.0 didn't include all necessary .bin files)


2.0.0 (2017-04-07)
------------------

* ATTENTION: major change!: there is a second version of timezonefinder now: `timezonefinderL <https://github.com/MrMinimal64/timezonefinderL>`__. There the data has been simplified
    for increasing speed reducing data size. Around 56% of the coordinates of the timezone polygons have been deleted there. Around 60% of the polygons (mostly small islands) have been included in the simplified polygons.
    For any coordinate on landmass the results should stay the same, but accuracy at the shorelines is lost.
    This eradicates the usefulness of closest_timezone_at() and certain_timezone_at() but the main use case for this package (= determining the timezone of a point on landmass) is improved.
    In this repo timezonefinder will still be maintained with the detailed (unsimplified) data.
* file_converter.py has been complemented and modified to perform those simplifications
* introduction of new function get_geometry() for querying timezones for their geometric shape
* added shortcuts_unique_id.bin for instantly returning an id if the shortcut corresponding to the coords only contains polygons of one zone
* data is now stored in separate binaries for ease of debugging and readability
* polygons are stored sorted after their timezone id and size
* timezonefinder can now be called directly as a script (experimental with reduced functionality, cf. readme)
* optimisations on point in polygon algorithm
* small simplifications in the helper functions
* clarification of the readme
* clarification of the comments in the code
* referenced the new conda-feedstock in the readme
* referenced the new timezonefinder API/GUI



1.5.7 (2016-07-21)
------------------


* ATTENTION: API BREAK: all functions are now keyword-args only (to prevent lng lat mix-up errors)
* fixed a little bug with too many arguments in a @jit function
* clarified usage of the package in the readme
* prepared the usage of the ahead of time compilation functionality of Numba. It is not enabled yet.
* sorting the order of polygons to check in the order of how often their zones appear, gives a speed bonus (for closest_timezone_at)


1.5.6 (2016-06-16)
------------------

* using little endian encoding now
* introduced test for checking the proper functionality of the helper functions
* wrote tests for proximity algorithms
* improved proximity algorithms: introduced exact_computation, return_distances and force_evaluation functionality (s. Readme or documentation for more info)

1.5.5 (2016-06-03)
------------------

* using the newest version (2016d, May 2016) of the `tz world data`_
* holes in the polygons which are stored in the tz_world data are now correctly stored and handled
* rewrote the file_converter for storing the holes at the end of the timezone_data.bin
* added specific test cases for hole handling
* made some optimizations in the algorithms

1.5.4 (2016-04-26)
------------------

* using the newest version (2016b) of the `tz world data`_
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


    .. _tz world data: <http://efele.net/maps/tz/world/>
