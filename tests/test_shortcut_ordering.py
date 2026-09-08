"""Independent enumeration and geometry regressions for shortcut conversion."""

import itertools
from types import SimpleNamespace

import h3.api.numpy_int as h3
import numpy as np
import pytest

from scripts.shortcut_ordering import (
    ShortcutOrderer,
    cell_points,
    optimal_order,
    BBOX,
    HOLE_LOOKUP,
    HOLE_BBOX,
)
from scripts.shortcuts import check_shortcut_sorting
from timezonefinder import utils

pytestmark = pytest.mark.unit


def objective(order, zones, hits, costs):
    # Deliberately replay query execution rather than using the DP recurrence.
    value = 0
    for sample in range(hits.shape[1]):
        for i in order:
            if zones[i] == zones[order[-1]]:
                break
            value += costs[i, sample]
            if hits[i, sample]:
                break
    return value


@pytest.mark.parametrize("zones", [[0, 1], [0, 0, 1], [0, 0, 1, 1, 2], [0, 1, 0, 1, 2]])
def test_matches_exhaustive_legal_orders(zones):
    rng = np.random.default_rng(42)
    for _ in range(10):
        hits = rng.random((len(zones), 13)) < 0.3  # overlaps and gaps included
        costs = rng.integers(1, 100, hits.shape)
        legal = []
        for last in set(zones):
            tail = [i for i, z in enumerate(zones) if z == last]
            for prefix in itertools.permutations(
                i for i, z in enumerate(zones) if z != last
            ):
                legal.append(list(prefix) + tail)
        order = optimal_order(zones, hits, costs)
        assert objective(order, zones, hits, costs) == min(
            objective(p, zones, hits, costs) for p in legal
        )
        check_shortcut_sorting(order, np.asarray(zones))


def test_interleaving_and_whole_terminal_zone():
    zones = [0, 0, 1, 2]
    hits = np.eye(4, dtype=bool)
    costs = np.array([1, 20, 2, 1000])[:, None] * np.array([0.45, 0.01, 0.44, 0.10])
    order = optimal_order(zones, hits, costs)
    assert order == [0, 2, 1, 3]
    assert objective(order, zones, hits, costs) == pytest.approx(4.30)
    assert objective([2, 0, 1, 3], zones, hits, costs) == pytest.approx(4.76)
    with pytest.raises(AssertionError):
        check_shortcut_sorting([0, 2, 1], np.array(zones))


def test_sampling_reproducible_at_poles_and_date_line():
    for lat, lng in [(89.9, 0), (-89.9, 0), (0, 179.99), (50, 5)]:
        cell = h3.latlng_to_cell(lat, lng, 4)
        points = cell_points(cell)
        np.testing.assert_array_equal(points, cell_points(cell))
        assert all(h3.latlng_to_cell(y, x, 4) == cell for x, y in points)


def synthetic_orderer(polygons, zones):
    orderer = object.__new__(ShortcutOrderer)
    orderer.data = SimpleNamespace(
        polygons=polygons, poly_zone_ids=zones, holes_in_poly=lambda _: ()
    )
    orderer.geometries = {}
    orderer.invalid_geometries = set()
    return orderer


def rectangle(x0, x1, y0=-5, y1=5):
    return np.array(
        [
            [utils.coord2int(x) for x in [x0, x1, x1, x0]],
            [utils.coord2int(y) for y in [y0, y0, y1, y1]],
        ]
    )


def test_geometric_gate_catches_unsampled_sliver_and_gap():
    cell = h3.latlng_to_cell(0, 0, 4)
    assert synthetic_orderer(
        [rectangle(-5, 0), rectangle(0, 5)], [0, 1]
    ).safe_to_reorder(cell, [0, 1])
    assert not synthetic_orderer(
        [rectangle(-5, 0.000001), rectangle(0, 5)], [0, 1]
    ).safe_to_reorder(cell, [0, 1])
    assert not synthetic_orderer(
        [rectangle(-5, -0.000001), rectangle(0, 5)], [0, 1]
    ).safe_to_reorder(cell, [0, 1])


def test_rejected_holes_are_not_free():
    orderer = object.__new__(ShortcutOrderer)
    orderer.data = SimpleNamespace(hole_registry={0: (95, 0)})
    orderer.boundaries = SimpleNamespace(
        outside_bbox=lambda *a: False, pip=lambda *a: True
    )
    orderer.holes = SimpleNamespace(outside_bbox=lambda *a: True)
    orderer.pip_cost = lambda *a: 700
    hits, costs = orderer.observe([0], np.array([[0, 0]]))
    assert hits[0, 0]
    assert costs[0, 0] == BBOX + HOLE_LOOKUP + 95 * HOLE_BBOX + 700


@pytest.mark.integration
def test_observation_hits_match_full_runtime_predicate(tf):
    # These cells exercise holes, references, outer bbox misses and overlap.
    orderer = object.__new__(ShortcutOrderer)
    orderer.data = SimpleNamespace(hole_registry=tf.hole_registry)
    orderer.boundaries = tf.boundaries
    orderer.holes = tf.holes
    for text in ["84b360bffffffff", "84be323ffffffff", "846a2cbffffffff"]:
        cell = int(text, 16)
        ids = tf.shortcuts.candidates_of(tf.shortcuts.entry_of(cell)).tolist()
        points = cell_points(cell)[:12]
        hits, _ = orderer.observe(ids, points)
        for j, (lng, lat) in enumerate(points):
            x, y = utils.coord2int(lng), utils.coord2int(lat)
            for i, pid in enumerate(ids):
                assert hits[i, j] == tf.inside_of_polygon(pid, x, y)


def test_illegal_input_order_is_not_retained_as_a_zero_cost_tie():
    zones = [0, 1, 0]
    order = optimal_order(zones, np.zeros((3, 2), dtype=bool), np.ones((3, 2)))
    check_shortcut_sorting(order, np.array(zones))
    assert objective(order, zones, np.zeros((3, 2), dtype=bool), np.ones((3, 2))) == 2


def test_rejected_cell_keeps_legacy_tie_precedence():
    from scripts.shortcuts import optimise_shortcut_ordering

    data = SimpleNamespace(polygon_lengths=[4] * 9, poly_zone_ids=np.arange(9))
    legacy = optimise_shortcut_ordering(data, [8, 1])
    assert legacy == [8, 1]
    orderer = object.__new__(ShortcutOrderer)
    orderer.data = data
    orderer.safe_to_reorder = lambda *args: False
    assert orderer.order(h3.latlng_to_cell(0, 0, 4), legacy) == [8, 1]
