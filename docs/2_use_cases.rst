.. _use_cases:

===========
Use Cases:
===========


Creating aware datetime objects
-------------------------------

The lookup returns an IANA timezone name, which is exactly what ``zoneinfo`` takes:

.. code-block:: python

    from datetime import datetime
    from zoneinfo import ZoneInfo
    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lng=13.41, lat=52.52)  # 'Europe/Berlin'
    aware = datetime.now(tz=ZoneInfo(tz_name))

``examples/aware_datetime.py`` shows the same thing with ``pytz``, including the difference between
attaching a timezone and localising a naive datetime.


Getting a location's time zone offset
--------------------------------------

The offset is a property of the aware datetime, so it comes straight from ``utcoffset()`` - and it
depends on the date, since it changes with daylight saving time:

.. code-block:: python

    from datetime import datetime
    from zoneinfo import ZoneInfo
    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lng=9.67, lat=45.69)  # 'Europe/Rome'
    offset = datetime.now(tz=ZoneInfo(tz_name)).utcoffset()

``examples/get_offset.py`` answers the same question with the optional ``pytz`` extra,
returning the offset in minutes from ``certain_timezone_at()``. For new code, the stdlib
`zoneinfo <https://docs.python.org/3/library/zoneinfo.html>`_ module is the
recommended way to attach an IANA timezone to a datetime.

.. warning::

    ``Etc/GMT±X`` zone names use an **inverted** sign convention: ``Etc/GMT+5`` is
    UTC-5 and ``Etc/GMT-5`` is UTC+5. The packaged data covers the oceans, so any
    coordinate at sea resolves to an ``Etc/GMT`` zone, the UTC+0 band to the
    signless ``Etc/GMT`` itself. Computing an offset by parsing the returned name
    will silently produce the wrong sign — always call ``utcoffset()`` on an
    aware datetime instead.


Django
------

querying the timezone name in a ``Django`` view:


.. code-block:: python

    def find_timezone(request, lat, lng):
        lat = float(lat)
        lng = float(lng)
        try:
            timezone_name = tf.timezone_at(lng=lng, lat=lat)
        except ValueError:
            # the coordinates were out of bounds
            pass  # {handle error}
        if timezone_name is None:
            # no timezone matched
            ...

        # do something with timezone_name
        ...




.. _parse_data:

Use other data
--------------


File converter script
*********************


This package includes the ``file_converter.py`` script to parse timezone data and compile the binary data files required
by the ``timezonefinder`` package.
This script is built for processing the specific ``geojson`` format of the default data: `timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder/releases>`__.
Any other data in this format can also be parsed:

::

    python -m scripts.file_converter \
        [-inp /path/to/input.json] \
        [-out /path/to/output_folder] \
        [--zone-id-dtype {uint8,uint16}] \
        [--data-version RELEASE]

Run it from the root of a ``timezonefinder`` repository checkout: the converter imports its
helpers as ``scripts.<module>``, so invoking it by path fails to resolve them. ``make testparse``
runs exactly this against the small ``tests/test_input.json`` fixture.



Per default the script parses the timezone-boundary-builder release named by the
repository's ``DATA_VERSION`` out of ``tmp/`` - where ``update_data.sh`` leaves it - into the
packaged data directory.

The release a parse came from is recorded in the compiled data and reported by
``TimezoneFinder.data_version``, and it is read off the input's filename
(``combined-with-oceans-2026c.json``), because nothing inside the GeoJSON states it. Your own
data needs no such name: it is recorded as ``unknown``, which is the true answer for boundaries
that are not a release. An *unpacked release archive* that lost its tag is refused rather than
recorded as ``unknown`` - rename it, or state the release with ``--data-version``.

Use ``--zone-id-dtype`` (or set ``TIMEZONEFINDER_ZONE_ID_DTYPE``) when your dataset
contains more than 256 distinct timezones so the generated binaries use
``uint16`` storage instead of the default ``uint8``.
How to use the ``timezonefinder`` package with data files from another location is described :ref:`HERE <init>`.




Data update shell script
************************

The included ``update_data.sh`` shell script simplifies downloading the latest version of
`timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder/releases>`__
data and parsing in with ``file_converter.py``.
It is non-interactive and controlled entirely via command line flags:

::

    /bin/bash /path/to/timezonefinder/update_data.sh [--dataset=full|same-since-now] [--with-oceans] [--rm-tmp]

Without the ``--with-oceans`` flag the dataset WITHOUT ocean timezones is used.
This is useful if you do not require ocean timezones and want to have smaller data files.
