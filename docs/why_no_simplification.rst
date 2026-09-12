.. _why_no_simplification:

==============================================
Why timezonefinder doesn't simplify polygons
==============================================

:Status: Settled. A proposal that gives up unsimplified geometry is out of scope; the conditions
         that would reopen the question are listed at the end.
:Scope: The boundary geometry shipped in ``timezonefinder-data`` and every lookup that reads it.
:See also: :doc:`architecture` (what was deliberately not built), :doc:`data_format` (the two
           coordinate grids), :doc:`alternatives` (the measured cost of simplification).


Summary
=======

``timezonefinder`` stores every vertex of every boundary polygon and hole exactly as
`timezone-boundary-builder`_ publishes it, and never runs a simplification pass over them.

Simplification is the obvious way to make a geometric lookup smaller and faster, and it is
proposed regularly. This page explains why the answer stays no. It does not claim simplification
is wrong in general. It claims three narrower things:

1. **Simplification removes accuracy exactly where a timezone lookup can be wrong.** A tolerance
   of *ε* is not a small error spread over all queries. It is a large error applied to the queries
   within *ε* of a border, and those are the only queries whose answer is in doubt at all.
2. **The benefits it would buy are already mostly bought by other means**, all of them lossless:
   the H3 shortcut index, the latitude block index, bit-packed coordinate frames and memory mapping.
3. **The remaining gap is a price some users should pay, and a well-maintained package already
   offers that trade.** Offering both trades in one package would weaken the guarantee this one
   exists to provide.


Context: where a lookup can be wrong
====================================

A coordinate far from every border has one possible answer, and any representation of the
boundaries returns it. This is why "we tested it on random points and it agrees" says nothing.
A uniformly drawn coordinate is usually hundreds of kilometres from the nearest border.
:doc:`alternatives` found that a uniform global sample produces no disagreement at all between
this package and a simplified one.

All of the uncertainty sits in a thin band along the borders. Accuracy there is the product.
Speed away from the borders is close to a solved problem: most H3 cells are covered by a single
zone, and the shortcut index answers those without touching geometry.

Border queries are also more common than their share of the Earth's surface suggests. Borders often
run along rivers with a town on each bank, cut through built-up areas, and cross transport corridors
where GPS traces are recorded. The package cannot know a caller's query distribution. It can only
decide how wrong it is willing to be when a query lands near a border.


What simplification costs
=========================

The error is concentrated, not averaged
---------------------------------------

Douglas-Peucker, Visvalingam-Whyatt and their variants all guarantee a bound: no removed vertex lies
more than *ε* from the simplified line. That bound is a promise about the *geometry*. For a lookup
it means something else: **every point within ε of a border may be assigned to the wrong side.**

The expected error over all queries can look negligible while the error for border queries is
close to a coin flip. Both descriptions are accurate. Only the second describes the queries where
the library's answer matters.

This is measured rather than argued. ``scripts/measure_tzfpy_agreement.py`` compares this package
with ``tzfpy``, which ships simplified polygons, at fixed distances from a border. Both packages use
the same upstream release. Near a border they differ on at least one side of most sampled land-zone
border locations. About half are still affected at ten metres. Disagreement stops at about a hundred
metres, which matches the maximum displacement ``tzfpy``'s maintainer states for its
simplification. :doc:`alternatives` has the current table, the chart and every individual case.

The *ε* that makes simplification worthwhile is orders of magnitude larger than the error that
remains without it. The source publishes coordinates on a ~11 cm grid, and queries are resolved on
a ~1.1 cm grid. Adding a tolerance measured in tens of metres trades a centimetre-scale ceiling for
a metre-scale one.

Simplifying polygons independently breaks shared borders
--------------------------------------------------------

A timezone border belongs to two polygons, and upstream emits it in both. Simplifying each polygon
on its own keeps different vertices on each side. The two copies of the border then stop
coinciding:

* **Gaps** appear where both simplified edges pull away from the true line. A point in a gap belongs
  to no zone, so ``certain_timezone_at()`` returns ``None`` for a location the source assigns.
* **Overlaps** appear where both edges bulge across it. A point in an overlap belongs to both zones,
  and the answer depends on candidate order instead of on the data.

Topology-preserving simplification, which simplifies each shared arc once, removes gaps and
overlaps. It still moves the border itself by up to *ε*, so it does not remove the cost described
above. It also requires an arc-topology build step and a store for shared arcs. Upstream does not
provide either.

It would also break the exact-equality invariants the format relies on
-----------------------------------------------------------------------

Several layout decisions assume the packaged geometry is the published geometry, vertex for vertex:

* **Holes are stored as references to boundary polygons.** An enclave's hole and the enclosed zone's
  boundary are the same ring, and the converter matches them by comparing integer coordinates, with
  no tolerance (see :doc:`data_format`, *Holes as Boundary References*). Simplifying the two rings
  separately would make them differ. The deduplication would disappear, and the two rings would
  disagree about the enclave's edge.
* **The data-update guard reviews a release by the answers it changes.** A simplification pass
  would change answers for reasons that have nothing to do with upstream edits, and would hide real
  border moves among them.
* **The converter refuses to round away information.** It rejects a seventh decimal instead of
  rounding it. Snapping vertices onto the source's own grid moved the packaged boundary *toward* the
  published one and removed a truncation error. That change is the opposite of simplification and
  must not be cited as a precedent for it.


What simplification would buy, and how the package gets it anyway
=================================================================

.. list-table::
   :header-rows: 1
   :widths: 18 40 42

   * - Benefit
     - What simplification offers
     - What is done instead, losslessly
   * - Lookup speed
     - Fewer edges per point-in-polygon test.
     - The **H3 shortcut** answers most queries without any geometry. The **latitude block index**
       skips every block of 128 vertices that cannot cross the query's latitude, so the cost of a
       ray cast grows only slightly with polygon size (:doc:`benchmark_results_polygon`).
   * - Memory
     - Fewer vertices held in memory.
     - Coordinates are **memory-mapped** by default, so resident memory is single-digit MiB and only
       the pages a lookup reads are loaded (:doc:`benchmark_results_memory`).
   * - Download and install size
     - Fewer vertices to ship.
     - **Bit-packed residuals against per-block coordinate frames**, stored at the source's
       resolution, remove the bytes that carried no information. A separate data distribution means
       a data update does not require a code release. Install-time decompression was measured and
       rejected. It saves little beyond the lossless encoding and needs an unpack step.
   * - Build and startup
     - Smaller files to read.
     - ``TimezoneFinderL`` answers from the shortcut index alone. It is the explicit
       low-accuracy option inside this package, and it never loads polygons.

The remaining difference is real. ``tzfpy`` is faster per lookup by a single-digit factor, and its
wheel is several times smaller (:doc:`benchmark_results_comparison`). That gap is the price of border
accuracy, and this page accepts it on purpose.


Options considered
==================

**Global Douglas-Peucker or Visvalingam at a fixed tolerance.** Rejected. It concentrates error at
borders, opens gaps and overlaps between neighbouring zones, and breaks hole deduplication.

**Topology-preserving arc simplification.** Rejected. It fixes gaps and overlaps but still moves
every border by up to *ε*. The border-accuracy argument applies unchanged, and it adds a build step
the package would own alone.

**Adaptive tolerance, fine near populated areas and coarse elsewhere.** Rejected. The package would
be deciding which borders matter, which is a judgement it has no basis for. Answers would also depend
on a curated input, the same liability that caused hand-maintained zone mappings and a zone-precedence
engine to be refused.

**Ship a simplified dataset as a second, opt-in distribution.** Not pursued. It adds a second
release axis and a second accuracy contract to maintain. It also duplicates a trade that ``tzfpy``
already offers well. ``TimezoneFinderL`` already covers the low-accuracy end inside this package
without simplifying anything: it skips the geometry instead.

**Cell-local geometry, storing only the parts of each polygon inside an ambiguous cell.** Studied,
not adopted. Naive clipping and rounded cut vertices changed containment on the real dataset.
Exact clipping with shared coordinate runs was lossless, but no measured query benefit justified its
size. See the cell-local findings in the contributor documentation. It is listed here because it is
the only size and speed idea that took border accuracy as a hard constraint, which is the kind of
proposal this page invites.

**Keep the full geometry and make it cheap. (Chosen.)**


Consequences
============

* Wheels are tens of megabytes, almost all of it boundary data (:doc:`data_report`).
* An ambiguous-cell lookup does a real point-in-polygon test against full-resolution rings. The
  block index keeps this affordable; it does not make it free.
* Border accuracy is limited by the source, not by this package. That is a claim about fidelity,
  not about ground truth. `timezone-boundary-builder`_ derives its boundaries from OpenStreetMap, and
  where OSM is wrong, this package is wrong in the same way.
* Every speed or size proposal must be lossless or be refused before it is measured. The contributor
  trade-off rules call such an option *dead on arrival regardless of how well it measures*.


When to revisit
===============

The following would reopen this decision. A faster benchmark would not.

* **Upstream publishes simplified boundaries itself.** The package then mirrors the source, and the
  fidelity argument holds without changes. The data-update size guard is symmetric so that such a
  release is reviewed rather than published automatically.
* **A lossless representation needs less size or latency than the current one.** This does not
  reopen simplification. It is the route this page asks proposals to take.
* **Evidence that users of this package, not users in general, would accept a stated border error
  in exchange for a stated gain.** Until then, the recommendation in :doc:`alternatives` stands:
  if an occasional wrong answer within a hundred metres of a border costs you nothing, use ``tzfpy``.


.. _timezone-boundary-builder: https://github.com/evansiroky/timezone-boundary-builder
