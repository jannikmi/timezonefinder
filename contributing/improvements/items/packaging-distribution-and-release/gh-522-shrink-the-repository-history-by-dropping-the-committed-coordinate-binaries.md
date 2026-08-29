# GH-522 — shrink the repository history by dropping the committed coordinate binaries


## Related memory

- [Data distribution, packaging, and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Tracks:** issue #522.
- **What it would reclaim:** of 571.4 MiB of unique blobs across all history, the coordinate binaries are 543.8 MiB (**95 %**) across 46 distinct blobs. The pack is ~357 MiB; dropping them takes the repository to single-digit MiB. Everything else under the data directory totals 1.79 MB and is not worth rewriting history over.
- **What it costs:** `git filter-repo` rewrites every commit SHA — every existing clone and fork is detached, all tags are rewritten and any signatures on them invalidated, links to commit SHAs from issues, changelogs and external references break, and it is a force-push over `master` and every tag. None of that is recoverable by halves, so it is worth doing exactly once.
- **Status:** blocked by DATA-BINARIES — see *Sequencing*.
- **Last touched:** 2026-08-20 — migrated from the roadmap issue.
