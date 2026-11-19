# Internal review of the JOSS paper against the reviewer criteria

An internal pre-submission review of `paper.md` and the repository against the [JOSS review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html), done on 2026-11-18 at commit `a75e9ae`. The paper requirements (length, required sections, no API documentation) were checked against [paper.html](https://joss.readthedocs.io/en/latest/paper.html) and [submitting.html](https://joss.readthedocs.io/en/latest/submitting.html) on the same day. Claude Code (Claude Opus 5.5) drafted this review and the matching edits to `paper.md`, for the authors to check. The fixes add citations, figures and links but shorten nothing: trimming is left to a later pass, and this review only marks candidates for it. The fixes bring the body text to about 4,560 words.

Open questions and TODOs for the authors are left as HTML comments in `paper.md`. They do not appear in the compiled PDF. Search for `TODO(authors)` and `OPEN QUESTION`.

**Overall assessment: minor revisions.** The software, its repository and its research use clear the JOSS bar comfortably. The paper has one problem a reviewer or editor would raise at once, its length, and several smaller ones about specific evidence and citations.

## Paper

| Item | Before this review | Status after this review |
|---|---|---|
| Length (750–1750 words) | About 4,400 words, 2.5 times the upper limit. The Software design section alone (about 1,570 words) was close to the limit. JOSS "may ask [authors] to reduce the length". | Unchanged; trimming is deferred to a later pass. The section sizes are listed at the top of `paper.md`, and `TRIM CANDIDATE` comments mark candidates. |
| No API documentation | The paper names `TimezoneFinder.data_version`, `TimezoneFinderL`, the version string scheme (`4.2026.5`), cell sizes, 4 × 4 refinement, 128-vertex blocks, the wheel matrix and the test strategy. | API names (`TimezoneFinder.data_version`, `TimezoneFinderL`, "function"/"return type" wording) removed at the maintainer's request; the text now describes capabilities, not calls. The version-string example, index parameters, wheel matrix and test strategy are design detail rather than API and remain marked as a `TRIM CANDIDATE`. |
| Authors and affiliations | Two affiliations "to be confirmed"; no ORCIDs for the co-authors; date set to the draft date. | Lucas Hemkemeier's affiliation (Independent Researcher) and ORCID added from #780. TODO: Evgenii Seliverstov's affiliation, which waits on his employer's approval, and the submission date. |
| Summary | Clear and written for a non-specialist audience. | Unchanged. |
| Statement of need | Good: problem, audience and context are clear. It repeats the usage examples of the Research impact statement almost word for word. | `zoneinfo` cited. The duplicated examples are marked as a `TRIM CANDIDATE`. |
| State of the field | Good: four routes, a measured comparison with `tzfpy` and a build-vs-contribute paragraph. Weak spots: uncited online services and `tzf-rs`, an uncited count of "more than twenty libraries", and the comparison given in words ("order of magnitude", "small single-digit factor") rather than numbers. | Citations added for the online services, `tzf-rs`, the lookup-library list (26 libraries in 15 languages) and the Zenodo archive. The `tzfpy` comparison now states the measured figures, the versions measured, the wheel sizes and the source of the ~111 m simplification bound (the `tzfpy` README), and links the documentation reports. The `pytzwhere` measurement is linked. TODO: re-run the `tzfpy` comparison against the current `tzfpy` 2.1.2 before submission. |
| Build vs. contribute | Argued from the 2016 state of `pytzwhere`. | Answered from the public `pytzwhere` tracker: the paper now cites the first author's bug report (#34, fixed upstream) and data-update PR (#36, not merged), and the data that was never updated (#42). It also corrects "`pytzwhere` has had no release since", which was wrong: `pytzwhere` released 3.0 to 3.0.3 in 2017. The maintainer confirmed there was no other contact with the `pytzwhere` maintainers, so the public record is complete. |
| Software design | Thoughtful: every choice is tied to a trade-off. But about 1,570 words, much of it documentation. | Douglas–Peucker and FlatBuffers cited. The documentation-level parts are marked as a `TRIM CANDIDATE`. |
| Research impact statement | Strong and specific: 40 publications found by a documented search, 31 checked against the full text, all cited works at "full text read" grade. Weak spots: "thousands of repositories and hundreds of packages" with no numbers or date, and named downstream projects with no reference or URL. | Dependency-graph counts stated with the access date (about 5,000 repositories and 260 packages on 2026-11-18), and every named project linked. The repository paths are links. TODO: refresh the counts at submission; ETHOS.TISED citation pending its full-text check. |
| AI usage disclosure | Complete and specific (tools, models, scope, verification, lower-bound caveat). One open point remained from `ai-usage-disclosure.md`: each author confirms the review statement for their own part. | "Drafted with" changed to "drafted and revised with" Claude Code, which covers this review's edits without a separate clause (maintainer's decision). Confirmation TODO kept; a `TRIM CANDIDATE` comment lists what may be cut and what JOSS requires to stay. |
| Acknowledgements, funding, conflicts of interest | Financial support and the sponsorship by the `tzfpy` author are disclosed, with a statement on the sponsor's involvement, as JOSS requires. No explicit competing-interests statement. | Competing-interests sentence added ("The authors declare no other competing interests."), chosen by the maintainer. TODO: each co-author confirms it. |
| References | All cited keys resolve and every entry in `paper.bib` is cited. Repository paths (`paper/references/`, `contributing/...`) do not resolve in a PDF. | Repository paths are now links to `master`. TODO: pin them to the archived release at submission. |

Compiling locally with `pandoc --citeproc` produced no warnings, and none of the review comments appear in the output. The `Paper draft` workflow builds the JOSS PDF on this pull request.

## Repository

| Criterion | Assessment | Evidence |
|---|---|---|
| License | Good | `LICENSE`: MIT (OSI approved), full text. The data package has its own `DATA_LICENSE` (ODbL boundary data). |
| Scope and significance | Good | Research impact statement and `paper/references/`. Downstream research software depends on the package. |
| Development timeline | Good | Public since 2016, continuous releases (currently 9.2.0, with the data package at 4.2026.6). |
| Open development | Good | Public issues, pull requests, Discussions and tagged releases since the start. |
| Collaborative effort | Good | Many outside contributors, credited in `CHANGELOG.rst` and `docs/5_contributing.rst`. The maintainer reviews and merges pull requests. |
| Installation | Good | `pip install timezonefinder` installs the code and the data package. Checked in a fresh virtual environment: 9.2.0 with data 2026f returned `Europe/Berlin` for Berlin and `Etc/GMT+2` for a point in the Atlantic, in single and batch lookups. |
| Example usage, API documentation | Good | README, the Read the Docs usage and API pages, and `examples/`. |
| Tests and CI | Good | pytest suite with property-based tests, run on GitHub Actions for every accelerator path, plus end-to-end wheel tests. |
| Community guidelines | Good | `CONTRIBUTING.md` (Support and governance section), issue templates, a Discussions link for questions, and a link to the upstream tracker for boundary errors. |
| Code of conduct | Good | `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), added in #791 after this review flagged it. JOSS does not require one, but many reviewers expect it. |

## Authorship

The first author made the large majority of the commits. The co-authors' contributions are documented in the repository (`docs/5_contributing.rst` and `CHANGELOG.rst`): Evgenii Seliverstov (GitHub `theirix`, confirmed by the maintainer on 2026-11-18) built the build and release pipeline, and Lucas Hemkemeier (`hemkdev`) built the automated data updates (PRs #429, #432, #434 and #436). The maintainer considers this documentation sufficient, so the paper does not repeat it. Each co-author must agree to be listed.

## Points from the submission issue (#780)

- **Archive author list.** JOSS's editor guide (editing.html, Post-review) asks editors to "check the archive deposit has the correct metadata (title and author list)": "In most situations, the two author lists should match. Authors and editors should review the two, and any differences need to be explained." #780 keeps `CITATION.cff`, which the Zenodo archive is built from, at a single author. Either the archive lists all three paper authors, or the difference needs an explanation ready for the editor. This answers the open item in #780 on whether the archive has to list the paper's authors. Left as an OPEN QUESTION in `paper.md`.
- **Development history.** #780 notes that a large share of the commits falls in 2026, and that JOSS runs automated checks on the commit distribution. The Summary now states the release history from `CHANGELOG.rst`: 86 releases since April 2016 across nine major versions, at least two in every year, with the milestones that added the ocean zones (5.0.0, 2020), the separate data package (8.3.0, 2026) and batch lookups (9.0.0, 2026). PyPI keeps files only from 2019 (3.4.2) on, so the earlier releases are attested by the changelog alone. Added at the maintainer's request.
- **Snippet- and index-grade entries.** The paper cites only publications at "full text read" grade, including the walking-at-night example (`vellimana2023walking`). The 9 lower-grade entries in `paper/references/` are not cited, so the paper does not depend on them.
- **Distribution exclusion.** `paper/` is excluded from the distributions as a whole (`tests/test_package_contents.py`), so this review file is excluded too. `check-manifest` passes.

## Not checked

- The `tzfpy` comparison was not re-run against the current `tzfpy` 2.1.2. The figures in the paper come from the generated documentation reports, measured with 1.3.3.
- The `pytzwhere` memory and speed comparison was not re-run. The paper now links its documentation page.
- Whether each linked downstream project still depends on `timezonefinder` was not checked. The links are the ones from the README.
- The National Laboratory of the Rockies naming was checked only against its GitHub organisation, which hosts HOPP under that name; `nrel.gov` was not reachable from here.
