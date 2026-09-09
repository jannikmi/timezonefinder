# GH-657 — adopt H3 geodesic polygon coverage for shortcuts

[Issue #657](https://github.com/jannikmi/timezonefinder/issues/657) holds the implementation scope, upstream references, acceptance criteria, and verification matrix.

## Why it belongs in the register

GEOM-1 audits whether the planar exclusions in `scripts/hex_utils.py::Hex.lies_in_cell` omit a required packaged-data candidate and establishes the conservative repair scope. The preferred long-term authority is H3 itself: geodesic `OVERLAPPING` can decide which polygons remain candidates, and geodesic `FULL` can support PERF-7 without timezonefinder maintaining a second model of H3 cell geometry.

Released H3 4.x exposes experimental modes with those names, but their implementation remains planar. [uber/h3#1052](https://github.com/uber/h3/pull/1052) adds the distinct great-circle containment and intersection paths this item requires; [uber/h3#775](https://github.com/uber/h3/issues/775) is the originating containment-mode request. Do not treat the released mode names or an unmerged upstream branch as the dependency being available.

- **Size:** M — adopt the released API, raise and validate the dependency floor, replace or validate candidate generation, regenerate the index, and verify all geometry/backend/data-release gates named on the issue.
- **Status:** blocked on merge and release of uber/h3#1052, and sequenced after GEOM-1 establishes the production repair scope.
