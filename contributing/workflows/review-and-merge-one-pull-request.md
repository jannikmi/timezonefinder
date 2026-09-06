# Review and merge one pull request

Drain the open pull-request queue, keeping the maintainer in the loop for the judgements that are theirs and out of it for the ones that are not. One round is: survey, order, pick, update, judge, then merge or hand over with a brief. A run is rounds until the queue is empty, each starting from a fresh survey: an ordering computed one round ago is evidence about that round only, and a merge can make a pull request that was not eligible last round the obvious pick this one.

Read the [pull-request and CI workflow](../development/pull-request-and-ci-workflow.md) and the [testing strategy](../development/testing-strategy-and-change-scope.md), which decides what a merged change still has to be gated on.

## Hard boundaries

- Merging is the one step this workflow cannot take back cheaply. The default is to merge; the three triggers below buy a maintainer's reading, and everything they catch waits for an answer in the same session.
- Never merge a release pull request, push a tag, publish a distribution, or push to `master`. The [release workflow](prepare-and-publish-code-release.md) owns those and requires its own authorization.
- Never force-push. `master` refuses them and a sandbox may deny them outright; bring a head branch up to date by merging the base into it, which the squash merge flattens anyway.
- Never fix substance during a round. Conflict resolution, a stale register reference, a malformed changelog fragment, and a contributor-memory file over its word budget are in scope — for the last, cut only restatement the file makes elsewhere, never a rule; a behavioural change, a new test for a gap the review found, or a redesign is a register item and a separate pass.
- Never read a thin check list as success: the one aggregate check branch protection requires reports only on the jobs it aggregates, so a job outside its `needs` list, or one a `paths:` filter skipped, is silence rather than a pass.

## Survey, every round

```bash
git fetch --prune origin
gh pr list --state open --json number,title,headRefName,isDraft,mergeable,mergeStateStatus,reviewDecision,updatedAt,files
git ls-remote origin 'refs/heads/improvement-claims/*'
```

Say what moved since the previous round: pull requests opened or closed, heads pushed, and whether `origin/master` advanced. GitHub recomputes mergeability lazily, so `UNKNOWN` means ask again rather than assume the previous answer. A claim ref with no pull request yet is work in flight against the same register item, and merging a register change can strand it.

## Order the queue

Apply in order, and take the first pull request that discriminates:

1. **Publishing order wins.** A release pull request merges last, after everything intended for that version, because every later merge invalidates the changelog and reports it froze. A data-distribution change ships before the code that requires it.
2. **Blockers before dependents.** A pull request another is based on, or sequenced after, goes first; otherwise the dependent's diff cannot be read for what it adds.
3. **Bottleneck before satellites.** Among ready candidates, prefer the one whose runtime, script, and test files the most other open pull requests also touch: everyone pays that rebase either way, and paying it against a merged base is cheaper. Weight overlap in code and tests; shared edits to the ranking table are mechanical and barely count.
4. **Perishable evidence first.** Committed measurements, data markers, and CI-workflow changes rot: their numbers describe an ageing tree and their conflicts are regenerate-only.
5. **Then cheap and green**, to shrink the queue without spending maintainer attention.
6. **Tie-breaks:** smaller diff, then the older pull request, which has already been rebased the most times.

Park, but never let block: a pull request that needs a maintainer decision, a draft, one whose checks are red for a reason outside this round's scope, one with unresolved review threads, and one from a fork whose head you cannot push to. A missing independent review does not park anything — see below. Announce the pick with one clause per waiting pull request saying why it waits — the ordering is the cheapest thing for the maintainer to overrule.

## Bring it up to date

Follow the [branch-update rules](../development/branch-updates-and-conflict-resolution.md): `gh pr update-branch <n>` for a clean update, a dedicated worktree and `git merge origin/master` for a conflict, and the resolutions for ranking rows, decision files, changelog fragments, generated artifacts, and the semantic conflicts git cannot see. A worktree already holding the head branch is another session's: work detached and push to the branch.

## Judge it

The default is to merge. A change escalates because a listed trigger fires, not because it touched an important file: a behaviour-preserving refactor of the query path, matrix green, merges unread, and a revert costs one command. Doubt about *whether a trigger fired* escalates; doubt about whether the maintainer would have made the same call does not.

| Touched | Read it for | Escalates when |
|---|---|---|
| Query path — `timezonefinder.py`, `utils*.py`, `polygon_array.py`, `coord_accessors.py`, `shortcut_index.py`, `_block_index.py` | correctness at borders, parity across the numba, clang, and pure-Python backends, behaviour under the memory-mapped mode | an answer, an error, or a backend's behaviour changes; a rename, an extraction, or a dead-branch removal does not |
| `global_functions.py`, `command_line.py`, exported names | the [compatibility contract](../project/public-api-and-compatibility-contract.md) | always — an exported name, signature, or documented semantic is a promise |
| Binary format, `DATA_VERSION`, `DATA_BUILD_RUN`, `packages/timezonefinder-data`, `scripts/file_converter.py` | the [ordered two-distribution release](../development/data-pipeline-format-versioning-and-release-order.md) it commits the next release to | always — the next release inherits the ordering, and a published distribution cannot be recalled |
| `.github/workflows/`, release targets in the `Makefile`, `pyproject.toml`, `uv.lock` | what publishes, what every install inherits, which job is load-bearing for the trusted publisher | publishing, permissions, secrets, or shipped dependency metadata change; a lock refresh or a CI-internal step does not |
| `docs/benchmark_results_*.rst`, `docs/data_report.rst`, tracked benchmark JSON | the machine, the backend, and the noise floor behind the numbers | a performance claim rests on them; a regeneration that only restates the current tree does not |
| `contributing/`, provider adapters, `changelog.d/`, prose documentation, tests | invariants and links only | never, once the structural tests pass |

### Review what nothing else reviewed

An absent independent review is work for this round, not a reason to park. Silence includes a review that stopped on a provider usage limit and one whose commit predates the head: a body claiming a review names the commit it covered, so compare that against `headRefOid` and read what landed after it.

Review against the tree, never against the body — a body is the one part of a pull request nothing else verifies. Check each factual claim at the symbol it names: a kernel property in the kernel, a dtype in the packaged file, a byte-identical artifact by regenerating it. A correctness finding parks the pull request and becomes a register item; finding nothing is a merge.

Brief what a diff does not show, whether the outcome is a merge or a question:

- **Claim against evidence.** What the body claims, what was measured, on which machine and backend, and which claims were only argued — including the side that was traded away, per the [trade-off rules](../development/trade-off-surfacing-and-validation.md).
- **The two or three hunks to read**, named by file and symbol, each with the question it answers.
- **What merging makes true** for the next release, the next data publish, and the other open pull requests.
- **Reversibility.** What reverting the squash commit restores, and what it cannot: anything published, fetched upstream, or already built on.
- **What CI covered and what it structurally cannot** — one interpreter and backend per job, and jobs a `paths:` filter skipped.
- **Decisions the pull request embedded** that meet the maintainer bar, and a recommendation with the one fact that would change it.

## Merge

Merge without asking unless one of three triggers fires.

1. **It is observable.** A user can see the difference: an exported name, signature, or documented semantic; a lookup answer, an error, or CLI output; dependency metadata or supported interpreters that every install inherits.
2. **It escapes the repository.** Reverting the squash commit is not the whole undo: a release or tag, a data-distribution version or format marker, an upstream fetch, a workflow's permissions or secrets, a history rewrite, or work another merged pull request already builds on.
3. **It is opinionated.** Reasonable maintainers would differ and everything after it pays: a layout move, a mass rename or formatting sweep, a new dependency or tool, an expanded lint rule set, a new abstraction or architectural seam, a change embedding a question at the maintainer bar, or one contradicting a [recorded decision](../improvements/improvement-register-rules.md).

Regardless of triggers, never merge on incomplete evidence: every check the workflows should have produced for this head exists and passed, the gate and the review both ran after the last update, and no review thread is open. A review covers a commit, not a pull request: one whose fixes postdate every review of it has had its riskiest code read by nobody.

Verify the checks against the head, not against the pull request:

```bash
gh pr view <n> --json headRefOid --jq .headRefOid
gh api repos/<owner>/<repo>/commits/<sha>/check-runs --jq '.check_runs[] | "\(.name) \(.conclusion)"'
```

Compare those names with the workflows that trigger on `pull_request` and the `paths:` filters that legitimately skip some. A healthy list carries the pre-commit job, the four-interpreter tox matrix, the end-to-end jobs, and the wheel and sdist builds; a list without the matrix never ran. Then:

```bash
gh pr merge <n> --squash --delete-branch
```

An escalated pull request is briefed and merged only on an answer in the same session; use the provider's structured question interface for that one question when it has one, recommendation first. Report every unasked merge by number and squash commit, which is what a maintainer who disagrees reverts from.

Branch protection requires an up-to-date head, so every merge puts the rest of the queue `BEHIND` and each update re-runs a full matrix. Update and merge one pull request at a time; updating the whole queue after a merge spends that matrix on all of them for nothing.

Once per run, before reporting, collect the finished refs the round leaves behind, per the [branch-update rules](../development/branch-updates-and-conflict-resolution.md).

After merging, fast-forward `master`, confirm the head is the squash commit, and re-check every remaining pull request: `--delete-branch` closes any based on that branch.

## Triage-only mode

For `triage`, `status`, `what is next`, or `why is this stuck`, survey, order, and brief only. Create no worktree, resolve no conflict, clean up nothing, push nothing, and merge nothing.

## When the run ends

The run ends when no open pull request is left, or when every one that remains is waiting on somebody else. Waiting is not a round — never poll an unanswered question in a loop. Say what each remaining pull request is waiting for and what would restart it, and stop. A round that merges nothing and changes nothing about the queue is also the end: repeating the survey cannot produce a different answer until something outside the run moves.

## Reporting

Per round: the pick and one clause for each pull request that waited; what the update did and which conflicts were resolved how; the review this round performed and what it found; the gate that ran and its result; merged, briefed, or parked, with the reason. Close the run with the pull requests merged in order, each with its squash commit, the refs cleaned up, what remains open and what each waits for, and the pick the next run would start from.
