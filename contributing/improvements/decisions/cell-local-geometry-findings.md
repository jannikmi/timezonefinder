# Cell-local geometry: findings and reopening conditions

Recorded at the maintainer's request on 2026-09-09. These are dated experimental findings, not current performance claims or an approved implementation. [Raw measurements](../measurements/cell-local-geometry-2026-09-09.json) retain the pilot, censuses, counterexamples, file sizes, environment, source-data hashes and individual timing rounds. [Correctness, formats and reproduction method](cell-local-geometry-correctness-and-format.md) define what was measured.

## Decision and scope

The proposal was to store/query only the relevant polygon sections for ambiguous shortcut cells. It is not structurally impossible, but **no measured query benefit currently justifies adopting it**. The maintainer rejected the roughly 96 MB representation retaining originals as too large and required reductions without sacrificing boundary accuracy. Lossless sharing subsequently reached roughly 45 MB; that footprint was measured, not accepted as a product budget.

Preserve these distinctions when revisiting the idea:

- **Naive planar clipping and rounded cut vertices are unsuitable:** both change containment on the recorded dataset. Padding the cell alone does not repair moved source edges.
- **Exact rectangular clipping is a viable geometric construction, not a production correctness certificate.** Its Python implementation passed the recorded checks; its floating-point cell envelopes remain uncertified.
- **Sharing original coordinate runs is lossless relative to those exact fragments.** It avoids paying twice for geometry exposed by `get_geometry` and preserves the existing source precision and holes.
- **The Python reference reader is not a viable query engine.** Its latency does not measure the potential of a future native reader. Do not use its approximately 200x slowdown to rule out every cell-local design, or describe a speedup as established because fewer edges seem necessary.

The existing lookup already skips latitude blocks; the comparator is not a full scan of every candidate polygon. Unique-zone queries already avoid geometry entirely and gain nothing. Expected benefits are fewer distant blocks/edges and better ambiguous-query tail latency; costs are extra addressing, indirect coordinate access, exact-intersection processing, build complexity and storage. Memory mapping and a correct pure-Python fallback remain requirements, not negotiable accuracy/performance trades.

An initial suggestion to preselect existing blocks per cell was **not implemented or benchmarked**. Nor is retaining only edges physically inside a cell sufficient: an infinite ray can cross edges outside it. Such a representation needs the missing parity contribution or an equivalent correct construction.

## Storage evidence

All figures below are decimal MB of uncompressed installed files, not wheel sizes or resident memory. Figures are frozen to data 2026c and the recorded source bytes; they are not forecasts for subsequent releases.

| Representation | Size | Meaning |
| --- | ---: | --- |
| Original boundary/hole geometry only | 32.76 MB | Actual files, including geometry metadata |
| Original complete dataset | 33.38 MB | Actual files; baseline for complete representations |
| Naive six-decimal fragment model | 37.87 MB | Estimate, incomplete and incorrect geometry |
| Naive seven-decimal fragment model | 44.99 MB | Estimate, incomplete and incorrect geometry |
| Exact rectangular fragments | 63.17 MB | Actual serialized geometry and lookup metadata |
| Exact fragments plus originals | 95.93 MB | Original geometry APIs' data retained; common files counted once |
| Shared exact fragments plus originals | 44.96 MB | Original dataset once plus 11.58 MB of references/new vertices |

The naive census processed 30,873 of 31,394 ambiguous cells, excluding 521 antimeridian cells. It produced 8,515,808 vertices, including 330,022 off the source grid. Its block-packing model omitted bridging vertices, sentinels, file headers, cell addressing, shell/hole grouping, antimeridian handling and exact intersections; it did not optimize rotations. Raw float64 coordinate pairs alone would occupy 136.25 MB. Neither packed estimate prices a correct final format.

The exact census included every ambiguous cell, with 31,916 rectangles, 522 split cells and one full-longitude polar window. It retained 69,483 nonempty rings and 12,706,733 vertices. Empty clipped holes were omitted and holes of an empty exterior skipped. A preliminary encoding unnecessarily retained 509,051 empty ring records, costing 14,253,428 bytes; the final figure excludes that avoidable overhead.

Only 2.92 MB of the exact representation was its exception table; its ordinary packed payload was 52.81 MB. Fraction metadata alone was not the main storage problem. The shared form references 12,411,686 source vertices through contiguous runs and separately stores 295,047 vertices with 103,798 exact rational overrides. Every reconstructed ring matched the exact predecessor. That removes 53.1% of the complete predecessor's storage, but leaves 34.7% overhead over the original dataset. Tighter envelopes, additional deduplication and optimized ring rotations were not measured.

## Correctness evidence and limits

The exact representation passed all 69,483 ring round trips, 1,161,572 window-coverage probes, 161,169 candidate-containment checks and 31,916 candidate-order checks. Detailed border probes used a seeded 512-cell subset; every ambiguous cell received query checks. All 30,000 committed fixture queries agreed, of which 7,937 actually used fragments; unique-cell agreement is only a control. Another 120 exact-pole/antimeridian queries and 755 candidate comparisons passed.

Five focused tests covered integer-grid queries, binary round trips, disconnected intersections, holes, fractional cuts and recorded failures. Independent review additionally checked 72,200 integer queries on 200 randomized polygon walks, all 756 source-hole resolutions and a fractional-floor/source-vertex collision. These are evidence, not exhaustive proofs of the implementation. Sharing's full coordinate comparison establishes equivalence to the tested exact predecessor, not that the predecessor has no remaining defects.

Production prerequisites remain a certified numerical envelope or explicit floating-point error bound, an overflow audit of native rational products, source-release pairing enforcement, and a reader that does not materialize whole source rings. Stored int64 numerators do not imply int64 intermediate products are safe. The shared prototype records source hashes but does not enforce them in its reader; the measured run checked against the same source dataset.

## The only latency experiment

The metric was **whole-query ambiguous p99**, not kernel time or batch throughput. On Apple arm64, Python 3.14.2, data 2026c, the median of seven round-level p99s was **11.75 microseconds for the current C-backed lookup versus 2,320.66 microseconds for the shared Python oracle**. Ranges were 11.21-12.96 and 2,210.72-2,390.32 microseconds respectively. The prototype won zero rounds; every answer agreed.

Each arm received 5,000 queries per round sampled with replacement from the same 5,000 ambiguous fixtures. The repository's paired harness supplied identical draws, alternating order and one warm-up batch per arm. Per-call clocks covered the whole lookup, excluding result assertions and sample bookkeeping. Warm-up samples were discarded; the harness's batch-mean verdict was not used as a p99 verdict. The prototype reconstructed rings, cached up to 64 decoded source rings and used Python `Fraction` arithmetic; the production comparator used `timezonefinder.utils_clang`. No comparable native fragment kernel existed.

The timing therefore establishes **no benefit from the implementation tested**, not the absence of a possible geometric benefit. The experiment used checkout `c2b1cbd104660a3906d7e2bf7fe097172315206f`; query code on master had already changed when this record was prepared. Do not treat these numbers as today's baseline. No memory, cold-start, native-reader, mixed-workload regression or alternative-format latency study was performed.

## Conditions for further work

Reopening implementation needs an acceptable storage budget and an exact reader capable of a meaningful comparison with current latitude-block filtering. The proposed deciding metric remains ambiguous-query p99 (p95 can supplement it), paired against the then-current lookup with the backend named. Ordinary workloads and mapped-mode memory must also avoid unacceptable regressions before adoption. An earlier suggested 20% p95 improvement was only a screening suggestion, not an agreed threshold or an observed result. Do not exchange source precision, hole correctness or public geometry completeness for a faster number.
