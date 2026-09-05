# TOOL-4 — three small lint families are not selected at all

- **Location:** `pyproject.toml`, `[tool.ruff.lint] select` — `["E4", "E7", "E9", "F", "B", "RUF013"]`, which contains none of `A`, `PLW`.
- **Defect:** three families this register has surfaced findings in are enforced nowhere, and each is small enough that the whole question is whether it is worth adopting. Measured 2026-09-06 on ruff 0.15.22:

  | family | sites | what it says |
  |---|---:|---|
  | `PLW2901` | 3 | a loop variable is overwritten inside its own body |
  | `A001` | 2 | a binding shadows a Python builtin |
  | `A002` | 2 | an argument shadows a Python builtin |

- **Seven sites is the whole cost, so the item is the judgement and not the edit.** Read each one, decide per family whether the rule earns a permanent place in `select`, and either adopt it — fixing the sites and adding a probe to `SELECTED_RULE_PROBES` in `tests/test_lint_configuration.py` — or record the refusal in the [dependency and tooling decisions](../../decisions/benchmarking-tooling-and-dependency-decisions.md) so the next discovery pass does not re-surface it. A family may go either way independently; they are one item only because none of them is worth a pull request alone.
- **Whatever is enabled, pick deliberately rather than taking a whole prefix.** `TRY003` / `EM101` / `EM102` fire in the hundreds across `scripts/` and are not worth adopting. `B` was taken whole only because two named exceptions covered it; a family needing six is not the same trade. Selecting bare `A` or bare `PLW` would pull in far more than the rules measured above.
- **Status:** open.
- **Last touched:** 2026-09-06 — split out of the single lint item that used to hold every unenforced ruff family, refined into these slices because 73 sites across disjoint rules plus a dependency pin is not one reviewable change.
