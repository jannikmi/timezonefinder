

===============
Getting started
===============


Installation
------------

Installation with conda:
see instructions at `conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__



Installation with pip:
in your command line:

::

    pip install timezonefinder


If the vanilla Python code is too slow for you, the time critical algorithms (in ``helpers_numba.py``) can be automatically JIT compiled by ``numba``.
This speeds things up by a factor of around 100 (cf. :ref:`speed test results <speed-tests>`).

::

    pip install timezonefinder[numba]



Dependencies
------------

``python3.6+``, ``numpy``, (``numba``)



Basics
------



.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()
    latitude, longitude = 52.5061, 13.358
    tf.timezone_at(lng=longitude, lat=latitude) # returns 'Europe/Berlin'


All available features of this package are explained :ref:`HERE <usage>`.

Examples for common use cases can be found :ref:`HERE <use_cases>`.
