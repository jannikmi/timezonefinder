.. _data_format:

===============
Data Format
===============

This document describes the data format used by ``timezonefinder`` library, including the data sources, design rationales, and performance optimizations.

For detailed statistics of the current dataset in use, see :doc:`data_report`.


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


The script ``parse_data.sh`` automates this process.

Alternative Dataset Options
============================

The ``parse_data.sh`` script also supports downloading the reduced ``timezones-now`` dataset, which merges timezones with identical behavior (as of now) into a single zone. This reduces the number of timezones from ~440 to ~90 and provides a smaller memory footprint. However, this dataset:

* Provides incorrect data for observed timekeeping methods in the past at certain locations
* Loses location-specific information (e.g., ``Europe/Berlin`` becomes ``Europe/Paris``)
* Reduces localization capabilities

If your use case requires the reduced dataset, you can use the ``parse_data.sh`` script to download and process the ``timezones-with-oceans-now.geojson`` file.



Data Structure Overview
=======================

The timezonefinder library uses highly optimized binary data structures to enable fast and memory-efficient timezone lookups. The data is organized into several files:

1. **Polygon Coordinates**: Stored in a FlatBuffers binary file (``coordinates.fbs``) one for all timezone boundary polygons and one for all holes
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

The integer coordinates are stored in a columnar format, with x (longitude) and y (latitude) coordinates stored separately, which improves memory access patterns and computational efficiency for the raycasting point in polygon algorithm.

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

Spatial Indexing
----------------

* ``hybrid_shortcuts_uint8.fbs`` (or ``hybrid_shortcuts_uint16.fbs``): FlatBuffer binary file containing the hybrid spatial index that maps H3 hexagon IDs to either:

   - Direct zone IDs (when all polygons in a hexagon belong to the same timezone)
   - Arrays of polygon IDs that intersect with each hexagon (when multiple timezones are present)

   The file format is automatically selected based on the zone ID data type to optimize storage.

Other Files
-----------

* ``timezone_names.txt``: List of all timezone names

FlatBuffers Schema
==================

The library uses the `Google FlatBuffers <https://pypi.org/project/flatbuffers/>`_ binary file format for efficient binary serialization of the polygon and shortcut data.
The schemas are defined in the ``timezonefinder/flatbuf/*.fbs`` files.


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

The library uses H3 resolution 3 with 41k hexagons for its spatial index, which offers a good balance between:

* **Precision**: Enough to significantly reduce the search space
* **Memory Efficiency**: Not too many cells to store
* **Lookup Speed**: Quick to determine which cell contains a point

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
