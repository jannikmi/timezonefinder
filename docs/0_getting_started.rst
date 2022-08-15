

Getting started
===============


Installation
------------


.. code-block:: console

    pip install timezonefinder


For installation within a Conda environment see instructions at `conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__


Dependencies
------------

``python3.7+``, ``numpy``




Basic Usage
-----------



.. code-block:: python

    from timezonefinder import TimezoneFinder

    tf = TimezoneFinder()  # reuse

    query_points = [(13.358, 52.5061), ...]
    for lng, lat in query_points:
        tz = tf.timezone_at(lng=lng, lat=lat)  # 'Europe/Berlin'


All available features of this package are explained :ref:`HERE <usage>`.

Examples for common use cases can be found :ref:`HERE <use_cases>`.
