# GH-522 — shrink the repository history by dropping the committed coordinate binaries


## Related memory

- [Data distribution, packaging, and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Tracks:** issue #522.
- **What it would reclaim:** of 571.4 MiB of unique blobs across all history, the coordinate binaries are 543.8 MiB (**95 %**) across 46 distinct blobs. The pack is ~357 MiB; dropping them takes the repository to single-digit MiB. Everything else under the data directory totals 1.79 MB and is not worth rewriting history over.
- **What it costs:** `git filter-repo` rewrites every commit SHA — every existing clone and fork is detached, all tags are rewritten and any signatures on them invalidated, links to commit SHAs from issues, changelogs and external references break, **including this register's own** — the measurement baseline's `590e21b` anchor is the load-bearing one, since a pass diffs against it to decide whether the timings still describe the tree, so re-anchoring it belongs in this item's own checklist rather than being discovered afterwards, and it is a force-push over `master` and every tag. None of that is recoverable by halves, so it is worth doing exactly once.
- **Maintainer decision, 2026-09-02:** park the rewrite until repository size causes a concrete operational problem worth invalidating commit and tag identities. The precondition being clear and the space being reclaimable are not sufficient reasons by themselves. Resume only against that observed need; refused: rewriting preemptively merely because nothing would re-add the binaries now.
- **Status:** parked — until there is a concrete need to shrink the repository history.
- **Last touched:** 2026-09-02 — parked by maintainer decision. Previously, on 2026-08-31, the precondition cleared when the packaged binaries stopped being committed and format branches gained `compile_data.yml`, so the 46 coordinate blobs became history and nothing adds a 47th.
