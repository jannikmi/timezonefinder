==============
timezonefinder
==============

.. include:: ./badges.rst


This is a fast and lightweight python package for looking up the corresponding
timezone for given coordinates on earth entirely offline.


Quick Guide:

::

    pip install timezonefinder[numba] # also installs numba -> x100 speedup


.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()
    latitude, longitude = 52.5061, 13.358
    tf.timezone_at(lng=longitude, lat=latitude) # returns 'Europe/Berlin'


For more refer to the `Documentation <https://timezonefinder.readthedocs.io/en/latest/>`__.

Also check:

`PyPI <https://pypi.python.org/pypi/timezonefinder/>`__

`online GUI and API <https://timezonefinder.michelfe.it>`__

`conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__

ruby port: `timezone_finder <https://github.com/gunyarakun/timezone_finder>`__

`download stats <https://pepy.tech/project/timezonefinder>`__

