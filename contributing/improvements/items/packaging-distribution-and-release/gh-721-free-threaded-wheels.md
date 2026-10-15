# GH-721 — free-threaded wheels

- **Tracks:** issue #721, the user-facing statement of this plan and the place where demand for 3.14t wheels is collected.
- **Where:** `CIBW_BUILD_VERSIONS` in `.github/workflows/build.yml` (`cp312-*`), the `[tool.cibuildwheel]` repair commands in `pyproject.toml`, and the `_abi3` guard in `setup.py`.
- **What it is:** shipping wheels a free-threaded interpreter can install. None exist: the release ships three `cp312-abi3` Linux wheels plus the sdist, and an abi3 wheel cannot serve a free-threaded build. Source installs work on 3.14t, so nothing is broken while this waits; it buys not needing a C compiler and libffi.
- **Decided by the maintainer: 3.15t and later only, via the `abi3t` stable ABI.** One set of wheels serves every free-threaded release from 3.15 on, for +3 artifacts once and no growth per CPython release.
- **Refused: version-specific `cp314t` wheels.** They cost +3 artifacts on every release until 3.14 leaves `requires-python`, for the free-threaded version that `abi3t` can never serve and that expires first. Revisit only on demand voiced on issue #721; until then a 3.14t user builds from the sdist. **`cp313t` is not an option at all:** `CIBW_BUILD='cp313t-* cp314t-* cp315t-*'` on the pinned cibuildwheel 4.3.0 prints `cp314t` and `cp315t` identifiers and no `cp313t` one.
- **Do not add `CIBW_ENABLE=cpython-freethreading`.** Free-threaded identifiers are not gated behind an enable group, and an unknown group exits non-zero. With the 4.3.0 pin, `cp315t-*` and `cp315-*` print without any enable group.
- **Blocked on setuptools.** setuptools 84.0.0's `bdist_wheel._validate_py_limited_api` raises on any `py_limited_api` whenever `Py_GIL_DISABLED` is set, so no free-threaded build can carry a stable-ABI tag. That is also why `setup.py` withholds the abi3 claim on every free-threaded interpreter rather than only below 3.15, as cffi does. cffi supports `abi3t` from 2.1.0, and `uv.lock` holds 2.1.1. CPython 3.15 is at 3.15.0b4.
- **What the change carries once unblocked:**
  - Relax the `setup.py` guard for 3.15t and later, so a free-threaded build there claims `abi3t`.
  - Add the `cp315t` identifiers to `CIBW_BUILD_VERSIONS`.
  - Settle the wheel tag. Whether an `abi3t` build keeps `py_limited_api="cp312"`, needs a `cp315` base or needs a different value is untested, and `tests/test_python_version_support.py` asserts against that literal, so the two are reconciled in the same change.
  - Run every wheel through `abi3audit --strict` in the repair step, and confirm that it accepts an `abi3t` wheel or give the `t` identifiers their own repair command.
- **Size:** M.
- **Status:** blocked — on a setuptools release that accepts a limited-API tag on a free-threaded interpreter; reopen for `cp314t` wheels only on demand voiced on issue #721.
- **Last touched:** 2026-10-15 — interpreter set decided by the maintainer; re-keyed to issue #721.

## Related memory

- [Data distribution packaging and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
