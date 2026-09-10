# GEOM-3 — conservatively repair shortcut candidate generation

## Reopening condition

Parked at the maintainer's request on 2026-09-10 after 21,561,744 adversarial probes found no packaged candidate omissions. `update_data.sh` now guards newly compiled datasets once, before release preparation; fast pytest tests verify pipeline ordering and refusal. Reopen for a reproducible missing-candidate counterexample or a proposed optimization that needs certified cell coverage. The current exclusion proof gaps remain; these sampled guards can miss an unsampled defect, and their passing does not unblock PERF-7. A speculative L-sized repair with storage/query costs is not justified by the present evidence.

## Work if reopened

Replace unsafe exclusions in `scripts/hex_utils.py`: vertex-derived cell bounds, planar exterior overlap and hole containment, and recursive candidate propagation through `Hex.true_parents`. Every exclusion must prove disjointness for all coordinates assigned by `h3.latlng_to_cell`; uncertainty retains the polygon. Do not treat sampled agreement, fixed subdivision depth or empirical padding as that proof.

Use `scripts/audit_shortcut_candidates.py` to establish production witnesses and compare the repair. The [audit and geometry-authority record](../../decisions/shortcut-candidate-audit-and-geometry-authority.md) evaluates released H3 region APIs and the isolated replacement geodesic branch, with a source-semantics counterexample. Released planar modes are not a correctness authority for spherical cells. Upstream geodesic modes change source edges into great-circle arcs too, whereas the package's source segments are planar in longitude/latitude; adopting them directly changes the question. Preserve source geometry and holes.

Deliver the enclosure/propagation proof and regression witnesses together with regenerated shortcuts. Compare candidate sets, compiled bytes, lookup answers, converter cost and query cost on both pure-Python and accelerated paths. The cost side is increased candidate storage and lookup work; preserve mapped mode and existing API semantics. A repair requiring a new dependency remains subject to the improvement-pass dependency boundary.

PERF-7 stays blocked: replacing a whole cell with an unconditional zone requires the opposite proof, that every assigned point is covered. Merely retaining uncertain exterior candidates does not establish it.

- **Size:** L — numerical enclosure, propagation and regeneration form one correctness boundary.
- **Status:** parked — one-time validation guards future datasets; reopen for a counterexample or a proposed optimization requiring certified cell coverage.
