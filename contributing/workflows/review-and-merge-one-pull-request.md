# Review and merge one pull request

Drain the open pull-request queue, keeping the maintainer in the loop for the judgements that are theirs and out of it for the ones that are not. One round is: survey, order the queue, pick the next pull request, bring it up to date, judge it, then merge it or hand it over with a brief. A run is rounds until the queue is empty, each starting from a fresh survey — pull requests are opened, pushed to, reviewed, and closed while a round runs, so an ordering computed one round ago is evidence about that round only, and a merge can make a pull request that was not eligible last round the obvious pick this one.

Read the [pull-request and CI workflow](../development/pull-request-and-ci-workflow.md) and the [testing strategy](../development/testing-strategy-and-change-scope.md), which decides what a merged change still has to be gated on.

## Hard boundaries

- Merging is the one step this workflow cannot take back cheaply. The default is to merge; the three triggers below are what buys a maintainer's reading, and everything they catch waits for an answer in the same session.
- Never merge a release pull request, push a tag, publish a distribution, or push to `master`. The [release workflow](prepare-and-publish-code-release.md) owns those and requires its own authorization.
- Never force-push. `master` refuses force pushes and a sandbox may deny them outright; bring a head branch up to date by merging the base into it, which the squash merge flattens anyway.
- Never fix substance during a round. Conflict resolution, a stale register reference, and a malformed changelog fragment are in scope; a behavioural change, a new test for a gap the review found, or a redesign is a register item and a separate pass.
- Never read a thin check list as success. Branch protection requires one aggregate check, which reports only on the jobs it aggregates: a job outside its `needs` list, or a workflow a `paths:` filter skipped, is silence rather than a pass.

## Survey, every round

```bash
git fetch --prune origin
gh pr list --state open --json number,title,headRefName,isDraft,mergeable,mergeStateStatus,reviewDecision,updatedAt,files
git ls-remote origin 'refs/heads/improvement-claims/*'
```

Say what moved since the previous round: pull requests opened or closed, heads pushed, and whether `origin/master` advanced. A merge last round restates every remaining pull request's mergeability; GitHub recomputes it lazily, so `UNKNOWN` means ask again rather than assume the previous answer. A claim ref with no pull request yet is work in flight against the same register item, and merging a register change can strand it.

## Order the queue

Apply in order, and take the first pull request that discriminates:

1. **Publishing order wins.** A release pull request merges last, after everything intended for that version, because every later merge invalidates the changelog and reports it froze. A data-distribution change ships before the code that requires it.
2. **Blockers before dependents.** A pull request another open one is based on, or is sequenced after, goes first; otherwise the dependent's diff cannot be read for what it actually adds.
3. **Bottleneck before satellites.** Among ready candidates, prefer the one whose runtime, script, and test files the most other open pull requests also touch. Everyone pays that rebase either way, and paying it against a merged base is cheaper than against a moving one. Weight overlap in code and tests; shared edits to the ranking table are mechanical and barely count.
4. **Perishable evidence first.** Committed measurements, data markers, and CI-workflow changes rot: their numbers describe a tree that is ageing and their conflicts are regenerate-only.
5. **Then cheap and green**, to shrink the queue without spending maintainer attention.
6. **Tie-breaks:** smaller diff, then the older pull request, which has already been rebased the most times.

Park, but never let block: a pull request that needs a maintainer decision, a draft, one whose checks are red or absent, one with unresolved review threads, and one from a fork whose head you cannot push to. Announce the pick with one clause per waiting pull request saying why it waits — the ordering is the cheapest thing for the maintainer to overrule.

## Bring it up to date

For a clean update, `gh pr update-branch <n>` merges the base in server-side, with no checkout and no force push. For a conflict, work in a dedicated worktree on the head branch, `git merge origin/master`, resolve, and push — a fast-forward, so no force push arises.

- **Ranking table and item files.** Both sides delete what they shipped, so the union of the deletions is the resolution. Never resurrect a row or item file the other side removed, grep the id across `contributing/improvements/` afterwards, and re-run the ledger and contributor-memory tests, which is what catches a row without an entry.
- **Changelog fragments.** One file per change means they cannot conflict; a conflict there is a change that edited `CHANGELOG.rst` directly, against the [changelog policy](../development/changelog-and-release-note-policy.md).
- **Generated and measured files.** Regenerate through the [generator that owns them](../development/generated-file-regeneration-rules.md), or take the base and let the pull request that owns the artifact regenerate it. A hand-merged report is a number nobody measured.
- **Semantic conflicts git cannot see.** Two branches that each pass alone can fail together: a symbol one renamed and the other calls, a fixture both add, a constant that moved. After every update, run the gate the merged-in change selects, not the one this branch selected when it was opened, and re-read the diff of the merge itself rather than only the resolved files.

## Judge it

The default is to merge. A change is escalated because a listed trigger below fires, not because it touched an important file: a behaviour-preserving refactor of the query path, with the matrix green, is merged without a maintainer reading it, and if the maintainer would have written it differently the revert costs one command. Doubt about *whether a trigger fired* escalates; doubt about whether the maintainer would have made the same call does not.

| Touched | Read it for | Escalates when |
|---|---|---|
| Query path — `timezonefinder.py`, `utils*.py`, `polygon_array.py`, `coord_accessors.py`, `shortcut_index.py`, `_block_index.py` | correctness at borders, parity across the numba, clang, and pure-Python backends, behaviour under the memory-mapped mode | an answer, an error, or a backend's behaviour changes; a rename, an extraction, or a dead-branch removal does not |
| `global_functions.py`, `command_line.py`, exported names | the [compatibility contract](../project/public-api-and-compatibility-contract.md) | always — an exported name, signature, or documented semantic is a promise |
| Binary format, `DATA_VERSION`, `DATA_BUILD_RUN`, `packages/timezonefinder-data`, `scripts/file_converter.py` | the [ordered two-distribution release](../development/data-pipeline-format-versioning-and-release-order.md) it commits the next release to | always — the next release inherits the ordering, and a published distribution cannot be recalled |
| `.github/workflows/`, release targets in the `Makefile`, `pyproject.toml`, `uv.lock` | what publishes, what every install inherits, which job is load-bearing for the trusted publisher | publishing, permissions, secrets, or shipped dependency metadata change; a lock refresh or a CI-internal step does not |
| `docs/benchmark_results_*.rst`, `docs/data_report.rst`, tracked benchmark JSON | the machine, the backend, and the noise floor behind the numbers | a performance claim rests on them; a regeneration that only restates the current tree does not |
| `contributing/`, provider adapters, `changelog.d/`, prose documentation, tests | invariants and links only | never, once the structural tests pass |

Brief what a diff does not show, whether the outcome is a merge or a question:

- **Claim against evidence.** What the body claims, what was measured, on which machine and backend, and which claims were only argued — including the side that was traded away, per the [trade-off rules](../development/trade-off-surfacing-and-validation.md).
- **The two or three hunks to read**, named by file and symbol, each with the question it answers.
- **What merging makes true** for the next release, the next data publish, and the other open pull requests.
- **Reversibility.** What reverting the squash commit restores, and what it cannot: anything published, fetched from upstream, or already built on.
- **What CI covered and what it structurally cannot** — one interpreter and one backend per job, and jobs skipped by a `paths:` filter.
- **Decisions the pull request embedded** that meet the maintainer bar, and a recommendation with the one fact that would change it.

## Merge

Merge without asking unless one of three triggers fires.

1. **It is observable.** A user can see the difference: an exported name, signature, or documented semantic; a lookup answer, an error, or CLI output; dependency metadata or supported interpreters that every install inherits.
2. **It escapes the repository.** Reverting the squash commit is not the whole undo: a release or tag, a data-distribution version or format marker, an upstream fetch, a workflow's permissions or secrets, a history rewrite, or work another merged pull request already builds on.
3. **It is opinionated.** Reasonable maintainers would differ and everything after it pays: a layout move, a mass rename or formatting sweep, a new dependency or tool, an expanded lint rule set, a new abstraction or architectural seam, a change embedding a question at the maintainer bar, or one contradicting a [recorded decision](../improvements/improvement-register-rules.md).

Regardless of triggers, never merge on incomplete evidence: every check the workflows should have produced for this head exists and passed, the gate ran after the last update rather than before it, and no review thread is open.

Verify the checks against the head, not against the pull request:

```bash
gh pr view <n> --json headRefOid --jq .headRefOid
gh api repos/<owner>/<repo>/commits/<sha>/check-runs --jq '.check_runs[] | "\(.name) \(.conclusion)"'
```

Compare those names with the workflows that trigger on `pull_request` and the `paths:` filters that legitimately skip some. A healthy list carries the pre-commit job, the four-interpreter tox matrix, the end-to-end jobs, and the wheel and sdist builds; a list without the matrix is a run that never happened. Then:

```bash
gh pr merge <n> --squash --delete-branch
```

An escalated pull request is briefed and merged only on an answer in the same session; use the provider's structured question interface for that one question when it has one, recommendation first. Report every unasked merge by number and squash commit; a merge the maintainer disagrees with is reverted from that, and spelling out the command for a case this rare costs a line in every report to save a lookup in almost none.

After merging, fast-forward local `master`, confirm the head is the squash commit, and re-check every remaining pull request before the next round begins.

## Triage-only mode

For `triage`, `status`, `what is next`, or `why is this stuck`, survey, order, and brief only. Create no worktree, resolve no conflict, push nothing, and merge nothing.

## When the run ends

The run ends when no open pull request is left, or when every one that remains is waiting on somebody else: an unanswered brief, a red or missing check list, an unresolved review thread, a blocked or draft pull request, or a release the maintainer has not authorized. Waiting is not a round — do not poll a running matrix or an unanswered question in a loop. Say what each remaining pull request is waiting for and what would restart it, and stop. A round that merges nothing and changes nothing about the queue is also the end: repeating the survey cannot produce a different answer until something outside the run moves.

## Reporting

Per round: the pick and one clause for each pull request that waited; what the update did and which conflicts were resolved how; the gate that ran and its result; merged, briefed, or parked, with the reason; and what changed for the rest of the queue. Close the run with the pull requests merged in order, each with its squash commit, what remains open and what each one waits for, and the pick the next run would start from.
