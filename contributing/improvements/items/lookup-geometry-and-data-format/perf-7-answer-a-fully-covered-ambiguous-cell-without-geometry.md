# PERF-7 — answer a fully covered ambiguous cell without geometry

## Related memory

- [Overlap precedence](../../decisions/shortcut-ordering-and-fallback-semantics.md#overlap-precedence) — where the containment precedence rule this item introduced now lives, applied through the candidate ordering in every cell instead of only in covered ones.
- [GEOM-3](geom-3-conservatively-repair-shortcut-candidate-generation.md) — the full-cell coverage proof an unconditional answer needs, which is the opposite of the no-omission proof GEOM-3 carries.
- Closed PR #652 — the converter half, implemented and measured: a whole-cell coverage test, a zone-precedence pass, and two full 2026c compiles diffed against each other.

## The proposal

Store an ambiguous shortcut cell that one boundary polygon covers entirely as a unique-zone entry, so no point in it pays for geometry. Such a cell always holds candidates of other zones, or it would already be a unique-zone entry, and every one of them overlaps the coverer inside it; the conversion therefore ordered the overlapping zones by containment, the enclave winning.

## Why it is withdrawn

**Withdrawn 2026-09-21, after a review of whether it made sense at all.** Three findings, in order of weight.

**It answers one overlap region differently per H3 cell.** The rule applies only inside covered cells, while every other cell of the same overlap keeps the candidate ordering's zone precedence. Sampling points that lie in *both* zones of each pair the conversion decides, on 2026c:

| overlap | in converted cells | in the other cells |
|---|---|---|
| `Africa/Juba` / `Africa/Khartoum` (Abyei) | Juba, 217 points | **Khartoum, 322 points** |
| `Asia/Urumqi` / `Asia/Shanghai` | Urumqi | Urumqi |
| `Asia/Tbilisi` / `Europe/Moscow` | Tbilisi | Tbilisi |
| `America/Sitka` / `America/Vancouver` | — | Sitka |

Where the ordering already picked the enclave the conversion moved nothing; where it did not, it split Abyei by H3 cell. That is the "deciding per cell" outcome the precedence decision refused, and an answer depending on the index, which the [geometry decisions](../../decisions/geometry-data-format-and-validation-decisions.md) forbid. The two fixture answers the item reported as moving were this split. **Precedence, if wanted, belongs in the ordering of every cell** — which is where it now is.

**What remains is a sub-noise speed-up.** With no answer changing where the rule is consistent, the item is performance alone. Of the committed fixtures, **0.23 % of random, 0.88 % of on-land and 2.76 % of ambiguous points** land in a converted cell, each skipping ~4 µs: ~0.6 %, ~1.9 % and ~2.1 % of a query. A paired, order-alternated A/B on the C-extension backend, 61 rounds × 2,500 points, resolved no difference on any stratum.

**Against that, the costs were large and one of them is silent.**

- An unconditional answer needs certified full-cell coverage. The planar ring through `h3.cell_to_boundary` vertices is not the set of points H3 assigns to the cell — its geodesic edges bow away by up to tens of metres at resolution 4 — and a wrong claim is a wrong timezone with no geometry left to catch it. That proof is GEOM-3-sized.
- `timezones_at` reads the candidates the conversion discards, and every converted cell is a two-zone overlap. Two routes keep them, both priced on 2026c. **(a)** A per-entry covering-zone column over entries deduplicated on *(candidate list, covering zone)*: 7 entries on top of 2,994, no payload growth, but a shortcut layout change and therefore a `DATA_FORMAT_VERSION` bump. **(b)** Data-only: store the winner's polygons last with a stop index of 0 — the released reader already returns the final zone untested from the stop index onward — at the price of loosening `_data_integrity`'s `last_change == get_last_change_idx(...)` to `<=`, so a corrupted, too-small stop index would pass, and of adapting `timezones_at`'s early break and first-element contract. A format bump was therefore *not* unavoidable, as this entry briefly recorded.

## Measured, so a revival starts from it

On 2026c at H3 resolution 4: **826 of 31,394 ambiguous cells** are covered by one polygon; **742 convert and 84 cannot**, because a smaller zone reaches into them without covering them and would take the part it reaches. Converting the 742 removed **2.6 %, 2.1 % and 4.4 %** of point-in-polygon tests on the ambiguous, random and on-land fixtures; `shortcuts.bin` was the only binary that moved, and it kept its size.

No polygon clipping is needed. Coverage is a whole-cell-inside-polygon test plus no hole of the covering polygon meeting the cell, and containment reduces to comparing spherical zone areas: the two ratios share the shared area as their numerator.

## Reopen only if

The index's cells are exact planar rectangles — the grid tree shipped in format 4, so full coverage is an exact rectangle-in-polygon test — **and** precedence is consistent in every cell, so that converting a covered cell changes no answer. **Both halves are now met**: the [overlap precedence](../../decisions/shortcut-ordering-and-fallback-semantics.md#overlap-precedence) ranks zones by spherical area in every cell. What still keeps this closed is its price, which was measured on H3 and is not evidence about the grid tree: a discovery pass may re-propose it as a pure performance item, priced on its own count over the grid tree and without the per-cell split that withdrew it.

- **Status:** withdrawn — applying precedence only in covered cells splits an overlap region by H3 cell, and the remaining ~0.6–2.1 % gain does not pay for certified coverage and keeping `timezones_at`'s candidates.
