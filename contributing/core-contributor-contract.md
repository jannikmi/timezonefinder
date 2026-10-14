# Core contributor contract

`timezonefinder` performs offline WGS84-coordinate lookups with unsimplified boundary geometry. Preserve correctness at borders, the low-memory memory-mapped mode, constrained container use, and the correct pure-Python fallback when optional accelerators are unavailable.

Use `uv` for dependency management and run Python commands through `uv run`. Work from the project root without redundant `cd` prefixes. During iteration run the narrow test or pattern affected; broaden verification according to the linked testing rules. Run `make hook` after code changes and after regeneration, before interpreting generated diffs.

Do not break exported functions, classes, signatures, or documented semantics between minor versions. Internal code, binary assets, and data formats ship with the package and do not need compatibility with unreleased predecessors. Before adding a shim, establish that the older state was actually released.

Never edit generated files directly. Change the generator or schema, regenerate, and require the generator to emit pre-commit-clean output. Validate artifacts where they are produced and in tests, not repeatedly in latency-sensitive runtime construction.

Name what a change trades away before implementing it, rule out the options a project constraint already forbids, and validate the surviving trade-off with measurement rather than argument; the [trade-off rules](development/trade-off-surfacing-and-validation.md) say when a trade-off is instead a maintainer decision.

Keep changes focused and production-ready: no placeholders, speculative compatibility, unrelated cleanup, or unmeasured fast-path trade-offs. Preserve unrelated working-tree changes and stage explicit paths. Put durable reasoning at the decision site or in the narrowest contributor-memory file; do not use temporary plans, issues, or pull-request numbers as the sole explanation. Avoid temporal references a reader cannot resolve, like “this morning”, “in September” or “recently”, which silently go stale; where one helps, use an absolute parameter such as a commit hash.

Add targeted tests for behavioral changes. Select integration, slow, acceleration-path, benchmark, or documentation gates by the changed subsystem rather than running expensive suites reflexively. Rebase onto current `master` before the final gate, because rebasing afterwards invalidates it.

Every change needs a fragment in the matching unreleased changelog section, with development-only changes under `internal/`. Changes confined to contributor memory, provider adapters, and their structural tests are the exception and receive no changelog entry. Describe the final state rather than the sequence of commits, and amend an existing bullet instead of adding a corrective follow-up.

The detailed rules are routed from [`CONTRIBUTING.md`](../CONTRIBUTING.md), which says how to match its routes.

How a rule is recorded, where it belongs, and what never belongs in one is in [writing and keeping contributor memory](contributor-memory-rules.md).
