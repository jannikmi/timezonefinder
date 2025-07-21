.. _usage:

=====
Usage
=====

.. note::

   Also check out the :ref:`API documentation <api>` or the `code <https://github.com/jannikmi/timezonefinder>`__.


.. _global_functions:

Global Functions
---------------

Starting with version ``7.0.0``, ``timezonefinder`` provides global functions:

.. code-block:: python

    from timezonefinder import timezone_at

    tz = timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'
    tz = timezone_at_land(lng=1.0, lat=50.5)
    tz = unique_timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'
    geometry = get_geometry(tz_name="Europe/Berlin", coords_as_pairs=True)

The functionality of these global functions is equivalent to the respective methods of the :ref:`TimezoneFinder class <api_finder>` documented below.

.. warning::
   Global functions share a single ``TimezoneFinder`` instance and are not thread-safe, due reading binary data on demand.
   For multi-threaded applications, create separate ``TimezoneFinder`` instances per thread.


.. note::
    Lazy initialisation: expect the first call to be slightly slower due to the instance creation.
    This also introduces a small overhead for every function call to access the global instance.
    Consider using a custom TimezoneFinder instance for performance-critical applications.



.. _init:

Instance Initialisation
----------------------

For more control and thread safety, you can create your own instance of the :ref:`TimezoneFinder class <api_finder>`
to be reused for multiple consequent timezone queries:

.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()  # reuse


Use the ``in_memory`` argument to read all polygon data into memory for faster access at the cost of memory consumption and initialisation time:

.. code-block:: python

    tf = TimezoneFinder(in_memory=True)


Use the argument ``bin_file_location`` to use data files from another location (e.g. :ref:`your own compiled files <parse_data>`):

.. code-block:: python

    tf = TimezoneFinder(bin_file_location="path/to/files")



timezone_at()
--------------

This is the default function to check which timezone a point lies within.
If no timezone has been matched, ``None`` is being returned.

Using the global function:

.. code-block:: python

    from timezonefinder import timezone_at

    tz = timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'
    tz = timezone_at(lng=1.0, lat=50.5)  # 'Etc/GMT'

Using a TimezoneFinder instance:

.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()
    tz = tf.timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'
    tz = tf.timezone_at(lng=1.0, lat=50.5)  # 'Etc/GMT'

.. note::

    To reduce the risk of mixing up the coordinates, the arguments ``lng`` and ``lat`` have to be given as keyword arguments

.. note::

    This function is optimized for speed: The last possible timezone in proximity is always returned (without checking if the point is really included).



timezone_at_land()
------------------

This package includes ocean timezones (``Etc/GMT...``).
If you want to explicitly receive only "land" timezones use:

Using the global function:

.. code-block:: python

    from timezonefinder import timezone_at_land

    tz = timezone_at_land(lng=13.358, lat=52.5061)  # 'Europe/Berlin'
    tz = timezone_at_land(lng=1.0, lat=50.5)  # None

Using a TimezoneFinder instance:

.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()
    tz = tf.timezone_at_land(lng=13.358, lat=52.5061)  # 'Europe/Berlin'
    tz = tf.timezone_at_land(lng=1.0, lat=50.5)  # None

unique_timezone_at()
--------------------

For fast execution ``timezonefinder`` internally uses precomputed "shortcuts" which store the possible zones in proximity.
Call ``unique_timezone_at()`` if you want to compute an exact result without actually performing "point-in-polygon" tests (<- computationally expensive).
This function will return ``None`` when the correct zone cannot be uniquely determined without further computation.

Using the global function:

.. code-block:: python

    from timezonefinder import unique_timezone_at

    tz = unique_timezone_at(lng=longitude, lat=latitude)

Using a TimezoneFinder instance:

.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()
    tz = tf.unique_timezone_at(lng=longitude, lat=latitude)



.. note::
    The "lightweight" class :ref:`TimezoneFinderL <usage_finderL>`, which is using only shortcuts, also supports just querying the most probable timezone.


certain_timezone_at()
----------------------

.. note::

    DEPRECATED: Due to the included ocean timezones one zone will always be matched.
    Use ``timezone_at()`` or ``timezone_at_land()`` instead.


This function is for making sure a point is really inside a timezone. It is slower, because all polygons (with shortcuts in that area)
are being checked until one polygon is matched. ``None`` is being returned in the case of no match.

Using the global function:

.. code-block:: python

    from timezonefinder import certain_timezone_at

    tz = certain_timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'

Using a TimezoneFinder instance:

.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()
    tz = tf.certain_timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'



.. note::

    Due to the "point-in-polygon-test" algorithm being used, the state of a point on the edge of a (timezone) polygon is undefined.
    For those kind of points the return values is hence uncertain and might be ``None``.
    This applies for example for all points with lng=+-180.0, because the timezone polygons in the data set are being cropped at the 180 longitude border.



closest_timezone_at()
----------------------

removed in version ``6.0.0``


get_geometry()
--------------


For querying a timezone for its geometric multi-polygon shape use ``get_geometry()``.
output format: ``[ [polygon1, hole1,...), [polygon2, ...], ...]``
and each polygon and hole is itself formated like: ``([longitudes], [latitudes])``
or ``[(lng1,lat1), (lng2,lat2),...]`` if ``coords_as_pairs=True``.

Using the global function:

.. code-block:: python

    from timezonefinder import get_geometry

    get_geometry(tz_name="Africa/Addis_Ababa", coords_as_pairs=True)
    get_geometry(tz_id=400, use_id=True)

Using a TimezoneFinder instance:

.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()
    tf.get_geometry(tz_name="Africa/Addis_Ababa", coords_as_pairs=True)
    tf.get_geometry(tz_id=400, use_id=True)


check out the example script in ``examples/get_geometry.py`` for more details.


.. _usage_finderL:

TimezoneFinderL
---------------

:ref:`TimezoneFinderL <api_finderL>` is a light version of the :ref:`TimezoneFinder class <api_finder>`.
It is useful for quickly suggesting probable timezones without using as many computational resources (cf. :ref:`speed tests <speed-tests>`).
Instead of using timezone polygon data this class instantly returns the timezone just based on precomputed "shortcuts".

Check the (:ref:`API documentation <api_finderL>`) of ``TimezoneFinderL``.

The most probable zone in proximity can be retrieved with ``timezone_at()``:

.. code-block:: python

    from timezonefinder import TimezoneFinderL

    tf = TimezoneFinderL(in_memory=True)  # reuse

    query_points = [(13.358, 52.5061), ...]
    for lng, lat in query_points:
        tz = tf.timezone_at(lng=lng, lat=lat)  # 'Europe/Berlin'





Certain results can be retrieved with ``unique_timezone_at()``:

.. code-block:: python

    tf.unique_timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'


.. note::

    If you only use ``TimezoneFinderL``, you may delete all unused timezone polygon data files in the folders ``data/boundaries`` and ``data/holes`` to obtain a truly lightweight installation (few MB).




Using vectorized input
----------------------

Check `numpy.vectorize <https://docs.scipy.org/doc/numpy/reference/generated/numpy.vectorize.html>`__
and `pandas.DataFrame.apply <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.apply.html>`__



Calling timezonefinder from the command line
---------------------------------------------

A command line script is being installed as part of this package.

**Command Line Syntax**:

::

    timezonefinder [-h] [-v] [-f {0,1,2,3,4,5}] lng lat


**Example**:

::

    timezonefinder -f 4 40.5 11.7


With ``-v`` you get verbose output, without it only the timezone name is being printed.
With the argument of the flag ``-f`` one can choose between the different functions to be called:

::

    0: timezone_at() = default (uses global function)
    1: certain_timezone_at() (uses global function)
    2: removed
    3: TimezoneFinderL.timezone_at()
    4: TimezoneFinderL.timezone_at_land()
    5: timezone_at_land() (uses global function)


.. note::

    Command line usage is efficient as it uses the global functions where possible (function IDs 0, 1, and 5),
    avoiding repeated initialization of TimezoneFinder instances.
