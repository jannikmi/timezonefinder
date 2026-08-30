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

What that scale factor buys, and why it is enough
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

One unit is 10\ :sup:`-7` degrees - a *tenth* of a microdegree, not a microdegree.
At the equator, where a degree of longitude is longest and the ground error of a fixed angular step is therefore worst, that is **~1.11 cm**.
The error is a whole step rather than half of one because the conversion truncates toward zero rather than rounding; a rounding conversion would halve it.

The two properties that make this a ceiling rather than a defect:

* **The spacing is even.** A fixed-point integer resolves the same amount at the antimeridian as at Greenwich, which a float does not.
* **It is finer than the source data, by exactly a factor of ten.** timezone-boundary-builder publishes coordinates with **six** decimal places - 10\ :sup:`-6` degrees, ~11.1 cm at the equator - so the seventh decimal this encoding provides carries no information from upstream. That is measurable rather than assumed: across all 15,850,626 packaged coordinate values the last decimal digit is only ever ``0`` or ``9`` and never ``1``-``8``, and the ``9``\ s are the conversion truncating toward zero (``133580000`` stored as ``133579999``) rather than a seventh digit that means anything.

The width is set by the *range*, not by the precision. Covering ±180° at 10\ :sup:`-7` needs 3.6 × 10\ :sup:`9` distinct values, which is 32 bits - but so does 10\ :sup:`-6`, at 3.6 × 10\ :sup:`8`. No precision a boundary dataset could plausibly want brings the global range inside ``int16``, whose 65,536 values over 360° would be 610 m apart. Dropping the redundant decimal would therefore not save a single byte of the current fixed-width layout, and would not make a query faster: the ray-casting kernel does ``int32`` arithmetic whose cost does not depend on the magnitudes involved.

Where it *would* pay is a variable-width encoding, which is why the two are considered together rather than separately. Storing per-polygon deltas as varints, measured over the packaged boundaries: 60.5 MiB fixed-width today, 33.7 MiB at 10\ :sup:`-7`, and **27.7 MiB at 10\ :sup:`-6`** - so the decimal that carries no information costs ~18 % of the encoded size once the encoding is able to charge for it.

For scale in the other direction, consecutive vertices of the packaged polygons are a median 47.6 m apart, and only 0.02 % of edges are shorter than the source's own 11.1 cm step. Coordinate precision and vertex density are separate axes, and neither is the binding constraint on accuracy at a border.

The figures are derived, not quoted: :func:`timezonefinder.utils.coordinate_resolution` returns the representable step of a dtype and :func:`timezonefinder.utils.degrees_to_metres` converts it to ground distance, and ``tests/test_coordinate_precision.py`` holds every claim on this page to what they compute.

.. list-table:: Representable step at ±180° longitude, and what it is on the ground
   :header-rows: 1
   :widths: 22 26 26 26

   * - Storage
     - Step (degrees)
     - At the equator
     - Against the packaged data
   * - ``int32`` × 10\ :sup:`7` *(packaged)*
     - 1.0e-07 (everywhere)
     - 1.11 cm
     - —
   * - ``float64``
     - 2.8e-14
     - 3.2 nm
     - ~3,500,000× finer
   * - ``float32``
     - 1.5e-05
     - 1.70 m
     - ~153× coarser
   * - ``float16``
     - 1.25e-01
     - 13.9 km
     - unusable

``float64`` is therefore the narrowest IEEE float that preserves what the packaged data holds, which is why it is what the lookup converts its input to.
``float32`` fails twice over: its step at the antimeridian is 153 times the stored resolution, and 180 × 10\ :sup:`7` exceeds its exact-integer range (2\ :sup:`24`), so the scaling itself would lose bits.
``float64`` represents that product exactly, well inside 2\ :sup:`53`.

The consequence for a caller is under :ref:`the batch lookups <usage>`: coordinates handed over as ``float32`` can be rounded across a border before the lookup ever runs.

Each polygon's integer coordinates are stored one axis at a time inside a single ``int32`` vector: all x (longitude) values followed by all y (latitude) values (``[x0...xN-1, y0...yN-1]``). The raycasting point in polygon algorithm scans a single axis per iteration, so contiguous per-axis blocks keep every loaded cache line fully used and let both acceleration backends read an axis without copying it first.

Data Files
==========

The library creates and uses the following files:

Polygon Data
------------

* ``coordinates.bin``: FlatBuffer binary file containing all polygon coordinates
* ``block_ranges.npy``, ``block_offsets.npy``: the latitude block index over those
  coordinates (see `Latitude Block Index`_)
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

* ``shortcuts.bin``: the spatial index, mapping every H3 cell at resolution 4 to either the
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

Latitude Block Index
====================

Ray casting flips the inside/outside parity only on an edge that *spans* the query
latitude: the kernel's test ``(y > y1) ^ (y > y2)`` is exactly
``min(y1, y2) < y <= max(y1, y2)``. An edge that does not span it contributes nothing,
however far the ray otherwise travels - and in a ring of nearly 200,000 vertices, almost
none of them do.

So every ring is split into fixed blocks of consecutive vertices, and the range of
latitudes each block's edges span is stored beside the coordinates. A block whose range
excludes the query latitude provably holds no flipping edge and is skipped whole.

.. list-table::
   :header-rows: 1

   * - File
     - What it holds
   * - ``block_ranges.npy``
     - ``int32``, shape ``(total blocks, 2)``: the ``[min, max]`` latitude of every
       block, all rings' blocks concatenated in ring order
   * - ``block_offsets.npy``
     - ``uint32``, one entry per ring plus one: ring *i* owns
       ``block_ranges[offsets[i]:offsets[i + 1]]``

A block owns the edges *leaving* its own vertices, so its last edge reaches the first
vertex of the next block - and on the final block, wraps to vertex 0. That bridging
vertex is included in the range, which is what makes every edge lie inside exactly one
block's stored range.

``POLYGON_BLOCK_SIZE`` (``timezonefinder/configs.py``) is 128 vertices per block. It is
chosen by measurement rather than by intuition, and the two sides of the trade run
opposite ways: smaller blocks bound a ring's latitudes more tightly and skip more of it,
larger blocks decide that in fewer comparisons.
``scripts/tune_block_size.py`` re-runs the sweep over whatever data is packaged.
Nothing in the files records the size they were built at, so it is part of what the
polygon layout version means - a directory blocked at another size is rejected by the
layout marker in ``coordinates.bin``, and by
``scripts.data_integrity.validate_block_index`` where the data is produced.

What it costs is one ``int32`` pair per block - about 0.5 MB against 63 MB of
coordinates - and one comparison for the 30 % of polygons small enough to fit in a
single block. What it buys is the long tail: the slowest queries this package answers
are one ray cast across a very large ring, and
:doc:`benchmark_results_timezonefinding` carries the distribution.

Where a ring starts
-------------------

Blocks partition a ring from its first vertex, so *where a stored ring starts* changes
how tightly its blocks bound it - and nothing downstream depends on that choice. The
canonical key used to match holes against boundaries is rotation-invariant, the bounding
boxes are unaffected, and a hole kept as a reference follows its boundary automatically.
The converter therefore rotates each ring to the start index that minimises the expected
scan, and stores nothing to record it: no reader can tell, and none needs to.

The objective is deliberately query-independent. For a latitude drawn uniformly from a
ring's own range - which is what a bounding-box check has already narrowed a query to -
the expected number of edges scanned is ``sum(edges in block × block span) / total
span``, so minimising the numerator minimises the expected scan without the builder ever
seeing a query. **Each block is weighted by the number of edges it holds**, which
matters because the final block is ragged: for a ring of 129 vertices it holds one edge
against the first block's 128, and weighting the two equally would trade a large real
cost for a tiny one. All rotations are searched, not one block of them, since rotating
by a whole block moves that ragged block and so repartitions the ring rather than
relabelling it. It is worth ~9 % of the edges a query scans - real, but well below what
the benchmark suite can resolve, which is why it is taken as a free step of a rebuild
that was happening anyway rather than claimed as a speedup.

The two rules that suggest themselves both *lose*: starting at the minimum-latitude
vertex costs 1.026x the edges of the unrotated order and the maximum-latitude one
1.010x. The reason is the bridging vertex - the last block's bridge wraps to vertex 0,
so putting a latitude extreme there stretches exactly that block.

Searching every rotation would be quadratic done directly. It is linear in the number of
blocks instead: the span of every window is computed once for all start positions, and
each rotation is then a gather and a sum over those. That is ~12 s for the whole
collection, in a converter that takes about a minute.

A consequence worth knowing: ``get_geometry`` returns each ring starting at the vertex
the converter chose, which is not the one the upstream GeoJSON began with. The ring is
the same closed path either way.

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

The library uses H3 resolution 4, about 288k hexagons, for its spatial index. That is a measured
choice, not an assumption: ``prototypes/single_resolution_bench.py`` builds a separate index at
every resolution from 0 upwards, prices each one in the layout described below, and benchmarks them
against a common set of globally random query points.

Every level multiplies the cells by seven and the table by eight, so the choice is a trade between
how often a lookup needs geometry at all and how much memory the table costs. Measured on the
packaged dataset:

.. list-table::
   :header-rows: 1

   * - resolution
     - cells
     - answered by one table read
     - index on disk
     - index resident
     - candidates tested per 10k random queries
   * - 3
     - 41,162
     - 74.5 %
     - 103 KiB
     - 143 KiB
     - 3,877
   * - **4**
     - **288,122**
     - **89.1 %**
     - **596 KiB**
     - **1,000 KiB**
     - **1,566**
   * - 5
     - 2,016,842
     - 95.4 %
     - 4,029 KiB
     - 7,832 KiB
     - 667

Resolution 4 removes **60 % of the point-in-polygon tests** a uniformly random workload runs, which
is worth ~40 % of such a query end to end, for ~0.9 MiB of resident table. It also *lowers* the
resident set of the default memory-mapped mode, because far fewer candidate polygons are fetched and
so far fewer coordinate pages are faulted in.

Resolution 5 is refused, and the reason is the exchange rate rather than its gains, which are real.
Memory paid per candidate polygon removed is 0.019 KiB going from resolution 2 to 3, 0.371 KiB from
3 to 4, and **7.600 KiB from 4 to 5** — each level about twenty times worse than the last. The table
is fixed by the resolution rather than by the data, so at resolution 5 it is 99.7 % of the index:
7.8 MiB resident, more than the entire index format generation 1 used, and ``TimezoneFinderL`` —
whose whole footprint is this index — would grow about forty-five fold. Resolutions above 5 are not
worth measuring, since resolution 6's table alone is the size of the polygon data it indexes.

Below resolution 3, cells cover too much area and too many of them come out ambiguous, which pushes
work back onto the expensive point-in-polygon path.

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

``shortcuts.bin`` holds four arrays after a 40-byte header. The header is the file
identifier ``TZSC``, a ``uint32`` layout version, and four ``int64``: the H3 resolution
the index was built for, the number of distinct candidate lists, and the widths chosen
for the two data-dependent columns.

The resolution is in the header because nothing else in the file records it, and it
changes what every slot *means* without changing anything a reader would notice - the
layout is identical at every resolution, so the layout version cannot cover it. A reader
built for another resolution is refused rather than allowed to answer with a different
cell's timezone.

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
*are* the cell and, with ``res`` the resolution the index was built for
(``SHORTCUT_H3_RES``),

.. code-block:: python

    digit_bits = 3 * res
    base = (cell >> 45) & 0x7F
    digits = (cell >> (45 - digit_bits)) & (2**digit_bits - 1)
    slot = base * 2**digit_bits + digits

is a bijection onto a dense table rather than a hash. The base cell sits immediately above
the digits, so the whole slot is one contiguous bit field and the lookup evaluates it as a
single shift and mask - ``(cell >> (45 - digit_bits)) & (2 ** (digit_bits + 7) - 1)``. No
keys are stored and no search runs at lookup time. That h3-py does not promise its index
encoding as API is handled by checking rather than by storing:
``scripts/data_integrity.validate_shortcut_index``
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
slot is exactly the C-order ravel of a ``(122,) + (8,) * res`` array, so the base-7 block
lands correctly when sliced into its corner. The in-memory table keeps its padding: addressing
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

Why the index makes no polygon redundant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Roughly three quarters of the cells resolve to a single zone ID, and a query answered from one of those reads no geometry at all. That invites an optimisation: if some boundary polygon were *only* ever reached through such cells, its coordinates would sit in ``boundaries/coordinates.bin`` serving nothing, and could be dropped — accepting that :meth:`~timezonefinder.TimezoneFinder.get_geometry` could then only report its bounding box.

**No such polygon exists.** Every boundary polygon appears in at least one ambiguous cell, and a large share of them appear in exactly one — which is what makes the idea look plausible in the first place.

This is structural rather than a property of a particular release or resolution. The packaged data covers the globe, so any cell that a polygon's *rim* passes through also holds area outside that polygon; that area belongs to a different zone, unless a polygon of the same zone abuts it there — which dissolved multipolygons do not do. Cell size never enters the argument, so a finer index does not create such polygons either. It only makes the rim cells smaller.

The nearest claim that *is* true concerns testing rather than candidacy: because ``timezone_at`` stops at the last zone change in the candidate list and returns the final zone untested, a polygon can be a candidate everywhere and still never be handed to the point-in-polygon kernel. In release ``2026c`` that describes 206 of the 1,322 boundary polygons, around a sixth of all vertices. Their coordinates are kept regardless, for reasons that are worth stating because the conclusion is easy to reach and wrong:

* **Most of them are hole rings.** 175 of the 206 are the ring some hole is stored as a reference to (see `Holes as Boundary References`_), so their coordinates serve the *surrounding* polygon's hole test, which is very much performed.
* **The remainder are the largest polygons in the dataset.** A zone that is the biggest in every cell listing it is, by construction, a mainland — the 31 survivors are around a sixth of all vertices, and include the main polygons of ``America/Toronto``, ``Europe/Berlin``, ``Europe/Moscow`` and ``Asia/Shanghai``. A bounding box is not a degraded outline of those: it averages well over twice the polygon's own area, so :meth:`~timezonefinder.TimezoneFinder.get_geometry` would answer a rectangle largely covering other countries, in the same return type and without an error. :meth:`~timezonefinder.TimezoneFinder.certain_timezone_at` degrades further still — it tests every candidate with no early break, so with the ring gone it would match nothing and return ``None`` across most of the zone.
* **It would make an API's output depend on the index.** Which polygons qualify follows from which cells happened to come out unique and from how shortcut candidates happened to be sorted. The index is a candidate *filter*, free to be reordered, rebuilt or replaced; deriving ``get_geometry``'s output from its structure would turn a future resolution change into a silent change in what the geometry API returns.

This is the boundary-polygon counterpart of `Holes without a twin`_, and it fails in the same way: covering the query path is not the same question as covering the public API.


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
