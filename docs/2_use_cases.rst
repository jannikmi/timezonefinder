.. _use_cases:

===========
Use Cases:
===========


Creating aware datetime objects
-------------------------------

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



Getting a location's time zone offset
--------------------------------------

.. code-block:: python

    from datetime import datetime
    from pytz import timezone, utc

    def get_offset(*, lat, lng):
        """
        returns a location's time zone offset from UTC in minutes.
        """

        today = datetime.now()
        tz_target = timezone(tf.certain_timezone_at(lng=lng, lat=lat))
        # ATTENTION: tz_target could be None! handle error case
        today_target = tz_target.localize(today)
        today_utc = utc.localize(today)
        return (today_utc - today_target).total_seconds() / 60


    bergamo = {'lat': 45.69, 'lng': 9.67}
    minute_offset = get_offset(**bergamo)


also see the `pytz Doc <http://pytz.sourceforge.net/>`__.


Django
------

Maximising the chances of getting a result in a ``Django`` view:


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

    python /path/to/timezonefinder/timezonefinder/file_converter.py [-inp /path/to/input.json] [-out /path/to/output_folder]



.. note::

    this script requires python3.6+ (as timezonefinder in general)


Per default the script parses the ``combined.json`` from its own parent directory (``timezonefinder``) into data files inside its parent directory.
How to use the ``timezonefinder`` package with data files from another location is described :ref:`HERE <init>`.




Data parsing shell script
*************************

The included ``parse_data.sh`` shell script simplifies downloading the latest version of
`timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder/releases>`__
data and parsing in with ``file_converter.py``.
It supports downloading the ``timezone-boundary-builder`` version with ocean timezones.


::

    /bin/bash  /path/to/timezonefinder/parse_data.sh



