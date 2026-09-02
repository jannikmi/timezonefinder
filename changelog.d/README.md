# Changelog fragments

One file per change, instead of every change editing the same section of `CHANGELOG.rst`. Concurrent pull requests then never contend on the changelog, because no two of them touch the same lines.

Add exactly one file per user-visible change:

- `changelog.d/user/<slug>.rst` — a bullet for the main list, read by users
- `changelog.d/internal/<slug>.rst` — a bullet for the `Internal:` sub-list: dev tooling, refactors, CI, test infrastructure

The directory decides the placement, so the text never says where it goes. `<slug>` is kebab-case — lowercase letters, digits and single hyphens, enforced rather than merely asked for — and describes the change, not the branch or the issue; the same slug may not appear under both categories. Two names differing only in case would be two fragments on Linux and one file on macOS or Windows, which is how a bullet disappears on someone else's checkout.

A fragment holds the bullet text only, on one line, without the leading `* `. One bullet per change — a feature delivered over several commits is still one fragment, amended in place rather than joined by a second one.

```bash
uv run python -m scripts.changelog_fragments
```

prints the unreleased section as it will read once assembled. `--check` validates without printing; the test suite runs the same validation, so a malformed fragment fails CI rather than a release.

The [changelog policy](../contributing/development/changelog-and-release-note-policy.md) still decides *what* earns a bullet — including the exemptions, which create no fragment at all. The release consumes every fragment with `--assemble` and then performs its end-state rewrite on the combined section; `CHANGELOG.rst` remains the published artifact. A fragment left behind cannot be published: `make release` and the release job both run `--check --require-consumed` before anything irreversible happens.
