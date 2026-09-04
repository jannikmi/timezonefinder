# Pull-request and CI workflow

## Pull Request Checklist

- [ ] Branch is cut from `master`, rebased on the latest `master`, and its commit history is clean.
- [ ] Code follows the standards above, with type hints, performance considerations, and Pythonic structure.
- [ ] Tests are updated/added and pass (`pytest`, and `integration`/`tox` where relevant).
- [ ] Documentation and changelog entries reflect the change, including the pages that paraphrase a file you touched (see the table under *Documentation & Communication*).
- [ ] Binary data or configuration changes are justified and the regeneration process is documented in the PR description.

## Base every branch on `master`

Never open a pull request against another open pull request's branch, even when the work genuinely builds on it. Merges here are squashes and `--delete-branch` removes the head, which closes anything based on it — attributed to the merging maintainer, so it reads as a rejection — and leaves the stacked work needing a rebase onto `master` regardless, since the base's commits never become ancestors of it. The [merge round](../workflows/review-and-merge-one-pull-request.md) takes one pull request at a time in any case, so stacking buys no parallelism and costs a recovery.

Wait for the base to land and cut from `master`. When that is genuinely impractical, say in the description that the branch carries another pull request's commits and which ones, so a reviewer reads the right diff and knows the rebase is coming.

Thank you for helping to keep timezonefinder robust and high-performance!
