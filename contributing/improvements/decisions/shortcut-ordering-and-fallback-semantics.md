# Shortcut ordering and fallback semantics

## Coverage and the two lookup contracts

The full dataset including ocean timezones may be treated as covering the globe for `timezone_at()`. Uncovered slivers are not a blocker for shortcut ordering, and proving coverage cell by cell is not required to justify its untested final-zone fallback. This is an accepted dataset assumption, not a claim that a geometric overlay proves exact coverage.

Users who want to avoid that fallback use `certain_timezone_at()`, which checks containment and can return `None`. Do not require the main lookup to adopt that contract. The full-coverage assumption is specific to the dataset with oceans; it is not evidence that an arbitrary custom or land-only dataset covers the globe.

## Overlap precedence

Where two zones' polygons overlap, the zone with the smaller spherical area takes precedence, in every cell: it is the enclave, since the shared area is the larger share of it. It is the primary key of `optimise_shortcut_ordering`, computed once per zone by `zone_areas` from the stored rings with holes cut out, and `tests/test_overlapping_zones.py` checks every documented overlap's answer against areas computed from the packaged geometry rather than from the index. Because it compares one scalar per zone it is acyclic, and because it is a property of the zones an index change cannot move an overlap answer. Decided by the maintainer on 2026-10-19 over keeping the per-cell vertex-count key, which made the pick a property of the index that a data update or a change of cells could flip for a whole region without announcement.

- **Refused: applying it only in some cells.** [PERF-7](../items/lookup-geometry-and-data-format/perf-7-answer-a-fully-covered-ambiguous-cell-without-geometry.md) measured one overlap answered two ways by cell.
- **Refused: a maintained per-pair list.** It is the precedence engine the [geometry decisions](geometry-data-format-and-validation-decisions.md) refuse.
- **What would reopen it:** evidence that users rely on the vertex-count winner in a disputed overlap, weighed against the instability above.
- **Superseded, kept for the record:** until 2026-10-19 the primary key was each zone's vertex total *in the cell*, fewest first. Compiled from 2026d and compared with the published `timezonefinder-data` 3.2026.4, switching moved eight overlaps as whole regions — Kafia Kingi and Abyei, the West Bank, the Southern Patagonian Ice Field, the Croatia-Serbia Danube border, the Bay of Piran, a strip of the Strait of Juan de Fuca, and slivers of the Sint Maarten and Nova Scotia-New Brunswick borders — at an unchanged point-in-polygon test count over the benchmark fixtures. The changelog fragment names each pair's old and new answer.

## Overlap ties

When compared spherical zone areas are equal, use the timezone identifier string as the secondary key, in ascending lexicographic order. Use the identifier, not a numeric zone index or iteration order: both depend on how the data happens to be laid out. Equality means equality of the computed area values, with no near-equality tolerance. A polygon's area *clipped to a cell* is not a semantic precedence rule and must not become one. Holes remain excluded from their owning polygons.

## Shortcut-ordering ties

Equal zone areas fall back to the timezone identifier, as above; within one zone, polygons go fewest vertices first and equal polygon vertex counts fall back to the polygon id, which reorders nothing a zone answer depends on. `optimise_shortcut_ordering` implements it. The converter's cross-zone precedence depends on neither set iteration, numeric zone ids nor the spatial index, so the same boundary release always compiles to the same `shortcuts.bin`.

**Why a tie rule can move answers when the work optimizer cannot.** The optimizer's guarantee is relative: it reorders a cell only where `safe_to_reorder` certifies that its candidates are disjoint across zones and cover the cell's envelope, which leaves the full lookup's answers unchanged. Where the gate refuses, an overlap or gap may exist, so the precedence order *is* the definition of the answer there and the optimizer keeps it. A tie rule changes that definition rather than reordering against it. So it can move `timezone_at` only for a point in an overlap or a gap, and `TimezoneFinderL` for a whole cell, because that lookup answers the untested final zone — the optimizer never promised `TimezoneFinderL` anything either, and may pick any final zone where the gate passes.

**Do not drop either secondary key as redundant:** a build that falls back to set order differs only in tied cells and still validates, so only the permutation test in `tests/test_shortcut_ordering.py` notices. **Refused:** determinizing only within a zone, which leaves cross-zone binaries unreproducible and so leaves two candidate indexes incomparable.

## Precedence is independent of the index

- **A correctness property is never expressed in terms of the shortcut index.** Zone precedence — which zone a query should reach first where several cover a point — is a property of the zones and their geometry. Stating it per cell makes correctness depend on the index, whose cells, layout and unique-zone encoding are implementation details the package is free to change, and a later index change then moves answers rather than only performance. The index is a candidate *filter* and may be reordered, rebuilt or replaced freely, which is exactly why nothing load-bearing may be derived from its structure. This forced GH-513's question into the zone-level form that turned out to be cyclic, and it binds any future argument that reaches for the shortcuts to prove something about answers.

## The −180° meridian and the −90° parallel

- **A lookup reads −180° as +180°, and −90° as the point one unit north.** As spelled, no polygon owns a point on either line: a kernel gives a boundary point to the polygon whose interior lies immediately west of it, or south of it along an east-west edge, and nothing lies west of −180° or south of −90°. Read as their other spelling, every point on both lines is owned by a polygon of the packaged data, so one physical point answers one zone whichever spelling it arrives in, `certain_timezone_at` never answers `None` there, and no answer depends on the index. `utils.query2int` holds the rewrite on every path that tests a polygon; a lookup that tests none has to agree, so **an index must wrap −180° to its last column rather than clamp it to the first**, which `tests/test_minus_180_meridian_and_minus_90_parallel.py` fails on.
  - **Why:** the only option under which the answer is a property of the point rather than of the index or of the spelling.
  - **Refused: reading −180° as the point one unit east**, so each spelling answers the side it names. The two sides of the meridian genuinely disagree at most latitudes, so this puts one physical point a day apart by spelling. Evidence that callers send −180° meaning the western edge, expecting the zone east of it, would reopen it.
  - **Refused: keeping the untested fallback on both lines.** It leaves the answer to whichever zone the index happens to list last, which on a measured index owned neither side of the meridian at a few percent of latitudes — the property this decision exists to remove.
  - **Refused: rewriting the float in `validate_coordinates`**, which runs on every query: +51 ns median per scalar call, slower in 25 of 31 alternating rounds, about 3 % of a unique-cell `timezone_at` (C extension, Intel Xeon 2.8 GHz container), for nothing a query testing no polygon needs. Keep the rewrite on the paths that test a polygon. What it costs where it sits is in the [query-path change-classification log](../query-path-change-classification-log.md).
  - **Reversibility:** a few lines in `utils.query2int` plus tests and documentation; another option later costs the same again plus a second user-visible change of the meridian's answers. **Unpriced:** what callers send at exactly −180° or −90°.
