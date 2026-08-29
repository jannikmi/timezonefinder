# Core contributor contract

`timezonefinder` performs offline WGS84-coordinate lookups with unsimplified boundary geometry. Preserve correctness at borders, the low-memory memory-mapped mode, constrained container use, and the correct pure-Python fallback when optional accelerators are unavailable.

Use `uv` for dependency management and run Python commands through `uv run`. Work from the project root without redundant `cd` prefixes. During iteration run the narrow test or pattern affected; broaden verification according to the linked testing rules. Run `make hook` after code changes and after regeneration, before interpreting generated diffs.

Do not break exported functions, classes, signatures, or documented semantics between minor versions. Internal code, binary assets, and data formats ship with the package and do not need compatibility with unreleased predecessors. Before adding a shim, establish that the older state was actually released.

Never edit generated files directly. Change the generator or schema, regenerate, and require the generator to emit pre-commit-clean output. Validate artifacts where they are produced and in tests, not repeatedly in latency-sensitive runtime construction.

Keep changes focused and production-ready: no placeholders, speculative compatibility, unrelated cleanup, or unmeasured fast-path trade-offs. Preserve unrelated working-tree changes and stage explicit paths. Put durable reasoning at the decision site or in the narrowest contributor-memory file; do not use temporary plans, issues, or pull-request numbers as the sole explanation.

Add targeted tests for behavioral changes. Select integration, slow, acceleration-path, benchmark, or documentation gates by the changed subsystem rather than running expensive suites reflexively. Rebase onto current `master` before the final gate, because rebasing afterwards invalidates it.

Every change needs an entry in the current unreleased changelog, with user-visible changes in the main list and development-only changes under `Internal:`. Changes confined to contributor memory, provider adapters, and their structural tests are the exception and receive no changelog entry. Describe the final state rather than the sequence of commits, and amend an existing bullet instead of adding a corrective follow-up.

The detailed rules are routed from [`CONTRIBUTING.md`](../CONTRIBUTING.md). Read only the modules whose trigger matches the task.

## Maintaining contributor memory

Record a repository fact only when it is durable beyond the current change, non-obvious enough to have caused a failed check or wrong assumption, and has a concrete failure mode. Put it in the narrowest existing module, or at the code/configuration decision site when that is sufficient. Never copy a rule merely to make it more visible: route to its canonical owner instead.

Amend existing memory instead of appending corrective history. Delete or correct stale rules as part of the change that invalidates them. A confidently wrong instruction costs more than a missing one. Do not restate what the code, git history, Makefile, or public documentation already makes clear.
