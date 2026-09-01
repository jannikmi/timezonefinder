# Documentation discovery coverage

## Baseline

- **Delta anchor:** `72678a1`.
- **Coverage state:** partial; no systematic sweep of all documentation prose has occurred.

## Covered subjects

- `docs/2_use_cases.rst` was checked for converter invocation.
- `docs/1_usage.rst` and `docs/4_api.rst` were read around batch behavior.
- `docs/alternatives.rst` was read end to end while its accuracy claim was measured.
- Exact-boundary and South Pole behavior documented for `certain_timezone_at()` received targeted contract review.

## Next useful gap

- **Highest-value discovery gap:** sweep the remaining `docs/` pages for behavior, platform, dependency, and generated-data claims that can drift from code or configuration.
