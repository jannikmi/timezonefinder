# FT-1 — `setup.py` claims abi3 where the interpreter forbids it

- **Where:** `setup.py`, `_abi3`; and `pyproject.toml`, the `[[tool.cibuildwheel.overrides]]` block with `select = "*"` that sets `BUILD_ABI3 = "true"`.
- **Defect:** `_abi3 = bool(os.getenv("BUILD_ABI3", ""))` consults the environment alone. A free-threaded build has no stable ABI at all — CPython's 3.14 howto says so, and cffi enforces it independently by forcing `recompiler.USE_LIMITED_API` to `False` whenever `Py_GIL_DISABLED` is set — so the claim is not merely wrong there, it is fatal: `BUILD_ABI3=true uv build --python 3.14t --wheel` fails with `ValueError: py_limited_api='cp311' not supported. Py_LIMITED_API is currently incompatible with Py_GIL_DISABLED`.
- **Why it is ranked here:** the `select = "*"` override applies `BUILD_ABI3=true` to *every* cibuildwheel identifier, so the first free-threaded identifier anyone adds to `CIBW_BUILD` breaks the wheel job rather than producing a wheel. It costs ~5 lines to make that impossible, and it is the precondition [FT-5](ft-5-free-threaded-wheels.md) needs before any free-threaded identifier can be selected.
- **The fix** is CPython's own one-liner — gate the flag on the interpreter as well as the environment: `_abi3 = bool(os.getenv("BUILD_ABI3", "")) and not sysconfig.get_config_var("Py_GIL_DISABLED")`.
- **Keep the `"py_limited_api": "cp311"` literal in place.** `tests/test_python_version_support.py::test_the_abi3_base_is_the_lowest_supported_version` regex-matches that exact string out of `setup.py`, and asserts explicitly that the test must be updated if it disappears. The guard belongs on `_abi3`, not on the literal.
- **Test:** the interpreter this repository's CI runs on is not free-threaded, so a test cannot exercise the true branch by building. Assert the source contract instead — that `_abi3` is not decided by the environment alone — beside the existing `py_limited_api` assertion in `tests/test_python_version_support.py`, which already exists to catch exactly this class of drift between `setup.py`, `pyproject.toml` and `build.yml`.
- **Size:** ~15 lines including the test.
- **Status:** open — no decision and no blocker; it is a latent build failure with a one-line fix.
- **Detail:** issue #364 carries the packaging scoping this was sliced out of, including the verified failure output.

## Related memory

- [Public API compatibility and runtime loading decisions](../../decisions/public-api-compatibility-and-runtime-loading-decisions.md)
- [Improvement sequencing and preconditions](../../improvement-sequencing-and-preconditions.md)
