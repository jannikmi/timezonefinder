"""Analytic area, integrated work, heuristic guarantees and geometry safety."""

import itertools
from types import SimpleNamespace

import math

import numpy as np
import pytest
from shapely import Polygon, box

from scripts.shortcut_ordering import (
    ACTIVE_VERTEX,
    BBOX,
    BLOCK_PROBE,
    HOLE_BBOX,
    HOLE_LOOKUP,
    HOLE_UNION_PROBE,
    PIP_DISPATCH,
    CellOptimizer,
    CheckCost,
    ShortcutOrderer,
    DEFAULT_COST_COEFFICIENTS,
    cell_envelope,
    cell_region,
    spherical_area,
)
from scripts.shortcuts import (
    check_shortcut_sorting,
    optimise_shortcut_ordering,
    zone_areas,
)
from timezonefinder.configs import (
    COORD2INT_FACTOR,
    INT2COORD_FACTOR,
    MAX_LAT_VAL_INT,
    MAX_LNG_VAL_INT,
    POLYGON_BLOCK_SIZE,
)
from timezonefinder.shortcut_index import (
    cell_bounds,
    child_cell_of,
    root_cell_of,
    shifted,
)

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


@pytest.mark.parametrize("clockwise", [False, True])
def test_spherical_area_is_exact_along_a_slanted_edge_in_either_winding(clockwise):
    # the triangle (0, 0), (L, 0), (0, H) has one edge slanted in the lng/lat plane,
    # along which the ring integral of sin(lat) dlng is L * (1 - cos H) / H exactly;
    # a rectangle never exercises that term, and a high H makes any approximation show
    lng, lat = 10, 80
    ring = np.array([(0, 0), (lng, 0), (0, lat)], dtype=np.float64)
    if clockwise:
        ring = ring[::-1]
    triangle = Polygon(ring * COORD2INT_FACTOR)
    height = np.radians(lat)
    expected = np.radians(lng) * (1 - np.cos(height)) / height
    assert spherical_area(triangle) == pytest.approx(expected, rel=1e-9)


CELL_PROBES = [
    (0.0, 0.0),
    (0.0, 60.0),
    (0.0, 89.9),
    (0.0, -89.9),
    (179.99, 0.0),
    (-179.99, 0.0),
    (179.99, 80.0),
    (-180.0, -90.0),
]


@pytest.mark.parametrize("lng, lat", CELL_PROBES)
@pytest.mark.parametrize("level", ["root", "finest"])
def test_the_cell_region_is_the_exact_rectangle_the_cell_owns(lng, lat, level):
    """Exact, not converged - which is the whole difference the aligned grid makes.

    The H3 version of this test asserted that subdividing great-circle arcs brought the
    represented area within 1e-6 of H3's own, and had to list pentagons, both poles and
    the date line as the cases that might not converge. A cell is now a rectangle of the
    very plane the areas are integrated in, so its spherical area has a closed form and
    the two must agree to floating point - at a pole and at the plane's edge like
    anywhere else, because neither is a special case any more.
    """
    cell = (root_cell_of if level == "root" else child_cell_of)(*shifted(lng, lat))
    region = cell_region(cell)
    assert region.is_valid
    x0, y0, x1, y1 = cell_bounds(cell)
    # Green's theorem over a planar lat/lng box reduces to this, and `spherical_area`
    # is that integral written out for an arbitrary ring
    expected = (math.radians((x1 - (x0 - 1)) * INT2COORD_FACTOR)) * (
        math.sin(math.radians(y1 * INT2COORD_FACTOR))
        - math.sin(math.radians((y0 - 1) * INT2COORD_FACTOR))
    )
    assert spherical_area(region) == pytest.approx(expected, rel=1e-12)
    assert region.bounds[0] >= -180 * COORD2INT_FACTOR - 1
    assert region.bounds[2] <= 180 * COORD2INT_FACTOR
    # the gate's envelope contains every integer point the cell owns, with a unit to spare
    envelope = cell_envelope(cell)
    assert envelope.contains(region)


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
    rings = [np.array(p.exterior.coords).T for p in polygons]
    orderer.data = SimpleNamespace(
        boundaries=SimpleNamespace(coords_of=rings.__getitem__),
        poly_zone_ids=zones,
        holes=SimpleNamespace(holes_of_poly=lambda _: ()),
    )
    orderer.geometries = {}
    orderer.invalid_geometries = set()
    return orderer


def test_geometric_safety_is_independent_of_objective_approximation():
    cell = root_cell_of(*shifted(0.0, 0.0))
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


def refusing_orderer():
    """An orderer whose geometry cannot be read, to prove a refusal came first."""
    orderer = object.__new__(ShortcutOrderer)

    def refuse(pid):
        raise AssertionError(f"geometry {pid} was consulted")

    orderer.geometry = refuse
    orderer.data = SimpleNamespace(poly_zone_ids=[0, 1])
    orderer.invalid_geometries = set()
    return orderer


@pytest.mark.parametrize("lng, lat", CELL_PROBES + [(90.0, 0.0)])
def test_the_safety_gate_reads_the_geometry_of_a_seam_cell_like_any_other(lng, lat):
    """No cell is refused before its geometry is read.

    The H3 gate derived its envelope from a circumscribed spherical cap, and the
    conversion broke where the cap reached a pole or spanned the antimeridian - so those
    cells bailed out before any geometry was read. A cell is now its own rectangle
    everywhere, so there is nothing left to bail out of.

    Asserted by making the geometry unreadable, so that reaching it is what fails. A
    verdict-only test cannot tell "refused early" from "refused on the geometry".
    """
    with pytest.raises(AssertionError, match="was consulted"):
        refusing_orderer().safe_to_reorder(root_cell_of(*shifted(lng, lat)), [0, 1])


def test_the_gate_can_pass_at_the_edges_of_the_domain():
    """Reaching the geometry is not the same as being able to pass, and this is the half
    that was missing.

    ``cell_envelope`` grows the cell by one unit, and the top row ends at exactly +90
    degrees while the last column ends at +180 - so without the clip to the coordinate
    domain the envelope asks for coverage where no polygon can be, and ``covers`` is
    False for all 384 top-row and 192 last-column root cells whatever their geometry.
    That is the H3 gate's pole and antimeridian refusals surviving the port as an
    arithmetic accident, and the test above cannot see it: those cells do read their
    geometry, and still always refuse.

    So: two synthetic zones tiling the entire legal domain exactly and disjointly - the
    most admissible input there is - must be admitted at every edge, not only inside.
    """
    legal = box(-MAX_LNG_VAL_INT, -MAX_LAT_VAL_INT, MAX_LNG_VAL_INT, MAX_LAT_VAL_INT)
    west = box(-MAX_LNG_VAL_INT, -MAX_LAT_VAL_INT, 0, MAX_LAT_VAL_INT)
    east = box(0, -MAX_LAT_VAL_INT, MAX_LNG_VAL_INT, MAX_LAT_VAL_INT)
    refused = []
    for lng, lat in [
        (0.0, 0.0),
        (-179.99, 0.0),
        (179.99, 0.0),
        (0.0, -89.99),
        (0.0, 89.99),
        (179.99, 89.99),
        (-179.99, -89.99),
    ]:
        cell = root_cell_of(*shifted(lng, lat))
        assert legal.covers(cell_envelope(cell)), (
            f"the envelope of the cell at ({lng}, {lat}) leaves the coordinate domain, "
            "so no geometry can ever cover it"
        )
        if not synthetic_orderer([west, east], [0, 1]).safe_to_reorder(cell, [0, 1]):
            refused.append((lng, lat))
    assert not refused, f"a tiling of the whole domain was refused at {refused}"


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
    orderer.coefficients = DEFAULT_COST_COEFFICIENTS
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


def test_zone_precedence_is_smaller_area_first_and_breaks_every_tie_independently_of_input_order():
    # zone 2 has by far the most vertices and the smallest area, so it goes first:
    # vertex counts no longer rank zones. Zones 0 "Etc/UTC" and 1 "Antarctica/Rothera"
    # tie on area, and their numeric ids sort opposite to their names. Within zone 2,
    # polygons 4 and 5 tie on 3 vertices and polygon 3 has 30.
    data = SimpleNamespace(
        boundaries=SimpleNamespace(nr_vertices=np.array([5, 3, 2, 30, 3, 3])),
        poly_zone_ids=np.array([0, 1, 1, 2, 2, 2]),
        all_tz_names=["Etc/UTC", "Antarctica/Rothera", "Etc/GMT+1"],
    )
    zone_area = np.array([1.0, 1.0, 0.5])
    # an equal area sorts by identifier, never by zone id; equal polygons by id
    expected = [4, 5, 3, 2, 1, 0]
    for poly_ids in itertools.permutations(range(6)):
        assert optimise_shortcut_ordering(data, list(poly_ids), zone_area) == expected


def test_zone_areas_sum_a_zones_polygons_and_cut_out_their_holes():
    # zone 0: a 10 x 10 degree square holding the enclave below as a hole-free overlap,
    # plus a second, detached 1 x 1 square. zone 1: the 2 x 2 enclave, minus a hole.
    def ring(x0, y0, x1, y1):
        return (
            np.array([[x0, x1, x1, x0], [y0, y0, y1, y1]], dtype=np.float64)
            * COORD2INT_FACTOR
        ).astype(np.int64)

    rings = [ring(0, 0, 10, 10), ring(20, 0, 21, 1), ring(4, 4, 6, 6)]
    holes = {2: [ring(4.5, 4.5, 5, 5)]}
    data = SimpleNamespace(
        nr_of_zones=2,
        poly_zone_ids=np.array([0, 0, 1]),
        boundaries=SimpleNamespace(coords_of=lambda i: rings[i]),
        holes=SimpleNamespace(holes_of_poly=lambda i: iter(holes.get(i, []))),
    )

    def area(x0, y0, x1, y1):
        return spherical_area(box(*(ring(x0, y0, x1, y1)[:, [0, 2]].T.ravel())))

    areas = zone_areas(data)
    assert areas[0] == pytest.approx(area(0, 0, 10, 10) + area(20, 0, 21, 1))
    assert areas[1] == pytest.approx(area(4, 4, 6, 6) - area(4.5, 4.5, 5, 5))
    assert areas[1] < areas[0]
