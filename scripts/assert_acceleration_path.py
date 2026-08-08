#!/usr/bin/env python3

"""Assert which point-in-polygon acceleration path is active in this environment.

``timezonefinder/utils.py`` picks the point-in-polygon implementation **at
import time**: the Numba-JIT'd Python function when ``numba`` is importable,
the CFFI-backed clang C extension otherwise. These are completely different
code paths with very different performance, so a benchmark trend chart that
silently switches between them is worse than no chart at all - the history
would compare numbers that were never comparable.

The benchmark CI workflow (``.github/workflows/benchmark.yml``) therefore
asserts the expected path *before* running anything, rather than assuming
that "we did not install the numba group" is still true after a lockfile or
dependency change.

Usage::

    uv run python -m scripts.assert_acceleration_path --expect clang
    uv run python -m scripts.assert_acceleration_path --expect numba
"""

import argparse
import sys
from collections.abc import Callable
from typing import Literal, get_args

import numpy as np

from timezonefinder import utils, utils_clang, utils_numba

AccelerationPath = Literal["clang", "numba"]
ACCELERATION_PATHS: tuple[str, ...] = get_args(AccelerationPath)

# the concrete function object `utils.inside_polygon` is bound to per path -
# checking the flags alone would not catch a mis-wired dispatch in utils.py.
# Public because tests/test_acceleration_paths.py binds these deliberately to
# cover the path this environment did *not* select at import time; keep the
# mapping declared here only.
ACCELERATION_IMPLEMENTATIONS: dict[str, Callable[[int, int, np.ndarray], bool]] = {
    "clang": utils_clang.pt_in_poly_clang,
    "numba": utils_numba.pt_in_poly_python,
}


def active_acceleration_path() -> AccelerationPath:
    """Return the acceleration path ``timezonefinder.utils`` actually bound."""
    return "numba" if utils.using_numba else "clang"


def check_acceleration_path(expected: AccelerationPath) -> None:
    """Raise ``RuntimeError`` unless ``expected`` is the active path.

    Also verifies that ``utils.inside_polygon`` is the implementation that
    path is supposed to provide, and - for the clang path - that the C
    extension is loaded at all rather than having silently fallen back to
    the pure-Python implementation.
    """
    active = active_acceleration_path()
    if active != expected:
        raise RuntimeError(
            f"expected the {expected!r} point-in-polygon acceleration path to be "
            f"active, but {active!r} is (utils.using_numba={utils.using_numba}, "
            f"utils.clang_extension_loaded={utils.clang_extension_loaded}). "
            "Benchmark numbers from the two paths are not comparable and must "
            "never be recorded under the same benchmark names."
        )
    if expected == "clang" and not utils.clang_extension_loaded:
        raise RuntimeError(
            "the clang point-in-polygon C extension is not loaded, so the slow "
            "pure-Python fallback would be benchmarked instead. Build the "
            "extension (`uv sync`) before benchmarking."
        )
    expected_impl = ACCELERATION_IMPLEMENTATIONS[expected]
    if utils.inside_polygon is not expected_impl:
        raise RuntimeError(
            f"the {expected!r} acceleration path is active, but "
            f"utils.inside_polygon is bound to {utils.inside_polygon!r} instead "
            f"of {expected_impl!r} - the dispatch in timezonefinder/utils.py "
            "does not match the reported flags."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Assert which point-in-polygon acceleration path timezonefinder "
            "bound at import time. Exits non-zero on a mismatch."
        )
    )
    parser.add_argument(
        "--expect",
        required=True,
        choices=ACCELERATION_PATHS,
        help="the acceleration path that must be active",
    )
    args = parser.parse_args()
    try:
        check_acceleration_path(args.expect)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: the {args.expect!r} point-in-polygon acceleration path is active")


if __name__ == "__main__":
    main()
