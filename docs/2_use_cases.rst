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


.. _parse_data:

Use other data
--------------

In some cases it might be useful to use other data (e.g. the releases of the `timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder/releases>`__ with sea timezones).
This package includes the script ``file_converter.py`` to parse the data file of this specific .json format.

Instructions:

* download a ``timezones.geojson.zip`` data set file from `timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder/releases>`__
* unzip and place the ``combined.json`` inside the ``timezonefinder`` folder
* now run the ``file_converter.py`` until the compilation of the binary files is completed

If you want to use your own data set, create a ``combined.json`` file with the same format .json as the timezone-boundary-builder and follow the above instructions.

You can also use data files from another location as described :ref:`HERE <init>`

.. TODO script



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


