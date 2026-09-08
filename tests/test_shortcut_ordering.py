"""Analytic area, integrated work, heuristic guarantees and geometry safety."""

import itertools
from types import SimpleNamespace

import h3.api.numpy_int as h3
import numpy as np
import pytest
from shapely import Polygon, box

from scripts.shortcut_ordering import (
    ACTIVE_VERTEX,
    BBOX,
    BLOCK_PROBE,
    CELL_AREA_RTOL,
    HOLE_BBOX,
    HOLE_LOOKUP,
    HOLE_UNION_PROBE,
    PIP_DISPATCH,
    CellOptimizer,
    CheckCost,
    ShortcutOrderer,
    cell_region,
    spherical_area,
)
from scripts.shortcuts import check_shortcut_sorting
from timezonefinder.configs import COORD2INT_FACTOR, POLYGON_BLOCK_SIZE

pytestmark = pytest.mark.unit


def rectangle(x0, x1, y0=0, y1=1):
    return box(
        x0 * COORD2INT_FACTOR,
        y0 * COORD2INT_FACTOR,
        x1 * COORD2INT_FACTOR,
        y1 * COORD2INT_FACTOR,
    )


def test_spherical_area_rectangles_holes_and_latitude_distortion():
    low = rectangle(0, 2, 0, 1)
    high = rectangle(0, 2, 70, 71)
    expected = np.radians(2) * (np.sin(np.radians(71)) - np.sin(np.radians(70)))
    assert spherical_area(high) == pytest.approx(expected, rel=1e-12)
    assert low.area == high.area
    assert spherical_area(high) < spherical_area(low) * 0.35
    hole = rectangle(0.5, 1, 0.2, 0.8)
    assert spherical_area(low.difference(hole)) == pytest.approx(
        spherical_area(low) - spherical_area(hole)
    )
    assert spherical_area(low.union(high)) == pytest.approx(
        spherical_area(low) + spherical_area(high)
    )


@pytest.mark.parametrize(
    "cell",
    list(h3.get_pentagons(4))
    + [
        h3.latlng_to_cell(lat, lng, 4)
        for lat, lng in [
            (0, 0),
            (60, 0),
            (89.9, 0),
            (-89.9, 0),
            (0, 179.99),
            (80, 179.99),
        ]
    ],
)
def test_cell_area_converges_at_poles_date_line_and_pentagons(cell):
    region = cell_region(int(cell))
    assert region.is_valid
    assert spherical_area(region) == pytest.approx(
        h3.cell_area(cell, unit="rads^2"), rel=CELL_AREA_RTOL
    )
    assert region.bounds[0] >= -180 * COORD2INT_FACTOR
    assert region.bounds[2] <= 180 * COORD2INT_FACTOR


def test_integrated_cost_uses_intersection_area():
    cell = rectangle(0, 2)
    cost = CheckCost(3)
    cost.add(tuple(int(v) for v in rectangle(1, 3).bounds), 10)
    assert cost.integral(cell) / spherical_area(cell) == pytest.approx(8)
    assert cost.integral(rectangle(0, 0.5)) / spherical_area(
        rectangle(0, 0.5)
    ) == pytest.approx(3)


def test_constant_cost_disjoint_case_matches_exhaustive_optimum():
    rng = np.random.default_rng(653)
    zones = [0, 0, 1, 1, 2]
    for _ in range(12):
        widths = rng.uniform(0.01, 1, 5)
        ends = np.r_[0, np.cumsum(widths)]
        hits = [rectangle(a, b) for a, b in zip(ends[:-1], ends[1:], strict=True)]
        optimizer = CellOptimizer(
            rectangle(0, ends[-1]),
            hits,
            [CheckCost(c) for c in rng.uniform(1, 100, 5)],
            zones,
        )
        best = float("inf")
        for final in set(zones):
            for prefix in itertools.permutations(
                i for i, z in enumerate(zones) if z != final
            ):
                best = min(best, optimizer.score(list(prefix)))
        order = optimizer.order(True)
        prefix = [i for i in order if zones[i] != zones[order[-1]]]
        assert optimizer.score(prefix) == pytest.approx(best, rel=1e-10)
        check_shortcut_sorting(order, np.array(zones))


def test_interleaving_witness_without_sampling():
    ends = [0, 0.45, 0.46, 0.9, 1]
    hits = [rectangle(a, b) for a, b in zip(ends[:-1], ends[1:], strict=True)]
    cell = rectangle(0, 1)
    optimizer = CellOptimizer(
        cell, hits, [CheckCost(c) for c in [1, 20, 2, 1000]], [0, 0, 1, 2]
    )
    assert optimizer.order(True) == [0, 2, 1, 3]
    assert optimizer.score([0, 2, 1]) / spherical_area(cell) == pytest.approx(4.30)


def test_overlap_survival_is_union_not_sum():
    cell = rectangle(0, 3)
    hits = [rectangle(0, 2), rectangle(1, 3), rectangle(0, 3)]
    optimizer = CellOptimizer(cell, hits, [CheckCost(1)] * 3, [0, 0, 1])
    assert spherical_area(optimizer.remaining(3)) == 0
    assert optimizer.score([0, 1]) / spherical_area(cell) == pytest.approx(1 + 1 / 3)


def test_point_dependent_cost_does_not_factor_unconditional_mean():
    cell = rectangle(0, 2)
    a = CheckCost(1)
    a.add(tuple(int(v) for v in rectangle(0, 1).bounds), 100)
    optimizer = CellOptimizer(
        cell, [rectangle(1, 2), rectangle(0, 1)], [a, CheckCost(1)], [0, 1]
    )
    # Once polygon 1 has failed, candidate 0 costs only one unit, not its mean 51.
    assert optimizer.cost(2, 0) / spherical_area(cell) == pytest.approx(0.5)
    assert optimizer.cost(0, 0) / spherical_area(cell) == pytest.approx(51)


@pytest.mark.parametrize("unrestricted", [False, True])
def test_large_lists_keep_every_candidate_and_never_worsen_incumbent(unrestricted):
    cell = rectangle(0, 1)
    hits = [rectangle(2, 3)] * 49 + [rectangle(0, 0.7), rectangle(0.7, 1)]
    costs = [CheckCost(1000)] + [CheckCost(1)] * 49 + [CheckCost(100000)]
    zones = [0] * 50 + [1]
    optimizer = CellOptimizer(cell, hits, costs, zones)
    order = optimizer.order(unrestricted)
    assert sorted(order) == list(range(51))
    assert order[0] == 49
    assert optimizer.score(order[:-1]) < optimizer.score(list(range(50)))


def test_tiny_positive_region_is_not_lost_to_a_sample():
    cell = rectangle(0, 1)
    tiny = rectangle(0, 1e-8)
    assert spherical_area(tiny) > 0
    optimizer = CellOptimizer(
        cell, [tiny, rectangle(2, 3), cell], [CheckCost(1)] * 3, [0, 0, 1]
    )
    # No minimum probability gate: even this tiny region has a nonzero priority.
    assert optimizer.greedy([1, 0]) == [0, 1]


def test_fixed_zone_precedence_preserves_every_hit_pattern():
    zones = [0, 0, 1, 1, 2]
    hits = [rectangle(i, i + 1) for i in range(5)]
    optimizer = CellOptimizer(
        rectangle(0, 5), hits, [CheckCost(c) for c in [100, 1, 100, 1, 1]], zones
    )
    order = optimizer.order(False)
    assert order != list(range(5))

    def answer(sequence, pattern):
        for i in sequence:
            if zones[i] == zones[sequence[-1]] or pattern[i]:
                return zones[i]

    for pattern in itertools.product([False, True], repeat=5):
        assert answer(order, pattern) == answer(list(range(5)), pattern)


def synthetic_orderer(polygons, zones):
    orderer = object.__new__(ShortcutOrderer)
    orderer.data = SimpleNamespace(
        polygons=[np.array(p.exterior.coords).T for p in polygons],
        poly_zone_ids=zones,
        holes_in_poly=lambda _: (),
    )
    orderer.geometries = {}
    orderer.invalid_geometries = set()
    return orderer


def test_geometric_safety_is_independent_of_objective_approximation():
    cell = h3.latlng_to_cell(0, 0, 4)
    assert synthetic_orderer(
        [rectangle(-5, 0, -5, 5), rectangle(0, 5, -5, 5)], [0, 1]
    ).safe_to_reorder(cell, [0, 1])
    for offset in [-0.000001, 0.000001]:
        assert not synthetic_orderer(
            [rectangle(-5, offset, -5, 5), rectangle(0, 5, -5, 5)], [0, 1]
        ).safe_to_reorder(cell, [0, 1])
    invalid = Polygon([(0, 0), (10, 10), (0, 10), (10, 0), (0, 0)])
    orderer = synthetic_orderer([invalid, rectangle(-5, 5, -5, 5)], [0, 1])
    assert not orderer.safe_to_reorder(cell, [0, 1])
    assert 0 in orderer.invalid_geometries


def test_hole_union_gate_skips_all_individual_hole_costs():
    def array(n, low, high):
        return SimpleNamespace(
            xmin=np.full(n, low),
            ymin=np.full(n, low),
            xmax=np.full(n, high),
            ymax=np.full(n, high),
            block_offsets=list(range(n + 1)),
            block_ranges=np.tile([low, high], (n, 1)),
        )

    orderer = object.__new__(ShortcutOrderer)
    orderer.data = SimpleNamespace(hole_registry={0: (95, 0)})
    orderer.boundaries = array(1, 0, 100)
    orderer.holes = array(95, 10, 20)
    orderer.models = {}
    model = orderer.model(0)
    pip = PIP_DISPATCH + BLOCK_PROBE + ACTIVE_VERTEX * POLYGON_BLOCK_SIZE
    outside = box(50, 50, 60, 60)
    inside = box(12, 12, 13, 13)
    assert model.integral(outside) / spherical_area(outside) == pytest.approx(
        BBOX + HOLE_UNION_PROBE + pip
    )
    assert model.integral(inside) / spherical_area(inside) == pytest.approx(
        BBOX + HOLE_UNION_PROBE + pip + HOLE_LOOKUP + 95 * (HOLE_BBOX + pip)
    )
