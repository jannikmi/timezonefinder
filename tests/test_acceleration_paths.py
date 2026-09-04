"""Drive both point-in-polygon acceleration paths through the *real* lookup stack.

``timezonefinder/utils.py`` binds ``inside_polygon_packed`` once, at import time, and
Numba wins whenever it is importable::

    if clang_extension_loaded and not using_numba:
        inside_polygon_packed = utils_clang.pt_in_poly_clang_packed

The recommended local setup installs Numba - ``make install`` / ``uv sync
--all-groups`` pull in the ``numba`` group, and ``uv run`` syncs *inexactly*, so it
stays for every later invocation. A developer machine therefore binds the Numba
dispatcher, and the C extension is reached only by the direct-kernel tests in
``utils_test.py``, which feed it hand-built arrays from ``convert_polygon``.
Everything about how *real* polygon buffers arrive at the C function - dtypes,
C-contiguity, read-only memory-mapped views, the lifetime of the ``ffi.from_buffer``
handles - used to be exercised first in CI's non-numba tox envs, i.e. the
configuration a plain ``pip install timezonefinder`` produces.

These tests close that gap by building a finder with the other path's kernel bound.
The finder has to be built *under* the patch since polygon layout 3: a collection wraps
its payload for the bound backend once, when it is loaded, so a kernel swapped in
afterwards would be handed the other backend's buffers. Both implementations therefore
run against the real coordinate accessors whatever happens to be installed - and against
the real latitude block index and payload, which is what decides which edges either
kernel ever sees.
"""

from collections.abc import Callable

import pytest

from scripts.assert_acceleration_path import (
    ACCELERATION_PATHS,
    PACKED_ACCELERATION_IMPLEMENTATIONS,
    PACKED_BUFFER_FACTORIES,
    interpreted_path_name,
)
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
    single_location_test,
)
from tests.locations import TEST_LOCATIONS, TEST_LOCATIONS_AT_LAND
from timezonefinder import TimezoneFinder, utils

# ``utils_test.py::test_clang_extension_loaded`` is the loud guard that the extension
# is present at all. Skipping here rather than failing keeps that single assertion the
# one place that reports a missing extension, instead of a cascade of failures.
pytestmark = pytest.mark.skipif(
    not utils.clang_extension_loaded,
    reason="the clang C extension is not loaded, so there is no second path to compare",
)

# Points whose H3 shortcut cell holds boundaries of more than one zone: the shortcut
# layer cannot answer them, so the PIP implementation actually decides the result.
# A slice keeps this inside `make test`'s budget - the count is asserted to produce
# PIP calls below, so shrinking it can never silently empty the workload.
NR_AGREEMENT_POINTS = 1_000

# `certain_timezone_at` is deliberately absent: it checks every candidate polygon and
# costs several seconds over this many points. `timezone_at` and `timezone_at_land`
# reach the same `PolygonArray.pip` entry point.
LOOKUP_METHOD_NAMES = ["timezone_at", "timezone_at_land"]

FINDER_FIXTURE_NAMES = ["timezonefinder_in_memory", "timezonefinder_disk"]

# The two *distinct* implementations this process holds. Not `ACCELERATION_PATHS`,
# which names three: `numba` and `python` are one source decorated or not, so whichever
# of them this environment did not produce is not a second implementation to compare
# against - it is the same object under another name, and running it would double the
# suite's cost to re-measure agreement with itself.
COMPARED_PATHS = ("clang", interpreted_path_name())


def _ambiguous_points() -> list[tuple[float, float]]:
    points = load_benchmark_points(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)
    return points[:NR_AGREEMENT_POINTS]


def _bind_path(monkeypatch: pytest.MonkeyPatch, path: str) -> Callable[[], int]:
    """Bind ``path``'s packed kernel and buffer factory, counting the kernel's calls.

    Returns a callable giving the count so far. Counting matters because equal results
    alone would pass trivially if the shortcut layer answered every query and the
    point-in-polygon implementation never ran - the same silent no-coverage failure
    these tests exist to prevent.
    """
    impl = PACKED_ACCELERATION_IMPLEMENTATIONS[path]
    calls = 0

    def counting_impl(*args):
        nonlocal calls
        calls += 1
        return impl(*args)

    monkeypatch.setattr(utils, "inside_polygon_packed", counting_impl)
    monkeypatch.setattr(utils, "packed_buffers", PACKED_BUFFER_FACTORIES[path])
    return lambda: calls


def _lookup_all(
    method_name: str, points: list[tuple[float, float]], path: str, in_memory: bool
) -> tuple[list[str | None], int]:
    """Run ``points`` through a finder built with ``path``'s implementation bound.

    The finder is built inside the patch rather than reused: it wraps its payload for
    whichever backend is bound at construction, so a finder built outside would answer
    from the other path's buffers however the kernel is swapped afterwards.
    """
    with pytest.MonkeyPatch.context() as monkeypatch:
        count = _bind_path(monkeypatch, path)
        finder = TimezoneFinder(in_memory=in_memory)
        try:
            method = getattr(finder, method_name)
            results = [method(lng=lng, lat=lat) for lng, lat in points]
        finally:
            finder.cleanup()

    return results, count()


@pytest.mark.unit
@pytest.mark.parametrize("finder_fixture", FINDER_FIXTURE_NAMES)
@pytest.mark.parametrize("method_name", LOOKUP_METHOD_NAMES)
def test_lookups_agree_across_acceleration_paths(
    request: pytest.FixtureRequest, method_name: str, finder_fixture: str
) -> None:
    """Both implementations must return the same answers on the real data.

    Runs against the in-memory and the memory-mapped finder, since only the latter
    hands the C extension read-only mmap views.
    """
    in_memory = finder_fixture == "timezonefinder_in_memory"
    points = _ambiguous_points()

    results = {
        path: _lookup_all(method_name, points, path, in_memory)
        for path in COMPARED_PATHS
    }

    for path, (_, calls) in results.items():
        assert calls > 0, (
            f"the {path!r} point in polygon implementation was never called for "
            f"{method_name} - the workload no longer reaches the PIP stage, so this "
            "test proves nothing about it"
        )

    other = interpreted_path_name()
    clang_results, _ = results["clang"]
    other_results, _ = results[other]
    mismatches = [
        (point, clang, interpreted)
        for point, clang, interpreted in zip(points, clang_results, other_results)
        if clang != interpreted
    ]
    assert not mismatches, (
        f"{len(mismatches)} of {len(points)} {method_name} lookups disagree between "
        f"the acceleration paths (clang vs {other}), first: {mismatches[0]}"
    )


@pytest.mark.unit
def test_finders_on_different_paths_coexist_and_agree() -> None:
    """Two finders, two backends, one process - which is what a comparison needs.

    A collection wraps its payload for the bound backend when it is loaded, so before
    the kernel was captured beside those buffers the second finder's lookups ran
    whichever kernel the *module* happened to hold: one backend's buffers through the
    other's kernel. Numba's eager signature refuses those - it sees five ``pyobject``
    arguments where it declared arrays - and the C kernel, which has no such guard, is
    handed numpy arrays where it expects cffi handles. Nothing could hold both alive,
    so no paired A/B of the two paths through the public API was possible -
    and a paired A/B is the only design ``docs/benchmarking_methodology.rst`` accepts
    for two candidates in one working tree.

    Both finders are therefore built here, under their own patch, and then used
    *interleaved* - alternating point by point, as the harness alternates round by
    round. Building them in sequence and querying them in sequence would pass even with
    the kernel read per call, since the module would happen to hold the right one at
    each moment.
    """
    points = _ambiguous_points()
    other = interpreted_path_name()

    with pytest.MonkeyPatch.context() as monkeypatch:
        clang_calls = _bind_path(monkeypatch, "clang")
        clang_finder = TimezoneFinder(in_memory=False)
    with pytest.MonkeyPatch.context() as monkeypatch:
        other_calls = _bind_path(monkeypatch, other)
        other_finder = TimezoneFinder(in_memory=False)

    # Neither patch is in force any more: whatever `utils.inside_polygon_packed` holds
    # now, each finder has to run the kernel it was built with. That is the property.
    try:
        mismatches = [
            (point, clang_answer, other_answer)
            for point in points
            for clang_answer, other_answer in [
                (
                    clang_finder.timezone_at(lng=point[0], lat=point[1]),
                    other_finder.timezone_at(lng=point[0], lat=point[1]),
                )
            ]
            if clang_answer != other_answer
        ]
    finally:
        clang_finder.cleanup()
        other_finder.cleanup()

    assert clang_calls() > 0 and other_calls() > 0, (
        "one of the two finders never reached its point-in-polygon kernel, so this "
        f"proves nothing: clang={clang_calls()}, {other}={other_calls()}"
    )
    assert not mismatches, (
        f"{len(mismatches)} of {len(points)} interleaved lookups disagree between "
        f"coexisting clang and {other} finders, first: {mismatches[0]}"
    )


@pytest.mark.unit
@pytest.mark.parametrize("lat, lng, description, expected", TEST_LOCATIONS)
def test_timezone_at_on_the_clang_path(
    monkeypatch: pytest.MonkeyPatch,
    lat: float,
    lng: float,
    description: str,
    expected: str,
) -> None:
    """The clang path must produce the known-correct answers, not merely agree.

    Agreement with Numba would also hold if both were broken the same way; these are
    the same expectations ``global_functions_test.py`` pins for the default path.
    The memory-mapped finder is used because its read-only views are what the C
    extension never saw locally, and it is built here rather than taken from a fixture
    because the binding happens when a collection is loaded.
    """
    _bind_path(monkeypatch, "clang")
    finder = TimezoneFinder(in_memory=False)
    try:
        single_location_test(finder.timezone_at, lat, lng, description, expected)
    finally:
        finder.cleanup()


@pytest.mark.unit
@pytest.mark.parametrize("lat, lng, description, expected", TEST_LOCATIONS_AT_LAND)
def test_timezone_at_land_on_the_clang_path(
    monkeypatch: pytest.MonkeyPatch,
    lat: float,
    lng: float,
    description: str,
    expected: str,
) -> None:
    _bind_path(monkeypatch, "clang")
    finder = TimezoneFinder(in_memory=False)
    try:
        single_location_test(finder.timezone_at_land, lat, lng, description, expected)
    finally:
        finder.cleanup()


@pytest.mark.unit
@pytest.mark.parametrize("path", ACCELERATION_PATHS)
def test_using_clang_pip_reports_the_bound_implementation(
    monkeypatch: pytest.MonkeyPatch, tf, path: str
) -> None:
    """``using_clang_pip()`` must track the binding, not just return *a* bool.

    ``main_test.py::test_using_clang_pip`` only asserts ``isinstance(res, bool)``,
    which passes on either path and so cannot catch the accessor going stale.
    """
    monkeypatch.setattr(
        utils, "inside_polygon_packed", PACKED_ACCELERATION_IMPLEMENTATIONS[path]
    )

    assert tf.using_clang_pip() is (path == "clang")
