

Getting started
===============


Installation
------------


.. code-block:: console

    pip install timezonefinder


for improved speed also install the optional dependency ``numba`` via its extra (also check the :ref:`performance chapter <performance>`):

.. code-block:: console

    pip install timezonefinder[numba]



in case you are using ``pytz``, also require it via its extra to avoid incompatibilities (e.g. due to updated timezone names):

.. code-block:: console

    pip install timezonefinder[pytz]



For installation within a Conda environment see instructions at `conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__


Dependencies
------------

Four runtime dependencies, each carrying part of the lookup:

* ``numpy`` - the arrays the polygon data is read into
* ``h3`` - the hexagonal grid the shortcut index is built on
* ``cffi`` - builds and binds the optional C extension
* ``flatbuffers`` - reads the packaged binary data without unpacking it

The list is deliberately short: the timezone data ships with the package, so nothing is downloaded or
looked up at runtime, and no geospatial stack is pulled in. ``numba`` is an *extra* rather than a
dependency because it only makes the package faster, never more correct - see :ref:`performance
chapter <performance>`.

``pyproject.toml`` remains the authoritative source for the supported version ranges.


Basic Usage
-----------


All available features of this package are explained in the :ref:`usage chapter <usage>`.

Examples for common use cases can be found in the :ref:`use case chapter <use_cases>`.
