# GEOM-1 — audit and conservatively fix shortcut candidate generation

## Finding to establish

`scripts/hex_utils.py::Hex.lies_in_cell` decides which boundary polygons reach each H3 shortcut cell. Its vertex and edge tests treat the coordinates from `h3.cell_to_boundary` as a planar ring joined by straight longitude/latitude segments. H3 assigns queries through `latlng_to_cell` using its spherical/icosahedral cell geometry; valid cell points can lie outside that planar ring where an edge bows between reported vertices. The [cell-local geometry witnesses](../../decisions/cell-local-geometry-correctness-and-format.md#two-independent-failures-of-naive-clipping) demonstrate that mismatch, but they do not yet demonstrate a shipped lookup answer whose required candidate is absent. This is therefore a suspected correctness defect and an audit until a production counterexample is reproduced.

The risk is one-sided. A false positive only retains an extra candidate for the point-in-polygon loop. A false negative removes the only later check that could recover the polygon, so a real query can return another zone or no zone without an error. The current checks do not establish the exclusion they are used for: a polygon edge can enter the real H3 cell while no polygon vertex maps to it, no reported cell vertex lies in the polygon, and no polygon edge crosses the planar chord ring.

## Work

- Audit every exclusion in `Hex.is_poly_candidate`, `Hex.lies_in_cell`, `Hex.poly_candidates`, and the recursive `Hex.true_parents` propagation. State the invariant each exclusion proves about all coordinates for which `h3.latlng_to_cell(..., SHORTCUT_H3_RES)` returns the cell; uncertainty must retain the polygon.
- Reproduce or rule out a missing-candidate lookup on the packaged dataset. Start with the recorded curved-edge witness construction, then test polygon-edge/cell-edge crossings, face crossings, pentagons, poles, and the antimeridian. A fixture-only disagreement is evidence about the construction, not proof that a packaged candidate is missing.
- Evaluate H3's own region APIs before maintaining another cell model. Released H3 4.x exposes experimental `full`, `overlap`, and `bbox_overlap` modes, but their current implementation is planar. The still-open upstream [geodesic coverage change](https://github.com/uber/h3/pull/1052) adds distinct great-circle containment and intersection paths; test it in isolation rather than treating the released mode names as a correctness guarantee.
- Replace each unsafe exclusion with a conservative predicate: definitely disjoint may be removed, while uncertain overlap stays a candidate. A certified enclosure of the real H3 cell or an H3-owned geodesic overlap predicate are viable directions. Sampling, subdivision depth, or an empirical padding without an outward error bound cannot justify exclusion.
- Regenerate the shortcut index through its owner and compare candidate sets, compiled bytes, lookup answers, converter cost, and query cost. Add regression witnesses for every repaired exclusion and exercise the pure-Python and accelerated point-in-polygon paths where the resulting candidate order can reach both.

## Relationship to PERF-7

PERF-7 replaces an ambiguous candidate list with a zone id when one polygon appears to cover the cell. That requires the stronger, opposite proof: every real H3-cell point is covered. It stays blocked until this audit establishes a shared cell-geometry authority that can conservatively prove both overlap and full containment; reusing the same planar ring in `covers_cell` does not do so.

- **Size:** M for the audit and a conservative converter fix; larger if correctness requires adopting or implementing geodesic H3/polygon intersection.
- **Status:** open — the geometric mismatch is reproduced, the production missing-candidate consequence is not yet confirmed, and all required anchors and adversarial witnesses are available locally.
