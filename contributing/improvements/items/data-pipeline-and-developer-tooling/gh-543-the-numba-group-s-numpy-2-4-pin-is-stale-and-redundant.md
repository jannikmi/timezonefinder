# GH-543 — the numba group's `numpy<2.4` pin is stale and redundant

- **Tracks:** issue #543, which carries the per-release numba bounds and the two lock lags.
- **Defect:** `numpy<2.4` plus the comment *"Numba requires NumPy 2.3.x or lower"*, duplicated verbatim in `[dependency-groups] numba` and `[project.optional-dependencies] numba`. It matches numba 0.63.0's bound; **`uv.lock` holds numba 0.65.1, which itself declares `numpy<2.5`**, so the hand-written pin is stricter than the numba it is locked against.
- **Fix:** delete it from both blocks — numba declares its own ceiling and the group exists only to install numba, so the pin adds nothing but a second place to be wrong. ~4 lines removed.
- **Why it is ranked above pure tidying:** the `cffi` 2.0.0 → 2.1.1 lag riding with it is a **precondition for evaluating GH-364's cheaper packaging option at all**, since 2.1.0 is where `abi3t` support arrived.
- **Status:** open.
- **Last touched:** 2026-08-21 — verified against PyPI and created.
