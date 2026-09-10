# GH-657 — adopt H3 geodesic polygon coverage for shortcuts

[Issue #657](https://github.com/jannikmi/timezonefinder/issues/657) holds the implementation scope, upstream references, acceptance criteria, and verification matrix.

## Why it belongs in the register

GEOM-3 establishes a conservative repair for exclusions in `scripts/hex_utils.py`. The preferred long-term cell authority is H3 itself, but its geodesic modes also reinterpret source polygon edges. The [isolated evaluation](../../decisions/shortcut-candidate-audit-and-geometry-authority.md#upstream-authority-evaluation) demonstrates that direct adoption excludes valid planar-source points. Establish a conservative treatment of the original source geometry before using geodesic `OVERLAPPING` for candidate exclusion or `FULL` for PERF-7.

Released H3 4.5.0 exposes experimental modes with those names, but their implementation remains planar. [uber/h3#1178](https://github.com/uber/h3/pull/1178) replaces the closed, unmerged #1052 with distinct great-circle containment and intersection paths; [uber/h3#775](https://github.com/uber/h3/issues/775) is the originating containment-mode request. Do not treat the released mode names or an unmerged upstream branch as the dependency being available.

- **Size:** M — adopt the released API, raise and validate the dependency floor, replace or validate candidate generation, regenerate the index, and verify all geometry/backend/data-release gates named on the issue.
- **Status:** blocked on merge and release of uber/h3#1178, and sequenced after GEOM-3 establishes a conservative treatment of planar source edges.
