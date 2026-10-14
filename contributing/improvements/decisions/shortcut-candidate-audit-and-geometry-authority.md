# Shortcut candidate audits and geometry authority

## What the audit establishes

`scripts/audit_shortcut_candidates.py` compares the candidates exposed by the packaged shortcut index with independent full-polygon containment, including holes. It asks the index which cell a coordinate reads, then uses integer query coordinates and the runtime polygon kernel. It does not use the converter's candidate rule as its oracle. A unique-zone entry exposes every polygon of that zone; the compiled format no longer reveals which individual polygons the converter originally retained there.

Run each deterministic stream with `uv run python -m scripts.audit_shortcut_candidates --mode MODE --output tmp/audit.json`: `cell-edges` enumerates every stored cell's four corners and the midpoint of each of its four edges - the corners probe each grid line from both sides, because a cell owns its north and east edges and its neighbour owns the other side, and the midpoints cover a polygon boundary crossing an edge between corners; `source-edges` enumerates stored boundary/hole vertices and planar midpoints; `seams` checks both poles and antimeridian representations. Source probes preserve the integer coordinate reached by runtime truncation. `--points` accepts a JSON array of longitude/latitude pairs for replay. `--max-points` bounds exploratory runs and records whether the stream was exhausted. Exit 1 means at least one omission; empty input fails instead of reporting success.

Reports retain data hashes, the grid shape, the Python version, the backend, counts and bounded witnesses. A missing polygon is not necessarily a wrong zone: overlapping polygons may supply the same answer. The report separately counts omissions whose answer belongs to none of the directly containing polygons. It makes no precedence claim when multiple zones contain a point. This is not an independent test of the polygon kernel, and zero sampled omissions is never a completeness certificate.

At the maintainer's request, `update_data.sh` runs all three untruncated audit streams once after conversion, before returning binaries or preparing a release. An omission or audit error stops the update before CI builds the data wheel. Reports live under `tmp/`, outside the packaged data; failure diagnostics include replay coordinates and missing IDs. Ordinary pytest/tox runs do not repeat these expensive streams: `tests/test_shortcut_candidate_coverage.py` executes the update script with external commands stubbed to verify all streams run and each failure blocks preparation, while the audit's unit tests check real missing-candidate detection and CLI failure. This intentionally leaves ordinary code PRs without a full sampled geometry census; rerun the diagnostic streams when changing candidate generation or the oracle.

## What a candidate rule has to prove

**The shipped rule discharges this by construction.** An exclusion is a planar predicate over two rectangles and a ring, because a cell is an axis-aligned rectangle of the integer coordinates the kernel reads and no candidate is inherited from a coarser level. The rule is *tight, not exact*: it over-includes a polygon whose interior enters the cell without reaching one of its integer points, and never omits one the kernel can place a cell's point inside. Over-inclusion costs a bounding-box rejection, so what remains is a smaller certification question, carried by [GEOM-3](../items/lookup-geometry-and-data-format/geom-3-conservatively-repair-shortcut-candidate-generation.md).

**The list below stays because the next index - or a custom-data path - has to answer the same questions in its own frame**, and each entry is a way of answering "this polygon cannot own a point of this cell" that does not establish it. A rule whose cells are not rectangles of the query's own coordinates owes all five.

- **Bounds that enclose reported vertices rather than assigned coordinates.** A cell's edges may reach farther than its vertices do, and the query coordinate is quantised after the cell is assigned, so disjoint bounds exclude a polygon only if the cell's bounds enclose *every* coordinate the cell will be asked about.
- **A positive membership witness read as a negative.** That a source vertex lies in the cell proves the polygon is a candidate; that none does proves nothing, because a polygon can cross the cell between its vertices. Nor can a special case that skips the edge tests prove less than the tests it skipped.
- **A planar relation standing in for coverage.** "The cell's ring lies inside this hole" is a relation between two rings; rejection needs the whole cell, every assigned coordinate of it, to be inside the hole.
- **A sampled parent union.** Mapping a child's reported vertices to a coarser level and taking the union there is sampling, not a demonstrated covering union.
- **An exclusion inherited from a coarser level.** If each level starts from its parent's candidates, every ancestor's union must provably cover every descendant point: a polygon dropped at an ancestor cannot be recovered by a leaf test, and caching does not repair the loss.

Sampling, a subdivision depth or an empirical pad cannot justify a negative answer. Retaining uncertain candidates is safe but costs index space and query work; replacing an ambiguous cell with one unconditional zone requires a separate full-coverage proof.

## Borrowing a coverage predicate from a library

**An externally-owned containment or coverage predicate can only be this package's candidate authority if it encloses the original *planar* source geometry.** The boundaries are planar longitude/latitude rings and a cell is a rectangle in that same frame, so a candidate rule asks a planar question of them. A *geodesic* predicate does not merely bound a cell more conservatively: it reinterprets the source segments as great-circle arcs, which is a different polygon — a rectangle spanning twenty degrees of longitude contains a point near its own edge that a geodesic containment mode excludes, and both answers are correct about their own geometry. Whatever library the next such offer arrives in, that is the test to apply to it, and a mode that is conservative about *cells* is not thereby conservative about this package's *polygons*.

## Packaged-data evidence

The dated reports linked below identify the actual bytes and sample streams, and the counts in them are the record rather than anything restated here. They measure diagnostic cost, not converter or query performance, and they change no candidate set. **A green sampled audit cannot establish a full-coverage predicate** - one of the reasons PERF-7 was withdrawn - and enumerating every edge still does not test every coordinate.

On data 2026d against the shipped index, Python 3.14.2, clang backend, macOS arm64, all three streams exhausted with zero omissions:

| Stream | Points |
| --- | ---: |
| [Cell edges](../measurements/shortcut-candidates-cell-edges-2026-10-13.json) | 1,854,384 |
| [Source edges](../measurements/shortcut-candidates-source-edges-2026-10-13.json) | 16,505,010 |
| [Coordinate seams](../measurements/shortcut-candidates-seams-2026-10-13.json) | 124 |

These are single audit wall-clock runs with concurrent local work, not performance comparisons. Backend regression tests deliberately remove candidates, so that a zero-miss result is not a vacuous test of the oracle.
