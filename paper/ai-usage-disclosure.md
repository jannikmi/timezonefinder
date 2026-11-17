# AI usage disclosure

JOSS requires every paper to carry an AI usage disclosure that names the tools and models (with versions) and where they were used, describes the nature and scope of the assistance, and confirms that the human authors reviewed, edited and validated all AI-assisted output and made the core design decisions ([submission guidelines](https://joss.readthedocs.io/en/latest/submitting.html#ai-usage-policy)). An incomplete disclosure is treated as an ethical breach.

This file holds the draft statement for `paper.md` and the evidence it rests on, compiled from the git history and the pull requests of `jannikmi/timezonefinder` up to commit `1337c67`. The statement goes into `paper.md` once the [open points](#open-points-for-the-authors) are settled. This file and the draft statement were themselves drafted with Claude Code (Claude Opus 5.5) and reviewed by the maintainer.

## Draft statement for `paper.md`

> **AI usage disclosure.** Generative AI was used in the development of `timezonefinder` since September 2025. OpenAI Codex (models: *to be confirmed*) generated pull requests and reviewed pull requests between September 2025 and October 2026. GitHub Copilot reviewed a few pull requests and resolved one merge conflict. From August 2026, most changes were developed with Anthropic's Claude Code, using Claude Opus 5, Claude Opus 5.5 and, rarely, Claude Sonnet 5. The assistance covered code generation and refactoring, test scaffolding, benchmark and report scripts, CI configuration, documentation, the contributor guide, the survey of publications that reference the package, and drafting and copy-editing of this paper. All earlier development, including the original design of the package, its data format and its shortcut index, was done without generative AI. The problem framing, the architecture and every design decision were made by the human authors, who reviewed, edited and validated all AI-assisted output before it was merged; the design decisions are recorded in the repository's contributor guide. *(Contributions of the co-authors: to be confirmed.)*

## Evidence from the repository

### Tools and models

| Tool | Model (version) | Used for | Period | Evidence |
|---|---|---|---|---|
| Claude Code (Anthropic) | Claude Opus 5 | Writing code, tests, documentation and contributor memory | 2026-08-01 to 2026-10-14 | 231 commits on `master` with a `Co-Authored-By: Claude Opus 5` trailer, one of them in the 1M-context variant |
| Claude Code (Anthropic) | Claude Opus 5.5 | Same, plus the JOSS preparation (#771, #772, #777, #780) | 2026-10-11 to 2026-11-17 | 32 commits with a `Co-Authored-By: Claude Opus 5.5` trailer, three of them in the 1M-context variant |
| Claude Code (Anthropic) | Claude Sonnet 5 | Smaller changes | 2026-08-04 to 2026-08-24 | 3 commits with a `Co-Authored-By: Claude Sonnet 5` trailer |
| OpenAI Codex | not recorded in the repository | Generating pull requests | 2025-09-16 to 2026-10-05 | 30 pull requests from `codex/` branches, 29 of them merged |
| OpenAI Codex (`chatgpt-codex-connector`) | not recorded in the repository | Automated pull-request review | 2025-09 to 2026-09 | Reviews on 38 pull requests. The review round was dropped in #710 |
| GitHub Copilot | not recorded in the repository | Pull-request review, applied review suggestions, one merge-conflict resolution | 2026-04-30 to 2026-08-19 | Reviews on 6 pull requests; `Co-authored-by: Copilot` on #419, #420, #528 and #529 |

Commits authored by the `claude` GitHub account carry an unversioned `Co-authored-by: Claude` trailer added by GitHub's squash merge. Every such commit also carries a versioned trailer, so it is counted under its model above. 148 pull requests came from `claude/` branches, 142 of them merged.

### Where the AI-assisted commits landed

The 273 commits with a Claude trailer touched these areas (a commit can touch several):

| Area | Commits |
|---|---|
| `tests/` | 125 |
| `contributing/` (contributor guide and decision records) | 105 |
| `docs/` | 89 |
| `timezonefinder/` (the package) | 58 |
| `scripts/` (data build, benchmarks, reports) | 58 |
| `prototypes/` | 51 |
| `.github/` (CI) | 35 |
| `packages/` (data package) | 17 |
| `benchmarks/` | 13 |

### Share of the history

- Up to 2025-09, the history contains no trace of generative AI: no trailers, no AI branches, no AI reviewers.
- 273 of the 940 human-authored commits on `master` carry a Claude trailer, all from 2026-08-01 on. Of the 381 human-authored commits since then, 273 carry one.
- The trailers undercount AI use: some squash merges dropped them. For example, #772 was produced with Claude Code but its commit on `master` has no trailer, and 25 of the trailerless commits since 2026-08 came from `codex/` branches. The figures above are lower bounds.

## Open points for the authors

These cannot be read from the repository and must be settled before the statement goes into `paper.md`:

- [ ] **Codex models:** which models the Codex pull requests and reviews used (the repository records none).
- [ ] **Tool versions:** whether to name Claude Code and Codex client versions, or the model versions only.
- [ ] **AI use that left no trace in git:** IDE completion (e.g. Copilot in the editor), chat assistants used for design discussions or text, and AI-assisted commits before 2025-09 or without trailers, such as #413–#415.
- [ ] **Co-authors' contributions:** whether Evgenii Seliverstov's and Lucas Hemkemeier's contributions used generative AI. Their commits carry no AI trailer.
- [ ] **Paper text:** the final statement must name the tools used for drafting and editing `paper.md` itself.
- [ ] **Review confirmation:** each author confirms the closing sentence of the statement for their own part. This is the authors' assertion and cannot be drafted on their behalf.
