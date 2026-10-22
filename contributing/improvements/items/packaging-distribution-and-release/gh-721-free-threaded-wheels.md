# GH-721 — free-threaded wheels

- **Tracks:** issue #721, the user-facing statement of this plan and the place where demand for 3.14t wheels is collected.
- **Where:** `CIBW_BUILD_VERSIONS` in `.github/workflows/build.yml` (`cp312-*`), the `[tool.cibuildwheel]` repair commands in `pyproject.toml`, and the `_abi3` guard in `setup.py`.
- **What it is:** shipping wheels a free-threaded interpreter can install. None exist: the release ships three `cp312-abi3` Linux wheels plus the sdist, and an abi3 wheel cannot serve a free-threaded build. Source installs work on 3.14t, so nothing is broken while this waits; it buys not needing a C compiler and libffi.
- **Decided by the maintainer: 3.15t and later only, via the `abi3t` stable ABI.** One set of wheels serves every free-threaded release from 3.15 on, for +3 artifacts once and no growth per CPython release.
- **Refused: version-specific `cp314t` wheels.** They cost +3 artifacts on every release until 3.14 leaves `requires-python`, for the free-threaded version that `abi3t` can never serve and that expires first. Revisit only on demand voiced on issue #721; until then a 3.14t user builds from the sdist. **`cp313t` is not an option at all:** `CIBW_BUILD='cp313t-* cp314t-* cp315t-*'` on the pinned cibuildwheel 4.3.0 prints `cp314t` and `cp315t` identifiers and no `cp313t` one.
- **Do not add `CIBW_ENABLE=cpython-freethreading`.** Free-threaded identifiers are not gated behind an enable group, and an unknown group exits non-zero. With the 4.3.0 pin, `cp315t-*` and `cp315-*` print without any enable group.
- **setuptools no longer blocks this.** From 84.2.0, `bdist_wheel._validate_py_limited_api` raises on a free-threaded `py_limited_api` build only below 3.15, and `stable_abi_tag` tags a 3.15t build `abi3.abi3t` after the `py_limited_api` value; 84.0.0 and 84.1.0 still raise on every free-threaded build. The build-system floor `setuptools>=62.3` still admits those two, and `setup.py` still withholds the abi3 claim on every free-threaded interpreter because their gate required it. cffi supports `abi3t` from 2.1.0, `uv.lock` holds 2.1.1, and CPython 3.15 is released.
- **Blocked on [PY-1](py-1-python-3-15-is-unclaimed-and-3-12-is-past-its-cited-drop-date.md).** `abi3t` wheels claim 3.15t, and neither the classifiers nor any test leg covers 3.15 until the maintainer's window decision adds it.
- **What the change carries once unblocked:**
  - Relax the `setup.py` guard for 3.15t and later, so a free-threaded build there claims `abi3t`, and raise the build-system setuptools floor to 84.2.0, or make the relaxed guard conditional on it.
  - Add the `cp315t` identifiers to `CIBW_BUILD_VERSIONS`.
  - Settle the wheel tag. Whether an `abi3t` build keeps `py_limited_api="cp312"`, needs a `cp315` base or needs a different value is untested, and `tests/test_python_version_support.py` asserts against that literal, so the two are reconciled in the same change.
  - Run every wheel through `abi3audit --strict` in the repair step, and confirm that it accepts an `abi3t` wheel or give the `t` identifiers their own repair command.
- **Size:** M.
- **Status:** blocked — on PY-1, the decision that adds 3.15 to the supported window; reopen for `cp314t` wheels only on demand voiced on issue #721.
- **Last touched:** 2026-10-22 — the setuptools blocker re-verified as cleared by 84.2.0, and the item re-blocked on PY-1.

## Related memory

- [Data distribution packaging and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
