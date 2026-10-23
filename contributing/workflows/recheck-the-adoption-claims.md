# Recheck the adoption claims

The *Used by* section in `README.md` and `docs/3_about.rst` makes claims that the outside world can falsify without a commit here, so recheck them while preparing every [code release](prepare-and-publish-code-release.md), before opening its pull request:

- **Most downloaded.** Compare the last month on [pypistats](https://pypistats.org/packages/timezonefinder) against every maintained package listed under *Alternative python packages* in `docs/alternatives.rst` (today [tzfpy](https://pypistats.org/packages/tzfpy)). If another one has caught up, drop the claim rather than qualify it.
- **Named dependents.** Each must still list `timezonefinder` in its own manifest (`pyproject.toml`, `setup.py`, a requirements file or its PyPI metadata), not merely appear in GitHub's dependency graph, which keeps stale entries. A repository that dropped it, was archived or moved comes out or is repointed. A replacement name needs the same manifest evidence; `prototypes/dependents_analysis.py` finds candidates.
- **Magnitudes.** "Thousands of repositories and hundreds of published packages" must still hold on the [dependency graph](https://github.com/jannikmi/timezonefinder/network/dependents). Never replace a magnitude with a count.
- **`CITATION.cff`** carries no version or date on purpose, so it cannot go stale; recheck only that the author, URLs and the Zenodo concept DOI (which names every version, not one) are still right.

A stale claim is fixed in its own pull request before the release pull request, edited in both copies; it never rides in the version commit, whose file list that workflow fixes.
