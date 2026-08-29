# Contributing to timezonefinder

This is the entrypoint for human and automated contributors. Read the
[core contributor contract](contributing/core-contributor-contract.md), then read only the row
matching the work. Follow conditional links only when their condition applies; do not preload the
whole `contributing/` tree.

| Task trigger | Required files | Conditional files |
|---|---|---|
| First orientation or architectural work | [Project purpose and constraints](contributing/project/project-purpose-runtime-constraints-and-non-goals.md), [repository layout and lookup flow](contributing/project/repository-layout-and-runtime-lookup-flow.md) | [Public API contract](contributing/project/public-api-and-compatibility-contract.md) when changing exported behavior |
| Ordinary code or test change | [Coding rules](contributing/development/coding-design-and-state-management-rules.md), [testing strategy](contributing/development/testing-strategy-and-change-scope.md) | [Generated-file rules](contributing/development/generated-file-regeneration-rules.md) when an artifact is generated |
| Setup, commands, pull request, or CI | [Environment and commands](contributing/development/development-environment-and-command-conventions.md), [pull-request and CI workflow](contributing/development/pull-request-and-ci-workflow.md) | [Changelog policy](contributing/development/changelog-and-release-note-policy.md) before finalizing a change |
| Performance or memory work | [Benchmarking and performance validation](contributing/development/benchmarking-and-performance-validation.md) | [Measurement baseline](contributing/improvements/query-performance-measurement-baseline.md) when ranking or changing the query path |
| Data, binary format, or data release | [Data pipeline and release order](contributing/development/data-pipeline-format-versioning-and-release-order.md), [generated-file rules](contributing/development/generated-file-regeneration-rules.md) | [Data-format decisions](contributing/improvements/decisions/geometry-data-format-and-validation-decisions.md) before proposing a layout |
| Documentation | [Documentation maintenance rules](contributing/development/documentation-maintenance-rules.md) | [Generated-file rules](contributing/development/generated-file-regeneration-rules.md) for generated reports |
| Improvement or cleanup pass | [Improvement-pass workflow](contributing/workflows/run-one-improvement-pass.md), [priority ranking](contributing/improvements/improvement-priority-ranking.md) | Open only the selected item and the memory it links |
| Resolve maintainer decisions | [Maintainer-decision workflow](contributing/workflows/record-maintainer-decisions.md), [priority ranking](contributing/improvements/improvement-priority-ranking.md) | Open only items whose status starts with `needs` |
| Prepare or publish a code release | [Code-release workflow](contributing/workflows/prepare-and-publish-code-release.md), [changelog policy](contributing/development/changelog-and-release-note-policy.md) | [Data release ordering](contributing/development/data-pipeline-format-versioning-and-release-order.md) for format changes |

The [improvement-register rules](contributing/improvements/improvement-register-rules.md) explain
how the ranking, item files, sequencing, decisions, measurements, and discovery records fit
together. Filenames and direct links are the index: if a file is not relevant to the current task,
do not read it.
