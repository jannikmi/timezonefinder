"""pytest-benchmark suite comparing this package head-to-head against ``tzfpy``.

Why this suite exists
---------------------

``docs/alternatives.rst`` weighs the two packages against each other, and its
speed and startup rows used to be qualitative because the two had only ever
been measured apart - different machines, different acceleration paths,
different query workloads. That is exactly the comparison this project refuses
to make for its own numbers (``docs/benchmarking_methodology.rst``), so it had
no business making it about someone else's. This suite removes the excuse: both
packages answer the *same committed query fixtures* in the *same process on the
same machine*, so the ratio between them is a measurement rather than an
impression.

What is deliberately *not* tracked
----------------------------------

None of these benchmarks carry ``benchmark_core``, so none of them reach the CI
trend chart. Two reasons, both structural rather than a matter of budget:

- the number is a ratio between two packages, and one of them releases on a
  schedule this repository does not control. A step in that chart would as
  often mean "they shipped a release" as "we changed something", and nothing on
  the chart could tell a reader which
- the tracked measurement environment is ``uv sync --group test``
  (``.github/workflows/benchmark.yml``), deliberately kept to what a plain
  ``pip install timezonefinder`` gives you. ``tzfpy`` is not in it and must not
  be

Fairness
--------

Each package is driven through its own natural API inside its own loop, so
neither pays for an adapter frame the other does not. That matters more than it
looks: a lambda wrapper costs tens of nanoseconds against per-query times of a
few hundred, so normalising the two call signatures into one shared callable
would have handed one side a penalty of the same order as the thing being
measured. ``timezone_at`` is keyword-only and ``get_tz`` is positional; each
loop below calls its own the way its own users do.

The optional dependency
-----------------------

``tzfpy`` lives in the ``compare`` dependency group, which only ``make
benchmarks`` and ``tox -e benchmarks`` install. Every benchmark here is
therefore written to **collect** without it and skip at setup: the set of
benchmark node ids is pinned by ``tests/test_benchmark_names.py`` and must not
depend on which optional packages happen to be installed, or that test starts
passing and failing by environment.
"""

import subprocess
import sys

import pytest

from scripts.benchmark_utils import TZFPY_DISTRIBUTION
from timezonefinder import TimezoneFinder, TimezoneFinderL

# The point classes this comparison is stratified by, same fixtures and same
# ids as benchmarks/test_timezone_finding.py - a reader comparing the two pages
# should not have to translate. `random` is the representative one (it holds
# unique- and ambiguous-shortcut points in their real ratio); the other three
# say where any difference comes from.
POINT_FIXTURES = [
    pytest.param("random_points", id="random"),
    pytest.param("on_land_points", id="on_land"),
    pytest.param("unique_shortcut_points", id="unique_shortcut"),
    pytest.param("ambiguous_shortcut_points", id="ambiguous_shortcut"),
]

# `in_memory=True` for the same reason test_timezone_finding.py tracks that
# mode: the file-based path carries its own I/O noise, and this page is about
# the gap between two libraries, not between two of this one's storage modes -
# which docs/benchmark_results_timezonefinding.rst already measures.
IN_MEMORY = True

# One land coordinate, only ever used to force a first lookup. Which zone comes
# back is irrelevant here and deliberately not asserted - this measures the
# work before the answer, not the answer.
FIRST_ANSWER_LNG, FIRST_ANSWER_LAT = 13.4, 52.5

_LOOKUP = f"timezone_at(lng={FIRST_ANSWER_LNG}, lat={FIRST_ANSWER_LAT})"

# Each snippet is run in a fresh interpreter, because the cost being measured
# happens exactly once per process and cannot be repeated in one: `tzfpy`
# deserialises its index lazily on the first query, and a `TimezoneFinder`
# reads its index when constructed. `baseline` is what an interpreter that
# imports nothing costs, and is what makes the other four rows readable - all
# of them include it, and subtracting it is the reader's job.
FIRST_ANSWER_CASES = [
    pytest.param("pass", False, id="baseline"),
    pytest.param(
        f"import {TZFPY_DISTRIBUTION}; "
        f"{TZFPY_DISTRIBUTION}.get_tz({FIRST_ANSWER_LNG}, {FIRST_ANSWER_LAT})",
        True,
        id="tzfpy",
    ),
    pytest.param(
        f"from timezonefinder import TimezoneFinder; TimezoneFinder().{_LOOKUP}",
        False,
        id="timezonefinder-file_based",
    ),
    pytest.param(
        "from timezonefinder import TimezoneFinder; "
        f"TimezoneFinder(in_memory=True).{_LOOKUP}",
        False,
        id="timezonefinder-in_memory",
    ),
    pytest.param(
        f"from timezonefinder import TimezoneFinderL; TimezoneFinderL().{_LOOKUP}",
        False,
        id="timezonefinderl",
    ),
]

# rounds, not iterations: every round must be a fresh interpreter. Twenty of
# them at ~100ms each keeps this suite's slowest part around ten seconds while
# still giving the tracked minimum a real sample to be drawn from.
FIRST_ANSWER_ROUNDS = 20

# Pinned rather than left to pytest-benchmark's calibration, which sizes the
# round count from one timed calibration round against a time budget. That is
# fine when a benchmark is only ever compared with its own history, and not
# fine here: an unlucky calibration round gave the fastest row in this suite ten
# rounds while the row beside it got six hundred, and the whole point of these
# benchmarks is that the rows are read against each other. A hundred rounds
# costs a few seconds even for the slowest case and gives every row the same
# footing under the minimum this report tracks.
LOOKUP_MIN_ROUNDS = 100


@pytest.fixture(scope="session")
def tzfpy():
    """The comparison package, or a skip.

    ``importorskip`` inside a fixture rather than at module level on purpose:
    the latter skips at *collection*, which would make the node ids this suite
    contributes depend on whether an optional group is installed - see the
    module docstring.
    """
    return pytest.importorskip(
        TZFPY_DISTRIBUTION,
        reason=(
            f"{TZFPY_DISTRIBUTION} is not installed - it lives in the `compare` "
            "dependency group (`uv sync --group compare`, or `make benchmarks`, "
            "which asks for it)"
        ),
    )


def _run_timezonefinder(finder, points) -> None:
    for lng, lat in points:
        finder.timezone_at(lng=lng, lat=lat)


def _run_tzfpy(get_tz, points) -> None:
    for lng, lat in points:
        get_tz(lng, lat)


@pytest.mark.benchmark(min_rounds=LOOKUP_MIN_ROUNDS)
@pytest.mark.parametrize("points_fixture_name", POINT_FIXTURES)
def test_lookup_timezonefinder(benchmark, request, points_fixture_name):
    points = request.getfixturevalue(points_fixture_name)
    finder = TimezoneFinder(in_memory=IN_MEMORY)
    benchmark(_run_timezonefinder, finder, points)


@pytest.mark.benchmark(min_rounds=LOOKUP_MIN_ROUNDS)
@pytest.mark.parametrize("points_fixture_name", POINT_FIXTURES)
def test_lookup_timezonefinderl(benchmark, request, points_fixture_name):
    # the like-for-like against `tzfpy`'s own trade: TimezoneFinderL answers
    # from the shortcut index alone and gives up exactness at borders to do it,
    # which is the same bargain simplified polygons strike
    points = request.getfixturevalue(points_fixture_name)
    benchmark(_run_timezonefinder, TimezoneFinderL(), points)


@pytest.mark.benchmark(min_rounds=LOOKUP_MIN_ROUNDS)
@pytest.mark.parametrize("points_fixture_name", POINT_FIXTURES)
def test_lookup_tzfpy(benchmark, request, tzfpy, points_fixture_name):
    points = request.getfixturevalue(points_fixture_name)
    benchmark(_run_tzfpy, tzfpy.get_tz, points)


@pytest.mark.benchmark
@pytest.mark.parametrize("snippet, needs_tzfpy", FIRST_ANSWER_CASES)
def test_first_answer(benchmark, request, snippet, needs_tzfpy):
    """Wall clock from ``python -c`` to one answered lookup.

    This is the honest form of the "startup time" row: what a reader is
    choosing between is time-to-first-answer, and the two packages spend it in
    completely different places - one on importing NumPy and H3 and building an
    index, the other on deserialising its own index inside the first query. A
    benchmark that timed only construction would score the second as free.

    The OS page cache is warm from round two onwards, for both packages
    equally. That is the realistic case (a service restarting on a machine that
    has run it before), not the pessimal one.
    """
    if needs_tzfpy:
        request.getfixturevalue("tzfpy")
    command = [sys.executable, "-c", snippet]

    def first_answer() -> None:
        subprocess.run(command, check=True)

    benchmark.pedantic(
        first_answer, rounds=FIRST_ANSWER_ROUNDS, warmup_rounds=0, iterations=1
    )
