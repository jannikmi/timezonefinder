"""pytest-benchmark suite for the point-in-polygon implementations.

Compares the clang (C extension) and pure-Python (optionally Numba-JIT)
implementations across the small/medium/large polygon-vertex-count strata
of the committed `pip_inputs` benchmark fixture (see
`scripts/generate_benchmark_fixtures.py`), so the cost of the largest
polygons isn't hidden behind an unweighted average over the mostly-small
polygon population.

Each kernel is timed in **both** of its forms, under separate names. The `blocked`
ones take a ring together with its stored latitude block index and are what a lookup
reaches (`PolygonArray.pip`); the bare ones take a ring alone and are what the
build-time geometry helpers and the raw-algorithm tests run. Timing only the bare form
would describe a code path no query takes, and dropping it would stop measuring one
that plenty of build-time code does - so both are tracked, and the gap between them at
the `large` stratum is what the block index buys.
"""

from typing import Callable, Iterable

import numpy as np
import pytest

from timezonefinder import utils_clang, utils_numba
from timezonefinder.configs import POLYGON_BLOCK_SIZE

STRATA = [
    pytest.param("small", id="small"),
    pytest.param("medium", id="medium"),
    pytest.param("large", id="large"),
]


def _run_over(func: Callable, inputs: Iterable[tuple[int, int, np.ndarray]]) -> None:
    for x, y, poly in inputs:
        func(x, y, poly)


@pytest.mark.benchmark
@pytest.mark.parametrize("stratum", STRATA)
@pytest.mark.usefixtures("strict_numpy_warnings")
def test_pt_in_poly_clang(benchmark, pip_inputs_by_stratum, stratum):
    inputs = pip_inputs_by_stratum[stratum]
    benchmark(_run_over, utils_clang.pt_in_poly_clang, inputs)


@pytest.mark.benchmark
@pytest.mark.parametrize("stratum", STRATA)
@pytest.mark.usefixtures("strict_numpy_warnings")
def test_pt_in_poly_python(benchmark, pip_inputs_by_stratum, stratum):
    # uses Numba JIT when available (utils.using_numba), the CFFI-backed
    # clang fallback otherwise - see timezonefinder/utils_numba.py
    inputs = pip_inputs_by_stratum[stratum]
    benchmark(_run_over, utils_numba.pt_in_poly_python, inputs)


def _run_over_blocked(
    func: Callable, inputs: Iterable[tuple[int, int, np.ndarray, np.ndarray]]
) -> None:
    for x, y, poly, block_ranges in inputs:
        func(x, y, poly, block_ranges, POLYGON_BLOCK_SIZE)


@pytest.mark.benchmark
@pytest.mark.parametrize("stratum", STRATA)
@pytest.mark.usefixtures("strict_numpy_warnings")
def test_pt_in_poly_clang_blocked(benchmark, blocked_pip_inputs_by_stratum, stratum):
    inputs = blocked_pip_inputs_by_stratum[stratum]
    benchmark(_run_over_blocked, utils_clang.pt_in_poly_clang_blocked, inputs)


@pytest.mark.benchmark
@pytest.mark.parametrize("stratum", STRATA)
@pytest.mark.usefixtures("strict_numpy_warnings")
def test_pt_in_poly_python_blocked(benchmark, blocked_pip_inputs_by_stratum, stratum):
    inputs = blocked_pip_inputs_by_stratum[stratum]
    benchmark(_run_over_blocked, utils_numba.pt_in_poly_blocked, inputs)
