#!/usr/bin/env python3

"""Assert which point-in-polygon acceleration path is active in this environment.

``timezonefinder/utils.py`` picks the point-in-polygon implementation **at
import time**, and there are three outcomes rather than two: the Numba-JIT'd
Python function when ``numba`` is importable, the CFFI-backed clang C
extension when it is not but the extension loaded, and the *undecorated*
Python function when neither is available. These are completely different
code paths with very different performance, so a benchmark trend chart that
silently switches between them is worse than no chart at all: the history
would compare numbers that were never comparable. How far apart they actually
are is measured rather than asserted here - ``make acceleration-paths`` and
``docs/benchmark_results_acceleration_paths.rst`` - because it depends on the
workload and has moved as the kernels have.

The benchmark CI workflow (``.github/workflows/benchmark.yml``) therefore
asserts the expected path *before* running anything, rather than assuming
that "we did not install the numba group" is still true after a lockfile or
dependency change.

Usage::

    uv run python -m scripts.assert_acceleration_path --expect clang
    uv run python -m scripts.assert_acceleration_path --expect numba
    uv run python -m scripts.assert_acceleration_path --expect python
"""

import argparse
import sys
from collections.abc import Callable
from typing import Literal, get_args

import numpy as np

from timezonefinder import utils, utils_clang, utils_numba

AccelerationPath = Literal["clang", "numba", "python"]
ACCELERATION_PATHS: tuple[str, ...] = get_args(AccelerationPath)

# ``numba`` and ``python`` are the *same source* - ``timezonefinder/utils_numba.py``
# decorated or not. Which of the two a process holds is decided by whether ``numba``
# imported, never by which name is asked for, so the tables below map both to the same
# objects and :func:`check_acceleration_path` is what separates them. Naming them apart
# matters because they are far apart in speed: a numba-free install whose C extension
# failed to build used to report ``clang`` while running the pure-Python kernel, and a
# report page cannot label a column it cannot name.
NUMBA_SOURCED_PATHS: frozenset[str] = frozenset({"numba", "python"})

# the concrete function object `utils.inside_polygon` is bound to per path -
# checking the flags alone would not catch a mis-wired dispatch in utils.py.
# Public because tests/test_acceleration_paths.py binds these deliberately to
# cover the path this environment did *not* select at import time; keep the
# mapping declared here only.
ACCELERATION_IMPLEMENTATIONS: dict[str, Callable[[int, int, np.ndarray], bool]] = {
    "clang": utils_clang.pt_in_poly_clang,
    "numba": utils_numba.pt_in_poly_python,
    # the same object; see NUMBA_SOURCED_PATHS
    "python": utils_numba.pt_in_poly_python,
}

# And for the packed kernel, which is the one the lookup path actually runs
# (``PolygonArray.pip``), together with the factory that wraps a collection's arrays for
# it. The two go together and are listed as a pair on purpose: what a collection stores
# in ``PolygonArray.packed`` is whatever the bound factory made, so a kernel from one
# path handed the other's buffers is a segfault rather than a wrong answer. That pairing
# is also why swapping these rebinds nothing on a finder that already exists - a test
# covering the other path has to construct one *under* the patch. Since the kernel is
# captured beside the buffers (``PolygonArray.__init__``) that is enforced rather than
# merely required, which is what lets two collections on different paths coexist.
PACKED_ACCELERATION_IMPLEMENTATIONS: dict[str, Callable[..., bool]] = {
    "clang": utils_clang.pt_in_poly_clang_packed,
    "numba": utils_numba.pt_in_poly_packed,
    # the same object; see NUMBA_SOURCED_PATHS
    "python": utils_numba.pt_in_poly_packed,
}

PACKED_BUFFER_FACTORIES: dict[str, Callable[..., tuple]] = {
    "clang": utils_clang.packed_buffers_clang,
    "numba": utils_numba.packed_buffers_numba,
    # the same object; see NUMBA_SOURCED_PATHS
    "python": utils_numba.packed_buffers_numba,
}


def interpreted_path_name() -> AccelerationPath:
    """Which of the two ``utils_numba``-sourced names this process's copy goes by.

    The two are one source, so a process holds exactly one of them and no caller can
    ask for the other: with ``numba`` importable every ``utils_numba`` function is a
    JIT dispatcher, without it every one of them is the plain Python function. Anything
    naming the non-clang path - a report column, a benchmark fixture key, a test
    parametrisation - has to ask this rather than assume ``numba``.
    """
    return "numba" if utils.using_numba else "python"


def active_acceleration_path() -> AccelerationPath:
    """Return the acceleration path ``timezonefinder.utils`` actually bound.

    Three answers, not two. ``utils.py`` chooses the C extension only when numba is
    absent *and* the extension loaded, so the remaining case - neither available - runs
    the undecorated ``utils_numba`` functions. Reporting that as ``clang`` was wrong in
    the direction that matters: an install whose extension silently failed to build then
    looked, in every report it produced, like the configuration a working one runs.
    """
    if utils.inside_polygon_packed is utils_clang.pt_in_poly_clang_packed:
        return "clang"
    return interpreted_path_name()


def check_acceleration_path(expected: AccelerationPath) -> None:
    """Raise ``RuntimeError`` unless ``expected`` is the active path.

    Also verifies that ``utils.inside_polygon`` is the implementation that
    path is supposed to provide, and - for the clang path - that the C
    extension is loaded at all rather than having silently fallen back to
    the pure-Python implementation.
    """
    # Before the generic mismatch, because a missing extension has a fix and the
    # generic message does not name it. ``active`` cannot be ``clang`` in this case
    # anyway, so without this the actionable message would be unreachable.
    if expected == "clang" and not utils.clang_extension_loaded:
        raise RuntimeError(
            "the clang point-in-polygon C extension is not loaded, so the slow "
            "pure-Python fallback would be benchmarked instead. Build the "
            "extension (`uv sync`) before benchmarking."
        )
    active = active_acceleration_path()
    if active != expected:
        raise RuntimeError(
            f"expected the {expected!r} point-in-polygon acceleration path to be "
            f"active, but {active!r} is (utils.using_numba={utils.using_numba}, "
            f"utils.clang_extension_loaded={utils.clang_extension_loaded}). "
            "Benchmark numbers from different paths are not comparable and must "
            "never be recorded under the same benchmark names."
        )
    # ``numba`` and ``python`` share their function objects, so the identity checks
    # below cannot tell them apart - only the import-time flag can, and it is the whole
    # difference between a JIT-compiled kernel and an interpreted one.
    if expected in NUMBA_SOURCED_PATHS and expected != interpreted_path_name():
        raise RuntimeError(
            f"expected the {expected!r} point-in-polygon acceleration path, but "
            f"utils.using_numba={utils.using_numba}. The Numba and pure-Python paths "
            "are the same source decorated or not, so only the environment decides "
            "which one runs: install the `numba` group to get 'numba', omit it to get "
            "'python'."
        )
    for attribute, table in (
        ("inside_polygon", ACCELERATION_IMPLEMENTATIONS),
        ("inside_polygon_packed", PACKED_ACCELERATION_IMPLEMENTATIONS),
        ("packed_buffers", PACKED_BUFFER_FACTORIES),
    ):
        expected_impl = table[expected]
        bound = getattr(utils, attribute)
        if bound is not expected_impl:
            raise RuntimeError(
                f"the {expected!r} acceleration path is active, but "
                f"utils.{attribute} is bound to {bound!r} instead "
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
