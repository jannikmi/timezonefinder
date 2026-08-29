# GH-505 — distance to the nearest timezone border


## Related memory

- [Public API and runtime-loading decisions](../../decisions/public-api-compatibility-and-runtime-loading-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Tracks:** issue #505, a demand-signal issue.
- **Signal check, 2026-08-20: none.** Zero reactions and zero third-party comments; the only comment
  is the maintainer's own note that a `closest_timezone_at` existed historically and the history is
  worth scanning first. Re-checking costs one `gh issue view 505` and is the whole of what a pass
  should do here.
- **Status:** conditional on publicly voiced user interest — **never implement it unprompted**; only
  report whether interest has appeared. It is an L-sized permanent maintenance surface justified by
  a hypothesis about who wants it, so the demand signal comes first.
- **Last touched:** 2026-08-20 — signal checked and recorded, so the next pass can see when it was
  last looked at rather than re-deciding whether to look.
