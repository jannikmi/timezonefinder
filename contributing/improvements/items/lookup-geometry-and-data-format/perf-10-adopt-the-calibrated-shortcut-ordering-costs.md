# PERF-10 — adopt the calibrated shortcut-ordering costs

- **Status:** withdrawn 2026-10-13 — re-measured against the index that ships, the fitted coefficients are not shown to be better than the reviewed ones.

## The dead end, and the evidence that killed it

**Measured 2026-10-09 on the H3 resolution-4 index:** `make shortcut-calibration` fitted bbox 134, hole union 54, hole lookup 258, hole bbox 100, PIP dispatch 446, block probe 0.52 and active vertex 1.14 ns against production 160, 80, 120, 120, 700, 1 and 1. Re-ordering every ambiguous cell with the fitted set changed 646 of 30,439; answers were identical, and the whole public call was 3.3–4.0 % faster on all 8 seeds in those cells, winning 97–100 % of rounds. Those cells took 0.24 % of random, 0.42 % of on-land and 1.76 % of ambiguous fixture queries, so no suite row could resolve it — which is why an in-query A/B on the touched path was the right instrument, and it won cleanly.

**Re-measured 2026-10-13 on the aligned grid tree, same machine and tooling, data 2026d:** the fitted set now changes 1,524 of 50,584 eligible cells and still leaves every answer identical, but the whole-query A/B over those cells reads **`unresolved` on all 8 seeds** — median −1.2 %, range −0.7 % to −2.0 %, 43–45 of 61 rounds won. By the [benchmark rules](../../../development/benchmarking-and-performance-validation.md) that is *no demonstrable difference*, not a small win: the two estimators disagree, which is the one verdict a single estimator cannot give. The changed cells take 0.12 % of random and 0.25 % of on-land fixture queries.

**And the fit itself is degenerate on this index's ambiguous population**, which the 2026-10-09 run had already flagged as its weakest point. Hole-union probe and PIP dispatch are now *perfectly* collinear — every probe of a surviving outer box is followed by a dispatch, and on 918 observations nothing separates them — so the fit assigns 493 ns to the probe and **0.02 ns to the kernel call behind it**, and hole-bbox collapses to 0.0 against a 0.96 correlation with hole-lookup. A cost model that prices a packed point-in-polygon dispatch at nothing is not a better model of the runtime than the reviewed defaults, whatever it does to a held-out error figure.

The run is recorded in `benchmarks/shortcut_ordering_model.json`, whose decision line carries this verdict, so the production coefficients now stand against a calibration taken on the index that ships rather than on one that does not.

## What would reopen it

A fit that separates the hole-union probe from the PIP dispatch — which needs observations where one occurs without the other, so a change to the predicate's structure rather than more sampling — **and** a changed-cell A/B that resolves. Nothing less: the reviewed coefficients have never been shown to produce a wrong order, only one a collinear fit disagrees with, and publishing a different order costs an ordered two-distribution release.

## Related memory

- [Benchmarking methodology: calibrating the shortcut-ordering model](../../../../docs/benchmarking_methodology.rst#calibrating-the-shortcut-ordering-model)
- [Release-batching decisions](../../decisions/data-format-version-marker-and-release-batching-decisions.md) — this is the item the format-4 hold was keeping a rebuild for, and could not deliver
