#!/usr/bin/env python3

"""Measure this environment's point-in-polygon path against the clang C extension.

Why this is not a ``benchmarks/`` suite
---------------------------------------

The pytest-benchmark suites compare *one* implementation across commits or machines,
and their node ids are the join key for the trend chart, which is calibrated for a
single configuration. Comparing the acceleration paths is the other measurement: two
candidates in one working tree, which is what ``benchmarks/candidate_comparison.py``
exists for and what ``docs/benchmarking_methodology.rst`` records three wrong designs
for. Nothing here adds a node id, so the chart and the per-pull-request job are
untouched.

Why one environment cannot answer the whole question
----------------------------------------------------

There are three paths and ``timezonefinder/utils.py`` binds one at *import* time, but
the constraint that shapes this script is narrower: ``numba`` and pure Python are the
same source decorated or not, so no process holds both. What a process does hold is
clang plus whichever of the two its environment produced::

    uv run --isolated --group test                python -m scripts.measure_acceleration_paths
    uv run --isolated --group test --group numba  python -m scripts.measure_acceleration_paths

The first pairs clang against pure Python, the second clang against numba - each of
them *in one process*, which is what makes them paired comparisons rather than two
timings put beside each other. ``make acceleration-paths`` runs both and
``scripts/render_benchmark_reports.py`` composes them, anchoring on clang, which is the
one path present in both and the one a plain ``pip install`` runs.

The third ratio - numba against pure Python - is a ratio of those two ratios and is
labelled *derived* on the page, never measured. Reporting it as a measurement would be
the cross-process comparison the harness exists to refuse: across two processes the
order cannot alternate, the two candidates cannot be handed the same draw, and the
round-level win count is undefined, which leaves only the estimator this repository has
already been misled by.

Both levels, because they answer different questions
----------------------------------------------------

The packed kernel is where the paths actually differ; ``TimezoneFinder.timezone_at`` is
what a caller experiences, and the shortcut layer answers most queries before any
kernel runs. A kernel ratio therefore *bounds* the lookup ratio and does not predict
it - which is the whole point of publishing both.

Reporting only, like every other measurement here: nothing in this module fails a
build.

Usage::

    uv run python -m scripts.measure_acceleration_paths --output tmp/acceleration.json
"""

import argparse
import json
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Iterator

from benchmarks.candidate_comparison import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_ROUNDS,
    CandidateComparison,
    compare_candidates,
)
from scripts.assert_acceleration_path import (
    PACKED_ACCELERATION_IMPLEMENTATIONS,
    PACKED_BUFFER_FACTORIES,
    interpreted_path_name,
)
from scripts.benchmark_utils import cpu_info, get_system_status
from scripts.configs import DEBUG
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    benchmark_fixture_provenance,
    group_packed_pip_inputs_by_stratum,
    load_benchmark_points,
    load_pip_inputs,
    load_pip_strata,
    packed_buffers_by_backend,
)
from timezonefinder import TimezoneFinder, utils
from timezonefinder.configs import POLYGON_BLOCK_SIZE

#: The clang path is the baseline in every pair: it is the one both environments hold,
#: so it is what the two runs can be anchored on, and it is what a plain
#: ``pip install timezonefinder`` runs.
BASELINE_PATH = "clang"

#: Polygon size strata, as ``benchmarks/test_inside_polygon.py`` uses them.
STRATA = ("small", "medium", "large")

#: Point classes, named as the report pages name them.
POINT_CLASSES = {
    "random": RANDOM_POINTS_FIXTURE,
    "unique_shortcut": UNIQUE_SHORTCUT_POINTS_FIXTURE,
    "ambiguous_shortcut": AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
}

#: Rounds for a pair whose two candidates are within a few percent of each other -
#: which is what numba against clang is (measured in #497: the two kernels agree within
#: 5 %). That is the regime the harness's defaults were chosen for.
NUMBA_ROUNDS = DEFAULT_ROUNDS

#: Rounds for the pure-Python pair, which the report has always measured as separated
#: from clang by orders of magnitude rather than by percent. While that holds no number
#: of rounds changes the verdict and more of them buy only wall clock - a single round
#: on the large stratum is already a fraction of a second. Fifteen for the same reason
#: and with the same value the ``Makefile``'s ``BENCHMARK_REPORT_ROUNDS`` uses, and odd,
#: so the sign count still cannot tie. Revisit it if the rendered page ever reports
#: these two within a few percent of each other - then this pair needs the statistical
#: power the numba pair gets, not less of it.
PYTHON_ROUNDS = 15


def _rounds_for(path: str) -> int:
    return NUMBA_ROUNDS if path == "numba" else PYTHON_ROUNDS


def _packed_caller(kernel: Callable[..., bool], buffers: tuple) -> Callable[..., bool]:
    """One packed-kernel call for one ``(x, y, nr_coords, block_start, nr_blocks)``.

    The buffers are closed over rather than passed per call because that is how a
    lookup reaches the kernel: a collection wraps its arrays once and every query
    spreads the same tuple (``PolygonArray._pip_at``).
    """

    def call(item: tuple[int, int, int, int, int]) -> bool:
        x, y, nr_coords, block_start, nr_blocks = item
        return kernel(
            x, y, nr_coords, POLYGON_BLOCK_SIZE, block_start, nr_blocks, *buffers
        )

    return call


def compare_kernels(path: str) -> dict[str, CandidateComparison]:
    """The packed kernel on ``path`` against the packed kernel on clang, per stratum."""
    buffers = packed_buffers_by_backend()
    inputs = group_packed_pip_inputs_by_stratum(
        load_pip_inputs(), load_pip_strata(), DEFAULT_BATCH_SIZE
    )
    results = {}
    for stratum in STRATA:
        results[stratum] = compare_candidates(
            (
                BASELINE_PATH,
                _packed_caller(
                    PACKED_ACCELERATION_IMPLEMENTATIONS[BASELINE_PATH],
                    buffers[BASELINE_PATH],
                ),
            ),
            (
                path,
                _packed_caller(
                    PACKED_ACCELERATION_IMPLEMENTATIONS[path], buffers[path]
                ),
            ),
            inputs[stratum],
            rounds=_rounds_for(path),
        )
    return results


@contextmanager
def _bound(path: str) -> Iterator[None]:
    """Bind ``path``'s packed kernel and buffer factory for the duration.

    Hand-rolled rather than ``pytest.MonkeyPatch``: this is a measurement script, and
    the two attributes are restored unconditionally, which is the whole of what is
    needed. Restoring matters because the *next* finder must be built under its own
    path, not under whatever the previous one left behind.
    """
    previous = (utils.inside_polygon_packed, utils.packed_buffers)
    utils.inside_polygon_packed = PACKED_ACCELERATION_IMPLEMENTATIONS[path]
    utils.packed_buffers = PACKED_BUFFER_FACTORIES[path]
    try:
        yield
    finally:
        utils.inside_polygon_packed, utils.packed_buffers = previous


def _finder_on(path: str) -> TimezoneFinder:
    """A finder whose collections captured ``path``'s kernel and buffers.

    Built *under* the rebind, never merely used under it: a collection wraps its payload
    for the bound backend when it is loaded and captures that backend's kernel beside
    it (``PolygonArray.__init__``). Because the two are captured together the finder
    keeps running its own path after the rebind is lifted, which is what lets both
    finders be alive at once - and being alive at once is what makes this a *paired*
    comparison rather than two runs beside each other.
    """
    with _bound(path):
        return TimezoneFinder(in_memory=True)


def _lookup_caller(finder: TimezoneFinder) -> Callable[[tuple[float, float]], object]:
    """One whole ``timezone_at`` call for one ``(lng, lat)`` pair."""
    return lambda point: finder.timezone_at(lng=point[0], lat=point[1])


def compare_lookups(path: str) -> dict[str, CandidateComparison]:
    """``timezone_at`` on ``path`` against ``timezone_at`` on clang, per point class.

    ``in_memory=True`` to match the CI-tracked core subset, and the whole public call is
    timed - the boundary between the kernel and everything around it falls where each
    path puts it rather than where this script does.
    """
    baseline_finder = _finder_on(BASELINE_PATH)
    challenger_finder = _finder_on(path)
    try:
        results = {}
        for point_class, fixture in POINT_CLASSES.items():
            points = load_benchmark_points(fixture)[:DEFAULT_BATCH_SIZE]
            results[point_class] = compare_candidates(
                (BASELINE_PATH, _lookup_caller(baseline_finder)),
                (path, _lookup_caller(challenger_finder)),
                points,
                rounds=_rounds_for(path),
            )
        return results
    finally:
        baseline_finder.cleanup()
        challenger_finder.cleanup()


def build_report(
    path: str,
    kernels: dict[str, CandidateComparison],
    lookups: dict[str, CandidateComparison],
) -> dict[str, Any]:
    """Assemble the JSON the renderer composes.

    Each comparison is stored as the fields :class:`CandidateComparison` is built from
    rather than as a rendered verdict, so the renderer stays a pure function of stored
    JSON - as every renderer here is - and reconstructs the dataclass to reuse its
    ``verdict`` and ``best_round_change`` instead of reimplementing the agreement rule.

    ``machine_info`` is the shape ``scripts.benchmark_utils.machine_label`` reads, so
    the page can name its machine and - because the two runs are composed - refuse to
    compose runs from two different ones.
    """
    return {
        "machine_info": {
            "cpu": cpu_info(),
            "timezonefinder": {
                **get_system_status(),
                **benchmark_fixture_provenance(),
                "acceleration_path": path,
                "baseline_path": BASELINE_PATH,
            },
        },
        "kernels": {name: asdict(c) for name, c in kernels.items()},
        "lookups": {name: asdict(c) for name, c in lookups.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare this environment's point-in-polygon path against the clang C "
            "extension, at the packed kernel and at TimezoneFinder.timezone_at."
        )
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="Path to write the JSON report to"
    )
    args = parser.parse_args()

    if DEBUG:
        # the same guard benchmarks/conftest.py and measure_query_latency.py apply
        raise RuntimeError(
            "scripts.configs.DEBUG is True, which overrides SHORTCUT_H3_RES to a much "
            "coarser resolution. It changes how many queries reach the geometry at "
            "all, which is most of what this comparison measures."
        )
    if not utils.clang_extension_loaded:
        raise RuntimeError(
            "the clang point-in-polygon C extension is not loaded, so there is no "
            "baseline to compare against - and it is the one path both environments "
            "must hold for their two runs to be composable. Build it (`uv sync`)."
        )

    path = interpreted_path_name()
    kernels = compare_kernels(path)
    lookups = compare_lookups(path)

    report = build_report(path, kernels, lookups)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{path} against {BASELINE_PATH}\n")
    for heading, results in (("packed kernel", kernels), ("timezone_at", lookups)):
        print(f"  --- {heading} ---")
        for name, comparison in results.items():
            block = comparison.render().replace("\n", "\n  ")
            print(f"  {name}: {block}\n")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
