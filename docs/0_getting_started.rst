
.. _getting_started:

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



Dependencies
------------

``python3``, ``numpy``

Currently tested under: python 3.6, 3.7, 3.8


**Optional:**

If the vanilla Python code is too slow for you, also install

`Numba <https://github.com/numba/numba>`__ and all its Requirements (e.g. `llvmlite <http://llvmlite.pydata.org/en/latest/install/index.html>`_)

This causes the time critical algorithms (in ``helpers_numba.py``) to be automatically JIT compiled to speed things up.


.. warning::

    Python 3.8 is NOT yet supported by Numba. Use Python version 3.6 or 3.7




Basics
------



.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()
    latitude, longitude = 52.5061, 13.358
    tf.timezone_at(lng=longitude, lat=latitude) # returns 'Europe/Berlin'


All available features of this package are explained :ref:`HERE <usage>`.

Examples for common use cases can be found :ref:`HERE <use_cases>`.
