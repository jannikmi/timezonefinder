# Shortcut index resolution decisions

Which H3 resolution the shortcut index is built at, and what each level costs. Split out of the [query performance and shortcut index decisions](query-performance-and-shortcut-index-decisions.md), which holds everything else about the index and the query path. Do not re-propose a level without new evidence.

- **The H3 shortcut resolution moved from 3 to 4 — measured 2026-08-23, with 5 refused.** Built, not modelled: every resolution below was compiled from the 2026c boundaries and priced in the shipped layout. Restated here rather than left in `prototypes/single_resolution_bench.py`, because a prototype is deletable and this verdict has to outlive it.

  | res | cells | unique | file | resident | candidates tested /10k queries |
  |---|---|---|---|---|---|
  | 3 | 41,162 | 74.5 % | 103 KiB | 143 KiB | 3,877 |
  | **4** | **288,122** | **89.1 %** | **596 KiB** | **1,000 KiB** | **1,566** |
  | 5 | 2,016,842 | 95.4 % | 4,029 KiB | 7,832 KiB | 667 |

  * **What resolution 4 bought, paired and order-alternated against a resolution 3 index in one process:** random −41.6 %, on_land −37.8 %, both 0 of 61 rounds where resolution 3 won. The committed report page moved from ~3.40 µs to ~2.02 µs per random lookup. The unique stratum is unchanged (−1.1 % on minima, 40 of 61 rounds — the estimators disagree, so: no effect), which is the expected shape: a unique-cell query does the same work at either resolution, and what changes is *how many* queries are unique.
  * **What it cost:** `TimezoneFinderL`'s heap 176 KiB → 1.01 MiB, the default finder's 1.13 → 1.96 MiB, construction 7.98 → 8.28 ms. **The mapped mode's resident set went down**, 32.4 → 26.1 MiB, because far fewer candidate polygons are fetched and so far fewer coordinate pages are faulted in — a second-order effect worth remembering when pricing a future level.
  * **The `ambiguous` benchmark stratum is not comparable across this change**, and neither is `unique`. Both are a *classification by the shortcut index*, so changing its resolution re-labels the points: the easy members of the old ambiguous set became unique, leaving a harder residue. `FIXTURE_VERSION` was bumped for exactly this. Compare `random` and `on_land`, which are sampled independently of the index.
  * **Resolution 5 is refused on the exchange rate, not on its gains, which are real.** Memory paid per candidate polygon removed is 0.019 KiB going 2→3, 0.371 KiB going 3→4 and **7.600 KiB going 4→5** — each level about twenty times worse than the last. The table is `122 * 8**res`, fixed by the resolution rather than by the data, so it is 99.7 % of the index at resolution 5. 7.8 MiB resident is more than the entire index format generation 1 used, and would take `TimezoneFinderL` from ~176 KiB to ~7.9 MiB.
  * **Resolutions above 5 are not worth measuring** — the table grows eightfold per level, so resolution 6 is ~63 MiB resident, the size of the polygon data it indexes.
  * **A hierarchical index over several resolutions is refused** and its prototype deleted. The maximum resolution dominates the size, so a multi-resolution index is *larger* than the single-resolution one it contains; H3 cells do not nest cleanly, so a parent must be kept even once its children exist; and consulting several resolutions per query costs more than the refinement saves.
  * **A resolution change is only safe because the file now stamps its own.** The binary layout is identical at every resolution, so `layout_version` cannot distinguish them and a stale data directory would silently index the wrong cells. The reader rejects a mismatch by name.
  * **It was also only safe after the edge-crossing test.** A resolution 4 index built before that answered a point in the Strait of Malacca wrongly, because the overlap test ignored polygon edges crossing a cell — a defect that grows as cells shrink. Any future level must re-check that class before being adopted, not merely re-time.
