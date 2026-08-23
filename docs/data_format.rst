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
3. Renaming it after the release it came from (``combined-2026c.json``), which nothing inside the file records
4. Running the ``file_converter.py`` script to compile the data into the binary format used by ``timezonefinder``


The script ``update_data.sh`` automates this process. It resolves the release tag first and names the download after it (``combined-with-oceans-2026c.json``), since a release archive says nothing about which release it is - the converter reads the tag back off that name, and refuses an unpacked archive that lacks it rather than compiling data that could never say where it came from. The tag is also recorded in the repository's ``DATA_VERSION`` file. The script further regenerates the committed benchmark input fixtures under ``tests/fixtures/benchmarks/`` (see ``scripts/generate_benchmark_fixtures.py``), since some of those fixtures (on-land/shortcut classification, point-in-polygon polygon IDs) are derived from this boundary data and are pinned to the ``DATA_VERSION`` they were generated against.

Alternative Dataset Options
============================

The ``update_data.sh`` script also supports downloading the reduced ``timezones-now`` dataset (via ``--dataset=same-since-now``), which merges timezones with identical behavior (as of now) into a single zone. This reduces the number of timezones from ~440 to ~90 and provides a smaller memory footprint. However, this dataset:

* Provides incorrect data for observed timekeeping methods in the past at certain locations
* Loses location-specific information (e.g., ``Europe/Berlin`` becomes ``Europe/Paris``)
* Reduces localization capabilities

If your use case requires the reduced dataset, you can use the ``update_data.sh`` script to download and process the ``timezones-with-oceans-now.geojson`` file.



Data Structure Overview
=======================

Where the data lives
--------------------

The compiled binaries ship in their own distribution, ``timezonefinder-data`` (installed
automatically with ``timezonefinder``), and are reached through ``timezonefinder_data.DATA_DIR`` -
which is what ``timezonefinder.configs.DEFAULT_DATA_DIR`` resolves to. Any other directory of the
same shape works just as well: pass it as ``bin_file_location`` (see :ref:`use cases <use_cases>`).

That distribution's **major version is the data format generation**
(``timezonefinder.configs.DATA_FORMAT_VERSION``), and its remaining two components name the
upstream release: ``2.2026.3`` is format 2 built from ``2026c``. ``timezonefinder`` requires
``timezonefinder-data>=…,<N+1``, so a dataset update needs no code release while a format change is
refused when resolving rather than when reading. Bumping either per-file ``layout_version`` below
requires bumping ``DATA_FORMAT_VERSION`` too.

The timezonefinder library uses highly optimized binary data structures to enable fast and memory-efficient timezone lookups. The data is organized into several files:

1. **Polygon Coordinates**: Stored in a FlatBuffers binary file (``coordinates.bin``) one for all timezone boundary polygons and one for all holes. The hole file holds only the rings that are not a copy of a boundary polygon (see `Holes as Boundary References`_)
2. **Shortcut Index**: Spatial index over H3 hexagons (``shortcuts.bin``) holding, per cell, either the timezone that covers it or the polygons a lookup there has to test
3. **Numpy Arrays**: Various NumPy binary files (.npy) storing information about the polygons
4. **Zone Names**: Text file listing the timezone names
5. **Hole Registry**: a mapping from polygon IDs to the amount and position of its holes
6. **Schemas**: a copy of the FlatBuffers schema definitions the binaries above were written by, under ``schemas/``


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

* ``coordinates.bin``: FlatBuffer binary file containing all polygon coordinates
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

* ``shortcuts.bin``: the spatial index, mapping every H3 cell at resolution 3 to either the
  zone that covers it or the boundary polygons a lookup there has to test. Its layout is
  described under `Shortcut Index Layout`_.

Other Files
-----------

* ``schemas/*.fbs``: the FlatBuffers schema definitions describing the binaries in this
  directory, copied from ``timezonefinder/flatbuf/schemas/`` when the data is compiled.
  A data directory that carries the definition of its own format can be read back
  without the package that wrote it. Generated, never hand-edited:
  ``scripts/data_integrity.validate_shipped_schemas`` holds the copy to the original
  both in the converter and over the committed data

.. note::

    The two extensions are not interchangeable. ``.fbs`` is the FlatBuffers *schema*
    extension and is used here only for schema definitions; the serialised buffers are
    ``.bin``, and each says what it is through the file identifier in its first bytes
    rather than through its name.
* ``timezone_names.txt``: List of all timezone names
* ``data_version.txt``: the timezone-boundary-builder release this data was compiled
  from, as ``TimezoneFinder.data_version`` reports it. Taken from the input's filename
  (``combined-with-oceans-2026c.json``), or from ``file_converter.py --data-version``
  for an input that cannot carry it. Data that is not a release at all - your own
  GeoJSON - is stamped ``unknown``

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
     - the hole ring *is* boundary polygon ``v``; read it from ``boundaries/coordinates.bin``
   * - ``v < 0``
     - the ring is stored inline, at index ``-(v + 1)`` of ``holes/coordinates.bin``

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

The library uses the `Google FlatBuffers <https://pypi.org/project/flatbuffers/>`_ binary file format for the polygon coordinate data.
The schemas are defined in the ``timezonefinder/flatbuf/schemas/*.fbs`` files.

``coordinates.bin`` and ``shortcuts.bin`` both carry a file identifier and a ``layout_version``, both checked when the file is opened; a mismatch raises a ``ValueError`` naming the offending file instead of silently returning wrong timezones. ``coordinates.bin`` uses the identifier ``TZFP``, and its ``layout_version`` records the coordinate encoding and, for a hole collection, whether it holds every ring or only the ones that are not references (see `Holes as Boundary References`_). ``shortcuts.bin`` uses ``TZSC``.

``layout_version`` tracks what the file *holds*, not the package version, and is bumped only when that actually changes. Data compiled by any release that writes a given layout is readable by any release that reads it, so a directory passed to ``bin_file_location`` does not need regenerating on an ordinary upgrade - only when the changelog reports a data format change, or when you want newer boundary data.

Note that this check covers those two files only. The NumPy arrays carry no such marker yet, so mixing those across a format change is still undetected.


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
every resolution from 0 upwards, prices each one in the layout described below, and benchmarks them
against a common set of globally random query points.

Below resolution 3, cells cover too much area and too many of them come out ambiguous, which pushes
work back onto the expensive point-in-polygon path. Resolutions above 5 are excluded outright, since
the table below grows eightfold per level.

**Resolution 4 is a live question rather than a closed one, and what changed is the reason.** It was
refused on size, back when the index was a file of individually decoded per-cell entries and a
sevenfold cell count meant a sevenfold file — more than 10 % of the packaged polygon data. In the
layout described below it does not: the candidate lists deduplicate, so seven times the cells add
only about a sixth more distinct lists, and almost the whole increase is the fixed-size table.
Measured over the packaged dataset, resolution 4 is a ~0.6 MiB file against ~0.1 MiB, still around
one percent of the distribution, and it removes about **60 % of the point-in-polygon tests** a
uniformly random workload runs, with 89 % of cells resolving to a single zone against 75 %.

What it costs instead is memory and cache. The resident table grows about sevenfold, which matters
most to ``TimezoneFinderL``, whose entire footprint is this index, and to the constrained containers
the memory-mapped mode exists for; and the table stops fitting a typical L2 cache, so the one read a
unique-zone query makes gets dearer even as far fewer queries need geometry at all. Compiling the
index also takes several times longer on every data update. Whether that trade is worth a second
data format generation is not settled here.

**A hierarchical index — several resolutions at once, refining only where cells are ambiguous — was
prototyped and dropped.** The maximum resolution dominates the size, so a multi-resolution index
comes out slightly *larger* than the single-resolution one it contains; H3 cells do not nest
cleanly, so a parent has to be kept even once its children exist; and consulting several resolutions
per query costs more than the refinement saves. It yielded no lookup benefit over a single-resolution
index at the same maximum resolution, so the simpler structure won.

The shortcuts are precompiled during the data build process. This preprocessing step is computationally intensive but only needs to be performed once, allowing all subsequent timezone lookups to be extremely fast.

.. _shortcut-index-layout:

Shortcut Index Layout
---------------------

``shortcuts.bin`` holds four arrays after a 32-byte header. The header is the file
identifier ``TZSC``, a ``uint32`` layout version, and three ``int64``: the number of
distinct candidate lists, and the widths chosen for the two data-dependent columns.

.. list-table::
   :header-rows: 1

   * - array
     - dtype
     - indexed by
     - holds
   * - ``table``
     - ``int16``
     - compact slot
     - the answer for that cell
   * - ``bounds``
     - narrowest that fits
     - distinct candidate list
     - CSR offsets into ``payload``, ``n+1`` of them
   * - ``payload``
     - ``uint16``
     - -
     - every distinct candidate list, back to back
   * - ``last_change``
     - narrowest that fits
     - distinct candidate list
     - where the candidate loop may stop

**The cell id is the index.** H3 packs a cell index as a base cell in bits 45-51 followed
by fifteen 3-bit digits. At a fixed resolution every other bit is constant, so those bits
*are* the cell and

.. code-block:: python

    slot = ((cell >> 45) & 0x7F) * 512 + ((cell >> 36) & 0x1FF)

is a bijection onto a dense table rather than a hash. No keys are stored and no search
runs at lookup time. That h3-py does not promise its index encoding as API is handled by
checking rather than by storing: ``scripts/data_integrity.validate_shortcut_index``
confirms the arithmetic against the public ``get_base_cell_number`` and
``cell_to_child_pos`` on every cell that exists, so an encoding change fails where the
data is built instead of silently returning a neighbour's timezone.

**The table holds the answer.** One ``int16`` per slot:

* ``>= 0`` - the zone id, and the whole answer. Roughly three quarters of the cells.
* ``== -1`` - no cell here. Custom data can leave cells uncovered, so this is a real
  state and not only padding.
* ``< -1`` - several zones; candidate list ``-(value + 2)``.

``-1`` is free for "absent" because a stored candidate list can never have length 1: a
lone candidate is unambiguous and is therefore stored as a zone id instead.

Because a cell the table answers reads nothing else, ``bounds`` and ``last_change`` are
indexed by *distinct candidate list* rather than by cell or by slot - far fewer of them,
and the cells that never read them cost nothing.

**Each distinct candidate list is stored once.** Cells with identical lists carry *equal*
offsets into the shared payload, not an index to a shared entry, so a repeated list costs
a lookup exactly what a unique one costs. The distinct lists are packed back to back, so
one CSR array of ``n+1`` bounds carries both starts and ends and no length column exists
to disagree with it.

**``last_change`` is ``get_last_change_idx`` precomputed.** It depends only on the
candidate list, so it deduplicates with everything else and costs one byte per distinct
list to take a scan off every ambiguous query.

**The file is base-7, the table is base-8.** H3 digits only take 0-6, so a third of the
base-8 slots can never be addressed. Which ones follows from the resolution and never from
the data, so the file stores the compact base-7 form and the reader expands it - a base-8
slot is exactly the C-order ravel of a ``(122, 8, 8, 8)`` array, so the base-7 block lands
correctly when sliced into its corner. The in-memory table keeps its padding: addressing
it base-7 per query costs more than the padding is worth.

**The two data-dependent widths are chosen by fit, not by headroom.** An overflow surfaces
where the data is built rather than in a user's process - provided something checks, which
is what ``scripts/data_integrity.py`` does, over what the converter just wrote and over
what is committed, naming the value, the ceiling, the width to move to and the version
bumps that follow.

A lookup, in full::

    slot = <the arithmetic above>            # no memory touched
    z = table[slot]
    if z >= 0:  return z                     # 1 read
    if z == -1: return None                  # 1 read
    i = -(z + 2)                             # several zones: the candidate list, plus
    return payload[bounds[i]:bounds[i + 1]]  # last_change[i] for where to stop

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
