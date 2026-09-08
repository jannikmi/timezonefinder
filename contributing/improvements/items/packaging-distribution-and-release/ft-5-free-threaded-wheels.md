# FT-5 — free-threaded wheels

- **Where:** `pyproject.toml`, `[tool.cibuildwheel]` (`CIBW_BUILD`, currently `cp311-*`) and `.github/workflows/build.yml`.
- **What it is:** shipping wheels a free-threaded interpreter can install. Today none exist and none can: 8.3.0 ships three `cp311-abi3` Linux wheels plus the sdist, and a single abi3 wheel cannot serve a free-threaded build at all. Turning it on means adding free-threaded identifiers to `CIBW_BUILD`, which is `cp311-*` today.
- **Do not add `CIBW_ENABLE=cpython-freethreading`.** Issue #364 prescribes it; the workflow pins `pypa/cibuildwheel@v4.2.0`, whose enable groups are `cpython-prerelease`, `graalpy`, `pypy`, `pypy-eol`, `pyodide-eol` and `pyodide-prerelease` — free-threaded builds are no longer gated behind one, and the unknown group exits non-zero. Verified 2026-09-08: with that pin, `CIBW_BUILD='cp313t-* cp314t-*'` prints `cp314t-manylinux_x86_64` and `cp314t-musllinux_x86_64` and needs no enable group at all.
- **The same check narrows the decision below:** cibuildwheel 4.2.0 offers no `cp313t` identifier for this project at all, so "3.13t as well" is not merely expensive, it is not currently buildable without moving the pin.
- **Not urgent, and that is the point:** source installs already work on 3.13t and 3.14t today, so nothing is broken while this waits — it buys convenience at a permanent artifact cost, which is why it is a decision rather than a task.
- **Decision needed:** which free-threaded interpreters to ship wheels for.
  - **3.15t only, via `abi3t`** — 7 artifacts (+3), and **no growth per CPython release** thereafter. CPython 3.15 introduces `abi3t`, a stable ABI for free-threaded builds that also covers non-free-threaded 3.15+. The precondition is met: `uv.lock` holds cffi 2.1.1 and `abi3t` support arrived in cffi 2.1.0. Untested for this extension — cffi claims support and only 3.15.0a2 was available during scoping.
  - **3.13t and 3.14t as well** — 10 artifacts (2.5x today), and **+3 per CPython release** until 3.15, because CPython's own table says those two versions can never be served by `abi3t`. They are simultaneously the expensive option and the versions with the shortest remaining life.
  - **Recommendation: 3.15t only.** It costs +3 once and nothing thereafter, and the versions it declines to serve are the ones that expire first. Revisit only if free-threaded 3.13t/3.14t demand is actually voiced.
- **Blocked on [FT-1](ft-1-setup-py-claims-abi3-where-the-interpreter-forbids-it.md) whichever way it is decided:** the `select = "*"` override sets `BUILD_ABI3=true` for every identifier, so adding a free-threaded identifier before that guard lands breaks the wheel job instead of building anything. **Check the guard FT-1 actually shipped before building on it**, and specifically that it did not turn the abi3 claim off for 3.15t: the unqualified form of that guard would disable the very wheel the recommendation below rests on.
- **This item owns the wheel tag.** Whether a 3.15t stable-ABI build keeps `py_limited_api="cp311"`, needs a `cp315` base, or needs something else for `abi3t` is untested — cffi claims support and only 3.15.0a2 was available during scoping — and `tests/test_python_version_support.py` asserts against that literal, so whatever is chosen has to be reconciled with it.
- **Size:** M.
- **Status:** needs the interpreter-set decision above, and blocked on FT-1.
- **Detail:** issue #364 carries the artifact arithmetic and the cibuildwheel identifier list.

## Related memory

- [Data distribution packaging and release decisions](../../decisions/data-distribution-packaging-and-release-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
