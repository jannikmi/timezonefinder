# Claim an improvement item and isolate its work

How one pass takes exclusive ownership of an item and sets up the tree it works in. Read it from the [improvement-pass workflow](run-one-improvement-pass.md), which owns everything else about a pass; the claim protocol lives here because concurrent passes share one checkout and one remote, and a claim that is not verified is not a claim.

Preserve the shared checkout. Survey first:

```bash
git fetch --prune origin
git branch -r
gh pr list --state open
```

Claim one item at a time — never a batch, never ahead of need, and never while another item is being worked on, which blocks a concurrent pass for no reason. Claim through the item's canonical remote ref, `refs/heads/improvement-claims/<ITEM-ID>`:

1. Create one unique claim commit on the `origin/master` tree and parent, without adding it to the implementation branch. Its message records the claimed item ID, a unique run token, the planned feature branch, the base commit, and the creation time. Never point a claim ref straight at `origin/master`: concurrent pushes of one commit can both report success.
2. Push the claim ref with `git push --atomic`, guarding it with `--force-with-lease=<claim-ref>:` so it succeeds only when the ref is absent. A rejected push acquires nothing: fetch again, inspect the winning claim and concurrent work, then re-rank rather than retrying blindly.
3. Fetch the ref immediately afterwards and verify it points at this run's claim commit. Until that succeeds nothing is claimed and no implementation may begin.

A refinement claims the oversized item's ID before it starts. Once the slices are recorded, claim the first slice's new ID the same way; the original ID's claim is released with the refinement's pull request, alongside the item it retires.

Never overwrite or steal a claim that still protects work. A claim protects work while its item is still in the register and the branch its claim commit names carries no pull request: a run may be implementing it right now, so treat it as blocking, report its recorded metadata, and continue down the ranking; a maintainer may remove it once confirmed orphaned. **Any other claim may be deleted, by any pass, whichever run made it:** one whose item has left the register, and one whose named branch has a pull request, open, merged or closed - an open one is already the durable claim, and the others leave nothing to protect. Inspect it first, delete it with a force-with-lease expecting the commit you inspected, and report each deletion with the claim's recorded metadata. What this stops examining is whether the run that made such a claim is still at work; nothing it could still be doing rests on the ref, because a claim covers one item up to its open pull request.

After ownership is verified, create a uniquely named worktree and, inside it, a feature branch named after the item ID and started from a recorded `origin/master` commit. A later item in the same session reuses the worktree but branches from `origin/master` afresh: never stack one item's branch on another's, because `master` squash-merges and deleting a merged base branch closes the pull request built on it. Push the branch as its work begins, so the work behind the claim is inspectable. Do not base a pass on another open pull request merely to absorb its contributor-memory edits; an item that truly depends on unmerged work is ineligible until that lands. Then install and record untouched `make test` and `make hook` baselines, which the session shares. Do not widen an item after implementation begins: finish what is claimed, and leave anything discovered beside it to the register.

Keep the claim until its pull request is open and visible, then delete this run's ref, guarding the deletion with a force-with-lease expecting this run's claim commit; the open pull request becomes the durable claim. Release claims the same way when abandoning or yielding work. If verification fails and findings are pushed without a pull request, retain the claims so another pass resumes rather than races that branch. Stage explicit paths, never `git add -A`.
