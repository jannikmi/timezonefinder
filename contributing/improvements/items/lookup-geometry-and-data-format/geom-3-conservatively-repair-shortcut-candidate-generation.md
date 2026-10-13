# GEOM-3 — certify the shortcut candidate rule

## What changed, and what is left

**Re-scoped 2026-10-13, when the grid tree replaced the H3 index.** This entry used to be a *repair*: the hexagon candidate rule excluded polygons on evidence that could not establish disjointness — vertex-derived cell bounds against great-circle edges, planar overlap tests on a chord ring standing in for a spherical cell, hole containment proved as a planar-ring relation, and candidates propagated recursively through up to two "true parents". Every one of those sites is gone with the hexagons. The rule in `scripts/grid_cells.py` is *exact* instead: a cell is an axis-aligned rectangle of the very integer coordinates the kernel reads, so "can this polygon own one of the cell's points" is a planar predicate over two rectangles and a ring, evaluated against the kernel's own edge convention. There is no over- or under-approximation left to repair, and no propagation step at all — each level is computed from the polygons directly.

**So what remains is a certification question rather than a repair, and it is a smaller one.** Three things the exactness rests on, none of them proved here:

- **Shapely's predicates.** `intersects` and `touches` over a prepared polygon and a box decide every exclusion. They are GEOS, not a proof, and a GEOS bug would be a silent omission. What stands against that: `update_data.sh` runs three untruncated audit streams on every compiled dataset, the default one probing all four corner integer points of every stored cell, and `prototypes/latlng_index_bench.py`'s gate matched an H3 control on 30,000 fixture points plus edge probes when the rule was chosen.
- **The half-unit shift.** A polygon that only *touches* the cell's box shifted half a unit south-west owns none of the cell's integer points. That follows from the kernel giving a boundary point to the polygon whose interior lies west or south of it, which `tests/test_point_in_polygon_boundary_convention.py` pins — but the implication from "touches the shifted box" to "owns no integer point of the cell" is an argument, not a machine-checked step.
- **Invalid source rings.** A ring that is not a valid planar polygon falls back to its own bounding box, which can only over-include. The packaged boundaries have no such ring; custom input may, and the converter prints the ids when it happens.

## Reopening condition

Parked. Reopen for a reproducible missing-candidate counterexample, or for a proposed optimization that needs *full-cell coverage* — the opposite claim, that every point a cell is asked about is covered by one of its candidates, which the withdrawn PERF-7 needed and which the exactness above does not supply. Retaining uncertain candidates never establishes coverage; neither does an exact rule, which establishes only that nothing was wrongly dropped.

## Work if reopened

Use `scripts/audit_shortcut_candidates.py` to establish witnesses and to compare any change. The [audit and geometry-authority record](../../decisions/shortcut-candidate-audit-and-geometry-authority.md) holds what the audit does and does not establish, and why no H3 coverage mode — released or geodesic — is an authority for planar source geometry. Preserve source geometry and holes. A certification requiring a new dependency remains subject to the improvement-pass dependency boundary.

- **Size:** M — a certification argument and its witnesses, against the L-sized numerical enclosure the hexagon repair would have needed.
- **Status:** parked — the rule is exact rather than conservative since format 4; reopen for a counterexample or for an optimization needing certified full-cell coverage.
