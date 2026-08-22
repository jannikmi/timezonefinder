---
name: cut-release
description: "Turns the accumulated `X.X.X (unreleased)` section of CHANGELOG.rst into a numbered release of timezonefinder: check the section is release-ready, derive patch/minor/major from the bullets and justify that level in the release PR - then land the version bump as that PR and, once the maintainer has merged it, push the tag that publishes to PyPI. One stop, the maintainer's: the tag. The bump level is decided by the skill and reviewed on the PR. Use this whenever the user asks to cut, prepare, trigger or ship a release, publish a new version, bump the version, release the unreleased changelog section, tag a release, or asks what the next version number would be and why - even if they never say the word skill. Data-only releases are published automatically by release_data_update.yml and do not go through here."
---

# Cut a release

Turn the accumulated `X.X.X (unreleased)` section of `CHANGELOG.rst` into a released version of
`timezonefinder` on PyPI.

The work splits at the maintainer's merge, so this skill has two halves and one invocation runs
exactly one of them (§1): **prepare** ends with a release PR, **tag** ends with a pushed tag.

## 0. This skill stops once. That stop is the point.

`.claude/skills/improvement-pass/SKILL.md` runs start to finish without asking at all, and hands the
choices it may not make to `.claude/skills/maintainer-decisions/SKILL.md`, which puts them to the
maintainer in a session they invoked. A release needs neither route: the bump level follows from
§4's table applied to bullets that are already written down, and it lands in a pull request the
maintainer reads before merging. Asking in chat put the same question to them twice, the first time
without the diff attached. §7's **Why this level** is where that judgement is now checked, which is
why it is mandatory and has a required shape.

What is not a judgement anyone reviews afterwards:

- **The tag is the publish.** Pushing it builds the wheels and uploads them, and PyPI refuses a
  re-upload of a version that already exists. A wrong tag is not fixed by deleting it. By then the
  PR review is over, and the tag can name a commit that PR never contained.

Do not "improve" this file by removing that stop, and do not restore the bump-level one - see
*Autonomy, and where it stops* at the end. Everything else here — worktree hygiene, the
verification gate, the PR body, the final report — follows the sibling skills and is not restated.

Hard gates, above everything else:

- **Never merge the release PR and never enable auto-merge.** A green check list can mean CI never
  ran. The maintainer merges — and since the level is no longer put to them in chat, that review is
  the only place a wrong one is caught.
- **Never tag without asking in the same session** (§8), never force-push or delete a tag, never
  upload to PyPI by hand. `build.yml` owns publishing.
- **Never run `make reports`, `make data`, `make benchmark-fixtures` or `update_data.sh` here.**
  They re-measure and rewrite four generated pages plus ~64 MB of binaries; a release commit
  contains the version bump and the changelog and nothing else.
- **Never invent or reword a changelog bullet into something it did not say.** §3 merges,
  compresses and reorders what is there. Adding a claim about behaviour nobody shipped puts a lie
  in the release notes.
- **The working tree is shared** with other agent sessions. Verify state on disk, stage explicit
  paths, never `git add -A`.

## 1. Which half you are in

`CLAUDE.md` is auto-loaded; read `CONTRIBUTING.md` too. Then:

```bash
git fetch origin --tags && uv version --short && sed -n '1,10p' CHANGELOG.rst && git tag --sort=-creatordate | head -3
```

| Top section of `CHANGELOG.rst` | pyproject version `V` | You are in |
|---|---|---|
| `X.X.X (unreleased)` | equals the newest tag | **prepare** — §2 |
| `V (YYYY-MM-DD)`, no tag `V` exists | not yet tagged | **tag** — §8 |
| `V (YYYY-MM-DD)`, tag `V` exists | released | nothing to do — report the run status (§9) and stop |

## 2. Prepare: preconditions

Each of these, with output you have read:

- [ ] `git status --short` clean, or the only changes are ones you can account for. Another session
      may be mid-edit — if so, stop; a release must describe a tree, not a moment in someone's edit.
- [ ] On `master`, and `git rev-parse HEAD origin/master` agrees. Branch from an up-to-date master
      or the release omits what landed since.
- [ ] `gh pr list --state open --search "release in:title"` and `git ls-remote --heads origin 'release/*'`
      are both empty. A release PR already open means another pass claimed this; add nothing.
- [ ] The unreleased section has at least one bullet. An empty one means there is nothing to
      release — say so and stop, rather than shipping a version whose notes are blank.
- [ ] `gh run list --branch master --limit 3` shows the latest master run green. Releasing off a red
      master publishes it.

## 3. Make the section describe the release, not its history

Apply `CLAUDE.md`'s changelog rules to the whole `X.X.X (unreleased)` section before anything else
— this is the last moment at which they are cheap, and after the tag the text is what users read:

- Merge bullets describing the same feature into one. Delivered-over-five-PRs must read as arrived
  once.
- Cut tuning history ("raised to X, then to Z"), superseded intermediate states, and self-review
  narration. State where the code landed.
- Keep the *why* only where it is decision-relevant to a user; contributor detail belongs in
  `CONTRIBUTING.md` or a docstring.
- User-facing bullets in the main list, tooling/CI/test/refactor ones under `Internal:`.

Then check the section is **complete**, which nothing else in the repo does:

```bash
git log --oneline "$(git tag --sort=-creatordate | head -1)"..origin/master
```

Every commit there should map to a bullet. Changes confined to `CLAUDE.md` / `CONTRIBUTING.md` are
exempt by `CLAUDE.md`; anything else that has no bullet is a gap — add one describing the end
state, and name it in the report so the maintainer sees what you wrote rather than discovering it
in the release notes.

Show the resulting diff in chat before §4. The bump level is read off this text, so the text has to
be visible next to the level derived from it.

## 4. Decide the bump

Compute the three candidates rather than doing the arithmetic yourself — `--dry-run` writes
nothing:

```bash
for level in patch minor major; do uv version --bump "$level" --dry-run; done
```

Classify by the **strongest single bullet** in the section, not by how many there are:

| Level | Warranted by |
|---|---|
| **major** | anything that breaks the public API — the `__all__` exports, an exported signature, or documented return semantics. `CLAUDE.md` promises no break between minor versions, so a break has nowhere else to go |
| **minor** | new public API; a user-visible behaviour change that is not a break; a new or raised runtime dependency; dropping a supported Python version; a packaged-data format change that makes users who compile their own data regenerate it |
| **patch** | bug fixes; documentation; a section whose bullets are all under `Internal:` |

Two things that look like majors and are not: internal code, binary data formats and packaged
assets are versioned with the package and carry no compatibility promise (`CLAUDE.md`), and a
changed `.fbs` layout is therefore a minor at most — it costs users a regeneration, not a rewrite.
An `Internal:`-only section is a patch however long it is.

A boundary-data update is **not on this table at all**: it releases
`timezonefinder-data`, leaves this version untouched, and never reaches `CHANGELOG.rst`. What does
belong here is a *format* change, which bumps `DATA_FORMAT_VERSION` and the data distribution's
major — and then the ordering is load-bearing: publish the data release first, then this one, or
the new bound resolves to nothing.

**Decide it here; do not ask.** The table above is the whole rule, and the bullets it applies to
are already written. State the level and the resulting version number in chat as you go on, so the
run is readable without opening the PR.

Deciding it unasked is paid for in §7, and both halves are obligatory there: quote the single
bullet that drove the level and name the table row it matches, then name the level you did *not*
pick and why. "minor, not major: no exported signature changed" can be checked in seconds; "minor"
cannot.

If the invocation already named the level ("cut a minor release"), that is the answer: state the
resulting number and go on. Say in the PR that the level was given rather than derived, and if the
table would have given a higher one, say that too — the promise is the maintainer's to make, but
the PR has to show them what they are making. The tag gate still stands.

## 5. Apply

```bash
git checkout -b "release/<version>"
uv version --bump <level>        # writes pyproject.toml AND re-locks uv.lock; both belong to the commit
uv version --short               # confirm
date +%Y-%m-%d                   # the release date - ask the shell, not your idea of today
```

Then rewrite the top of `CHANGELOG.rst`:

- The `X.X.X (unreleased)` title becomes `<version> (<date>)`.
- **The `---` underline must be at least as long as the title**, and rstcheck fails it otherwise.
  Both titles happen to be 18 characters today, because `unreleased` and `YYYY-MM-DD` are both 10 —
  that stops being true at version `10.0.0`. Recompute the underline; do not reuse the dashes.
- Insert a fresh empty `X.X.X (unreleased)` section above it, so the next change has somewhere to
  go. The file's layout is exact: three blank lines under the `=========` header, one blank line
  under each title's underline, two blank lines between sections. An empty section is valid RST and
  passes the hook — verified.

The three files this touches — `CHANGELOG.rst`, `pyproject.toml`, `uv.lock` — are the whole commit.

## 6. Verify, and what not to run

- [ ] `make hook` clean. This is what runs `rstcheck` over `CHANGELOG.rst`, so a short underline or
      a broken directive fails here rather than on the PyPI page.
- [ ] `make test` green.
- [ ] `make testint` green. It builds the sdist and wheel at the new version — the one gate that
      exercises packaging, which is exactly what a release changes.
- [ ] `git diff origin/master --stat` lists those three files and nothing else. Another session's
      work swept into a release commit is how something unreviewed gets tagged.

Do **not** run `make testall`, `make reports`, or the benchmarks: no file under `timezonefinder/`
changed, so they measure the same code as the last run and `make reports` would rewrite four
generated pages into the release commit.

## 7. Open the release PR

```bash
git add CHANGELOG.rst pyproject.toml uv.lock
git commit -m "Release <version>"
git push origin "release/<version>"
gh pr create --base master --title "Release <version>" --body "<body>"
```

Do not merge, do not enable auto-merge, do not tag. Body:

```markdown
## What
`<old> → <version>` (<level>), changelog section dated `<date>`.

## Why this level
`<level>`, because: the one bullet that drove it, quoted, and the §4 row it matches. Then the level
*not* taken, and why not, in one line. This is the only review the bump level gets, so it has to be
checkable without re-reading the whole section. Note it if the level came from the invocation
rather than from the table.

## Changelog edits
What §3 merged, cut or added — especially any bullet written here for a change that had none.

## Verification
`make hook`, `make test`, `make testint` — outcomes as run.

## After merge
The tag is pushed separately and publishes to PyPI; it is not part of this PR.
```

Then stop and report (§10). The maintainer merges.

## 8. Gate 2: tag

Only after the release PR is merged. Preconditions, each verified:

- [ ] `git checkout master && git fetch origin && git pull --ff-only` — and `git log -1 --oneline`
      is the release commit.
- [ ] `uv version --short` equals the top dated section in `CHANGELOG.rst`. The tag-push run checks
      out the tag and re-reads `pyproject.toml`, so a disagreement releases the wrong number.
- [ ] `git tag -l <version>` and `git ls-remote --tags origin <version>` are both empty (§9 if not).
- [ ] **Master's own push run for the release commit is green** — `gh run list --branch master
      --limit 3`, and the run whose head SHA is `git rev-parse HEAD`. Wait for it; the tag run does
      not re-run the tox matrix, and its `release` job refuses to publish unless a successful
      `build` run for that exact SHA exists on master. Tagging early therefore fails the release
      rather than slipping something untested past it — recoverable (§9), but only by re-running a
      job, never by re-tagging.

Then ask — plainly, in chat, naming what it does: tag `<version>` on `master` and push it, which
builds the wheels and uploads them to PyPI, and PyPI will not accept that version again. On a clear
yes:

```bash
make release
```

It refuses off `master`, tags `$(uv version --short)` annotated, and pushes. Afterwards confirm the
pipeline actually started:

```bash
gh run list --limit 5
```

A run on the tag ref must appear. Watch that `publish-pypi` (tag refs only) reaches PyPI; report
the run URL either way.

## 9. When it goes wrong

- **The tag run failed at "Verify this commit tested green on master".** The tag was pushed before
  master's push run for that commit finished, or that run was red. Nothing has been published — the
  check sits ahead of the GitHub Release, which is the first irreversible step. Once master's run is
  green, re-run the failed job from the tag run (`gh run rerun <id> --failed`). Do **not** re-tag,
  and do not delete the tag to "retry": `make rmtag` on a version that already reached PyPI cannot
  be undone there. If master's run is genuinely red, the version is not releasable — fix master and
  cut a new one.
- **The tag already exists remotely / `git push` said "Everything up-to-date".** Nothing in
  `build.yml` creates the tag any more, so this means a human or an earlier pass pushed it. Check
  `gh run list` for a run on that tag ref and report what you find rather than pushing again.
- **CI red on the tag run.** Report it with the failing job. Do not re-tag; the version is spent.
- **Preconditions in §2 fail.** Stop and name the one that failed. A release is not a place to work
  around a dirty tree.

## 10. Final report

In chat: the version and level, how it was derived (or that the invocation named it); the PR URL (prepare) or the tag and run URL
(tag); what §3 changed in the changelog, listing any bullet you wrote for a change that had none;
the verification commands and their real outcomes, failures stated plainly; and what the maintainer
does next — merge, or nothing.

---

## Maintaining this skill

Absent on purpose, and to stay absent:

**Rules that live elsewhere.** `CLAUDE.md` is auto-loaded and owns the changelog conventions and
the public-API contract; `Makefile`'s comments own the tag/push ordering; `build.yml` owns what a
tag triggers. A second copy here drifts, and the copy that drifts is the one an agent obeys.

**The changelog-ordering stop.** §1 carried a fourth row for "a dated section sits *above*
`X.X.X (unreleased)`", because `update_data.sh` spliced its entry under the file header. It no
longer writes to `CHANGELOG.rst` at all: a data update releases `timezonefinder-data`
and records itself in that package's README, so the automation cannot produce that state, and
nothing else writes release sections unattended. Do not re-add the row.

**Autonomy, and where it stops.** The bump level used to be a second `AskUserQuestion` stop, on the
reasoning that the level is a promise about the public API and so the maintainer's to make. It is
still theirs — they make it by merging the release PR. The stop went away because it asked them to
answer, from §4's table and without the diff, a question the PR then asked again with both
attached. Do not re-add it. If a wrong level ever gets through, the fix is a sharper §7 — the
justification is what the reviewer actually checks.

The tag stop is different in kind and stays. Nothing reviews it afterwards: the PR review is over,
`build.yml` publishes on the push, and PyPI will not take the version twice. A skill that both
decides the level and pushes the tag can publish an unreviewable, unrepeatable artifact with no
human in the loop at any point.

**The tag race, and what replaced it.** §8 used to say the opposite of what it says now: not to
wait for master's push run, because that run's `release` job created the GitHub Release and with it
the tag, so the maintainer's `git push` found the tag already there. `build.yml`'s `release` job is
tag-only now, so master publishes nothing and the race is gone — but the tag run no longer re-runs
the tox matrix either, and refuses to publish without a green master run for the same SHA. Waiting
is therefore mandatory rather than merely harmless. Do not restore the old advice.

What *should* change here: the §4 table, if the versioning contract in `CLAUDE.md` changes.
