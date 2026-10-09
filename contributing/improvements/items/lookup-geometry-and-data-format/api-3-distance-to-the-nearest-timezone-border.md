# API-3 — distance to the nearest timezone border


## Related memory

- [Public API and runtime-loading decisions](../../decisions/public-api-compatibility-and-runtime-loading-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Tracks:** [discussion #671](https://github.com/jannikmi/timezonefinder/discussions/671), a demand-signal poll. It began as issue #505, which the maintainer converted into the discussion on 2026-09-12; the conversion closed and locked the issue, which is why this entry no longer carries a `GH-` id — that prefix makes a closed issue read as resolved, and this item is still live.
- **Signal check, 2026-08-20: none.** Zero reactions and zero third-party comments; the only comment is the maintainer's own note that a `closest_timezone_at` existed historically and the history is worth scanning first. Re-checking costs one look at discussion #671 (`gh api repos/jannikmi/timezonefinder/discussions/671` and its comments) and is the whole of what a pass should do here.
- **Status:** conditional on publicly voiced user interest — **never implement it unprompted**; only report whether interest has appeared. It is an L-sized permanent maintenance surface justified by a hypothesis about who wants it, so the demand signal comes first.
- **Last touched:** 2026-10-09 — re-keyed from GH-505 to API-3 to track the discussion the issue became; the 2026-08-20 signal check above is still the latest.
