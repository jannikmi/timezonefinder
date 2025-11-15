

Getting started
===============


Installation
------------


.. code-block:: console

    pip install timezonefinder


for improved speed also install the optional dependency ``numba`` via its extra (also check the :ref:`performance chapter <performance>`):

.. code-block:: console

    pip install timezonefinder[numba]


Binary wheels from PyPI are prebuilt with a C extension using a stable "abi3" Python ABI instead of numba. To build a wheel with C extension locally, set ``BUILD_CFFI=true`` environment variable before installing.

In case you are using ``pytz``, also require it via its extra to avoid incompatibilities (e.g. due to updated timezone names):

.. code-block:: console

    pip install timezonefinder[pytz]



For installation within a Conda environment see instructions at `conda-forge feedstock <https://github.com/conda-forge/timezonefinder-feedstock>`__


Dependencies
------------


please confer to the  ``pyproject.toml``



Basic Usage
-----------


All available features of this package are explained :ref:`HERE <usage>`.

Examples for common use cases can be found :ref:`HERE <use_cases>`.
