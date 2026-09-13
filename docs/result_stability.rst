.. _result_stability:

====================================
Result stability and reproducibility
====================================

:Status: Documents current behaviour. Nothing here is a new feature; the guarantees and the
         non-guarantees both already hold.
:Scope: What makes a lookup return the same answer twice, and what can change it.
:See also: :doc:`0_getting_started` (pinning the data distribution), :doc:`1_usage` (the lookup
           methods themselves), :doc:`architecture` (how the two distributions are released),
           :doc:`why_no_simplification` (why the geometry is exact in the first place).


Summary
=======

A lookup is a **pure function of the coordinates and the installed boundary data**. There is no
sampling, no tolerance, no random tie-breaking and no dependence on call order, caching or
process state. Given the same coordinates and the same installed versions, every call returns the
same answer, on every machine and every supported accelerator.

What that does *not* mean is that the answer is fixed forever. An answer can change when you
install a different version of **the data** and, for the coordinates geometry does not decide by
itself, when you install a different version of **the code**. Applications that need an answer to
stay reproducible across deployments - audit trails, stored records, regression baselines - have to
pin both, not merely stay away from borders.


Within one installation
=======================

Deterministic, for both finder classes and every acceleration path. ``TimezoneFinder`` computes
exact point-in-polygon results over the unsimplified vertices, and ``TimezoneFinderL`` reads a
precomputed answer out of the shortcut index. Neither approximates at query time, so the
C extension, the ``numba`` kernel and the pure-Python fallback all return identical results -
which is what :doc:`benchmark_results_acceleration_paths` compares for speed alone.

The one documented exception is a point lying *exactly* on the edge of a polygon, at
``lat=±90.0``, or at ``lng=±180.0``. Such a point has no guaranteed answer - see the note under
``certain_timezone_at()`` in :doc:`1_usage`. It is still deterministic; it is simply not
guaranteed to be the zone you would expect.


Across data releases
====================

``timezonefinder-data`` ships a new dataset whenever `timezone-boundary-builder`_ publishes one,
independently of code releases. A new dataset can change your answer through **three independent
channels**, and only the first is what "the borders moved" usually brings to mind:

1. **Boundary geometry.** Upstream revises boundaries. This is not bounded by a small distance:
   a re-assigned region, a municipality moved between zones or a zone that is split or renamed
   can change the answer for coordinates far from any previous border.
2. **Polygon precedence.** A point lying exactly on a border shared by two polygons, or inside
   overlapping polygons, is resolved by which candidate the lookup tests first. That is a
   convention rather than a geometric fact, and a rebuild can decide it differently.
3. **Shortcut composition and ordering.** The H3 shortcut index is regenerated for every dataset.
   Which cells exist, which candidates a cell holds and in which order they are tested are all
   outputs of that run - and the rules that run follows are code, so a code-side optimization
   reaches you through this channel too, as the section on code releases below describes.

Channel 3 affects the two finder classes very differently, and the difference is the practical
one:

* ``TimezoneFinder`` **reads the order, but is held invariant by the converter rather than by the
  query.** The lookup returns the first candidate found to contain the point, and
  ``timezone_at()`` goes further: once no zone other than the last remains, it returns that zone
  *without a point-in-polygon test* (see the note on the method). So order does decide the answer
  for two kinds of point - one inside polygons of two different zones, and one inside none of the
  cell's candidates at all.

  What keeps a regenerated index from moving those answers is discipline in the converter.
  ``scripts/shortcut_ordering.py`` may change a cell's final zone, or interleave candidates from
  different zones, only where a conservative geometric gate certifies that the cell is covered and
  that no two zones overlap there with positive area - the two conditions that make both kinds of
  point impossible. Everywhere else it preserves the legacy zone priority and final zone, and
  reorders only *within* one zone's block, where which zone wins depends on the set of candidates
  tested rather than their order.

  The guarantee is therefore exactly as strong as that gate, whose own stated limitations are at
  the top of that module - not a property of the lookup, which would happily return a different
  zone for a differently ordered cell. It is also a guarantee about the **packaged** data, which
  the gate's coverage condition relies on. If you compile your own data and it leaves areas
  uncovered, a point inside none of a cell's candidates is attributed to the last zone untested, so
  the stored order decides it outright; use ``certain_timezone_at()`` there, which tests every
  candidate and returns ``None`` when none matches.
* ``TimezoneFinderL`` **is** its candidate order. In a cell containing several zones it returns
  the last candidate - the zone the full lookup would fall back on after every earlier candidate
  failed its geometry check - without testing any geometry against your point. A regenerated
  index that orders that cell differently therefore changes ``TimezoneFinderL``'s answer for
  *every* point in the cell, even when the boundary geometry is byte-identical, and those points
  need not be anywhere near a border.

So ``TimezoneFinderL`` should be treated as a suggestion that is stable only for a fixed dataset.
It is documented as approximate for a related reason: its answer is not an estimate of which zone
covers your point or most of the cell.


Across code releases
====================

Three things can move an answer here, and the third is the one that surprises people:

1. **Bug fixes** in the lookup.
2. **Documented semantic changes**, which a major release may make.
3. **Optimizations that change the query logic.** Candidate ordering, shortcut resolution and the
   order in which geometry is tested are all fair game for performance work, and changing them
   changes how *ambiguity* is resolved.

All three are described in the :doc:`changelog <6_changelog>`. The third is not hypothetical: 9.0.0
reordered candidate polygons by the work a full lookup needs, which changed what
``TimezoneFinderL`` returns in a multi-zone cell, and moved the shortcut index from H3 resolution 3
to 4, which changed which cells are multi-zone at all.

Note how such a change reaches you. The ordering optimizer and the shortcut builder live in the
code repository (``scripts/``) but their *output* ships in ``timezonefinder-data``, so an
optimization of this kind arrives with a new dataset rather than with a code upgrade alone - which
is why 9.0.0 also raised the required data floor, so that an installation could not pair the new
code with an index built by the old ordering.

**What no optimization can move:** a point strictly inside exactly one polygon. There, the answer
follows from the geometry alone, and no ordering, index or traversal change reaches it. The
exposure is confined to points the geometry does not decide by itself - a point on a shared border
or inside overlapping polygons, and every ``TimezoneFinderL`` answer in a multi-zone cell, which is
a stored ordering decision rather than a geometric one.

Code and data are versioned on separate axes. ``timezonefinder`` requires the data within one
binary *format* generation, so any dataset released for the current format works with any code
release that accepts it; a format change becomes a dependency-resolution error rather than a
failure at the first lookup. :doc:`architecture` describes that split.


Pinning
=======

Pinning is per axis, and the two axes cover different things. Pinning ``timezonefinder-data``
freezes the artefacts: the boundary geometry, and the shortcut index with the candidate order
stored in it. That is the whole of channels 1 and 3, and the stored half of channel 2:

.. code-block:: console

    pip install timezonefinder "timezonefinder-data==<version>"

The `release history <https://pypi.org/project/timezonefinder-data/#history>`__ lists the
available versions.

**Pin the code as well.** A data pin does not freeze the rules that read the data: the
point-in-polygon predicate's behaviour for a point exactly on an edge, and the order in which the
lookup works through a cell's candidates, are code. For the coordinates geometry does not decide by
itself, a code upgrade alone can still move the answer - so pin ``timezonefinder`` too, or accept
that one of the two axes is free.

Record both versions alongside any stored result you may have to reproduce or defend later - the
installed ones are what an answer is reproducible against, and they are not necessarily the ones
this documentation was built from:

.. code-block:: python

    import importlib.metadata as md

    md.version("timezonefinder"), md.version("timezonefinder-data")

A distance to the nearest border is *not* a substitute for pinning. It describes how much
coordinate error the currently installed dataset tolerates at that point, which is a useful thing
to know and a different question: it cannot see channels 2 and 3, and it does not bound how far
channel 1 can move a border.


.. _timezone-boundary-builder: https://github.com/evansiroky/timezone-boundary-builder
