# Pull-request and CI workflow

## Pull Request Checklist

- [ ] Branch is rebased on the latest `master` and commit history is clean.
- [ ] Code follows the standards above, with type hints, performance considerations, and Pythonic structure.
- [ ] Tests are updated/added and pass (`pytest`, and `integration`/`tox` where relevant).
- [ ] Documentation and changelog entries reflect the change, including the pages that paraphrase a file you touched (see the table under *Documentation & Communication*).
- [ ] Binary data or configuration changes are justified and the regeneration process is documented in the PR description.

## Claims in a body or a commit message

A pull request body and a commit message are read as evidence, so state an empirical claim only where it was measured, and say so where it was not. A `--no-verify` commit here was justified with "`check-manifest` takes minutes"; it runs in about two seconds warm, and the real reason was narrower — the hook compares version control against a built sdist, so splitting a batch into per-item commits trips it on the other item's unstaged `tests/` file. A wrong reason costs more than a missing one, because it retires the question: the next reader inherits it as a fact rather than checking it. Name the number you observed and the machine you observed it on, and mark what you argued rather than measured, per the [trade-off rules](trade-off-surfacing-and-validation.md).

Say when a change was made because the maintainer asked for it, in the commit that makes it. Their feedback arrives in conversation and leaves no trace on the pull request, so a later reading of the history cannot tell a correction that was requested from one the author chose - and an intervention nobody recorded cannot be counted, learned from, or checked against what it was supposed to fix.

Thank you for helping to keep timezonefinder robust and high-performance!
