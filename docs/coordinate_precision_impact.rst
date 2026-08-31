===========================
Coordinate precision impact
===========================

The source's six decimal places are load-bearing at timezone borders.

timezone-boundary-builder publishes six decimal places (~11 cm at the equator).
The packaged int32 representation keeps one redundant decimal so those source
values survive conversion. This study asks the first genuinely lossy question:
what happens at 5 decimal places, using
round-to-nearest so the coarser candidate gets its smallest possible displacement?

Method
======

Boundary release ``2026c`` is used on both sides. The
packaged polygon and hole rings are rounded without removing vertices, then every
binary is regenerated and the H3 shortcut index is rebuilt from that geometry.
Comparing against the old shortcut index would be invalid because its candidate
lists describe the source geometry.

The border population samples locations uniformly by stored border length and
verifies probes at the stated nearest-border distance on both sides. A location is
affected when either probe changes answer. Ocean-only meridians are reported in the
global column but excluded from the land-zone column. The zero rows are finite-sample
bounds, not claims that the true rate is zero.

.. list-table:: Paired border locations affected by five-decimal coordinates
   :header-rows: 1
   :widths: 14 18 20 18 20

   * - Distance
     - Any-border locations
     - Affected
     - Land-border locations
     - Affected
   * - 10 cm
     - 10,000
     - 4,876 (48.8%)
     - 7,597
     - 4,873 (64.1%)
   * - 50 cm
     - 10,000
     - 231 (2.3%)
     - 7,548
     - 231 (3.1%)
   * - 1 m
     - 10,000
     - 0 (95% bound <0.030%)
     - 7,735
     - 0 (95% bound <0.039%)
   * - 5 m
     - 10,000
     - 0 (95% bound <0.030%)
     - 7,659
     - 0 (95% bound <0.039%)

Workload-shaped checks
======================

The same rebuilt data is compared over an area-uniform globe sample and every
committed benchmark point class. These are deliberately reported beside, not in
place of, the border sample: ordinary coordinates are almost never close enough to
a boundary to reveal a sub-metre displacement.

.. list-table:: Answers changed outside the targeted border population
   :header-rows: 1
   :widths: 45 20 35

   * - Population
     - Queries
     - Changed answers
   * - Area-uniform globe
     - 200,000
     - 0 (95% bound <0.002%)
   * - ``random_points``
     - 10,000
     - 0 (95% bound <0.030%)
   * - ``on_land_points``
     - 10,000
     - 0 (95% bound <0.030%)
   * - ``unique_shortcut_points``
     - 5,000
     - 0 (95% bound <0.060%)
   * - ``ambiguous_shortcut_points``
     - 5,000
     - 0 (95% bound <0.060%)

Decision
========

The six-decimal source geometry remains the accuracy floor. Reducing coordinate
precision changes real lookup answers even under nearest rounding, while preserving
it is lossless by construction. A format may omit the package's redundant seventh
decimal, but it must not quantize below the source's six decimals.

This is a measurement and recommendation, not a data-format change. The packaged
runtime data remains untouched.

:download:`Machine-readable run <coordinate_precision_impact.json>`
