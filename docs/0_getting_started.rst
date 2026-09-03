

Getting started
===============


Installation
------------


.. code-block:: console

    pip install timezonefinder


This builds a C extension for the point-in-polygon test, which is where the speed comes from. The optional ``numba`` extra swaps that extension for a JIT-compiled kernel; it is measurably *slower* here, so install it only if you want Numba for other reasons (see the :ref:`performance chapter <performance>` and :doc:`benchmark_results_acceleration_paths`):

.. code-block:: console

    pip install timezonefinder[numba]



in case you are using ``pytz``, also require it via its extra to avoid incompatibilities (e.g. due to updated timezone names):

.. code-block:: console

    pip install timezonefinder[pytz]



For installation within a Conda environment see instructions at `conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__


Dependencies
------------

Five runtime dependencies, each carrying part of the lookup:

* ``numpy`` - the arrays the polygon data is read into
* ``h3`` - the hexagonal grid the shortcut index is built on
* ``cffi`` - builds and binds the optional C extension
* ``flatbuffers`` - reads the packaged binary data without unpacking it
* ``timezonefinder-data`` - the boundary data itself

The list is deliberately short: the timezone data is installed with the package, so nothing is
downloaded or looked up at runtime, and no geospatial stack is pulled in. ``numba`` is an *extra*
rather than a dependency because it only makes the package faster, never more correct - see
:ref:`performance chapter <performance>`.

``timezonefinder-data`` is a distribution of this same project, published separately so that a new
timezone-boundary-builder release ships without a ``timezonefinder`` release. ``pip install
timezonefinder`` pulls it in automatically; pin it explicitly to hold a deployment to one dataset,
choosing the version from its `release history <https://pypi.org/project/timezonefinder-data/#history>`__:

.. code-block:: console

    pip install timezonefinder "timezonefinder-data==<version>"

``pyproject.toml`` remains the authoritative source for the supported version ranges.


Basic Usage
-----------


All available features of this package are explained in the :ref:`usage chapter <usage>`.

Examples for common use cases can be found in the :ref:`use case chapter <use_cases>`.
