# Changelog and release-note policy

Every change needs a `CHANGELOG.rst` entry in the `X.X.X (unreleased)` section — user-facing ones in the main bullet list, dev tooling / refactors / CI / test infrastructure appended to the `Internal:` sub-list. This is easy to forget for changes that don't touch `timezonefinder/` at all (docs, `scripts/`, CI config, fixtures); those still need one.

**Exception: the contributor-memory layer gets no entry at all, not even an `Internal:` one.** That is `CONTRIBUTING.md`, the pointer stubs, provider workflow adapters, everything under `contributing/`, and tests whose only subject is the memory graph or improvement-register structure. None of it ships or changes package behaviour, and the register lists work *not* done. `Internal:` remains the user's changelog. A change touching memory and something else is not covered by the exception: describe the something else.

The changelog is read by users, not by reviewers of the PR that produced it. Describe the **end state**, never the path taken to it:

- **Amend, don't append.** When a follow-up commit, review round, or fix changes something already described in the unreleased section, edit that bullet so it describes where the code landed. Adding a second bullet that corrects, tunes, or extends the first one is what makes the section unreadable — a released version should read as if the feature arrived in one step.
- **One bullet per user-visible change**, not per commit or per PR. A feature delivered over several commits (with its tests, docs, CI wiring and follow-up tuning) is one bullet.
- Keep the *why* only when it's decision-relevant for a reader — a deliberate trade-off, a non-obvious constraint, a gotcha. Drop tuning history ("raised from X to Y, then to Z" → state the final value), superseded intermediate states, and self-review narration.
- Keep bullets to a few sentences. Details that belong to contributors, not users, go in the narrow contributor-memory module or a docstring, and the bullet points there.
- Before finishing a task, re-read the whole `X.X.X (unreleased)` section: if two bullets describe the same feature, merge them.
- **Remember to acknowledge outside contributions**, in the form the existing `Thanks to …` bullets use. Credit the contributor's own PR, which is not the maintainer PR that superseded it.
