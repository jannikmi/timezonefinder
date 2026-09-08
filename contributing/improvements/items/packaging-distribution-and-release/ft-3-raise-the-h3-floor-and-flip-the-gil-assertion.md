# FT-3 — raise the `h3` floor and flip the GIL assertion

- **Where:** `pyproject.toml`, the `h3>=4` dependency bound and `uv.lock`; the strict-xfail assertion [FT-2](../data-pipeline-and-developer-tooling/ft-2-no-environment-tests-a-free-threaded-interpreter.md) adds; `docs/`, for the support statement.
- **What it is:** the single change that lets this project claim free-threading support. `h3` — not our C extension — is what re-enables the GIL on import; our cffi extension already declares `Py_MOD_GIL_NOT_USED` and already releases the GIL on every call.
- **Blocked on an h3 release, and the fix is merged but unshipped.** uber/h3-py#493 merged 2026-08-12; the newest h3 release is 4.5.0, published 2026-05-30, which predates it. `uv.lock` holds 4.5.0, and constructing a `TimezoneFinder` on a free-threaded build still emits the runtime warning that the GIL was re-enabled to load `h3._cy.cells` — re-verified 2026-09-08. The import itself does not: `h3` is not loaded until a finder is built, which is where FT-2's assertion has to sit. **The next h3 release is the thing to re-check** — do not read this as waiting for a release that has already happened.
- **What it does when the release lands:** raise the floor to that version, delete the `strict=True` xfail so the GIL assertion becomes a passing test, and state the support in the documentation.
- **What it must not claim:** that a shared instance now scales. It does not — 1.60x at 8 threads shared against 4.84x per-thread — and that is refcount contention, not a lock. See [FT-4](../data-pipeline-and-developer-tooling/ft-4-the-thread-safety-documentation-contradicts-itself.md), which is what makes the docs able to say this correctly.
- **Open, and not settled by the release:** uber/h3-py#493 adds a Cython directive and its author reports `pytest-run-parallel` green. That is a declaration of thread-safety, not a proof of one.
- **Size:** S.
- **Status:** blocked on an h3 release carrying uber/h3-py#493, and on FT-2 for the assertion it flips.
- **Detail:** issue #364.

## Related memory

- [Public API compatibility and runtime loading decisions](../../decisions/public-api-compatibility-and-runtime-loading-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
