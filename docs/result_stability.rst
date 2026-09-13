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
   convention rather than a geometric fact. A cell like this is one the reordering gate below
   refuses, so the converter keeps its inherited zone precedence - but that precedence orders zones
   by their total vertex count in the cell, so a dataset that adds, drops or reshapes a polygon can
   reorder them and decide such a point differently.
3. **Shortcut composition and ordering.** The H3 shortcut index is regenerated for every dataset.
   Which cells exist, which candidates a cell holds and in which order they are tested are all
   outputs of that run - and the rules that run follows are code, so a code-side optimization
   reaches you through this channel too, as the section on code releases below describes.

Channel 3 affects the two finder classes very differently, and the difference is the practical
one:

* ``TimezoneFinder`` **reads the order but does not depend on it**, for the reasons set out in the
  next section. The dependence is real - the lookup returns the first candidate found to contain
  the point, and ``timezone_at()`` returns the last remaining zone *without a point-in-polygon
  test* at all (see the note on the method) - so what holds the answer still is the converter's
  discipline in what it is willing to reorder, not anything in the query.
* ``TimezoneFinderL`` **is** its candidate order. In a cell containing several zones it returns
  the last candidate - the zone the full lookup would fall back on after every earlier candidate
  failed its geometry check - without testing any geometry against your point. A regenerated
  index that orders that cell differently therefore changes ``TimezoneFinderL``'s answer for
  *every* point in the cell, even when the boundary geometry is byte-identical, and those points
  need not be anywhere near a border.

So ``TimezoneFinderL`` should be treated as a suggestion that is stable only for a fixed dataset.
It is documented as approximate for a related reason: its answer is not an estimate of which zone
covers your point or most of the cell.


Why reordering leaves a ``TimezoneFinder`` answer alone
-------------------------------------------------------

Two different reorderings are permitted, resting on two different arguments. They are worth keeping
apart, because one is a proof about structure and the other is a geometric certification that can
in principle be wrong.

**Within one zone's block: structural, and exact.** This is the only reordering permitted when the
gate below refuses. ``CellOptimizer`` then swaps an adjacent pair only where both candidates carry
the same zone, runs its greedy pass per zone group, concatenates the groups in their original
order, and appends the final zone's group untouched. The *sequence of zones* and the final zone
therefore survive byte for byte; only polygons within one zone's block move.

No geometry is needed to see that the answer cannot change. The lookup returns the zone of the
first candidate containing the point, and any polygon of a zone yields that same zone, so which
polygon of the winning zone matched is irrelevant. The stopping index is the start of the final
block, which is unchanged because block order and sizes are. A point inside no candidate still
reaches the same untested final zone.

**Across zones: geometric, and conditional.** Changing the final zone or interleaving zones breaks
the argument above, so it is permitted only where ``safe_to_reorder`` establishes, for an envelope
enclosing the cell, that

1. no two candidates of *different* zones intersect with positive area, and
2. the candidates jointly **cover** the envelope.

Given both, every point in the cell lies inside a candidate, and inside candidates of at most one
zone. The answer is then "the zone whose polygon contains this point" - a function of the geometry
alone, and so the same under any permutation. Coverage is also exactly what makes the untested
final zone sound: a point that reaches it is inside none of the earlier zones' polygons, so
coverage forces it inside one of the final zone's.

This half is only as strong as that certification, and it is worth knowing what it assumes. The
envelope is derived from the H3 cell's spherical cap and padded by one integer coordinate unit,
with cells at the poles or across the antimeridian refused outright; the cap radius is the largest
centre-to-vertex distance plus one percent, which bounds the cell because distance to a fixed point
along a great-circle arc is largest at an endpoint - an argument, not a machine-checked proof. The
containment tests themselves are planar operations in the quantized coordinate frame standing in
for a spherical cell. Everything unproven fails closed: invalid or repaired geometry is rejected,
and any geometry error refuses the cell.

**Both arguments are asserted by tests, not only argued here.**
``tests/test_ordering_answer_invariance.py`` drives the real lookup over the committed
ambiguous-cell points: a within-zone shuffle cannot move an answer, a point contained by a single
zone's candidates survives any permutation, and - so that neither of those asserts nothing - a
cross-zone rotation does move answers. It also pins ``TimezoneFinderL`` to the final candidate's
zone. ``tests/test_shortcut_ordering.py`` covers the converter side: the restricted mode's answer
over every hit pattern, the gate's overlap and coverage refusals, and its refusal of pole and
antimeridian cells before any geometry is read.

What no test establishes is the certification itself - that a positive verdict really implies
coverage and disjointness for every point H3 assigns to the cell, which is where the cap-radius
argument above carries the weight.

Both arguments are about the **packaged** data, whose ocean zones cover the globe. If you compile
your own data and it leaves areas uncovered, a point inside none of a cell's candidates is
attributed to the last zone untested, so the stored order decides it outright. Use
``certain_timezone_at()`` there, which tests every candidate and returns ``None`` when none matches.


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
