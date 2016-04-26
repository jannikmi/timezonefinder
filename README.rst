==============
timezonefinder
==============

.. image:: https://img.shields.io/travis/MrMinimal64/timezonefinder.svg?branch=master
    :target: https://travis-ci.org/MrMinimal64/timezonefinder

This is a fast and lightweight python project to lookup the corresponding
timezone for a given lat/lng on earth entirely offline.

This project is derived from and has been successfully tested against
`pytzwhere <https://pypi.python.org/pypi/tzwhere/2.2>`__
(`github <https://github.com/pegler/pytzwhere>`__), but aims to provide
improved performance and usability.

It is also similar to
`django-geo-timezones <https://pypi.python.org/pypi/django-geo-timezones/0.1.2>`__

The underlying timezone data is based on work done by `Eric
Muller <http://efele.net/maps/tz/world/>`__.

Timezones at sea and Antarctica are not yet supported (because somewhat
special rules apply there).


Dependencies
============

(``python``, ``math``, ``struct``, ``os``)

``numpy``


**Optional:**

``Numba`` and its Requirements

This is only for precompiling the time critical algorithms. When you only look up a
few points once in a while, the compilation time is probably outweighing
the benefits. When using ``certain_timezone_at()`` and especially
``closest_timezone_at()`` however, I highly recommend using ``numba``
(see speed comparison below)! The amount of shortcuts used in the
``.bin`` is also only optimized for the use with ``numba``.

Installation
============

(install the dependencies)

in your terminal simply:

::

    pip install timezonefinder

(you might need to run this command as administrator)



Usage
=====

Basics:
-------

::

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()


for testing if numba is being used:
(if the import of the optimized algorithms worked)

::

    print(TimezoneFinder.using_numba())
    # this is a static method returning True or False


**fast algorithm:**

::

    # point = (longitude, latitude)
    point = (13.358, 52.5061)
    print( tf.timezone_at(*point) )
    # = Europe/Berlin

**To make sure a point is really inside a timezone (slower):**

::

    print( tf.certain_timezone_at(*point) )
    # = Europe/Berlin

**To find the closest timezone (slow):**

::

    # only use this when the point is not inside a polygon!
    # this checks all the polygons within +-1 degree lng and +-1 degree lat
    point = (12.773955, 55.578595)
    print( tf.closest_timezone_at(*point) )
    # = Europe/Copenhagens

**To increase search radius even more (very slow, use numba!):**

::

    # this checks all the polygons within +-3 degree lng and +-3 degree lat
    # I recommend only slowly increasing the search radius
    # keep in mind that x degrees lat are not the same distance apart than x degree lng!
    print( tf.closest_timezone_at(lng=point[0],lat=point[1],delta_degree=3) )
    # = Europe/Copenhagens

(to make sure you really got the closest timezone increase the search
radius until you get a result. then increase the radius once more and
take this result.)

Further application:
--------------------

**To maximize the chances of getting a result in a** ``Django`` **view it might look like:**

::

    def find_timezone(request, lat, lng):
        lat = float(lat)
        lng = float(lng)

        try:
            timezone_name = tf.timezone_at(lng, lat)
            if timezone_name is None:
                timezone_name = tf.closest_timezone_at(lng, lat)
                # maybe even increase the search radius when it is still None

        except ValueError:
            # the coordinates were out of bounds
            # {handle error}

        # ... do something with timezone_name ...

**To get an aware datetime object from the timezone name:**

::

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
        # ... handle the error ...

also see the `pytz Doc <http://pytz.sourceforge.net/>`__.

**Using the conversion tool:**

Make sure you installed the GDAL framework (thats for converting .shp shapefiles into .json)
Change to the directory of the timezonefinder package (location of ``file_converter.py``) in your terminal and then:

::

    wget http://efele.net/maps/tz/world/tz_world.zip
    # on mac: curl "http://efele.net/maps/tz/world/tz_world.zip" -o "tz_world.zip"
    unzip tz_world
    ogr2ogr -f GeoJSON -t_srs crs:84 tz_world.json ./world/tz_world.shp
    rm ./world/ -r
    rm tz_world.zip


Credits to `cstich <https://github.com/cstich>`__.
There has to be a tz_world.json (of approx. 100MB) in the folder together with the ``file_converter.py`` now.
Then you should run the converter by:

::

    python file_converter.py


This converts the .json into the needed ``.bin`` (overwriting the old version!) and also updates the ``timezone_names.py``.

**Please note:** Neither tests nor the file\_converter.py are optimized or
really beautiful. Sorry for that. If you have questions just write me (s. section 'Contact' below)

Comparison to pytzwhere
=======================

In comparison to
`pytzwhere <https://pypi.python.org/pypi/tzwhere/2.2>`__ I managed to
*speed up* the queries *by up to 190 times* (depending on the dependencies used, s. test results below).
Initialisation time and memory usage are significanlty reduced,
while my algorithm yields the same results. In some cases ``pytzwhere``
even does not find anything and ``timezonefinder`` does, for example
when only one timezone is close to the point.

**Similarities:**

-  results

-  data being used


**Differences:**

-  highly decreased memory usage

-  highly reduced start up time

-  the data is now stored in a memory friendly 18MB ``.bin`` and needed
   data is directly being read on the fly (instead of reading, converting and KEEPING the 76MB ``.csv``
   -mostly floats stored as strings!- into
   memory every time a class is created).

-  precomputed shortcuts are stored in the ``.bin`` to quickly look up
   which polygons have to be checked (instead of computing and storing the shortcuts
   on every startup)

-  introduced proximity algorithm

-  use of ``numba`` for precompilation (reaching the speed of tzwhere with shapely on and having everything preloaded in the memory)

**test results**\*:

::


    test correctness:
    Results:
    [point, target, timezonefinder is correct, tzwhere is correct]
    (-60.968888, -3.442172) America/Manaus True True
    (14.1315716, 2.99999) Africa/Douala True True
    (-106.1706459, 23.7891123) America/Mazatlan True True
    (33, -84) uninhabited True True
    (103.7069307, 1.3150701) Asia/Singapore True True
    (-71.9996885, -52.7868679) America/Santiago True True
    (-4.8663325, 40.0663485) Europe/Madrid True True
    (-152.4617352, 62.3415036) America/Anchorage True True
    (-44.7402611, 70.2989263) America/Godthab True True
    (12.9125913, 50.8291834) Europe/Berlin True True
    (37.0720767, 55.74929) Europe/Moscow True True
    (14.1315716, 0.2350623) Africa/Brazzaville True True

    testing 10000 realistic points
    [These tests dont make sense at the moment because tzwhere is still using old data]


    shapely: OFF (tzwhere)
    Numba: OFF (timezonefinder)

    TIMES for  1000 realistic queries:
    tzwhere: 0:00:17.819268
    timezonefinder: 0:00:03.269472
    5.45 times faster


    TIMES for  1000 random queries:
    tzwhere: 0:00:09.189154
    timezonefinder: 0:00:01.748470
    5.26 times faster


    shapely: OFF (tzwhere)
    Numba: ON (timezonefinder)

    TIMES for  10000 realistic queries:
    tzwhere: 0:02:55.985141
    timezonefinder: 0:00:00.905828
    194.28 times faster

    TIMES for  10000 random queries:
    tzwhere: 0:01:29.427567
    timezonefinder: 0:00:00.604325
    147.98 times faster


    w/o Numba:
    TIMES for  1000 realistic queries:
    tzwhere: 0:00:17.819268
    timezonefinder: 0:00:03.269472
    5.45 times faster


    TIMES for  1000 random queries:
    tzwhere: 0:00:09.189154
    timezonefinder: 0:00:01.748470
    5.26 times faster


    Startup times:
    tzwhere: 0:00:08.302153
    timezonefinder: 0:00:00.008768
    946.87 times faster


    shapely: ON (tzwhere)
    Numba: ON (timezonefinder)

    TIMES for  10000 realistic queries:
    tzwhere: 0:00:00.845834
    timezonefinder: 0:00:00.979515
    0.86 times faster

    TIMES for  10000 random queries:
    tzwhere: 0:00:01.358131
    timezonefinder: 0:00:01.042770
    1.3 times faster

    Startup times:
    tzwhere: 0:00:13.570615
    timezonefinder: 0:00:00.000265
    51209.87 times faster

\* System: MacBookPro 2,4GHz i5 4GB RAM SSD pytzwhere with numpy active

\*\*mismatch: pytzwhere finds something and then timezonefinder finds
something else

\*\*\*realistic queries: just points within a timezone (= pytzwhere
yields result)

\*\*\*\*random queries: random points on earth

Speed Impact of Numba
=====================

::

    TIMES for 1000 realistic queries***:

    timezone_at():
    wo/ numa: 0:00:01.017575
    w/ numa: 0:00:00.289854
    3.51 times faster

    certain_timezone_at():
    wo/ numa:   0:00:05.445209
    w/ numa: 0:00:00.290441
    14.92 times faster

    closest_timezone_at():
    (delta_degree=1)
    wo/ numa: 0:02:32.666238
    w/ numa: 0:00:02.688353
    40.2 times faster

(this is not included in my tests)

Known Issues
============

I ran tests for approx. 5M points and this are the mistakes I found:

All points in **Lesotho** are counted to the 'Africa/Johannesburg' timezone instead of 'Africa/Maseru'.
I am pretty sure this is because it is completely surrounded by South Africa and in the data the area of Lesotho is not excluded from this timezone.

Same for the small **usbekish enclaves** in **Kirgisitan** and some points in the **Arizona Dessert** (some weird rules apply here).


Those are mistakes in the data not my algorithms and in order to fix this I would need check for and then separately handle these special cases.
This would not only slow down the algorithms, but also make them ugly.


Contact
=======

This is the first public python project I did, so most certainly there is stuff I missed,
things I could have optimized even further etc. That's why I would be really glad to get some feedback on my code.


If you notice that the tz data is outdated, encounter any bugs, have
suggestions, criticism, etc. feel free to **open an Issue**, **add a Pull Requests** on Git or ...

contact me: *python at michelfe dot it*

License
=======

``timezonefinder`` is distributed under the terms of the MIT license
(see LICENSE.txt).
