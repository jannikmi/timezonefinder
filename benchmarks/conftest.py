"""Shared fixtures for the pytest-benchmark suites under ``benchmarks/``.

Not collected by `make test` / `make testall` (see `testpaths` in
`pyproject.toml`); run explicitly via `make benchmarks`.
"""

import numpy as np
import pytest

from scripts.benchmark_utils import get_system_status, tzfpy_version
from scripts.configs import DEBUG
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    benchmark_fixture_provenance,
    group_blocked_pip_inputs_by_stratum,
    group_pip_inputs_by_stratum,
    load_benchmark_points,
    load_pip_inputs,
    load_pip_strata,
    strict_numpy_warnings,  # noqa: F401  # re-exported as a fixture for this suite
)

# Fixed unit of work for every benchmark: one pass over a batch of this many
# points/inputs. Every round then performs identical work, which is what
# makes rounds within a benchmark (and the benchmark across commits)
# comparable. Changing this number invalidates historical trend data.
#
# Sized for the shortest tracked benchmark: unique-shortcut lookups are ~7x
# cheaper than ambiguous ones, so that batch is the noisiest in relative terms
# - and since one alert threshold covers every tracked benchmark, the noisiest
# one sets it. More *rounds* would not help (the tracked estimator is the min,
# whose variance comes from the runner's best-case state, not the sample
# size); per-round resolution is the lever, so this is it.
#
# Hard ceilings, enforced only as a ValueError when the fixtures are loaded:
#   - `_load_batch` below needs BATCH_SIZE points per fixture -> 5,000
#     (N_UNIQUE_SHORTCUT_POINTS / N_AMBIGUOUS_SHORTCUT_POINTS)
#   - `group_pip_inputs_by_stratum` (tests/auxiliaries.py) needs BATCH_SIZE
#     *per stratum*, and N_PIP_INPUTS=10,000 split three ways -> 3,333, the
#     binding one
# Raising past either means bumping the matching N_* in
# scripts/generate_benchmark_fixtures.py and regenerating.
BATCH_SIZE = 2_500


def pytest_benchmark_update_machine_info(config, machine_info) -> None:
    """Record numba/clang availability, BATCH_SIZE and the fixture/data
    provenance from the run that *produced* the measurements, not whichever
    checkout later renders the JSON into RST
    (scripts/render_benchmark_reports.py reads this back out). Without this,
    rendering an older stored JSON against a checkout where BATCH_SIZE has
    since changed would silently derive Time/Query and Throughput from the
    wrong batch size, and the report would not say which fixture set and
    boundary data the timings actually describe. The comparison suite adds a
    fourth thing a stored JSON must carry: the version of the *other* package
    it measured, which releases outside this repository entirely."""
    machine_info["timezonefinder"] = {
        **get_system_status(),
        **benchmark_fixture_provenance(),
        "batch_size": BATCH_SIZE,
        # None unless the `compare` dependency group is installed - see
        # `scripts.benchmark_utils.tzfpy_version` and benchmarks/test_comparison.py
        "tzfpy_version": tzfpy_version(),
    }


@pytest.fixture(autouse=True, scope="session")
def _reject_debug_mode() -> None:
    """A DEBUG-mode number in the trend chart is worse than a missing one."""
    if DEBUG:
        raise RuntimeError(
            "scripts.configs.DEBUG is True, which overrides SHORTCUT_H3_RES to a "
            "much coarser resolution. Benchmark numbers produced under DEBUG are "
            "not comparable to real measurements and must never be recorded. "
            "Run benchmarks with scripts.configs.DEBUG = False."
        )


def _load_batch(fixture_name: str) -> list[tuple[float, float]]:
    points = load_benchmark_points(fixture_name)
    if len(points) < BATCH_SIZE:
        raise ValueError(
            f"benchmark fixture {fixture_name!r} has only {len(points)} points, "
            f"but the benchmark suite needs at least {BATCH_SIZE}. Regenerate "
            "the fixtures with a larger count via `make benchmark-fixtures`."
        )
    return points[:BATCH_SIZE]


@pytest.fixture(scope="session")
def random_points() -> list[tuple[float, float]]:
    return _load_batch(RANDOM_POINTS_FIXTURE)


@pytest.fixture(scope="session")
def on_land_points() -> list[tuple[float, float]]:
    return _load_batch(ON_LAND_POINTS_FIXTURE)


@pytest.fixture(scope="session")
def unique_shortcut_points() -> list[tuple[float, float]]:
    return _load_batch(UNIQUE_SHORTCUT_POINTS_FIXTURE)


@pytest.fixture(scope="session")
def ambiguous_shortcut_points() -> list[tuple[float, float]]:
    return _load_batch(AMBIGUOUS_SHORTCUT_POINTS_FIXTURE)


@pytest.fixture(scope="session")
def blocked_pip_inputs_by_stratum() -> dict[
    str, list[tuple[int, int, np.ndarray, np.ndarray]]
]:
    """The same pairs, plus each polygon's latitude block ranges - what the kernel a
    lookup reaches is actually handed."""
    return group_blocked_pip_inputs_by_stratum(
        load_pip_inputs(), load_pip_strata(), BATCH_SIZE
    )


@pytest.fixture(scope="session")
def pip_inputs_by_stratum() -> dict[str, list[tuple[int, int, np.ndarray]]]:
    """(x, y, polygon_coords) triples grouped by size stratum, `BATCH_SIZE`
    entries each, so per-stratum cost isn't hidden behind an average."""
    return group_pip_inputs_by_stratum(load_pip_inputs(), load_pip_strata(), BATCH_SIZE)
