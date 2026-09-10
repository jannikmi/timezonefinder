# Shortcut candidate audits and geometry authority

## What the audit establishes

`scripts/audit_shortcut_candidates.py` compares the candidates exposed by the packaged shortcut index with independent full-polygon containment, including holes. It uses actual `latlng_to_cell` assignment, then integer query coordinates and the runtime polygon kernel. It does not use the converter's cell bounds or planar cell ring as its oracle. A unique-zone entry exposes every polygon of that zone; the compiled format no longer reveals which individual polygons the converter originally retained there.

Run each deterministic stream with `uv run python -m scripts.audit_shortcut_candidates --mode MODE --output tmp/audit.json`: `cell-edges` enumerates all shortcut-resolution cells, including pentagons and face-crossing boundary vertices; `source-edges` enumerates stored boundary/hole vertices and planar midpoints; `seams` checks both poles and antimeridian representations. Source probes preserve the integer coordinate reached by runtime truncation. `--points` accepts a JSON array of longitude/latitude pairs for replay. `--max-points` bounds exploratory runs and records whether the stream was exhausted. Exit 1 means at least one omission; empty input fails instead of reporting success.

Reports retain data hashes, H3 and Python versions, backend, counts and bounded witnesses. A missing polygon is not necessarily a wrong zone: overlapping polygons may supply the same answer. The report separately counts omissions whose answer belongs to none of the directly containing polygons. It makes no precedence claim when multiple zones contain a point. This is not an independent test of the polygon kernel, and zero sampled omissions is never a completeness certificate.

At the maintainer's request, `tests/test_shortcut_candidate_coverage.py` runs all three untruncated streams against the dataset under test in pytest's `slow` suite. The existing required CI tox environment selects that suite, so an omission fails a data-update build before its automatic merge/release. Diagnostics retain coordinates and missing IDs for replay; a mutation test verifies that removing a shortcut fails the same guard. `tests/test_data_update_workflow.py::test_ci_selects_the_candidate_coverage_release_guards` checks both the CI matrix and actual pytest collection under tox's marker expression. The CLI remains an optional diagnostic; CI invokes the shared oracle through pytest.

## Exclusion audit

The following proof obligations remain in `scripts/hex_utils.py`; absence of a witness does not discharge them.

| Site | Required invariant and current gap |
| --- | --- |
| `Hex.is_poly_candidate` | Disjoint bounds exclude a polygon only if the cell bounds enclose every assigned query after integer conversion. `get_corrected_hex_boundaries` bounds reported vertices; great-circle edges can reach farther in latitude. Pole/antimeridian longitude widening does not fix ordinary curved latitude extrema. |
| `Hex.lies_in_cell`, exterior | Failure of all tests must prove no overlap. Source-vertex membership is a positive witness only; planar cell-vertex and segment tests cannot exclude a polygon intersecting the real cell outside the chord ring. Skipping edge tests for unrotatable special cells proves still less. |
| `Hex.lies_in_cell`, holes | Rejection requires the whole real cell to be inside a hole. `fully_contained_in_hole` proves a planar-ring relation, even after rotation, not coverage of all assigned coordinates. |
| `Hex.true_parents` | The inherited parent union must cover every child point. Mapping only reported child vertices to the coarser resolution is sampling, not a demonstrated covering union. |
| `Hex.poly_candidates` / `_init_candidates` | Resolution zero starts with all polygons; each recursive union and subsequent bbox exclusion must preserve that covering invariant. A polygon removed at any ancestor cannot be recovered by leaf overlap tests. Caching does not repair that loss. |

The repair must cover quantized query coordinates as well as spherical assignment. Sampling, a subdivision depth or an empirical pad cannot justify a negative answer. Retaining uncertain candidates is safe but costs index space and query work; replacing an ambiguous cell with one unconditional zone requires a separate full-coverage proof.

## Upstream authority evaluation

Verified 2026-09-10: [H3 #1052](https://github.com/uber/h3/pull/1052) closed unmerged and was replaced by the still-open [#1178](https://github.com/uber/h3/pull/1178), head `b7d298225f36c4e8de8e3514e096d9b2c6be9ac3`. Its isolated shared-library build passed the five `Geodesic|SphereCap` CTest suites. No project dependency changed.

Geodesic mode is not a drop-in conservative predicate for this package: it also changes source segments into great-circle arcs. Reproduce with the longitude/latitude rectangle `[(-10,60),(10,60),(10,61),(-10,61)]` at resolution 4 and point `(0,60.05)`, cell `8409a05ffffffff`. The point lies inside the source rectangle. Released H3 4.5.0 returns 54 full, 132 overlap and 169 bbox-overlap cells; overlap and bbox-overlap include the query cell. The isolated branch's planar modes give the same counts, while flags `CONTAINMENT_OVERLAPPING | FLAG_GEODESIC_MASK` return 129 cells and exclude it. This is a source-semantics witness, not a packaged lookup defect. Any H3-owned solution must enclose the original planar source geometry, not silently reinterpret it.

## Packaged-data evidence

The dated reports linked below identify the actual bytes and sample streams. They measure diagnostic cost, not converter or query performance. No candidate sets or packaged binaries were changed. The maintainer chose CI regression guards over a speculative construction repair: park the repair until a counterexample or a proposed optimization requires certified coverage. This leaves the documented proof gaps in place and can miss an unsampled defect. PERF-7 remains blocked; a green sampled audit cannot establish its full-coverage predicate.

On 2026-09-10, data 2026c, H3 4.5.0, Python 3.14.2 with Numba on macOS arm64:

| Stream | Points | Omissions | Seconds |
| --- | ---: | ---: | ---: |
| [H3 edges](../measurements/shortcut-candidates-cell-edges-2026-09-10.json) | 5,186,160 | 0 | 68.80 |
| [Source edges](../measurements/shortcut-candidates-source-edges-2026-09-10.json) | 16,375,460 | 0 | 168.39 |
| [Coordinate seams](../measurements/shortcut-candidates-seams-2026-09-10.json) | 124 | 0 | 0.05 |

These are single audit wall-clock runs, with concurrent local work, not performance comparisons. Enumerating every edge does not test every coordinate or solve every intersection. Backend regression tests deliberately remove candidates to ensure a zero-miss result is not a vacuous test of the oracle.
