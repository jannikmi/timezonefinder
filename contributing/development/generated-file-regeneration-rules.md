# Generated-file regeneration rules

**Invariant: every generator emits output that is already pre-commit-clean**, so regenerating and
diffing compares like with like. Keep it that way — when it breaks, a re-parse shows spurious diffs
that look like converter drift, or real changes drown in formatting churn, and the lossless check
after a data regeneration (`git status --short packages/timezonefinder-data/timezonefinder_data/data` listing only genuinely changed
binaries) stops meaning anything.

What it takes to hold, for anything you add:

- `scripts/utils.py` `write_json` stringifies keys before `sort_keys`, matching `pretty-format-json`.
  Sorting int keys directly gives numeric order; the hook re-reads the file, where JSON keys are
  strings, and sorts lexicographically
- `scripts/reporting.py` emits no trailing whitespace on empty table cells and exactly one final
  newline, matching `trailing-whitespace` / `end-of-file-fixer`. `BenchmarkReporter.write_report`
  (`scripts/benchmark_utils.py`) applies the same final-newline normalisation for every
  `docs/benchmark_results_*.rst`
- `make flatbuf` runs the formatters itself, since `flatc` output differs from the committed
  bindings under `ruff-format` and `pyupgrade`

Both normalisations are covered by tests in `tests/utils_test.py`. If a generated file still comes
out dirty, fix the generator rather than committing the hook's repair — the repair is invisible and
the next regeneration undoes it.

Corollary: don't edit a generated file directly. Change the generator or the schema and regenerate.

## Validate artifacts at production

Check an artifact where it is produced, never where it is consumed. Build-established facts—above
all packaged binaries—must not be re-derived whenever a finder is constructed. Assert them in the
generator over what it wrote and in the test suite over what is committed, sharing one
implementation. `scripts/data_integrity.py` is the pattern. Moving checks off initialization also
lets them be exhaustive instead of shallow enough for a latency budget.

Pick the narrowest integer dtype that fits and guard it; headroom alone is not a reason to pad.
Overflow must fail in the generator and committed-data tests. The error must name the value, dtype
ceiling, wider type required, and version bumps that follow. A guarded narrow type is smaller and
louder than an unguarded wide one.
