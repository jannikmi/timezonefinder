---
name: cut-release
description: "Turns the accumulated `X.X.X (unreleased)` section of CHANGELOG.rst into a numbered release of timezonefinder: check the section is release-ready, propose patch/minor/major with the bullets that justify it, and stop for the maintainer's decision - then land the version bump as a release PR and, once they have merged it, push the tag that publishes to PyPI. Two stops, both the maintainer's: the bump level and the tag. Use this whenever the user asks to cut, prepare, trigger or ship a release, publish a new version, bump the version, release the unreleased changelog section, tag a release, or asks what the next version number would be and why - even if they never say the word skill. Data-only releases are published automatically by release_data_update.yml and do not go through here."
---

# Cut a release

Turn the accumulated `X.X.X (unreleased)` section of `CHANGELOG.rst` into a released version of
`timezonefinder` on PyPI.

The work splits at the maintainer's merge, so this skill has two halves and one invocation runs
exactly one of them (§1): **prepare** ends with a release PR, **tag** ends with a pushed tag.

## 0. This skill stops twice. Both stops are the point.

`.claude/skills/code-quality-pass/SKILL.md` runs start to finish without asking, because an
internal refactor has an obvious correct answer. A release does not:

- **The bump level is a judgement about what users are promised**, and `CLAUDE.md` makes the public
  API a contract across minor versions. §4 puts the level to the maintainer as three concrete
  version numbers with the bullets behind each, and the pass halts there until answered.
- **The tag is the publish.** Pushing it builds the wheels and uploads them, and PyPI refuses a
  re-upload of a version that already exists. A wrong tag is not fixed by deleting it.

Do not "improve" this file by making it autonomous. Everything else here — worktree hygiene, the
verification gate, the PR body, the final report — follows the sibling skills and is not restated.

Hard gates, above everything else:

- **Never merge the release PR and never enable auto-merge.** A green check list can mean CI never
  ran. The maintainer merges.
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
| a dated section sits *above* `X.X.X (unreleased)` | — | stop, see below |

That last row is not a corrupt file: `update_data.sh` inserts its release section directly under
the three-line header, i.e. above the unreleased one, so an automated data release that landed
while work accumulated leaves the sections out of order and its tag shipped that work under a
version number that documents none of it. Report it and let the maintainer decide; do not
silently reorder the file as part of a release.

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

Show the resulting diff in chat before §4. The bump level is read off this text, so the maintainer
should see the text they are being asked about.

## 4. Gate 1: propose the bump

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
| **patch** | bug fixes; data-only updates; documentation; a section whose bullets are all under `Internal:` |

Two things that look like majors and are not: internal code, binary data formats and packaged
assets are versioned with the package and carry no compatibility promise (`CLAUDE.md`), and a
changed `.fbs` layout is therefore a minor at most — it costs users a regeneration, not a rewrite.
An `Internal:`-only section is a patch however long it is.

Put it to the maintainer with `AskUserQuestion`: one question, the three options as the actual
version numbers (`8.3.0 — minor`, …), recommended first, each with the bullet that drives it quoted
in the description. **Do not proceed on silence or inference.** If they choose a level other than
the recommendation, take it without arguing — the promise is theirs to make.

If the invocation already named the level ("cut a minor release"), that is the answer: skip the
question, state the resulting number, and go on. Gate 2 still stands.

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
The bullets that decide it, one line each. Note it if the maintainer chose a level other than the
proposed one.

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
- [ ] **The release PR's own CI run was green.** That is the signal — the same tree master now
      carries. Do not wait for master's push run to finish, and this is not laziness: that run's
      `release` job creates the GitHub Release itself, which creates the tag, and a `git push` of a
      tag the remote already has reports "Everything up-to-date" and fires no webhook. The
      automated data path (`release_data_update.yml`) tags immediately after merging for this
      reason.

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

- **`git push` said "Everything up-to-date" / the tag already exists remotely.** Master's push run
  created the release and its tag first. `build.yml` also triggers on `release: published`, whose
  ref *is* the tag, so publishing may still happen on its own — check `gh run list` and report what
  you find. Do not delete the tag to "retry": `make rmtag` on a version that already reached PyPI
  cannot be undone there.
- **CI red on the tag run.** Report it with the failing job. Do not re-tag; the version is spent.
- **Preconditions in §2 fail.** Stop and name the one that failed. A release is not a place to work
  around a dirty tree.

## 10. Final report

In chat: the version and level, and who chose it; the PR URL (prepare) or the tag and run URL
(tag); what §3 changed in the changelog, listing any bullet you wrote for a change that had none;
the verification commands and their real outcomes, failures stated plainly; and what the maintainer
does next — merge, or nothing.

---

## Maintaining this skill

Absent on purpose, and to stay absent:

**Rules that live elsewhere.** `CLAUDE.md` is auto-loaded and owns the changelog conventions and
the public-API contract; `Makefile`'s comments own the tag/push ordering; `build.yml` owns what a
tag triggers. A second copy here drifts, and the copy that drifts is the one an agent obeys.

**Autonomy.** §0 explains why the two stops exist. Removing them makes the skill able to publish an
unreviewable, unrepeatable artifact without a human in the loop.

What *should* change here: the §8 race note, if `build.yml`'s `release` job stops creating the tag;
the §4 table, if the versioning contract in `CLAUDE.md` changes; §1's data-update row, if
`update_data.sh` stops inserting above the unreleased section.
