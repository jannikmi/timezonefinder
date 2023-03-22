

Getting started
===============


Installation
------------


.. code-block:: console

    pip install timezonefinder


in case you are using ``pytz``, also require it via its extra to avoid incompatibilities (e.g. due to updated timezone names):

.. code-block:: console

    pip install timezonefinder[pytz]


for improved speed also install the optional dependency ``numba`` via its extra (also check the :ref:`performance chapter <performance>`):

.. code-block:: console

    pip install timezonefinder[numba]


For installation within a Conda environment see instructions at `conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__


Dependencies
------------


``python3.8+``, ``numpy``, ``h3``, ``cffi``

optional: ``numba``

(cf. ``pyproject.toml``)



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
