==============
timezonefinder
==============

.. image:: https://img.shields.io/travis/MrMinimal64/timezonefinder/master.svg
    :target: https://travis-ci.org/MrMinimal64/timezonefinder

.. image:: https://img.shields.io/circleci/project/github/conda-forge/timezonefinder-feedstock/master.svg?label=noarch
    :target: https://circleci.com/gh/conda-forge/timezonefinder-feedstock

.. image:: https://img.shields.io/pypi/wheel/timezonefinder.svg
    :target: https://pypi.python.org/pypi/timezonefinder

.. image:: https://img.shields.io/pypi/dd/timezonefinder.svg
    :alt: daily PyPI downloads
    :target: https://pypi.python.org/pypi/timezonefinder

.. image:: https://pepy.tech/badge/timezonefinder
    :alt: Total PyPI downloads
    :target: https://pepy.tech/project/timezonefinder

.. image:: https://img.shields.io/pypi/v/timezonefinder.svg
    :alt: latest version on PyPI
    :target: https://pypi.python.org/pypi/timezonefinder

.. image:: https://anaconda.org/conda-forge/timezonefinder/badges/version.svg
    :alt: latest version on Conda
    :target: https://anaconda.org/conda-forge/timezonefinder



This is a fast and lightweight python project for looking up the corresponding
timezone for given coordinates on earth entirely offline.

Timezones internally are being represented by polygons.
To find out which timezone a point belongs to, it is being checked if the point lies within a polygon.
A few tweaks have been added to keep the computational requirements low.

Current **data set** in use: precompiled `timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder>`__ (without oceans, 116MB, JSON)

NOTE: The timezone polygons do NOT follow the shorelines any more (as they did with the previous data set tz_world).
This makes the results of ``closest_timezone_at()`` and ``certain_timezone_at()`` somewhat meaningless.

If memory usage and speed matter more to you than accuracy, use `timezonefinderL <https://github.com/MrMinimal64/timezonefinderL>`__.

Also see:
`GitHub <https://github.com/MrMinimal64/timezonefinder>`__,
`PyPI <https://pypi.python.org/pypi/timezonefinder/>`__,
`conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__,
`timezone_finder <https://github.com/gunyarakun/timezone_finder>`__: ruby port,
`timezonefinderL <https://github.com/MrMinimal64/timezonefinderL>`__: faster, lighter version
`timezonefinderL GUI <http://timezonefinder.michelfe.it/gui>`__: demo and online API of the outdated ``timezonefinderL``


Dependencies
------------

``python3``, ``numpy``, ``importlib_resources``


**Optional:**

If the vanilla Python code is too slow for you, also install

`Numba <https://github.com/numba/numba>`__ and all its Requirements (e.g. `llvmlite <http://llvmlite.pydata.org/en/latest/install/index.html>`_)

This causes the time critical algorithms (in ``helpers_numba.py``) to be automatically precompiled to speed things up.


Installation
------------


Installation with conda: see instructions at `conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__ (NOTE: The newest version of timezonefinder might not be available via conda yet)



Installation with pip:
in the command line:

::

    pip install timezonefinder



Usage
-----

check ``example.py``

Basics:
=======

in Python:

.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()


To save computing time at the cost of memory consumption and initialisation time pass ``in_memory=True``. This causes all binary files to be read into memory. See the "speed test results" below.

.. code-block:: python

    tf = TimezoneFinder(in_memory=True)


for testing if numba is being used:
(if the import of the optimized algorithms worked)

.. code-block:: python

    TimezoneFinder.using_numba()   # this is a static method returning True or False


**timezone_at():**

This is the default function to check which timezone a point lies within.
If no timezone has been matched, ``None`` is being returned.

**NOTE:**

* to avoid mixing up the arguments latitude and longitude have to be given as keyword arguments
* this function is optimized for speed and the common case to only query points within a timezone. The last possible timezone in proximity is always returned (without checking if the point is really included). So results might be misleading for points outside of any timezone.


.. code-block:: python

    longitude = 13.358
    latitude = 52.5061
    tf.timezone_at(lng=longitude, lat=latitude) # returns 'Europe/Berlin'


**certain_timezone_at():**

This function is for making sure a point is really inside a timezone. It is slower, because all polygons (with shortcuts in that area)
are being checked until one polygon is matched. ``None`` is being returned in the case of no match.

NOTE: The timezone polygons do NOT follow the shoreline.
Consequently even if certain_timezone_at() does not return ``None``, a query point could be in the sea.




.. code-block:: python

    tf.certain_timezone_at(lng=longitude, lat=latitude) # returns 'Europe/Berlin'


**closest_timezone_at():**


This function computes and compares the distances to the timezone polygon boundaries (expensive!).
By default the function returns the closest timezone of all polygons within +-1 degree lng and +-1 degree lat (or None).

NOTE:

* This function does not check whether a point is included in a timezone polygon.

* The timezone polygons do NOT follow the shoreline. This causes the computed distance from a timezone polygon to be not really accurate!


.. code-block:: python

    longitude = 12.773955
    latitude = 55.578595
    tf.closest_timezone_at(lng=longitude, lat=latitude) # returns 'Europe/Copenhagen'


Options:


To increase search radius even more, use the ``delta_degree``-option:

.. code-block:: python

    tf.closest_timezone_at(lng=longitude, lat=latitude, delta_degree=3)


This checks all the polygons within +-3 degree lng and +-3 degree lat.
I recommend only slowly increasing the search radius, since computation time increases quite quickly
(with the amount of polygons which need to be evaluated). When you want to use this feature a lot,
consider using ``Numba`` to save computing time.


Also keep in mind that x degrees lat are not the same distance apart than x degree lng (earth is a sphere)!
As a consequence getting a result does NOT mean that there is no closer timezone! It might just not be within the area (given in degree!) being queried.

With ``exact_computation=True`` the distance to every polygon edge is computed (way more complicated), instead of just evaluating the distances to all the vertices.
This only makes a real difference when the boundary of a polygon is very close to the query point.


With ``return_distances=True`` the output looks like this:

::

    ( 'tz_name_of_the_closest_polygon',[ distances to every polygon in km], [tz_names of every polygon])


Note that some polygons might not be tested (for example when a zone is found to be the closest already).
To prevent this use ``force_evaluation=True``.

A single timezone might be represented by multiple polygons and the distance to each of the candidate polygons is being computed and returned. Hence one may get multiple results for one timezone. Example:


.. code-block:: python

    longitude = 42.1052479
    latitude = -16.622686
    tf.closest_timezone_at(lng=longitude, lat=latitude, delta_degree=2,
                                        exact_computation=True, return_distances=True, force_evaluation=True)
    '''
    returns ('uninhabited',
    [80.66907784731714, 217.10924866254518, 293.5467252349301, 304.5274937839159, 238.18462606485667, 267.918674688949, 207.43831938964408, 209.6790144988553, 228.42135641542546],
    ['uninhabited', 'Indian/Antananarivo', 'Indian/Antananarivo', 'Indian/Antananarivo', 'Africa/Maputo', 'Africa/Maputo', 'Africa/Maputo', 'Africa/Maputo', 'Africa/Maputo'])
    '''



**get_geometry:**


For querying a timezone for its geometric multi-polygon shape use ``get_geometry()``.
output format: ``[ [polygon1, hole1,...), [polygon2, ...], ...]``
and each polygon and hole is itself formated like: ``([longitudes], [latitudes])``
or ``[(lng1,lat1), (lng2,lat2),...]`` if ``coords_as_pairs=True``.


.. code-block:: python

    tf.get_geometry(tz_name='Africa/Addis_Ababa', coords_as_pairs=True)
    tf.get_geometry(tz_id=400, use_id=True)




Further application:
====================


**To use vectorized input:**

Check `numpy.vectorize <https://docs.scipy.org/doc/numpy/reference/generated/numpy.vectorize.html>`__
and `pandas.DataFrame.apply <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.apply.html>`__


**To maximize the chances of getting a result in a** ``Django`` **view it might look like:**


.. code-block:: python

    def find_timezone(request, lat, lng):
        lat = float(lat)
        lng = float(lng)
        try:
            timezone_name = tf.timezone_at(lng=lng, lat=lat)
            if timezone_name is None:
                timezone_name = tf.closest_timezone_at(lng=lng, lat=lat)
                # maybe even increase the search radius when it is still None
        except ValueError:
            # the coordinates were out of bounds
            pass # {handle error}
        # ... do something with timezone_name ...




**To get an aware datetime object from the timezone name:**


.. code-block:: python

    # first pip install pytz
    from pytz import timezone, utc
    from pytz.exceptions import UnknownTimeZoneError

    # tzinfo has to be None (means naive)
    naive_datetime = YOUR_NAIVE_DATETIME

    try:
        tz = timezone(timezone_name)
        aware_datetime = naive_datetime.replace(tzinfo=tz)
        aware_datetime_in_utc = aware_datetime.astimezone(utc)

        naive_datetime_as_utc_converted_to_tz = tz.localize(naive_datetime)

    except UnknownTimeZoneError:
        pass # {handle error}



**Getting a location's time zone offset from UTC in minutes:**

solution from `communikein <https://github.com/communikein>`__ and `phineas-pta <https://github.com/phineas-pta>`__



.. code-block:: python

    from pytz import timezone
    import pytz
    from datetime import datetime

    utc = pytz.utc

    def offset(target):
        """
        returns a location's time zone offset from UTC in minutes.
        """
        today = datetime.now()
        tz_target = timezone(tf.certain_timezone_at(lat=target['lat'], lng=target['lng']))
        # ATTENTION: tz_target could be None! handle error case

        # today_target = tz_target.localize(today)
        # today_utc = utc.localize(today)
        # offset = today_utc - today_target
        offset = tz_target.utcoffset(today)

        # if `today` is in summer time while the target isn't, you may want to substract the DST
        offset -= tz_target.dst(today)
        return offset.total_seconds() / 60

    bergamo = dict({'lat':45.69, 'lng':9.67})
    print(offset(bergamo))


also see the `pytz Doc <http://pytz.sourceforge.net/>`__.


**Parsing the data** (Using your own data):


Download the latest ``timezones.geojson.zip`` data set file from `timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder/releases>`__, unzip and
place the ``combined.json`` inside the timezonefinder folder. Now run the ``file_converter.py`` until the compilation of the binary files is completed.

If you want to use your own data set, create a ``combined.json`` file with the same format as the timezone-boundary-builder and compile everything with ``file_converter.py``.


**Calling timezonefinder from the command line:**

With -v you get verbose output, without it only the timezone name is being printed.
Choose between functions timezone_at() and certain_timezone_at() with flag -f (default: timezone_at()).
Please note that this is much slower than keeping a Timezonefinder class directly in Python,
because here all binary files are being opend again for each query.

::

    usage: timezonefinder.py [-h] [-v] [-f {0,1}] lng lat




Contact
-------

Most certainly there is stuff I missed, things I could have optimized even further etc. I would be really glad to get some feedback on my code.

If you notice that the tz data is outdated, encounter any bugs, have
suggestions, criticism, etc. feel free to **open an Issue**, **add a Pull Requests** on Git or ...

contact me: *[python] {*-at-*} [michelfe] {-*dot*-} [it]*


Acknowledgements
----------------

Thanks to:

`Adam <https://github.com/adamchainz>`__ for adding organisational features to the project and for helping me with publishing and testing routines.

`snowman2 <https://github.com/snowman2>`__ for creating the conda-forge recipe.

`synapticarbors <https://github.com/synapticarbors>`__ for fixing Numba import with py27.

License
-------

``timezonefinder`` is distributed under the terms of the MIT license
(see LICENSE.txt).



Speed Test Results:
-------------------

obtained on MacBook Pro (15-inch, 2017), 2,8 GHz Intel Core i7

::

    Speed Tests:
    -------------
    "realistic points": points included in a timezone


    in memory mode: False
    Numba: ON (precompiled functions in use)

    startup time: 0.001301s

    testing 100000 realistic points
    total time: 6.7015s
    avg. points per second: 1.5 * 10^4

    testing 100000 random points
    total time: 4.6289s
    avg. points per second: 2.2 * 10^4


    in memory mode: True
    Numba: ON (timezonefinder)

    startup time: 0.03545s


    in memory mode: True
    Numba: ON (precompiled functions in use)

    testing 100000 realistic points
    total time: 2.0659s
    avg. points per second: 4.8 * 10^4


    testing 100000 random points
    total time: 1.1928s
    avg. points per second: 8.4 * 10^4


Speed bonus of in-memory mode: 3x (realistic points), 4x (random pts)


Comparison to pytzwhere
-----------------------

This project has originally been derived from `pytzwhere <https://pypi.python.org/pypi/tzwhere>`__
(`github <https://github.com/pegler/pytzwhere>`__), but aims at providing
improved performance and usability.

``pytzwhere`` is parsing a 76MB .csv file (floats stored as strings!) completely into memory and computing shortcuts from this data on every startup.
This is time, memory and CPU consuming. Additionally calculating with floats is slow,
keeping those 4M+ floats in the RAM all the time is unnecessary and the precision of floats is not even needed in this case (s. detailed comparison and speed tests below).

In comparison most notably initialisation time and memory usage are significantly reduced.
``pytzwhere`` is using up to 450MB of RAM (with ``shapely`` and ``numpy`` active),
because it is parsing and keeping all the timezone polygons in the memory.
This uses unnecessary time/ computation/ memory and this was the reason I created this package in the first place.
This package uses at most 40MB (= encountered memory consumption of the python process) and has some more advantages:

**Differences:**

-  highly decreased memory usage

-  highly reduced start up time

-  usage of 32bit int (instead of 64+bit float) reduces computing time and memory consumption. The accuracy of 32bit int is still high enough. According to my calculations the worst accuracy is 1cm at the equator. This is far more precise than the discrete polygons in the data.

-  the data is stored in memory friendly binary files (approx. 41MB in total, original data 120MB .json)

-  data is only being read on demand (not completely read into memory if not needed)

-  precomputed shortcuts are included to quickly look up which polygons have to be checked

-  available proximity algorithm ``closest_timezone_at()``

-  function ``get_geometry()`` enables querying timezones for their geometric shape (= multipolygon with holes)

-  further speedup possible by the use of ``numba`` (code precompilation)



::

    Startup times:
    tzwhere: 0:00:29.365294
    timezonefinder: 0:00:00.000888
    33068.02 times faster

    all other cross tests are not meaningful because tz_where is still using the outdated tz_world data set

