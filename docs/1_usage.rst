.. _usage:

=====
Usage
=====

.. note::

   Also check out the :ref:`API documentation <api>` or the `code <https://github.com/jannikmi/timezonefinder>`__.


.. _global_functions:

Global Functions
----------------

Starting with version ``7.0.0``, ``timezonefinder`` provides global functions:

.. code-block:: python

    from timezonefinder import timezone_at

    tz = timezone_at(lng=13.358, lat=52.5061)  # 'Europe/Berlin'
    tz = timezone_at_land(lng=13.358, lat=52.5061)
    tz = unique_timezone_at(lng=13.358, lat=52.5061)
    geometry = get_geometry(tz_name="Europe/Berlin", coords_as_pairs=True)

The functionality of these global functions is equivalent to the respective methods of the :ref:`TimezoneFinder class <api_finder>` documented below.

.. note::
   The global functions use a singleton instance with thread-safe initialization.
   However, **the shared instance itself is NOT safe for concurrent reads**.

   **For parallel workloads, you must create separate ``TimezoneFinder`` instances for each thread/process.**
   This is the only way to guarantee thread-safe concurrent timezone lookups.

   If you need the convenience of a global function in a single-threaded context, the global functions
   are suitable. For any concurrent workload (threading, asyncio, multiprocessing), create independent
   instances as shown in the warning box below.

   For non-read-only operations or custom configurations (e.g., different data locations, in-memory mode),
   create separate ``TimezoneFinder`` instances for each configuration.


.. note::
    Lazy initialisation: expect the first call to be slightly slower due to the instance creation and singleton initialization.
    This also introduces overhead for every function call to access the global instance.
    **For any performance-critical or concurrent use, create your own TimezoneFinder instance instead.**



.. _init:

Instance Initialisation
-----------------------

For more control and better performance, you can create your own instance of the :ref:`TimezoneFinder class <api_finder>`
to be reused for multiple consequent timezone queries:

.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()  # reuse


Use the ``in_memory`` argument to read all polygon data into memory for faster access at the cost of memory consumption and initialisation time (see :doc:`benchmark_results_memory` for what each mode costs):

.. code-block:: python

    tf = TimezoneFinder(in_memory=True)


Use the argument ``bin_file_location`` to use data files from another location (e.g. :ref:`your own compiled files <parse_data>`):

.. code-block:: python

    tf = TimezoneFinder(bin_file_location="path/to/files")


.. note::

    Compiled data does **not** have to be regenerated on every upgrade. The coordinate files record
    the encoding they use, and a directory stays valid for as long as that encoding is unchanged -
    which is across most releases. When it does change, the changelog says so and loading raises a
    ``ValueError`` naming the file, rather than silently returning wrong timezones; regenerate with
    ``scripts/file_converter.py`` from the current checkout at that point.


.. warning::

    **For parallel computation (multiple threads/processes):** Each thread **must** have its own independent
    ``TimezoneFinder`` instance. Do **not** share a single instance across threads. Creating one instance
    per thread ensures proper isolation and avoids race conditions:

    .. code-block:: python

        import threading
        from timezonefinder import TimezoneFinder


        def lookup_in_thread(lng, lat):
            # Each thread creates its own instance
            tf = TimezoneFinder(in_memory=True)
            return tf.timezone_at(lng=lng, lat=lat)


        threads = [threading.Thread(target=lookup_in_thread, args=(13.4, 52.5))]
        # ...

    Alternatively, the global functions (``timezone_at()``, etc.) provide a thread-safe singleton
    for simple concurrent read-only lookups, though they come with additional overhead per call.



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

    timezonefinder [-h] [-v] [--stdin] [-d DELIMITER] [--lng-col LNG_COL]
                   [--lat-col LAT_COL] [--header | --no-header]
                   [--in-memory] [-f {0,1,3,4,5}]
                   [lng] [lat]


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

    A single invocation is orders of magnitude slower than using the package from
    within Python, because it pays the full initialisation cost to answer one query.
    Use ``--stdin`` (below) for more than a handful of coordinates.


Looking up many coordinates at once
-----------------------------------

With ``--stdin`` the script reads delimited rows from standard input and writes
each row back out with a ``timezone`` column appended. The finder is built once,
so initialisation amortises across the whole input instead of being paid per
coordinate:

::

    $ cat stores.csv
    store_id,name,lat,lng
    S-1,Amsterdam Centraal,52.37,4.89
    S-2,Pacific Buoy,0.0,-150.0

    $ timezonefinder --stdin < stores.csv
    store_id,name,lat,lng,timezone
    S-1,Amsterdam Centraal,52.37,4.89,Europe/Amsterdam
    S-2,Pacific Buoy,0.0,-150.0,Etc/GMT+10

Because the answer arrives attached to the row it belongs to, annotating a file
is one command - no projecting the coordinate columns out, and no rejoining the
results afterwards.

**Choosing the coordinate columns.** With a header row the columns are found by
name: ``lng``, ``lon``, ``long``, ``longitude`` or ``x`` for the longitude, and
``lat``, ``latitude`` or ``y`` for the latitude, matched case-insensitively.
Their position in the file does not matter. For a header that uses other names,
or for input with no header at all, name them explicitly - a header name, or a
1-based column number:

::

    timezonefinder --stdin --lng-col 3 --lat-col 2 < headerless.csv
    timezonefinder --stdin --lng-col longitude_deg --lat-col latitude_deg < f.csv

**Header or not.** Whether the first row names the columns or already holds data
is worked out from the row itself when nothing says otherwise. Say it outright with
``--header`` or ``--no-header`` when that could go wrong - a header whose names are
all numbers reads as data, and a first data row whose coordinates are placeholders
reads as a header.

.. note::

    The column order is **never** guessed. Input with no header and no
    ``--lng-col``/``--lat-col`` is rejected outright, because guessing would fail
    silently rather than loudly: for any point with a longitude between -90 and
    90 - most of the populated world - a swapped pair is still a valid
    coordinate, so it resolves to a real but wrong timezone. Swapping Moscow's
    pair yields ``Asia/Tehran``, which looks like an answer.

**Other flags.** ``-f`` selects the lookup function for the whole stream, exactly
as it does for a single query. ``-d``/``--delimiter`` sets the field delimiter for
input and output alike, defaulting to ``,`` - spell tab as ``'\t'``. ``-v`` is
rejected in this mode, since verbose output is per query and would break the
one-row-per-result contract, and so are ``lng``/``lat`` on the command line, since
the coordinates come from stdin. ``--in-memory`` reads the polygon coordinate data
into RAM rather than memory-mapping it, trading an order of magnitude more memory
for measurably faster lookups once the page cache is warm
(:doc:`benchmark_results_memory` and :doc:`benchmark_results_timezonefinding` carry
the current figures for both sides of that trade). It is worth passing for a long
stream and not for a single query, and does not apply to ``-f 3``/``-f 4``, which
load no polygon data.

**Rows that cannot be used.** There is always exactly one output row per input
row, which is what lets a caller consume the two in step. A row that is too short,
holds a non-numeric coordinate, or names a coordinate outside the valid range is
written back out with an empty ``timezone`` cell, and a warning naming the row
number and the reason goes to stderr. A row with no fields at all - a blank line,
or one csv itself could not parse - is echoed back blank, since there is no row to
append a cell to. An empty cell is also what a genuine
"no timezone here" looks like - which ``-f 4`` and ``-f 5`` return for every ocean
point - so the two are told apart by the **exit code**: ``1`` if any input row was
rejected, ``0`` if every row was answered. A consumer that stops reading early -
``| head``, a closed pipe - ends the run with ``141`` instead, so that a truncated
pipeline is not mistaken for a file full of bad coordinates.

Standard CSV quoting is honoured on the way in and reproduced on the way out, so a
field containing the delimiter survives intact. One consequence of that: a quoted
field may span several physical lines, so the guarantee is one output *row* per
input *row*, which is only the same thing as one line per line when no field is
quoted across a newline.
