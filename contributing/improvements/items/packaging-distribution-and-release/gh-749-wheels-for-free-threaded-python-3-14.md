# GH-749 — wheels for free-threaded Python 3.14

- **Tracks:** issue #749, where demand for `cp314t` wheels is collected.
- **What it would be:** a `cp314t-*` identifier in `CIBW_BUILD_VERSIONS` in `.github/workflows/build.yml`, built version-specific since `setup.py` withholds every stable-ABI claim from a free-threaded build below 3.15, plus a `cp314t` leg in the end-to-end matrix. `tests/test_python_version_support.py` then has to admit a second free-threaded identifier.
- **Why it waits:** the cost and the refusal are in the [distribution decisions](../../decisions/data-distribution-packaging-and-release-decisions.md). They refuse it on missing demand, not on merit.
- **Resume on:** a user on issue #749 saying the sdist build does not work for them. The item is moot once 3.14 leaves the supported versions, NEP 29's 2029-04-07.
- **Size:** S.
- **Status:** parked — resume only on demand voiced on issue #749.
- **Last touched:** 2026-10-22 — split out of issue #721 when the `abi3t` wheels shipped.
