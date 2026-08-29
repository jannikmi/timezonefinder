# BUG-5 — the exact poles lie on a polygon boundary, so `certain_timezone_at` answers `None` there

## Related memory

- [Public API and runtime-loading decisions](../../decisions/public-api-compatibility-and-runtime-loading-decisions.md)

- **Location:** `timezonefinder/utils_numba.py`, `pt_in_poly_python`, reached from `TimezoneFinder.certain_timezone_at`. Not the shortcut index: brute-forcing all 1,322 packaged boundary polygons at latitude −90 finds **no** polygon reporting that it contains the point, so there is nothing the index could have listed.
- **What it is:** `Antarctica/McMurdo`'s ring has vertices *on* the south pole, and a point lying exactly on a ring is answered whichever way the ray casting happens to fall. One ten-millionth of a degree away — latitude −89.999999, the next representable coordinate — both methods answer `Antarctica/McMurdo`. The north pole lies inside `Etc/GMT` rather than on its boundary and answers normally, which is why only one of the two shows.
- **What a caller sees:** `certain_timezone_at(lng=…, lat=-90)` is `None` at every longitude, while `timezone_at` answers `Antarctica/McMurdo` — by elimination, without testing containment.
- **Why it is ranked here and not higher:** it is two coordinates of the globe, one of which already works. It is also not a polar defect but the general on-boundary case, which every border in the dataset has: a point exactly on one has an unspecified answer, and there both sides are defensible. The pole is only the coordinate at which landing exactly on a boundary is *certain* rather than a measure-zero accident.
- **What not to do, and it is the tempting fix:** do not make the ray-casting kernel count boundary points as inside. It runs per candidate polygon on every ambiguous query, and changing what it answers on a boundary moves answers along every border in the dataset to buy these two coordinates.
- **Fix:** state it instead — one sentence in the usage docs saying a coordinate lying exactly on a zone boundary has an unspecified answer, with the poles as the case a caller can actually reach on purpose. ~5 lines, no code.
- **Status:** open.
- **Last touched:** 2026-08-25 — found while sweeping the index's cell coverage, then brute-forced against every polygon to establish that the index is not the cause.
