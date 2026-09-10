# LITE-1 — return the zone covering most of each H3 cell

## Why this is only an idea

`TimezoneFinderL` answers an ambiguous H3 cell without loading or testing polygon geometry. Its current answer is the full lookup's final fallback: the zone left after the converter has ordered the other candidates to minimise full-predicate work. That ordering has a performance meaning, but no probability meaning. The final zone is not necessarily the zone covering the greatest share of the cell.

A more intuitive lightweight heuristic would precompute the zone whose polygons cover the greatest area of each ambiguous H3 cell and return that zone from `TimezoneFinderL`. This would change only the deliberately approximate finder; it must not alter `TimezoneFinder`, `certain_timezone_at`, candidate completeness or overlap precedence.

There is no evidenced user need for a more accurate lightweight suggestion. Changing the answer would create compatibility churn, and storing a per-cell result may enlarge the shortcut index and `TimezoneFinderL`'s resident footprint—the resource trade-off the class exists to make. Do not spend that cost speculatively.

## Work if reopened

First establish an accuracy workload that can distinguish the current fallback from a cell-area result. Report agreement with full geometry over held-out points in ambiguous cells, separately from the percentage over all lookups where unique-zone cells dominate. The comparison must include borders, enclaves, holes, ocean zones and cells where zones overlap; a fixture used to choose the heuristic cannot also validate it.

Then define “covering the greatest area” precisely. The build must account for all polygons of a zone and subtract holes. It must document how overlapping zones and equal areas are resolved, and whether the cell/source-edge intersection is spherical or an explicit approximation. This is a heuristic, so it does not need the conservative coverage proof blocking PERF-7, but its geometry still has to be deterministic and reproducible across data builds.

Price at least these representations before selecting one:

- one zone id per ambiguous H3 cell, which preserves candidate ordering but adds a cell-sized column;
- one zone id per deduplicated candidate-list entry, which is compact but cannot express different area winners for cells sharing the same candidate list;
- making the area winner the final candidate, which stores nothing extra but couples `TimezoneFinderL` accuracy back into the full lookup's independently optimized order.

Measure compiled-file size, construction heap and resident memory, scalar and batch lookup latency, data-conversion time, and answer changes. Preserve the memory-mapped mode and the pure-Python path. Update the public description from “full lookup's fallback” only if the new result is actually shipped.

- **Where:** `TimezoneFinderL._fallback_zone_of` in `timezonefinder/timezonefinder.py`; `ShortcutOrderer.order` in `scripts/shortcut_ordering.py`; the shortcut layout in `timezonefinder/shortcut_index.py`.
- **Size:** M — build-time cell/zone intersections, an accuracy fixture and likely a shortcut-format extension plus regenerated data.
- **Status:** parked — resume only when users ask for a more accurate `TimezoneFinderL` approximation, or equivalent usage evidence shows that its ambiguous-cell accuracy matters.
