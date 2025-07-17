.. _performance:

Performance
===========

Binary Data Format
------------------

TimezoneFinder uses an optimized binary format based on FlatBuffers for storing and accessing timezone data. This format provides several performance advantages:

* **Zero-Copy Access**: FlatBuffers allows accessing serialized data without unpacking or parsing
* **Spatial Indexing**: H3 hexagonal grid system efficiently narrows down polygon candidates
* **Optimized Data Layout**: Compact storage with direct access to relevant data structures

For detailed information about the data format in use, see :doc:`data_format`.


C extension
-----------

During installation ``timezonefinder`` automatically tries to compile a C extension with an implementation of the time critical point in polygon check algorithm.
In order for this to work, a Clang compiler has to be installed.

.. note::

    If compilation fails (due to e.g. missing C compiler or broken ``cffi`` installation) ``timezonefinder`` will silently fall back to a pure Python implementation (~400x slower, cf. :ref:`speed test results <speed-tests>` below).


For testing if the compiled C implementation of the point in polygon algorithm is being used:

.. code-block:: python

    TimezoneFinder.using_clang_pip()  # returns True or False



Numba
-----

Some of the utility function (cf. ``utils.py``) can be JIT compiled automatically by installing the optional dependency ``numba``:

.. code-block:: console

    pip install timezonefinder[numba]


It is highly recommended to install ``Numba`` for increased performance when the C extensions cannot be used (e.g. C compiler is not present at build time).


.. note::

    If Numba can be imported, the JIT compiled Python version of the point in polygon check algorithm will be used instead of the C alternative as it is even faster (cf. :ref:`speed test results <speed-tests>` below).



For testing if Numba is being used to JIT compile helper functions:


.. code-block:: python

    TimezoneFinder.using_numba()  # returns True or False



In memory mode
--------------

To speed up the computations at the cost of memory consumption and initialisation time, pass ``in_memory=True`` during initialisation.
This causes all binary files to be read into memory.

.. code-block:: python

    tf = TimezoneFinder(in_memory=True)



.. _speed-tests:

Speed Benchmark Results
-----------------------

obtained on MacBook Pro (15-inch, 2017), 2,8 GHz Intel Core i7 and timezonefinder version ``6.1.0``


Timezone finding
^^^^^^^^^^^^^^^^

``scripts/check_speed_timezone_finding.py``


Results from version 6.6.0:

.. code-block:: text

    using C implementation: False
    using Numba: True
    in memory mode: True

    10,000 random points (anywhere on earth)
    function name                          | s/query    | pts/s
    ------------------------------------------------------------
    TimezoneFinder.certain_timezone_at()   | 1.9e-05    | 52.2k
    TimezoneFinder.timezone_at_land()      | 5.1e-06    | 195.3k
    TimezoneFinder.timezone_at()           | 4.6e-06    | 215.1k
    TimezoneFinder.unique_timezone_at()    | 2.4e-06    | 424.5k
    TimezoneFinderL.timezone_at_land()     | 1.6e-06    | 615.1k
    TimezoneFinderL.timezone_at()          | 1.4e-06    | 715.6k
    TimezoneFinderL.unique_timezone_at()   | 2.4e-06    | 420.1k



Point in polygon checks
^^^^^^^^^^^^^^^^^^^^^^^

``scripts/check_speed_inside_polygon.py``


Without Numba:

::

    testing the speed of the different point in polygon algorithm implementations
    testing 1000 queries: random points and timezone polygons
    Python implementation using Numba JIT compilation: False

    inside_clang: 2.7e-05 s/query, 3.7e+04 queries/s
    inside_python: 1.0e-02 s/query, 9.9e+01 queries/s
    C implementation is 374.1x faster than the Python implementation WITHOUT Numba


With Numba:

::

    testing the speed of the different point in polygon algorithm implementations
    testing 10000 queries: random points and timezone polygons
    Python implementation using Numba JIT compilation: True

    inside_clang: 2.2e-05 s/query, 4.5e+04 queries/s
    inside_python: 1.8e-05 s/query, 5.5e+04 queries/s
    Python implementation WITH Numba is 0.2x faster than the C implementation


Initialisation
^^^^^^^^^^^^^^^^^^^^^^^

::

    testing initialiation: TimezoneFinder(in_memory=True)
    avg. startup time: 7.01e-01 (10 runs)

    testing initialiation: TimezoneFinder(in_memory=False)
    avg. startup time: 7.85e-01 (10 runs)

    testing initialiation: TimezoneFinderL(in_memory=True)
    avg. startup time: 6.66e-01 (10 runs)

    testing initialiation: TimezoneFinderL(in_memory=False)
    avg. startup time: 7.30e-01 (10 runs)
