==============
timezonefinder
==============

.. image:: https://img.shields.io/travis/MrMinimal64/timezonefinder.svg?branch=master
    :target: https://travis-ci.org/MrMinimal64/timezonefinder

This is a fast and lightweight python project for looking up the corresponding
timezone for a given lat/lng on earth entirely offline.

This project is derived from and has been successfully tested against
`pytzwhere <https://pypi.python.org/pypi/tzwhere>`__
(`github <https://github.com/pegler/pytzwhere>`__), but aims at providing
improved performance and usability.


The underlying timezone data is based on work done by `Eric
Muller <http://efele.net/maps/tz/world/>`__.

Timezones at sea and Antarctica are not yet supported (because somewhat
special rules apply there).

`timezone_finder <https://github.com/gunyarakun/timezone_finder>`__ is a ruby port of this package.


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

This approach is fast, but might not be what you are looking for:
For example when there is only one possible timezone in proximity, this timezone would be returned
(without checking if the point is included first).

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
only use this when the point is not inside a polygon!
this checks all the polygons within +-1 degree lng and +-1 degree lat

::

    #
    point = (12.773955, 55.578595)
    print( tf.closest_timezone_at(*point) )
    # = Europe/Copenhagens


**Other options:**

To increase search radius even more, use the ``delta_degree``-option:

::

    print( tf.closest_timezone_at(point[0],point[1],delta_degree=3))
    # = Europe/Copenhagens


This checks all the polygons within +-3 degree lng and +-3 degree lat
I recommend only slowly increasing the search radius, since computation time increases quite quickly
(with the amount of polygons which need to be evaluated). When you want to use this feature a lot,
consider using ``Numba``, to save computing time.


Also keep in mind that x degrees lat are not the same distance apart than x degree lng!
So to really make sure you got the closest timezone increase the search radius until you get a result,
then increase the radius once more and take this result. This should only make a difference in really rare cases however.


With ``exact_computation=True`` the distance to every polygon edge is computed (way more complicated)
, instead of just evaluating the distances to all the vertices. This only makes a real difference when polygons are very close.


With ``return_distances=True`` the output looks like this:

( 'tz_name_of_the_closest_polygon',[ distances to all polygons in km], [tz_names of all polygons])

Note that some polygons might not be tested (for example when a zone is found to be the closest already).
To prevent this use ``force_evaluation=True``.


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
There should be a tz_world.json (of approx. 100MB) in the folder together with the ``file_converter.py`` now.
Then run the converter by:

::

    python file_converter.py


This converts the .json into the needed ``.bin`` (overwriting the old version!) and also updates the ``timezone_names.py``.

**Please note:** Neither tests nor the file\_converter.py are optimized or
really beautiful. Sorry for that. If you have questions just write me (s. section 'Contact' below)

Comparison to pytzwhere
=======================

In comparison to
`pytzwhere <https://pypi.python.org/pypi/tzwhere/2.2>`__ most notably initialisation time and memory usage are
significantly reduced, while the algorithms yield the same results and are as fast or event faster
(depending on the dependencies used, s. test results below).
In some cases ``pytzwhere``
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

-  use of ``numba`` for precompilation (almost reaching the speed of tzwhere with shapely on and keeping the hole data in the memory)

**test results**\*:

::


    test correctness:
    Results:
    LOCATION             | EXPECTED             | COMPUTED             | Status
    ====================================================================
    Arlington, TN        | America/Chicago      | America/Chicago      | OK
    Memphis, TN          | America/Chicago      | America/Chicago      | OK
    Anchorage, AK        | America/Anchorage    | America/Anchorage    | OK
    Eugene, OR           | America/Los_Angeles  | America/Los_Angeles  | OK
    Albany, NY           | America/New_York     | America/New_York     | OK
    Moscow               | Europe/Moscow        | Europe/Moscow        | OK
    Los Angeles          | America/Los_Angeles  | America/Los_Angeles  | OK
    Moscow               | Europe/Moscow        | Europe/Moscow        | OK
    Aspen, Colorado      | America/Denver       | America/Denver       | OK
    Kiev                 | Europe/Kiev          | Europe/Kiev          | OK
    Jogupalya            | Asia/Kolkata         | Asia/Kolkata         | OK
    Washington DC        | America/New_York     | America/New_York     | OK
    St Petersburg        | Europe/Moscow        | Europe/Moscow        | OK
    Blagoveshchensk      | Asia/Yakutsk         | Asia/Yakutsk         | OK
    Boston               | America/New_York     | America/New_York     | OK
    Chicago              | America/Chicago      | America/Chicago      | OK
    Orlando              | America/New_York     | America/New_York     | OK
    Seattle              | America/Los_Angeles  | America/Los_Angeles  | OK
    London               | Europe/London        | Europe/London        | OK
    Church Crookham      | Europe/London        | Europe/London        | OK
    Fleet                | Europe/London        | Europe/London        | OK
    Paris                | Europe/Paris         | Europe/Paris         | OK
    Macau                | Asia/Macau           | Asia/Macau           | OK
    Russia               | Asia/Yekaterinburg   | Asia/Yekaterinburg   | OK
    Salo                 | Europe/Helsinki      | Europe/Helsinki      | OK
    Staffordshire        | Europe/London        | Europe/London        | OK
    Muara                | Asia/Brunei          | Asia/Brunei          | OK
    Puerto Montt seaport | America/Santiago     | America/Santiago     | OK
    Akrotiri seaport     | Asia/Nicosia         | Asia/Nicosia         | OK
    Inchon seaport       | Asia/Seoul           | Asia/Seoul           | OK
    Nakhodka seaport     | Asia/Vladivostok     | Asia/Vladivostok     | OK
    Truro                | Europe/London        | Europe/London        | OK
    Aserbaid. Enklave    | Asia/Baku            | Asia/Baku            | OK
    Tajikistani Enklave  | Asia/Dushanbe        | Asia/Dushanbe        | OK
    Busingen Ger         | Europe/Busingen      | Europe/Busingen      | OK
    Genf                 | Europe/Zurich        | Europe/Zurich        | OK
    Lesotho              | Africa/Maseru        | Africa/Maseru        | OK
    usbekish enclave     | Asia/Tashkent        | Asia/Tashkent        | OK
    usbekish enclave     | Asia/Tashkent        | Asia/Tashkent        | OK
    Arizona Desert 1     | America/Denver       | America/Denver       | OK
    Arizona Desert 2     | America/Phoenix      | America/Phoenix      | OK
    Arizona Desert 3     | America/Phoenix      | America/Phoenix      | OK
    Far off Cornwall     | None                 | None                 | OK

    closest_timezone_at():
    LOCATION             | EXPECTED             | COMPUTED             | Status
    ====================================================================
    Arlington, TN        | America/Chicago      | America/Chicago      | OK
    Memphis, TN          | America/Chicago      | America/Chicago      | OK
    Anchorage, AK        | America/Anchorage    | America/Anchorage    | OK
    Shore Lake Michigan  | America/New_York     | America/New_York     | OK

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


    TIMES for  10000 realistic points
    tzwhere: 0:03:01.536640
    timezonefinder: 0:00:00.930006
    195.2 times faster


    TIMES for  10000 random points
    tzwhere: 0:01:34.495648
    timezonefinder: 0:00:00.545236
    173.31 times faster

    Startup times:
    tzwhere: 0:00:07.760545
    timezonefinder: 0:00:00.000874
    8879.34 times faster


    shapely: ON (tzwhere)
    Numba: ON (timezonefinder)

    TIMES for  10000 realistic points
    tzwhere: 0:00:00.787326
    timezonefinder: 0:00:00.895679
    0.88 times faster

    TIMES for  10000 random queries:
    tzwhere: 0:00:01.358131
    timezonefinder: 0:00:01.042770
    1.3 times faster

    Startup times:
    tzwhere: 0:00:35.286660
    timezonefinder: 0:00:00.000281
    125575.3 times faster

\* System: MacBookPro 2,4GHz i5 4GB RAM SSD pytzwhere with numpy active

\*\*mismatch: pytzwhere finds something and then timezonefinder finds
something else

\*\*\*realistic queries: just points within a timezone (= pytzwhere
yields result)

\*\*\*\*random queries: random points on earth


Known Issues
============

I ran tests for approx. 5M points and these are no mistakes I found.


Contact
=======

This is the first public python project I did, so most certainly there is stuff I missed,
things I could have optimized even further etc. That's why I would be really glad to get some feedback on my code.


If you notice that the tz data is outdated, encounter any bugs, have
suggestions, criticism, etc. feel free to **open an Issue**, **add a Pull Requests** on Git or ...

contact me: *python at michelfe dot it*


Credits
=======

Thanks to `Adam <https://github.com/adamchainz>`__ for adding organisational features to the project and for helping me with publishing and testing routines.


License
=======

``timezonefinder`` is distributed under the terms of the MIT license
(see LICENSE.txt).
