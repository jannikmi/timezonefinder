.. _use_cases:

===========
Use Cases:
===========


Creating aware datetime objects
-------------------------------

check out the example script in ``examples/aware_datetime.py``


Getting a location's time zone offset
--------------------------------------

check out the example script in ``examples/get_offset.py``


also see the `pytz Doc <http://pytz.sourceforge.net/>`__.


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

    python /path/to/timezonefinder/scripts/file_converter.py \
        [-inp /path/to/input.json] \
        [-out /path/to/output_folder] \
        [--zone-id-dtype {uint8,uint16,uint32}]



Per default the script parses the ``combined.json`` from its own parent directory (``timezonefinder``) into data files inside its parent directory.
Use ``--zone-id-dtype`` (or set ``TIMEZONEFINDER_ZONE_ID_DTYPE``) when your dataset
contains more than 256 distinct timezones so the generated binaries can store the
larger zone identifiers safely.
How to use the ``timezonefinder`` package with data files from another location is described :ref:`HERE <init>`.




Data parsing shell script
*************************

The included ``parse_data.sh`` shell script simplifies downloading the latest version of
`timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder/releases>`__
data and parsing in with ``file_converter.py``.
It supports downloading and parsing the ``timezone-boundary-builder`` version WITHOUT ocean timezones.
This is useful if you do not require ocean timezones and want to have smaller data files.

::

    /bin/bash  /path/to/timezonefinder/parse_data.sh
