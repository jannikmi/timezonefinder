"""Shared fixtures for the pytest-benchmark suites under ``benchmarks/``.

Not collected by `make test` / `make testall` (see `testpaths` in
`pyproject.toml`); run explicitly via `make benchmarks`.
"""

import warnings
from typing import Iterator

import numpy as np
import pytest

from scripts.benchmark_utils import get_system_status
from scripts.configs import DEBUG
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    PIP_INPUTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    boundaries,
    load_benchmark_points,
    load_pip_inputs,
    load_pip_strata,
)

# Fixed unit of work for every benchmark: one pass over a batch of this many
# points/inputs. Every round then performs identical work, which is what
# makes rounds within a benchmark (and the benchmark across commits)
# comparable. Changing this number invalidates historical trend data.
BATCH_SIZE = 1_000


def pytest_benchmark_update_machine_info(config, machine_info) -> None:
    """Record numba/clang availability under the machine that *ran* the
    benchmarks, not whichever machine later renders the JSON into RST
    (scripts/render_benchmark_reports.py reads this back out)."""
    machine_info["timezonefinder"] = get_system_status()


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
def pip_inputs_by_stratum() -> dict[str, list[tuple[int, int, np.ndarray]]]:
    """(x, y, polygon_coords) triples grouped by size stratum, `BATCH_SIZE`
    entries each, so per-stratum cost isn't hidden behind an average."""
    inputs = load_pip_inputs()
    strata = load_pip_strata()
    grouped: dict[str, list[tuple[int, int, np.ndarray]]] = {}
    for (x, y, poly_id), stratum in zip(inputs, strata):
        bucket = grouped.setdefault(stratum, [])
        if len(bucket) < BATCH_SIZE:
            bucket.append((x, y, boundaries.coords_of(poly_id)))
    for stratum, bucket in grouped.items():
        if len(bucket) < BATCH_SIZE:
            raise ValueError(
                f"benchmark fixture {PIP_INPUTS_FIXTURE!r} has only {len(bucket)} "
                f"'{stratum}' entries, but the benchmark suite needs at least "
                f"{BATCH_SIZE} per stratum. Regenerate the fixtures with a larger "
                "count via `make benchmark-fixtures`."
            )
    return grouped


@pytest.fixture
def strict_numpy_warnings() -> Iterator[None]:
    """Turn numpy overflow/invalid-value warnings into errors for one test.

    Scoped per-test (not module scope, unlike the old
    `scripts/check_speed_inside_polygon.py`) so it cannot leak into other
    modules collected in the same pytest session.
    """
    original_state = np.seterr(all="warn")
    with warnings.catch_warnings():
        warnings.filterwarnings("error")
        try:
            yield
        finally:
            np.seterr(**original_state)
