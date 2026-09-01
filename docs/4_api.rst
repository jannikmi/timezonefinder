.. _api:

=================
API documentation
=================


.. py:module:: timezonefinder

.. _api_global:

Global Functions
----------------

.. autofunction:: timezone_at
.. autofunction:: timezone_ids_at
.. autofunction:: timezone_names_at
.. autofunction:: timezone_at_land
.. autofunction:: unique_timezone_at
.. autofunction:: certain_timezone_at
.. autofunction:: get_geometry

.. _api_zoneinfo:

Timezone conversion helpers
---------------------------

The three steps most callers take after the lookup, as global functions and as methods
on both finder classes. They resolve the returned IANA name through the standard
library's ``zoneinfo``, which applies the inverted ``Etc/GMT±X`` sign convention
correctly - deriving an offset by reading the name instead produces the wrong sign
without failing, and the packaged data returns an ``Etc/GMT`` zone for every coordinate
at sea.

.. note::

    Windows ships no system timezone database, so ``pip install tzdata`` is required
    there before any of these resolve a name; without it they raise
    ``zoneinfo.ZoneInfoNotFoundError``. This package returns IANA names and does not
    carry the database itself.

.. autofunction:: zoneinfo_at
.. autofunction:: utc_offset_at
.. autofunction:: localize

.. _api_finderL:


TimezoneFinderL
---------------
.. autoclass:: TimezoneFinderL


.. _api_finder:

TimezoneFinder
--------------
.. autoclass:: TimezoneFinder
