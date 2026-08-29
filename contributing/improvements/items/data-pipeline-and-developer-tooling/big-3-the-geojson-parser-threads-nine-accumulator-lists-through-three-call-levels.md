# BIG-3 — the GeoJSON parser threads nine accumulator lists through three call levels

- **Location:** `scripts/timezone_data.py`, `TimezoneData.from_geojson` and the three classmethods below it: `_process_timezone_feature` (12 parameters), `_process_polygon_with_holes` (12), `_process_hole` (8).
- **Defect:** `from_geojson` declares nine empty lists plus two counters and passes them down two levels for the callees to append to. `poly_id` and `nr_of_holes` are additionally returned and reassigned at each level, so each function both mutates shared state and threads a counter — and which arguments are inputs and which are outputs is visible only by reading the bodies. The parameter order also has to match at three call sites with nothing checking it: several neighbouring parameters share a type (`PolygonList` appears twice, `list[int]` three times), so a transposition type-checks.
- **Fix:** one mutable accumulator (a dataclass with the nine lists and two counters) passed once, turning the three signatures into `(accumulator, <the thing being parsed>)`. Size: ~120 lines touched, no logic moved.
- **Why it is not a straight refactor:** this is the data converter, and the only thing that proves it neutral is regenerating the binaries and confirming `git status --short packages/timezonefinder-data/timezonefinder_data/data` is empty — which needs a timezone-boundary-builder download (`update_data.sh`), not just a test run. Worth doing, but the verification is the expensive part, so it should be its own pass.
- **Status:** open.
- **Last touched:** 2026-08-09 — found.
