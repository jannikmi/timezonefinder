.. _data_format:

===============
Data Format
===============

This document describes the data format used by ``timezonefinder`` library, including the data sources, design rationales, and performance optimizations.

For detailed statistics of the current dataset in use, see :doc:`data_report`. For how these structures are consumed at query time - and for the design decisions behind them - see :doc:`architecture`.


Data Source
===========

The timezone boundary data used in ``timezonefinder`` is sourced from the `timezone-boundary-builder <https://github.com/evansiroky/timezone-boundary-builder>`_ project.
This project compiles timezone boundaries from OpenStreetMap data and makes them available as GeoJSON files.


Dataset version ``timezones-with-oceans``: Currently the boundaries with ocean time zones and the full original dataset are being used.


.. note::

    In the data set the timezone polygons often include territorial waters -> they do NOT follow the shorelines.
    This makes the results of ``certain_timezone_at()`` less expressive:
    from a timezone match one cannot distinguish whether a query point lies on land or in ocean.

.. note::

    Please note that timezone polygons might be overlapping (cf. e.g. `timezone-boundary-builder/issue/105 <https://github.com/evansiroky/timezone-boundary-builder/issues/105>`__)
    and that hence a query coordinate can actually match multiple time zones.
    ``timezonefinder`` does currently NOT support such multiplicity and will always only return the first found match.


The processing pipeline for this data involves:

1. Downloading the latest ``timezones-with-<...>.geojson.zip`` file from the releases section of the timezone-boundary-builder repository
2. Unzipping into the ``combined.json`` file
3. Running the ``file_converter.py`` script to compile the data into the binary format used by ``timezonefinder``


The script ``update_data.sh`` automates this process. It also records the release tag in the ``DATA_VERSION`` file and regenerates the committed benchmark input fixtures under ``tests/fixtures/benchmarks/`` (see ``scripts/generate_benchmark_fixtures.py``), since some of those fixtures (on-land/shortcut classification, point-in-polygon polygon IDs) are derived from this boundary data and are pinned to the ``DATA_VERSION`` they were generated against.

Alternative Dataset Options
============================

The ``update_data.sh`` script also supports downloading the reduced ``timezones-now`` dataset (via ``--dataset=same-since-now``), which merges timezones with identical behavior (as of now) into a single zone. This reduces the number of timezones from ~440 to ~90 and provides a smaller memory footprint. However, this dataset:

* Provides incorrect data for observed timekeeping methods in the past at certain locations
* Loses location-specific information (e.g., ``Europe/Berlin`` becomes ``Europe/Paris``)
* Reduces localization capabilities

If your use case requires the reduced dataset, you can use the ``update_data.sh`` script to download and process the ``timezones-with-oceans-now.geojson`` file.



Data Structure Overview
=======================

The timezonefinder library uses highly optimized binary data structures to enable fast and memory-efficient timezone lookups. The data is organized into several files:

1. **Polygon Coordinates**: Stored in a FlatBuffers binary file (``coordinates.fbs``) one for all timezone boundary polygons and one for all holes. The hole file holds only the rings that are not a copy of a boundary polygon (see `Holes as Boundary References`_)
2. **Hybrid Shortcut Index**: Spatial index using H3 hexagons (``hybrid_shortcuts_uint8.fbs`` or ``hybrid_shortcuts_uint16.fbs``) that stores either direct zone IDs or polygon lists depending on timezone complexity
3. **Numpy Arrays**: Various NumPy binary files (.npy) storing information about the polygons
4. **Zone Names**: Text file listing the timezone names
5. **Hole Registry**: a mapping from polygon IDs to the amount and position of its holes


Coordinate Representation
-------------------------

All coordinates (longitude and latitude) from the timezone polygons are converted from floating-point to 32-bit integers by multiplying them by 10^7. This transformation:

* Makes computations faster
* Requires significantly less storage space
* Maintains high accuracy (minimum accuracy at the equator is still ~1 cm)

Each polygon's integer coordinates are stored one axis at a time inside a single ``int32`` vector: all x (longitude) values followed by all y (latitude) values (``[x0...xN-1, y0...yN-1]``). The raycasting point in polygon algorithm scans a single axis per iteration, so contiguous per-axis blocks keep every loaded cache line fully used and let both acceleration backends read an axis without copying it first.

Data Files
==========

The library creates and uses the following files:

Polygon Data
------------

* ``coordinates.fbs``: FlatBuffer binary file containing all polygon coordinates
* ``zone_ids.npy``: NumPy array mapping polygon IDs to timezone IDs. Stored as
  unsigned integers (``uint16`` by default, ``uint8`` for datasets with less than 256 timezones); pass
  ``--zone-id-dtype`` to ``scripts/file_converter.py`` or set the environment variable
  the ``TIMEZONEFINDER_ZONE_ID_DTYPE`` environment variable when compiling custom data to override the default.
* ``zone_positions.npy``: NumPy array indicating where each timezone's polygons start and end

Boundaries Information
----------------------

* ``xmin.npy``, ``xmax.npy``, ``ymin.npy``, ``ymax.npy``: NumPy arrays storing the bounding boxes for each polygon

Hole Data
---------

* ``poly_ref.npy``: NumPy ``int32`` array, one entry per hole, saying where that hole's
  ring is stored (see `Holes as Boundary References`_)

Spatial Indexing
----------------

* ``hybrid_shortcuts_uint8.fbs`` (or ``hybrid_shortcuts_uint16.fbs``): FlatBuffer binary file containing the hybrid spatial index that maps H3 hexagon IDs to either:

   - Direct zone IDs (when all polygons in a hexagon belong to the same timezone)
   - Arrays of polygon IDs that intersect with each hexagon (when multiple timezones are present)

   The file format is automatically selected based on the zone ID data type to optimize storage.

Other Files
-----------

* ``timezone_names.txt``: List of all timezone names

Holes as Boundary References
============================

Almost every hole in the dataset is an **enclave**: the upstream boundary builder cuts a
hole into the surrounding zone using exactly the ring it also emits as the enclosed
zone's own boundary polygon. Both rings describe the same closed path, so storing the
hole ring a second time is pure redundancy — it is the same geometry under two IDs.

``poly_ref.npy`` records, per hole ID, which of the two cases applies. The sign carries
the discriminant, so no separate table and no ambiguous sentinel value is needed:

.. list-table::
   :header-rows: 1

   * - value
     - meaning
   * - ``v >= 0``
     - the hole ring *is* boundary polygon ``v``; read it from ``boundaries/coordinates.fbs``
   * - ``v < 0``
     - the ring is stored inline, at index ``-(v + 1)`` of ``holes/coordinates.fbs``

Both index spaces are dense and start at zero, which is why the inline case is offset by
one: without it, inline ring ``0`` would encode as ``-0 == 0`` and collide with boundary
polygon ``0``.

Two properties keep this cheap at runtime:

* **Hole IDs stay dense.** Every hole ID remains valid, so the hole registry and all of
  its consumers are untouched by the change.
* **The bounding box vectors stay valid verbatim.** A referenced ring is identical to
  the boundary ring, so its bounding box already equals the boundary's. The bounding box
  rejection test — the hot path — keeps reading a flat array with no indirection; only
  the coordinate lookup gains a branch, and only where a point in polygon test was about
  to happen anyway.

Matching is done on a canonical form of the ring (rotated to its lexicographically
smallest vertex, compared in both winding directions), with bounding box and vertex count
equality as a prefilter only. It compares the integer coordinates themselves rather than
any derived quantity, so there is no tolerance involved: two rings either trace the same
closed path or they do not.

A consequence worth knowing: a referenced hole ring is handed back exactly as the
boundary polygon stores it, which for part of the dataset means a different starting
vertex or winding direction than the hole ring originally had. The closed path — and
therefore every point in polygon result and every timezone answer — is unchanged, but
:meth:`~timezonefinder.TimezoneFinder.get_geometry` may report those hole rings starting
at a different vertex than an older release did.

Holes without a twin
--------------------

A small remainder (27 of 756 in release ``2026c``) matches no boundary polygon and stays
stored inline. These are mostly ocean zones (``Etc/GMT±XX``) cut by a hole whose area is
covered by a *union* of several land zones rather than by any single polygon, plus the
``Asia/Jerusalem`` enclaves.

They are kept rather than dropped. Probing their interiors shows every one of them is in
fact covered by other zones, so dropping them would not leave a gap — but only as long as
each covering polygon is tested before the parent polygon in every shortcut cell the hole
touches. That ordering is an emergent property of how shortcut candidates are sorted, not
an invariant the data guarantees, so relying on it is a separate change with a separate
risk profile.

FlatBuffers Schema
==================

The library uses the `Google FlatBuffers <https://pypi.org/project/flatbuffers/>`_ binary file format for efficient binary serialization of the polygon and shortcut data.
The schemas are defined in the ``timezonefinder/flatbuf/schemas/*.fbs`` files.

``coordinates.fbs`` carries a FlatBuffers file identifier (``TZFP``) and a ``layout_version`` field recording the coordinate encoding. Both are checked when the file is opened, and a mismatch raises a ``ValueError`` naming the offending file instead of silently returning wrong timezones.

``layout_version`` tracks the *encoding*, not the package version, and is bumped only when the encoding actually changes. Data compiled by any release that writes a given layout is readable by any release that reads it, so a directory passed to ``bin_file_location`` does not need regenerating on an ordinary upgrade - only when the changelog reports a data format change, or when you want newer boundary data.

Note that this check currently covers the coordinate files only. The shortcut index and the NumPy arrays carry no such marker yet, so mixing those across a format change is still undetected.


Spatial Indexing with H3 Hexagons
=================================

The Spatial Indexing Backbone
-----------------------------

The spatial indexing system based on `H3 hexagons  <https://github.com/uber/h3-py>`__ is the backbone of the ``timezonefinder`` package and its performance. This indexing mechanism drastically reduces the number of polygons that need to be checked to determine which timezone a point is located in.

How it works:
~~~~~~~~~~~~~

* The surface of the Earth is divided into a grid of hexagons using Uber's H3 library
* For each hexagon cell, the library uses a hybrid storage approach:

   - **Unique zones**: When all polygons in a hexagon belong to the same timezone, the zone ID is stored directly
   - **Multiple zones**: When a hexagon contains polygons from different timezones, an array of polygon IDs is stored

* When looking up a timezone for a specific point, the library:
   * Determines which H3 hexagon contains the point
   * Retrieves the shortcut entry for that hexagon
   * If it's a zone ID, returns the timezone immediately
   * If it's a polygon array, tests only those polygons to determine which timezone the point belongs to

This hybrid approach provides several performance benefits:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Reduced Search Space**: Instead of checking all polygons (thousands), only a small subset needs to be evaluated
* **Immediate Results**: For hexagons with unique timezones (~majority of cases), the result is returned immediately without any polygon testing
* **Memory Efficiency**: The spatial index is compact and optimized for fast lookups, storing zone IDs directly when possible
* **Adaptive Storage**: Uses the most efficient storage method for each hexagon based on its timezone complexity

H3 Resolution Selection
~~~~~~~~~~~~~~~~~~~~~~~

The library uses H3 resolution 3 with 41k hexagons for its spatial index. That is a measured
choice, not an assumption: ``prototypes/single_resolution_bench.py`` builds a separate index at
every resolution from 0 upwards and benchmarks each against a common set of globally random query
points.

The finding is a size cliff. At resolution 3 the hybrid index costs a low single-digit percentage
of the packaged polygon data (:doc:`data_report` lists the current sizes). When the study was run,
resolution 4 would have accounted for **more than 10 %** of it, for lookup gains that do not
justify the increase. Resolutions above 5 are excluded outright, since the index size explodes.
Below resolution 3, cells cover too much area and too many of them turn out ambiguous, which pushes
work back onto the expensive point-in-polygon path.

Resolution 3 is therefore the largest index that still costs a small fraction of the data it
indexes.

The shortcuts are precompiled during the data build process. This preprocessing step is computationally intensive but only needs to be performed once, allowing all subsequent timezone lookups to be extremely fast.

Hybrid Shortcut Data Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The hybrid shortcut system combines two previous approaches into a single optimized data structure:

* **Direct Zone Storage**: For hexagons where all intersecting polygons belong to the same timezone, the zone ID is stored directly as an integer. This eliminates the need for polygon testing in the majority of cases.

* **Polygon List Storage**: For hexagons that contain polygons from multiple timezones, an array of polygon IDs is stored. Only these polygons need to be tested during lookup.

This hybrid approach automatically chooses the most efficient storage method for each hexagon, providing optimal performance across different geographic regions. Areas with clear timezone boundaries benefit from immediate zone ID lookups, while complex border regions still use the efficient polygon list approach.

Design Rationales
=================

Several key design decisions make ``timezonefinder`` extremely efficient:

1. **Binary Data Format**: All data is stored in optimized binary formats (FlatBuffers and NumPy arrays) for fast loading and minimal memory footprint

2. **Integer Coordinates**: Converting floating-point coordinates to integers improves computational speed and reduces memory usage

3. **Spatial Indexing**: The H3 hexagon-based spatial index drastically reduces the search space for polygon containment tests

4. **Memory Mapping**: Binary files be read fully into memory with the setting ``in_memory=True``


Advantages
==========

The data format and algorithms used by ``timezonefinder`` provide several key advantages:

1. **Speed**: Timezone lookups are extremely fast, also see :ref:`speed tests <speed-tests>`

2. **Memory Efficiency**: The library has a small memory footprint due to its binary data format and memory mapping

3. **Accuracy**: The data maintains high precision (~1 cm at the equator) despite the space-saving optimizations

4. **Offline Operation**: No internet connection is required for lookups

5. **Cross-platform**: The binary format works across different operating systems and architectures
