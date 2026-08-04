"""pytest-benchmark suite for the point-in-polygon implementations.

Compares the clang (C extension) and pure-Python (optionally Numba-JIT)
implementations across the small/medium/large polygon-vertex-count strata
of the committed `pip_inputs` benchmark fixture (see
`scripts/generate_benchmark_fixtures.py`), so the cost of the largest
polygons isn't hidden behind an unweighted average over the mostly-small
polygon population.
"""

from typing import Callable, Iterable

import numpy as np
import pytest

from timezonefinder import utils_clang, utils_numba

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
