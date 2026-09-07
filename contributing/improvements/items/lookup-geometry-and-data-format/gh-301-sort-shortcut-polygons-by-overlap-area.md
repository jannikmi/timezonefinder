# GH-301 — sort shortcut polygons by overlap area


## Related memory

- [Query performance and shortcut decisions](../../decisions/query-performance-and-shortcut-index-decisions.md) — the refusal in one paragraph. This file is the measurement record it points at, and is retained for that reason rather than deleted.
- [Query performance measurement baseline](../../query-performance-measurement-baseline.md)
- **Tracks:** issue #301, **closed as not planned 2026-08-21** with the enumeration as justification.
- **Status:** rejected 2026-09-06, and closed by construction rather than by sampling: the ordering that provably minimises expected compute is worth 0.27 % of a mixed workload, and measures as no difference. Eight heuristic keys spanning the whole per-cell blend of the two properties available — a zone's vertex count in the cell and the area it covers of the cell — were compiled into real shortcut binaries; the family is monotone and its best member is what already ships. What is refused is the family, not one key.

## What was measured

Both indices per comparison were compiled from the verified 2026c GeoJSON, and the *count* of point-in-polygon tests taken by wrapping `inside_of_polygon` over the committed benchmark fixtures. Timings are `benchmarks/candidate_comparison.py`, 61 rounds x 2,500 points, order alternated, one process holding both indices, mapped coordinate access, on the ranked C-extension column.

| ordering | zone key, per cell | tests, ambiguous | random | on-land | answers moved | ambiguous query |
|---|---|---:|---:|---:|---:|---:|
| shipped | vertices ↑ (w = 0) | — | — | — | — | — |
| tie-break | vertices ↑, area ↓ breaking ties | +0.0 % | +0.0 % | −0.1 % | **0** | not timed |
| w = 0.25 | vertices / area^0.25 ↑ | −0.6 % | −0.4 % | −1.2 % | **0** | **+4.2 %** |
| w = 0.5 | vertices / area^0.5 ↑ | −1.2 % | −0.5 % | −1.6 % | 1 | **+5.5 %** |
| w = 1 | vertices / area ↑ — Smith's rule | −1.7 % | −2.0 % | −2.4 % | 2 | **+9.7 %** |
| w = ∞ | area ↓ — likeliest zone first | −2.8 % | −3.6 % | −3.6 % | 158 | **+24.8 %** |
| area ↑ | likeliest zone last, in the free slot | +1.3 % | +0.2 % | +1.1 % | 153 | not timed |
| w = ∞, block-capped | area ↓, test cost capped at four blocks | −2.7 % | −3.5 % | −3.5 % | 158 | not timed |

**The family is monotone in the area weight and its optimum is `w = 0`, the shipped key.** More area weight buys fewer tests, moves more answers, grows the index (610,210 bytes at `w = 0` to 624,849 at `w = ∞`, because distinct orderings deduplicate less well than distinct candidate sets) and costs more time, without a turning point anywhere between. That is the result: not that one key was chosen badly, but that no per-cell blend of the two properties available beats vertex count alone.

- **Every timed row is slower on the ambiguous stratum, both estimators agreeing.** `w = ∞` also reads +25.0 / +8.0 / +9.4 % on numba; `w = 1` was run twice (+10.8 % and +9.7 %, 8 and 4 of 61 rounds). The small blends are *no difference* on `random` and `on-land`, so the loss sits on ambiguous, ~40 % of a mixed wall clock.
- **The `unique` control drifted toward the challenger** on three runs (37-47 of 61 rounds, best round within 2 %, so `unresolved`). No ordering can reach that stratum, so the ambiguous losses are if anything understated.
- **Three rows were not timed, none having a side that could win**: `area ↑` costs more tests everywhere; the block-capped variant reproduces `w = ∞`'s counts and its 158 moved answers, which is what says the vertex count rather than the cap carries the signal; the tie-break row changes nothing.

## Why a count of tests was the wrong instrument

The 2.90 % this item was ranked on was a count of *tests*, and a count is a workload share only when the things counted cost the same. They do not: the zone with the largest overlap is usually the zone with the most vertices, so ordering by area buys fewer tests by making the first test the expensive one. Weighting each cell's candidates by overlap area and summing over the 31,368 ambiguous cells whose areas could be computed gives **+101 % expected vertices tested** against −2.8 % tests. The A/B confirms that *direction* and not that size — the query loses far less than the vertices predict, because the latitude block index makes a test sublinear in the ring. Sublinear, not free, which is the whole result.

Smith's rule (`w = 1`) is what the cost model says to do about that, and it helps: it keeps a huge polygon in the free final slot, moving 2 answers where `w = ∞` moves 158. It still loses, as does every weight between, because today's key already minimises the dominant term — the cost of a *failed* test. **Sweeping the weight is what turns a refusal of one key into a refusal of the family**, at one pass over the fixtures per key.

**This is a different instrument from the 2.90 %, not the same number re-run.** That was an index-uniform enumeration at resolution 3 over 41,162 cells; these are fixture-weighted counts at resolution 4. The two landing within a tenth of a point is a coincidence of denominators, not corroboration.

## The optimum, constructed and verified

The heuristic sweep above refuses a family by sampling it. The optimum settles it outright.

**The model.** The loop stops at the first hit and never tests the final zone's run, so with `S` the index where that run starts, `c_t` the expected compute of testing the candidate at position `t` and `p_t` its hit probability for a uniform point in the cell, the expected compute is `E = Σ_{t<S} c_t · (1 − Σ_{u<t} p_u)`. Zone contiguity is a hard constraint: `last_zone_change_idx` is only well defined with one final run.

**The construction.** Within a zone, order by `c/p` ascending — adjacent exchange of `i` and `j` moves `E` by `c_j·p_i − c_i·p_j`. Across zones, a zone entered at survival `R` contributes `R·C − K` with `C = Σc`, `K = Σ_i c_i·Σ_{u<i} p_u`, so exchanging adjacent zone blocks moves `E` by `C_A·P_B − C_B·P_A`: the `K` terms cancel and a zone behaves **exactly** as one job of cost `C` and probability `P`, ordered by `C/P` ascending. The free final slot does not reduce to a sort key, because designating zone `m` last both saves its own contribution and removes its probability from shielding everything after it — `E(m) = E_all − (R_m·C_m − K_m) + P_m·Σ_{j>m} C_j`. With `k ≤ 25` zones, and `k = 2` in 94 % of cells, evaluate all `k` and keep the minimum.

**Verified, not argued.** Enumerating every contiguity-respecting ordering of all 31,344 ambiguous cells holding at most 5 candidates, the construction attains the minimum in **31,344 of 31,344** — no cell where it is beaten.

**The cost coefficient is not the vertex count**, and this is the part with teeth. The packed kernel walks every latitude block of a ring, skips those whose stored range excludes the query latitude, and scans only survivors, so `c_i = α + β·(blocks) + γ·(in-band edges)`, all three counts computable at build time from `_block_index.block_latitude_ranges`. Calibrated against measured `PolygonArray.pip` times over 1,500 (polygon, latitude) samples: **`437.5 ns + 0.511·blocks + 1.133·in-band edges`, R² = 0.9886**, against **R² = 0.524 for the total vertex count** the shipped key sorts on. A polygon of ≥512 vertices scans a median **2.2 %** of its ring, and the two keys disagree on which of two candidates is cheaper in **31.6 % of candidate pairs**.

**And it still does not matter, because the loop is overhead-bound.** With the calibrated model, expected candidate-loop compute per ambiguous query is 758.5 ns shipped, 735.8 ns under a pure true-cost key and **723.8 ns under the optimum — −4.57 %**. But 437.5 ns of that is fixed per-candidate overhead and only ~1.05 candidates are tested, so the loop is **14.7 % of a 5,150 ns ambiguous query**: the optimum saves **34.7 ns, 0.67 % of an ambiguous query and 0.27 % of a mixed workload**. Three paired A/B runs agree — +3.8 %, −6.3 %, +0.2 % on ambiguous with 29, 30 and 30 of 61 rounds won, dead even every time and `unresolved` or `no difference` throughout. **Even an oracle** that knows the answer and pays only the cheapest candidate saves 80 % of the loop, which is 11.8 % of an ambiguous query and **4.7 % of a mixed workload** — that is the ceiling on candidate ordering as a subject, reached only by clairvoyance.

**Dropping zone contiguity for everything but the final zone is correct and buys nothing.** Only the final zone must be a suffix — `last_zone_change_idx` needs that and nothing else does, since `_zone_id_among` returns the zone of whichever polygon hits — so the tested prefix may interleave zones freely, and the ratio rule then applies to individual polygons. That relaxed construction is also verified optimal by enumeration (0 mismatches over 31,354 cells). It is worth **0.04 ns per ambiguous query, −0.005 %**: contiguity *could* bind on 2,020 of 31,368 cells and actually costs something on **16**, worth −5.77 % on those alone and 226 ns on the worst. It binds only where a prefix zone contributes two or more polygons and another zone exists to interleave with, which the two-polygon majority rules out. Relaxing it would also mean relaxing `has_coherent_sequences` and `check_shortcut_sorting`, for that.

**What this prices for the future.** The candidate loop is bound by per-call overhead, not by geometry: 437.5 ns fixed against ~1.1 ns per scanned edge. Any further work on this loop should attack the overhead, not the order; and the block index has already collected the win that reordering would have been reaching for.

## What else the measurement turned up

- **Reordering candidates moves answers, with no data change** — how many depends entirely on the key, from 2 to 158 of 5,000 ambiguous points. Every moved point lies inside **two** zones' polygons, where the upstream boundaries genuinely overlap; `Asia/Urumqi` inside `Asia/Shanghai` is most of them. Which zone answers is decided by whichever is tested first. Nothing runs the [data-update guard](../../../development/data-pipeline-format-versioning-and-release-order.md) for an index reordering, so a future one owes that diff by hand. `tzfpy` agrees with the reordered answer on almost all of them, which is evidence about `tzfpy`'s precedence and not about correctness: [no correctness property may be stated in terms of the shortcut index](../../decisions/geometry-data-format-and-validation-decisions.md).
- **Resolution 4 shrank the prize.** With `last_zone_change_idx` making the final zone free, **29,372 of 31,394 ambiguous cells hold exactly two polygons of two zones**, where every order costs exactly one test. At resolution 3 the entry recorded 9,046 of 10,511.
- **Rebuilding the shipped ordering from source reproduces the packaged binary to 29 bytes**, across the handful of cells where the sort key ties and `polys_in_cell`'s set iteration order breaks the tie. Recorded separately as [TOOL-7](../data-pipeline-and-developer-tooling/tool-7-the-shortcut-ordering-leaves-its-ties-to-set-iteration-order.md); it needs no area and no dependency.

## Reproducing it

Taken against `c27b452` on Apple arm64, free-threaded CPython 3.14.2, data 2026c, fixture set v3. The scripts are not committed, because `prototypes/` is out of scope for an improvement pass: compile the shortcut mapping from the verified 2026c GeoJSON, take each candidate's `shapely` intersection area with its cell in the frame `Hex.lies_in_cell` uses, and write each ordering through `build_shortcut_index`.

**`shapely` is not what refused this.** The maintainer decided on 2026-09-06, directing the pass that took the item, that a `shapely`-class dependency is acceptable at conversion time and not at runtime; one in the `data` group costs users nothing. It was added there to measure and taken out again.
