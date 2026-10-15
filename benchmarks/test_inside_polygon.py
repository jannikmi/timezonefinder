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

from scripts.assert_acceleration_path import interpreted_path_name
from timezonefinder import utils_clang, utils_numba
from timezonefinder.configs import POLYGON_BLOCK_SIZE

STRATA = [
    pytest.param("small", id="small"),
    pytest.param("medium", id="medium"),
    pytest.param("large", id="large"),
]


#: Rounds for the one row that dominates the published suite's runtime. The interpreted
#: bare kernel over the `large` stratum takes ~20 s a round on a CI runner, so the
#: Makefile's 15 report rounds spent ~5 of the suite's ~7 minutes on it - while its
#: rounds spread 0.6 %, against a gap of two orders of magnitude to the compiled
#: kernel it is published beside. Five rounds describe that row as well as fifteen.
#: The marker sits on each parameter rather than on the function: pytest-benchmark
#: reads the *closest* `benchmark` marker, and a bare one on the function wins over a
#: parameter's, which silently left this row at 15 rounds. Every other row keeps the
#: report's round count, and the node ids the trend chart and
#: `tests/test_benchmark_names.py` pin are unchanged.
SLOW_INTERPRETED_ROUNDS = 5

INTERPRETED_STRATA = [
    pytest.param("small", id="small", marks=pytest.mark.benchmark),
    pytest.param("medium", id="medium", marks=pytest.mark.benchmark),
    pytest.param(
        "large",
        id="large",
        marks=pytest.mark.benchmark(min_rounds=SLOW_INTERPRETED_ROUNDS),
    ),
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


@pytest.mark.parametrize("stratum", INTERPRETED_STRATA)
@pytest.mark.usefixtures("strict_numpy_warnings")
def test_pt_in_poly_python(benchmark, pip_inputs_by_stratum, stratum):
    # times `utils_numba` directly, so this is the JIT-compiled kernel wherever numba
    # is installed (`utils_numba.using_numba`) and the interpreted one otherwise -
    # independently of which kernel `utils.py` bound for a lookup
    inputs = pip_inputs_by_stratum[stratum]
    benchmark(_run_over, utils_numba.pt_in_poly_python, inputs)


def _run_over_packed(
    func: Callable, buffers: tuple, inputs: Iterable[tuple[int, int, int, int, int]]
) -> None:
    for x, y, nr_coords, block_start, nr_blocks in inputs:
        func(x, y, nr_coords, POLYGON_BLOCK_SIZE, block_start, nr_blocks, *buffers)


@pytest.mark.benchmark
@pytest.mark.parametrize("stratum", STRATA)
@pytest.mark.usefixtures("strict_numpy_warnings")
def test_pt_in_poly_clang_packed(
    benchmark, packed_pip_inputs_by_stratum, packed_buffers_by_backend, stratum
):
    inputs = packed_pip_inputs_by_stratum[stratum]
    buffers = packed_buffers_by_backend["clang"]
    benchmark(_run_over_packed, utils_clang.pt_in_poly_clang_packed, buffers, inputs)


@pytest.mark.benchmark
@pytest.mark.parametrize("stratum", STRATA)
@pytest.mark.usefixtures("strict_numpy_warnings")
def test_pt_in_poly_python_packed(
    benchmark, packed_pip_inputs_by_stratum, packed_buffers_by_backend, stratum
):
    inputs = packed_pip_inputs_by_stratum[stratum]
    # keyed by whichever name this environment's `utils_numba` goes by - `numba` with
    # the JIT installed, `python` without it. The buffers are identical either way;
    # asking by name is what keeps the fixture from claiming a backend it has not got.
    buffers = packed_buffers_by_backend[interpreted_path_name()]
    benchmark(_run_over_packed, utils_numba.pt_in_poly_packed, buffers, inputs)
