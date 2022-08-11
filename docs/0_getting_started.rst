

===============
Getting started
===============


Installation
------------

Installation with conda:
see instructions at `conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__



Minimal installation with pip:


.. code-block:: console

    pip install timezonefinder


It is highly recommended to also install ``numba`` for increased performance (cf. :ref:`speed test results <speed-tests>`).
With ``numba`` installed, the time critical algorithms will be automatically JIT compiled (cf. ``utils.py``).


.. code-block:: console

    pip install timezonefinder[numba]



Dependencies
------------

``python3.7+``, ``numpy``, (``numba``)



Basics
------



.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()
    latitude, longitude = 52.5061, 13.358
    tf.timezone_at(lng=longitude, lat=latitude)  # returns 'Europe/Berlin'


All available features of this package are explained :ref:`HERE <usage>`.

Examples for common use cases can be found :ref:`HERE <use_cases>`.
