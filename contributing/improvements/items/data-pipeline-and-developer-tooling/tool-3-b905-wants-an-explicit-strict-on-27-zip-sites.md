# TOOL-3 — `B905` wants an explicit `strict=` on 27 `zip` sites

- **Location:** `pyproject.toml`, `[tool.ruff.lint] ignore` — `"B905"`; the 27 sites are spread over `scripts/`, `tests/`, `benchmarks/`, `examples/` and four library modules, and `uv run ruff check --select B905 .` lists them.
- **Defect:** the rule is selected as part of `B` and then ignored again, so nothing holds any `zip` in the tree to a stated length contract. Re-measured 2026-09-06 on ruff 0.15.22: **27 sites across 18 files**, unchanged from the count TOOL-1 recorded.
- **Each site needs its own judgement**, which is why this is a whole item rather than a fixer run: `strict=True` where the two iterables must agree and a silent truncation would be a wrong answer, `strict=False` where one is deliberately shorter. The rule cannot tell them apart and neither can a diff-wide default.
- **One earlier conclusion here was wrong, and is kept because the shape recurs.** The worry was that the FlatBuffers shortcut reader's `zip(poly_id_hex_ids, poly_id_lengths)` — then the only site on the library's own load path — could truncate silently, dropping shortcut entries the lookup would read back as "no candidate polygons", so those coordinates would answer `None` rather than raise. It could not: the two lists were local accumulators appended in the same iteration of the same loop a few lines above the `zip`, with no file read between them, so `strict=True` would have asserted what the control flow already guaranteed. That reader has since been replaced by the slot-addressed shortcut index, which pairs nothing, so the site is gone either way. **The lesson that survives it: a `zip` over two accumulators built in one loop is not a truncation risk, whatever the load path.**
- **The fix.** Judge the 27 sites, add the explicit `strict=`, and delete `"B905"` from `ignore` — which empties the list, so the `ignore` key goes with it. `tests/test_lint_configuration.py` already probes that a selected rule still fires; add `B905` to `SELECTED_RULE_PROBES` so it cannot be re-ignored silently.
- **Status:** open.
- **Last touched:** 2026-09-06 — split out of TOOL-1, which was refined into TOOL-2 to TOOL-6.

## Related memory

- [Coding rules](../../../development/coding-design-and-state-management-rules.md)
