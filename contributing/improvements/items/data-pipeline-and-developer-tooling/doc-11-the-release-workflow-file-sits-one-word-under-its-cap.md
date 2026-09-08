# DOC-11 — the release workflow file sits one word under its cap


## Related memory

- [Core contributor contract](../../../core-contributor-contract.md) — the split guidance this item exists to finish: condense first, then move one bounded section out whole and diff it against the original.
- [Code-release workflow](../../../workflows/prepare-and-publish-code-release.md) — the file itself.
- [Publish the data distribution](../../../workflows/publish-the-data-distribution.md) — the section #645 already moved out.
- **Defect (a booby trap for the next author, not a wrong rule):** `contributing/workflows/prepare-and-publish-code-release.md` is **1,999 words** against the 2,000-word `CANONICAL_LIMIT` that `tests/test_contributor_memory.py::test_memory_names_depth_and_size_budgets` enforces over every file under `contributing/`. One word of headroom means the next change to that file fails the matrix for a reason that has nothing to do with it, and hands its author an unplanned split.
- **Observed, 2026-09-08, merging #645.** That branch found the file at 1,943 words, took it to 2,326 by writing the data publish inline, and split 528 words out into `publish-the-data-distribution.md` — reaching 1,906 at commit `2ec01ee`. Two later commits then added the tag-verification and recovery text back, ending at 1,999. The pull-request body still claimed 1,906 and "below where this branch found it"; both were true when written and neither is true of what merged. The split was real and correct; it was simply spent.
- **Why it is worth a pass rather than a shave.** Trimming a few words back under the cap buys the same trap at a different number, and the core contract already forbids shaving load-bearing text to fit. The file is a canonical workflow at its budget: the resolution is to move one more bounded section out whole, the way the data publish went. *Prepare*'s changelog rewrite and the benchmark-report refresh are each self-contained enough to be one, and `tests/test_benchmark_workflows.py` already asserts the ordering of the latter, so a move has a check that it stayed intact.
- **Constraints on the move.** `CONTRIBUTING.md`'s release row already names the three files `test_routing_rows_require_at_most_three_files` allows, so a new file has to be reachable through the release workflow's own link rather than through a fourth entry in that row — which is what `test_every_canonical_file_is_reachable_from_entrypoint` checks.
- **Size:** S — one section moved verbatim, its link, and the word counts re-checked on both files.
- **Status:** open. Found in a merge round reviewing #645; the body's stale count is what surfaced it, and nothing was changed in that pull request.
