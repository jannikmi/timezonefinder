.. _usage:

=====
Usage
=====

.. note::

   Also check out the :ref:`API documentation <api>` or the `code <https://github.com/jannikmi/timezonefinder>`__.


.. _init:

Initialisation
--------------


Create a new instance of the :ref:`TimezoneFinder class <api_finder>` to be reused for multiple consequent timezone queries:

.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()  # reuse



Use the argument ``bin_file_location`` to use data files from another location (e.g. :ref:`your own compiled files <parse_data>`):

.. code-block:: python

    tf = TimezoneFinder(bin_file_location="path/to/files")






timezone_at()
--------------

This is the default function to check which timezone a point lies within.
If no timezone has been matched, ``None`` is being returned.



.. code-block:: python

    tz = tf.timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'
    tz = tf.timezone_at(lng=1.0, lat=50.5)  # 'Etc/GMT'

.. note::

    To reduce the risk of mixing up the coordinates, the arguments ``lng`` and ``lat`` have to be given as keyword arguments

.. note::

    This function is optimized for speed: The last possible timezone in proximity is always returned (without checking if the point is really included).



timezone_at_land()
------------------

This package includes ocean timezones (``Etc/GMT...``).
If you want to explicitly receive only "land" timezones use

.. code-block:: python

    tz = tf.timezone_at_land(lng=13.358, lat=52.5061)  # 'Europe/Berlin'
    tz = tf.timezone_at_land(lng=1.0, lat=50.5)  # None

unique_timezone_at()
--------------------

For fast execution ``timezonefinder`` internally uses precomputed "shortcuts" which store the possible zones in proximity.
Call ``unique_timezone_at()`` if you want to compute an exact result without actually performing "point-in-polygon" tests (<- computationally expensive).
This function will return ``None`` when the correct zone cannot be uniquely determined without further computation.

.. code-block:: python

    tf.unique_timezone_at(lng=longitude, lat=latitude)



.. note::
    The "lightweight" class :ref:`TimezoneFinderL <usage_finderL>`, which is using only shortcuts, also supports just querying the most probable timezone.


certain_timezone_at()
----------------------

.. note::

    DEPRECATED: Due to the included ocean timezones one zone will always be matched.
    Use ``timezone_at()`` or ``timezone_at_land()`` instead.


This function is for making sure a point is really inside a timezone. It is slower, because all polygons (with shortcuts in that area)
are being checked until one polygon is matched. ``None`` is being returned in the case of no match.


.. code-block:: python

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


.. code-block:: python

    tf.get_geometry(tz_name="Africa/Addis_Ababa", coords_as_pairs=True)
    tf.get_geometry(tz_id=400, use_id=True)




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

    If you only use ``TimezoneFinderL``, you may delete all data files except ``timezone_names.json``, ``shortcuts.bin`` to obtain a truly lightweight installation.




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

    0: TimezoneFinder.timezone_at() = default
    1: TimezoneFinder.certain_timezone_at()
    2: removed
    3: TimezoneFinderL.timezone_at()
    4: TimezoneFinderL.timezone_at_land()
    5: TimezoneFinder.timezone_at_land()


.. note::

    This will be orders of magnitude slower than using the package directly from within python as a separate Timezonefinder() instance is being
