# Pull-request and CI workflow

## Pull Request Checklist

- [ ] Branch is cut from `master`, rebased on the latest `master`, and its commit history is clean.
- [ ] Code follows the standards above, with type hints, performance considerations, and Pythonic structure.
- [ ] Tests are updated/added and pass (`pytest`, and `integration`/`tox` where relevant).
- [ ] Documentation and changelog entries reflect the change, including the pages that paraphrase a file you touched (see the table under *Documentation & Communication*).
- [ ] Binary data or configuration changes are justified and the regeneration process is documented in the PR description.

## Claims in a body or a commit message

A pull request body and a commit message are read as evidence, so state an empirical claim only where it was measured, and say so where it was not. A `--no-verify` commit here was justified with "`check-manifest` takes minutes"; it runs in about two seconds warm, and the real reason was narrower — the hook compares version control against a built sdist, so splitting a batch into per-item commits trips it on the other item's unstaged `tests/` file. A wrong reason costs more than a missing one, because it retires the question: the next reader inherits it as a fact rather than checking it. Name the number you observed and the machine you observed it on, and mark what you argued rather than measured, per the [trade-off rules](trade-off-surfacing-and-validation.md).

Say when a change was made because the maintainer asked for it, in the commit that makes it. Their feedback arrives in conversation and leaves no trace on the pull request, so a later reading of the history cannot tell a correction that was requested from one the author chose - and an intervention nobody recorded cannot be counted, learned from, or checked against what it was supposed to fix.

## Base every branch on `master`

Never open a pull request against another open pull request's branch, even when the work genuinely builds on it. Merges here are squashes and `--delete-branch` removes the head, which closes anything based on it — attributed to the merging maintainer, so it reads as a rejection — and leaves the stacked work needing a rebase onto `master` regardless, since the base's commits never become ancestors of it. The [merge round](../workflows/review-and-merge-one-pull-request.md) takes one pull request at a time in any case, so stacking buys no parallelism and costs a recovery.

Wait for the base to land and cut from `master`. When that is genuinely impractical, say in the description that the branch carries another pull request's commits and which ones, so a reviewer reads the right diff and knows the rebase is coming.

Thank you for helping to keep timezonefinder robust and high-performance!
