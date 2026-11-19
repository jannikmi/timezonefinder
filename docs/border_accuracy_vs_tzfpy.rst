.. _border_accuracy_vs_tzfpy:

=============================
Border Accuracy against tzfpy
=============================

How often this package and the PyPI build of `tzfpy <https://github.com/ringsaturn/tzfpy>`__, which ships simplified polygons, return different zones at a stated distance from a timezone border. :doc:`alternatives` weighs the two packages against each other, and :doc:`benchmark_results_vs_tzfpy` measures their speed and startup.

.. note::

   **What the simplification costs is not small where it matters.**
   Run both packages over a uniform sample of the globe and they never disagree - which is true and
   says nothing, because a uniformly drawn coordinate is hundreds of kilometres from the nearest
   border. So ``scripts/measure_tzfpy_agreement.py`` (``make tzfpy-agreement``) asks the question at
   a *stated distance from a border* instead. Its primary measure draws border locations uniformly
   by length, verifies a probe on each side, and asks whether either answer differs; the secondary
   measure remains a point drawn uniformly from the full two-sided offset locus. Both sweep from
   this package's own ~1.1 cm coordinate grid outwards.

.. image:: tzfpy_agreement_by_distance.svg
   :alt: At a centimetre from a timezone border, the packages differ on at least one side of about
         nine in ten sampled land-zone border locations. Two thirds are affected at a metre and
         almost half at ten metres, falling to no observed disagreement beyond a hundred metres.
   :width: 100%

.. note::

   Boundary release 2026f on both sides, ``tzfpy`` 2.1.2 (the PyPI build, with simplified
   polygons), 20,000 paired border locations and 20,000 individual points per distance, 2026-11-19.

   **Primary: border locations affected.** A location counts once when either of its two verified
   probes has an attributable disagreement. Its ceiling is 100 %, even when simplification moves a
   boundary in only one direction. ``One side`` and ``both sides`` partition the any-border rate;
   the last column is paired locations this package does not attribute to ``tzfpy``.

   .. list-table::
      :header-rows: 1
      :widths: 20 18 20 16 14 12

      * - Distance from a border
        - Any border location
        - Land-zone border location
        - One side
        - Both sides
        - Not attributed
      * - 1 cm
        - 71.9 %
        - 90.0 %
        - 68.8 %
        - 3.08 %
        - 14
      * - 5 cm
        - 69.1 %
        - 91.2 %
        - 69.1 %
        - 0
        - 0
      * - 10 cm
        - 66.6 %
        - 87.2 %
        - 66.6 %
        - 0
        - 0
      * - 50 cm
        - 53.8 %
        - 71.0 %
        - 53.8 %
        - 0
        - 0
      * - 1 m
        - 52.3 %
        - 68.6 %
        - 52.3 %
        - 0
        - 0
      * - 5 m
        - 43.2 %
        - 56.7 %
        - 43.2 %
        - 0.005 %
        - 0
      * - 10 m
        - 36.4 %
        - 47.8 %
        - 36.4 %
        - 0
        - 0
      * - 50 m
        - 8.70 %
        - 11.5 %
        - 8.70 %
        - 0
        - 0
      * - 100 m
        - 0.27 %
        - 0.36 %
        - 0.27 %
        - 0
        - 0
      * - 500 m
        - 0 observed of 20,000
        - 0 observed
        - 0
        - 0
        - 0
      * - 1 km
        - 0 observed of 20,000
        - 0 observed
        - 0
        - 0
        - 0

   **The near-border effect is now stated on a 0-100 % scale.** At 5 cm the packages differ on at
   least one side of 91.2 % of sampled land-zone border locations; two thirds remain affected at a
   metre and almost half at ten metres. Almost every affected location differs on one side, which
   is the expected signature of a displaced boundary. The 1 cm row is retained for completeness,
   but sits just below this package's stored coordinate step and is not the clean headline: 3.08 %
   differ on both sides and 14 pairs cannot be attributed there; by 5 cm both figures fall to
   zero.

   **The knee is between 10 m and 100 m, and past it the curve stops.** One in nine land-zone
   border locations is still affected at fifty metres and about one in 280 at a hundred. Beyond that,
   across 40,000 paired locations, **not one disagreement is attributable to** ``tzfpy``. That is
   the ~111 m maximum displacement its maintainer states for the simplification, holding as stated.

   Pairing changes the population deliberately. A base site is drawn uniformly by edge length and
   retained only when both normal probes independently verify at the requested nearest-border
   distance. Vertices have zero border length and no unique opposite normal; their circular arcs
   remain represented in the individual-point population below.

   The land-zone curve drops the ocean zones, whose mutual borders are meridians that no simplification
   can move and which therefore dilute the first; a coastline stays in both, since it is stored in the
   land polygon as well as in the ocean polygon around it.

   Two corrections make the numbers attributable rather than merely suggestive. The measurement
   refuses to report unless both packages carry the **same timezone-boundary-builder release**, so a
   difference cannot be a border that moved between datasets; and it asks whether this package's
   answer is among the zones ``tzfpy`` holds over the point rather than whether the two name the same
   one, because the dataset ships genuinely overlapping zones - ``Asia/Urumqi`` inside
   ``Asia/Shanghai`` - that each package resolves by its own rule. Those overlaps are almost every
   difference away from a border and next to none of the ones near it.

   **Secondary: individual-point disagreement.** This is the original probability over the full
   two-sided offset locus. It remains useful for a query chosen without regard to side, but a
   one-direction boundary displacement gives it a natural ceiling near 50 %, so it is no longer the
   headline chart.

   .. list-table::
      :header-rows: 1
      :widths: 25 25 25 25

      * - Distance from a border
        - Any border
        - Border of a land zone
        - Not attributed
      * - 1 cm
        - 36.8 %
        - 46.3 %
        - 10
      * - 5 cm
        - 34.6 %
        - 45.7 %
        - 0
      * - 10 cm
        - 32.6 %
        - 43.0 %
        - 0
      * - 50 cm
        - 26.4 %
        - 34.9 %
        - 0
      * - 1 m
        - 25.3 %
        - 33.5 %
        - 0
      * - 5 m
        - 21.1 %
        - 27.8 %
        - 0
      * - 10 m
        - 17.9 %
        - 23.5 %
        - 0
      * - 50 m
        - 4.2 %
        - 5.6 %
        - 0
      * - 100 m
        - 0.08 %
        - 0.11 %
        - 0
      * - 500 m
        - 0 of 20,000
        - 0 observed
        - 0
      * - 1 km
        - 0 of 20,000
        - 0 observed
        - 0

Reading the last column
~~~~~~~~~~~~~~~~~~~~~~~

**Not every difference belongs to the other package.** Where ``timezone_at`` answers but
:meth:`~timezonefinder.TimezoneFinder.certain_timezone_at` returns ``None``, this package cannot
stand behind the answer without another check. That result proves no *candidate* contains the
quantized point; it does not prove why. A missing shortcut candidate can cause it, but so can a coordinate in a sliver between two neighbouring stored boundaries, where an exhaustive scan finds no containing packaged polygon either. The paired table counts a location here when neither side has
an attributable disagreement and at least one side fails that containment check; the individual
table counts the probes themselves.

The current run leaves 14 paired locations and 10 individual probes in those columns, all at 1 cm -
just below this package's roughly 1.1 cm coordinate grid. For the 10 named individual probes,
exhaustive point-in-polygon checks over all 1,356 packaged polygons find no containing polygon,
while the shortcut already lists the neighbouring zones. They are therefore boundary-grid
ambiguity, not timezonefinder errors and not evidence against ``tzfpy``. The earlier run also
exposed real missing-candidate defects; after the shortcut index was corrected, every one of those
coordinates became an agreement and no unattributed case remains beyond 1 cm.


Every disagreement 100 m or more from a border
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Listed in full rather than sampled, so the figures above can be checked rather than taken on trust.
The 28 KiB ``docs/tzfpy_agreement.json`` also records every count and named sparse case; it is the
measured source for the SVG and lets the chart be regenerated without repeating the external sweep.
Each coordinate was re-queried against both packages afterwards and its distance to the nearest
border re-measured; the ``border`` column is that measurement, not the distance the point was drawn
at. Boundary release 2026f on both sides, ``tzfpy`` 2.1.2.

**Attributable to** ``tzfpy`` — all 16, and all drawn at 100 m. Beyond that there are none::

     border    latitude    longitude   timezonefinder        tzfpy
      100 m   -17.37815   -143.22951   Pacific/Tahiti        Etc/GMT+10
      100 m    65.22034     61.30873   Europe/Moscow         Asia/Yekaterinburg
       99 m     0.64935    -77.54633   America/Guayaquil     America/Bogota
      100 m    -3.89907     55.30436   Indian/Mahe           Etc/GMT-4
      100 m    45.41872     29.49809   Europe/Bucharest      Europe/Kyiv
      100 m    -9.62382    -70.78800   America/Rio_Branco    America/Lima
      100 m   -24.51380   -124.92503   Pacific/Pitcairn      Etc/GMT+8
      100 m   -18.26980    121.70734   Australia/Perth       Etc/GMT-8
      100 m    -3.70243     55.40935   Indian/Mahe           Etc/GMT-4
      100 m    50.60851     48.75227   Asia/Oral             Europe/Saratov
      100 m    28.66919    -95.34234   America/Chicago       Etc/GMT+6
      100 m    12.90717     99.18263   Asia/Bangkok          Asia/Yangon
      100 m     8.98356    114.81054   Asia/Ho_Chi_Minh      Etc/GMT-8
      100 m    19.75981   -154.77873   Pacific/Honolulu      Etc/GMT+10
      100 m    40.43072     50.98266   Asia/Baku             Etc/GMT-3
      100 m    -3.46199   -174.27655   Pacific/Kanton        Etc/GMT+12
