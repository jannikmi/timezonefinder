

Getting started
===============


Installation
------------


.. code-block:: console

    pip install timezonefinder


This builds a C extension for the point-in-polygon test. The optional ``numba`` extra JIT-compiles the same routine for an installation that could not build that extension; where the extension loaded, it is what a lookup runs. :doc:`benchmark_results_acceleration_paths` measures how the three compare (see also the :ref:`performance chapter <performance>`):

.. code-block:: console

    pip install timezonefinder[numba]


The extra is not free, and on an installation whose extension built it now buys nothing: ``numba``
and the LLVM toolchain it brings add more resident memory to every process than the whole packaged
boundary dataset does, and a JIT compilation to the first finder a process builds - which is paid
for compiling the helper functions even though the C extension is what answers the query. Install
it where no compiler is available, and leave it out where one is.


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
timezonefinder`` pulls it in automatically; pin it explicitly to hold a deployment to one dataset -
see :ref:`upgrading` below.

``pyproject.toml`` remains the authoritative source for the supported version ranges.

Which ``numpy`` generations are supported follows the `NumPy deprecation policy <https://numpy.org/neps/nep-0029-deprecation_policy.html#drop-schedule>`__: a generation leaves this package's floor once it leaves that schedule, and NumPy 1 did so in release 8.2.1.

An environment that has to keep NumPy 1 can constrain it and let the resolver fall back to the last release that accepts it. That is a stopgap rather than a destination, because the fallback carries the code and the boundary data of its own release:

.. code-block:: console

    pip install timezonefinder "numpy<2"

Where the clash is with a ``numpy`` installed by the system package manager, a virtual environment is the better answer: it leaves that installation untouched, and needs no fallback.


.. _upgrading:

Upgrading and pinning
---------------------

Pinning ``timezonefinder`` alone does not freeze the results: the boundary data is released separately, on its own schedule, and a new dataset can change the zone returned for a coordinate, not only near a border. Within one installed pair of versions, the same input always gives the same answer.

If you store or audit results:

* Pin both packages, choosing the data version from its `release history <https://pypi.org/project/timezonefinder-data/#history>`__, or use a lock file:

  .. code-block:: console

      pip install "timezonefinder==<version>" "timezonefinder-data==<version>"

* Record both versions next to the stored results, e.g. ``importlib.metadata.version("timezonefinder-data")``.
* Treat a bump of either package as a reason to recompute stored zones.
* Read the changelog before a major ``timezonefinder`` upgrade.

:doc:`result_stability` explains in detail what can change and what cannot.


Basic Usage
-----------


All available features of this package are explained in the :ref:`usage chapter <usage>`.

Examples for common use cases can be found in the :ref:`use case chapter <use_cases>`.
