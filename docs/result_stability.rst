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
**install a different version of the data**, and, much more rarely, when you install a different
version of the code. Applications that need an answer to stay reproducible across deployments —
audit trails, stored records, regression baselines — have to pin, not merely to stay away from
borders.


Within one installation
=======================

Deterministic, for both finder classes and every acceleration path. ``TimezoneFinder`` computes
exact point-in-polygon results over the unsimplified vertices, and ``TimezoneFinderL`` reads a
precomputed answer out of the shortcut index. Neither approximates at query time, so the
C extension, the ``numba`` kernel and the pure-Python fallback all return identical results —
which is what :doc:`benchmark_results_acceleration_paths` compares for speed alone.

The one documented exception is a point lying *exactly* on the edge of a polygon, at
``lat=±90.0``, or at ``lng=±180.0``. Such a point has no guaranteed answer — see the note under
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
   outputs of that run.

Channel 3 affects the two finder classes very differently, and the difference is the practical
one:

* ``TimezoneFinder`` is **unaffected by candidate reordering, by construction.** The converter's
  ordering optimization may only change a cell's final zone, or interleave candidates from
  different zones, after a conservative geometric gate certifies that the cell is covered and that
  no two zones overlap with positive area there. Where the gate does not certify this, the
  optimization is confined to reordering candidates *within* one zone's block, and which zone
  wins depends only on the set of candidates tested, not on their order. The reasoning and its
  stated limitations are documented at the top of ``scripts/shortcut_ordering.py``; the residual
  is channel 2, which any polygon precedence has.
* ``TimezoneFinderL`` **is** its candidate order. In a cell containing several zones it returns
  the last candidate — the zone the full lookup would fall back on after every earlier candidate
  failed its geometry check — without testing any geometry against your point. A regenerated
  index that orders that cell differently therefore changes ``TimezoneFinderL``'s answer for
  *every* point in the cell, even when the boundary geometry is byte-identical, and those points
  need not be anywhere near a border.

So ``TimezoneFinderL`` should be treated as a suggestion that is stable only for a fixed dataset.
It is documented as approximate for a related reason: its answer is not an estimate of which zone
covers your point or most of the cell.


Across code releases
====================

Lookup results are determined by the data, so an ordinary code release does not move them. They
can change when a release **fixes a bug** in the lookup, and a major release can change documented
semantics; both are described in the :doc:`changelog <6_changelog>`. Nothing in the query path
approximates, so there is no third category of drift — no retuned threshold or heuristic that
would shift answers as a side effect of performance work.

Code and data are versioned on separate axes. ``timezonefinder`` requires the data within one
binary *format* generation, so any dataset released for the current format works with any code
release that accepts it; a format change becomes a dependency-resolution error rather than a
failure at the first lookup. :doc:`architecture` describes that split.


Pinning
=======

Pinning the data distribution freezes all three channels at once, because it freezes the artefact
they are all outputs of:

.. code-block:: console

    pip install timezonefinder "timezonefinder-data==<version>"

The `release history <https://pypi.org/project/timezonefinder-data/#history>`__ lists the
available versions. Pin ``timezonefinder`` as well to hold the code axis. Record both versions
alongside any stored result you may have to reproduce or defend later - the installed ones are
what an answer is reproducible against, and they are not necessarily the ones this documentation
was built from:

.. code-block:: python

    import importlib.metadata as md

    md.version("timezonefinder"), md.version("timezonefinder-data")

A distance to the nearest border is *not* a substitute for pinning. It describes how much
coordinate error the currently installed dataset tolerates at that point, which is a useful thing
to know and a different question: it cannot see channels 2 and 3, and it does not bound how far
channel 1 can move a border.


.. _timezone-boundary-builder: https://github.com/evansiroky/timezone-boundary-builder
