# PY-1 — retire Python 3.12 after its NEP 29 drop date

- **Where:** `requires-python`, the per-minor classifiers and the schedule comment above them in `pyproject.toml`; `requires-python` in `packages/timezonefinder-data/pyproject.toml`; `envlist`, `[testenv:py312-min]` and the `basepython = python3.12` lines of `docs`, `charts` and `py312-min` in `tox.ini`; the `test` matrix, `CIBW_BUILD_VERSIONS` and the end-to-end `uv-python-version` matrix in `.github/workflows/build.yml`; `_ABI3_BASE` in `setup.py`; ruff `target-version` and mypy `python_version` in `pyproject.toml`; the `cp312` tag `docs/architecture.rst` quotes. `tests/test_python_version_support.py` holds both `requires-python` floors, the classifiers, the tox factors, both matrices, the abi3 base and the minimum-NumPy pin to one another. It does not check the comment, the `basepython` lines, or the ruff and mypy targets, so those are moved by reading this list.
- **The rule is decided.** The schedule comment above `requires-python` states it: the later of the NEP 29 and SPEC 0 drop dates applies, and why the earlier one is refused. For 3.12 the later date is 2027-04-02.
- **What the change carries:**
  - `requires-python >=3.13` in both `pyproject.toml` files, and the 3.12 classifier removed.
  - The abi3 base `cp313` in `_ABI3_BASE` and the first `CIBW_BUILD_VERSIONS` identifier, and the `cp312` tag and "3.12 to 3.14" in `docs/architecture.rst`.
  - The 3.12 `test`-matrix entry removed, with the environments riding on it (`docs`, `charts` and the minimum-dependency env) moved to the 3.13 entry with their `basepython`. Otherwise they keep running on the runner's system 3.12 unnoticed. `py312-min` becomes `py313-min`, and its pinned NumPy must publish cp313 wheels.
  - The `cp312` end-to-end leg removed, ruff `target-version = "py313"` and mypy `python_version = "3.13"`.
  - The dates in the comment rewritten for 3.13: SPEC 0 on 2027-10-07, NEP 29 on 2028-04-07. The rule and its reason stay as they are.
  - A fragment under `changed/`, per the [changelog policy](../../../development/changelog-and-release-note-policy.md).
- **The abi3t base does not move.** `_ABI3T_BASE` in `setup.py` and the `cp315t-*` identifier stay at 3.15 until the floor passes it, and `tests/test_python_version_support.py` holds that base separately from the GIL one.
- **Size:** S.
- **Status:** conditional — on 2027-04-02 passing. The window rule is decided, but an improvement pass may not change the supported Python versions, so the maintainer starts this one.
- **Last touched:** 2026-10-22 — kept by the maintainer when 3.15 was added, so 3.12's retirement has an entry.
