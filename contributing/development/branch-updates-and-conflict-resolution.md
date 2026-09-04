# Branch updates and conflict resolution

Bringing a branch onto current `master`, and resolving what that produces. Applies wherever a branch is updated — before an improvement pass's final gate, and in the [merge round](../workflows/review-and-merge-one-pull-request.md).

For a clean update, `gh pr update-branch <n>` merges the base in server-side, with no checkout and no force push. For a conflict, work in a dedicated worktree on the head branch, `git merge origin/master`, resolve, and push — a fast-forward, so no force push arises.

- **Ranking table and item files.** Both sides delete what they shipped, so the union of the deletions is the resolution. Never resurrect a row or item file the other side removed, grep the id across `contributing/improvements/` afterwards, and re-run the ledger and contributor-memory tests, which is what catches a row without an entry.
- **Recorded decisions.** Two branches editing different bullets of one decision file merge cleanly and leave it over its word budget, so check the count rather than the conflict markers. Where both edited the same bullet, the later measurement wins the claim and the earlier one stays as its dated evidence, per the [register rules](../improvements/improvement-register-rules.md).
- **Changelog fragments.** One file per change means they cannot conflict; a conflict there is a change that edited `CHANGELOG.rst` directly, against the [changelog policy](changelog-and-release-note-policy.md).
- **Generated and measured files.** Regenerate through the [generator that owns them](generated-file-regeneration-rules.md), or take the base and let the pull request that owns the artifact regenerate it. A hand-merged report is a number nobody measured.
- **Semantic conflicts git cannot see.** Two branches that each pass alone can fail together: a symbol one renamed and the other calls, a fixture both add, a constant that moved, a new `scripts/` command an exhaustiveness table on the base does not list. After every update, run the gate the merged-in change selects, not the one this branch selected when it was opened, and re-read the diff of the merge itself rather than only the resolved files.
