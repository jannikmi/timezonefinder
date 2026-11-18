# AI usage disclosure

JOSS requires every paper to carry an AI usage disclosure that names the tools and models (with versions) and where they were used, describes the nature and scope of the assistance, and confirms that the human authors reviewed, edited and validated all AI-assisted output and made the core design decisions ([submission guidelines](https://joss.readthedocs.io/en/latest/submitting.html#ai-usage-policy)). An incomplete disclosure is treated as an ethical breach.

This file holds the draft statement for `paper.md` and the evidence it rests on, compiled from the git history and the pull requests of `jannikmi/timezonefinder` up to commit `1337c67`. The statement goes into `paper.md` once the [open points](#open-points-for-the-authors) are settled. This file and the draft statement were themselves drafted with Claude Code (Claude Opus 5.5) and reviewed by the maintainer.

## Draft statement for `paper.md`

> **AI usage disclosure.** Generative AI was used in the development of `timezonefinder` since September 2025. OpenAI Codex (model GPT-5.6 Terra) generated pull requests and reviewed pull requests between September 2025 and October 2026, and was also used outside pull requests. GitHub Copilot reviewed a few pull requests, resolved one merge conflict and was also used outside pull requests. From August 2026, most changes were developed with Anthropic's Claude Code, using Claude Opus 5, Claude Opus 5.5 and, rarely, Claude Sonnet 5. The assistance covered code generation and refactoring, test scaffolding, benchmark and report scripts, CI configuration, documentation, the contributor guide, the survey of publications that reference the package, and drafting and copy-editing of this paper. All earlier development, including the original design of the package, its data format and its shortcut index, was done without generative AI. The problem framing, the architecture and every design decision were made by the human authors, who reviewed, edited and validated all AI-assisted output before it was merged; the design decisions are recorded in the repository's contributor guide. *(Contributions of the co-authors: to be confirmed.)*

## Evidence from the repository

### Tools and models

| Tool | Model (version) | Used for | Period | Evidence |
|---|---|---|---|---|
| Claude Code (Anthropic) | Claude Opus 5 | Writing code, tests, documentation and contributor memory | 2026-08-01 to 2026-10-14 | 231 commits on `master` with a `Co-Authored-By: Claude Opus 5` trailer, one of them in the 1M-context variant |
| Claude Code (Anthropic) | Claude Opus 5.5 | Same, plus the JOSS preparation (#771, #772, #777, #780) | 2026-10-11 to 2026-11-17 | 32 commits with a `Co-Authored-By: Claude Opus 5.5` trailer, three of them in the 1M-context variant |
| Claude Code (Anthropic) | Claude Sonnet 5 | Smaller changes | 2026-08-04 to 2026-08-24 | 3 commits with a `Co-Authored-By: Claude Sonnet 5` trailer |
| OpenAI Codex | [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra) | Generating pull requests | 2025-09-16 to 2026-10-05 | 30 pull requests from `codex/` branches, 29 of them merged |
| OpenAI Codex (`chatgpt-codex-connector`) | [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra) | Automated pull-request review | 2025-09 to 2026-09 | Reviews on 38 pull requests. The review round was dropped in #710 |
| GitHub Copilot | not recorded in the repository | Pull-request review, applied review suggestions, one merge-conflict resolution | 2026-04-30 to 2026-08-19 | Reviews on 6 pull requests; `Co-authored-by: Copilot` on #419, #420, #528 and #529 |

The models of both OpenAI Codex rows were stated by the maintainer, as was the use of Codex and GitHub Copilot outside pull requests, which leaves no trace in git.

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

- All development before September 2025 was done without generative AI, as the maintainer confirms. The history agrees: before then it has no AI trailers, branches or reviewers.
- 273 of the 940 human-authored commits on `master` carry a Claude trailer, all from 2026-08-01 on. Of the 381 human-authored commits since then, 273 carry one.
- The trailers undercount AI use: some squash merges dropped them. For example, #772 was produced with Claude Code but its commit on `master` has no trailer, and 25 of the trailerless commits since 2026-08 came from `codex/` branches. The figures above are lower bounds.

## Open points for the authors

These cannot be read from the repository and must be settled before the statement goes into `paper.md`:

- [x] **Tool versions:** the maintainer decided on 2026-11-18 to name the model versions only.
- [x] **GitHub Copilot model:** the models changed over the months and were not recorded (maintainer, 2026-11-18). The statement says so.
- [x] **Co-authors' contributions:** both co-authors used AI assistants for their contributions; Lucas Hemkemeier used Claude Code, models unknown (maintainer, 2026-11-18). Their commits carry no AI trailer.
- [x] **Paper text:** only Claude Code (Claude Opus 5.5) was used for `paper.md` (maintainer, 2026-11-18).
- [ ] **Review confirmation:** each author confirms the closing sentence of the statement for their own part. This is the authors' assertion and cannot be drafted on their behalf.
