# GH-522 — shrink the repository history by dropping the committed coordinate binaries


## Related memory

- [Data distribution, packaging, and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
- **Tracks:** issue #522.
- **What it would reclaim:** of 571.4 MiB of unique blobs across all history, the coordinate binaries are 543.8 MiB (**95 %**) across 46 distinct blobs. The pack is ~357 MiB; dropping them takes the repository to single-digit MiB. Everything else under the data directory totals 1.79 MB and is not worth rewriting history over.
- **What it costs:** `git filter-repo` rewrites every commit SHA — every existing clone and fork is detached, all tags are rewritten and any signatures on them invalidated, links to commit SHAs from issues, changelogs and external references break, **including this register's own** — the measurement baseline's `590e21b` anchor is the load-bearing one, since a pass diffs against it to decide whether the timings still describe the tree, so re-anchoring it belongs in this item's own checklist rather than being discovered afterwards, and it is a force-push over `master` and every tag. None of that is recoverable by halves, so it is worth doing exactly once.
- **Status:** open — the precondition cleared on 2026-08-31: the data directory is git-ignored, so a rewrite is no longer undone by the next data update.
- **Last touched:** 2026-08-31 — unblocked when the packaged binaries stopped being committed. One consequence of that change belongs in this item's checklist: the 46 coordinate blobs are all history now, and the only way a new one appears is a branch that deliberately `git add -f`s a regeneration it has no published release to fetch (see the [data-pipeline rules](../../../development/data-pipeline-format-versioning-and-release-order.md)) — so run the rewrite when no such branch is unmerged, or its blob survives it. Earlier: migrated from the roadmap issue on 2026-08-20.
