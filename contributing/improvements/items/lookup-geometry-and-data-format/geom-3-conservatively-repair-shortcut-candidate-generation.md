# GEOM-3 — certify the shortcut candidate rule

## What this item is

**Certify the candidate rule in `scripts/grid_cells.py`.** The rule is *tight*: a cell is an axis-aligned rectangle of the very integer coordinates the kernel reads, so "can this polygon own one of the cell's points" is a planar predicate over two rectangles and a ring, evaluated against the kernel's own edge convention, computed per level from the polygons directly with no propagation step. **It is not exact, and the difference is the thing to state precisely**: what it tests is whether the polygon's *interior* meets the cell's half-open region, which is a superset of "owns one of the cell's integer points". A polygon whose interior enters the cell without reaching a lattice point is admitted and owns nothing — 250 of 4,000 randomised small-polygon/small-cell pairs, against **zero** omissions in the same sweep. Over-inclusion costs a bounding-box rejection; an omission would be a wrong answer, and no sweep has produced one.

**So this is a certification question, not a repair.** Three things the "no omission" half rests on, none of them proved:

- **Shapely's predicates.** `intersects` and `touches` over a prepared polygon and a box decide every exclusion. They are GEOS, not a proof, and a GEOS bug would be a silent omission. What stands against that: `update_data.sh` runs three untruncated audit streams on every compiled dataset, the default one probing every stored cell's four corners and four edge midpoints, and `tests/grid_cells_test.py` holds the rule to the kernel over randomised polygons on every commit.
- **The half-unit shift.** A polygon that only *touches* the cell's box shifted half a unit south-west owns none of the cell's integer points. That follows from the kernel giving a boundary point to the polygon whose interior lies west or south of it, which `tests/test_point_in_polygon_boundary_convention.py` pins — but the implication from "touches the shifted box" to "owns no integer point of the cell" is an argument, not a machine-checked step. `tests/grid_cells_test.py` holds the rule to the kernel over randomised small polygons and names the two mutations that pass without it.
- **Invalid source rings.** A ring that is not a valid planar polygon falls back to its own bounding box, which can only over-include. The packaged boundaries have no such ring; custom input may, and the converter prints the ids when it happens.

## Reopening condition

Parked. Reopen for a reproducible missing-candidate counterexample, or for a proposed optimization that needs *full-cell coverage* — the opposite claim, that every point a cell is asked about is covered by one of its candidates, which the withdrawn PERF-7 needed and which the exactness above does not supply. Retaining uncertain candidates never establishes coverage; neither does an exact rule, which establishes only that nothing was wrongly dropped.

## Work if reopened

Use `scripts/audit_shortcut_candidates.py` to establish witnesses and to compare any change. The [audit and geometry-authority record](../../decisions/shortcut-candidate-audit-and-geometry-authority.md) holds what the audit does and does not establish, and why no upstream spherical-coverage API is an authority for planar source geometry. Preserve source geometry and holes. A certification requiring a new dependency remains subject to the improvement-pass dependency boundary.

- **Size:** M — a certification argument and its witnesses.
- **Status:** parked — the rule is tight rather than conservative since format 4, and omission-free in every sweep run against it; reopen for a counterexample or for an optimization needing certified full-cell coverage.
