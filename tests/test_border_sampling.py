"""The geometry `scripts/border_sampling.py` uses to place a point at a distance.

The claim this module makes is narrow and checkable: a point it hands back is
the stated number of metres from the nearest timezone border, and where such a
point lands is not biased by how the boundary data happens to be stored. Both
halves are asserted here on synthetic rings, where the right answer is known by
construction, plus a handful of cases over the packaged boundaries.

The two failure modes worth naming, because each is silent:

- an edge-only sampler drops the arcs a ring's offset locus has at its
  vertices, which are 83% of that locus at 10 km over the packaged data. It
  still returns points, they are just not the population that was asked for
- an unverified sampler labels a point with the distance it was *offset by*
  rather than its distance to the nearest border. Over the packaged data those
  differ wildly: a point offset a nominal 10 km once measured 1.3 m
"""

import math

import numpy as np
import pytest

from scripts.border_sampling import (
    DISTANCE_TOLERANCE,
    METRES_PER_DEGREE_LATITUDE,
    METRES_PER_DEGREE_LONGITUDE,
    BorderGeometry,
    Ring,
    offset_locus_measure,
)
from timezonefinder.configs import COORD2INT_FACTOR


def _ring(*vertices: tuple[float, float]) -> np.ndarray:
    """The `(2, n)` int32 layout the packaged boundary files store."""
    return np.array(
        [
            [round(lng * COORD2INT_FACTOR) for lng, _ in vertices],
            [round(lat * COORD2INT_FACTOR) for _, lat in vertices],
        ],
        dtype=np.int32,
    )


@pytest.mark.unit
def test_an_edge_is_measured_in_metres() -> None:
    ring = Ring(_ring((0.0, 0.0), (1.0, 0.0)))
    assert ring.length[0] == pytest.approx(METRES_PER_DEGREE_LONGITUDE, rel=1e-6)
    assert ring.east[0] == pytest.approx(METRES_PER_DEGREE_LONGITUDE, rel=1e-6)
    assert ring.north[0] == pytest.approx(0.0, abs=1e-6)
    # the ring closes, so the second edge is the return leg
    assert ring.length[1] == pytest.approx(METRES_PER_DEGREE_LONGITUDE, rel=1e-6)


@pytest.mark.unit
def test_a_degree_of_longitude_shortens_towards_the_pole() -> None:
    equator = Ring(_ring((0.0, 0.0), (1.0, 0.0)))
    sixty = Ring(_ring((0.0, 60.0), (1.0, 60.0)))
    assert sixty.length[0] == pytest.approx(equator.length[0] * 0.5, rel=1e-3)


@pytest.mark.unit
def test_the_seam_of_a_ring_that_wraps_the_antimeridian_has_no_length() -> None:
    # the jump from +179.9 to -179.9 is where the ring closes, not a piece of
    # border half the planet long - weighting by it would put most of a sample
    # on a line nobody can stand next to
    ring = Ring(_ring((179.9, 10.0), (-179.9, 10.0), (-179.9, 11.0), (179.9, 11.0)))
    assert ring.length[0] == 0.0
    assert ring.length[2] == 0.0
    assert ring.length[1] > 0.0 and ring.length[3] > 0.0


@pytest.mark.unit
def test_a_square_turns_through_a_full_circle() -> None:
    # four right angles, whatever the winding - the sum of |turning| is what
    # prices a ring's arcs, so getting the wrap wrong would price them at zero
    ring = Ring(_ring((0.0, 0.0), (0.0, 0.01), (0.01, 0.01), (0.01, 0.0)))
    assert float(np.abs(ring.turning).sum()) == pytest.approx(2 * math.pi, rel=1e-6)
    assert np.all(np.abs(np.abs(ring.turning) - math.pi / 2) < 1e-6)


@pytest.mark.unit
def test_a_vertex_next_to_a_seam_has_no_turn() -> None:
    ring = Ring(_ring((179.9, 10.0), (-179.9, 10.0), (-179.9, 11.0), (179.9, 11.0)))
    assert ring.turning[0] == 0.0
    assert ring.turning[1] == 0.0


@pytest.mark.unit
@pytest.mark.parametrize(
    ("distance_m", "expected_arc_share"),
    [(0.0, 0.0), (1.0, 2 * math.pi / (2 * 1000.0 + 2 * math.pi))],
)
def test_the_locus_is_the_two_parallel_curves_plus_the_vertex_arcs(
    distance_m: float, expected_arc_share: float
) -> None:
    # a ring 1000 m round turning through 2*pi: at zero offset the arcs vanish
    # and the locus is twice the ring, and every metre of offset adds 2*pi of arc
    measure = offset_locus_measure(1000.0, 2 * math.pi, distance_m)
    assert measure == pytest.approx(2 * 1000.0 + distance_m * 2 * math.pi)
    arc = distance_m * 2 * math.pi
    assert arc / measure == pytest.approx(expected_arc_share)


class _SquarePolygons:
    """One 0.02-degree square ring, in the interface `BorderGeometry` consumes."""

    def __init__(self) -> None:
        self._coords = _ring((0.0, 0.0), (0.0, 0.02), (0.02, 0.02), (0.02, 0.0))
        self.xmin = np.array([0], dtype=np.int32)
        self.xmax = np.array([round(0.02 * COORD2INT_FACTOR)], dtype=np.int32)
        self.ymin = np.array([0], dtype=np.int32)
        self.ymax = np.array([round(0.02 * COORD2INT_FACTOR)], dtype=np.int32)

    def __len__(self) -> int:
        return 1

    def coords_of(self, index: int) -> np.ndarray:
        assert index == 0
        return self._coords


@pytest.fixture
def square() -> BorderGeometry:
    return BorderGeometry(_SquarePolygons())


@pytest.mark.unit
def test_the_distance_to_a_ring_is_the_distance_to_its_nearest_edge(
    square: BorderGeometry,
) -> None:
    # 100 m due west of the square's western edge, at the equator
    offset = 100.0 / METRES_PER_DEGREE_LONGITUDE
    distances = dict(square.distances_to_rings(-offset, 0.01, 200.0))
    assert distances[0] == pytest.approx(100.0, rel=1e-3)


@pytest.mark.unit
def test_a_point_beyond_the_end_of_an_edge_measures_to_the_corner(
    square: BorderGeometry,
) -> None:
    # diagonally out from the corner at (0, 0): the perpendicular from either
    # edge lands outside it, so the nearest point on the ring is the corner and
    # the distance is the diagonal, not the shorter perpendicular offset
    offset_lng = 100.0 / METRES_PER_DEGREE_LONGITUDE
    offset_lat = 100.0 / METRES_PER_DEGREE_LATITUDE
    distances = dict(square.distances_to_rings(-offset_lng, -offset_lat, 400.0))
    assert distances[0] == pytest.approx(math.hypot(100.0, 100.0), rel=1e-3)


@pytest.mark.unit
def test_a_ring_out_of_range_is_never_measured(square: BorderGeometry) -> None:
    # the bounding-box prune is what keeps a point's cost proportional to the
    # borders near it rather than to the whole dataset
    assert list(square.distances_to_rings(90.0, 45.0, 1000.0)) == []


@pytest.mark.unit
def test_a_point_at_the_asked_distance_is_accepted(square: BorderGeometry) -> None:
    offset = 100.0 / METRES_PER_DEGREE_LONGITUDE
    candidate = square.verify(-offset, 0.01, 100.0)
    assert candidate is not None
    assert candidate.distance_m == pytest.approx(100.0, rel=DISTANCE_TOLERANCE)
    assert candidate.rings_at_distance == (0,)
    assert candidate.multiplicity == 1


@pytest.mark.unit
def test_a_point_nearer_another_stretch_of_border_is_rejected(
    square: BorderGeometry,
) -> None:
    # the failure the verification exists for. Offsetting 10 km *inwards* from
    # the western edge of a square only ~2.2 km across crosses the whole ring
    # and comes out the far side, where the nearest border is the eastern edge
    # at ~7.8 km. Labelled by the offset it was given, this point would enter
    # the sweep as a 10 km sample; measured, it is not one
    offset = 10_000.0 / METRES_PER_DEGREE_LONGITUDE
    assert square.verify(offset, 0.01, 10_000.0) is None
    measured = dict(square.distances_to_rings(offset, 0.01, 12_000.0))
    assert measured[0] == pytest.approx(
        10_000.0 - 0.02 * METRES_PER_DEGREE_LONGITUDE, rel=1e-3
    )


@pytest.mark.unit
def test_a_point_off_the_globe_is_rejected(square: BorderGeometry) -> None:
    assert square.verify(0.0, 90.5, 100.0) is None


@pytest.mark.unit
def test_every_drawn_point_is_at_the_distance_it_was_asked_for(
    square: BorderGeometry,
) -> None:
    # the whole contract, over a ring small enough that a naive edge-offset
    # sampler would fail it: at 100 m the arcs are a fifth of the locus
    rng = np.random.default_rng(0)
    accepted, drawn = square.sample(rng, 100.0, 200)
    assert drawn >= len(accepted) == 200
    for candidate in accepted:
        assert candidate.distance_m == pytest.approx(100.0, rel=DISTANCE_TOLERANCE), (
            f"({candidate.lng}, {candidate.lat}) is {candidate.distance_m} m out"
        )


@pytest.mark.unit
def test_the_arcs_at_the_corners_are_sampled_too(square: BorderGeometry) -> None:
    # a point diagonally out from a corner can only come from that corner's
    # arc; an edge-only sampler produces none of them, which is the bias this
    # module exists to remove. A square's four quarter-circles are
    # 2*pi*100 / (2*(4*2224) + 2*pi*100) ~ 3.4% of the locus at 100 m
    rng = np.random.default_rng(1)
    accepted, _ = square.sample(rng, 100.0, 3000)
    off_corner = [
        candidate
        for candidate in accepted
        if candidate.lng < 0.0 and candidate.lat < 0.0
    ]
    assert off_corner, "no point came from a vertex arc"


@pytest.mark.unit
def test_a_border_two_rings_describe_is_not_counted_twice() -> None:
    # every border between two zones is stored in both zones' rings, so without
    # the multiplicity correction a shared border would be drawn twice as often
    # as one only a single ring describes
    class _TwoIdenticalRings(_SquarePolygons):
        def __init__(self) -> None:
            super().__init__()
            self.xmin = np.repeat(self.xmin, 2)
            self.xmax = np.repeat(self.xmax, 2)
            self.ymin = np.repeat(self.ymin, 2)
            self.ymax = np.repeat(self.ymax, 2)

        def __len__(self) -> int:
            return 2

        def coords_of(self, index: int) -> np.ndarray:
            assert index in (0, 1)
            return self._coords

    geometry = BorderGeometry(_TwoIdenticalRings())
    offset = 100.0 / METRES_PER_DEGREE_LONGITUDE
    candidate = geometry.verify(-offset, 0.01, 100.0)
    assert candidate is not None
    assert candidate.multiplicity == 2

    # ... and the correction shows up as roughly half the draws surviving
    rng = np.random.default_rng(2)
    _, drawn = geometry.sample(rng, 100.0, 400)
    assert 1.6 < drawn / 400 < 2.6


# --- the prune must never hide a ring that is genuinely in range -------------
#
# `distances_to_rings` answers "every ring that could be within `search_m`" by
# testing the point against each ring's bounding box grown by that radius. That
# is a superset of the right answer by construction: the nearest point of a ring
# lies in the ring's own box, so a point within `search_m` of the ring is within
# `search_m` of the box, and a box grown by `search_m` contains its whole
# `search_m` neighbourhood. Moving away from a border moves the point out of the
# box, and the pad grows with the radius by exactly the amount that compensates.
#
# The argument only holds while the pad is never understated, which is what
# these check. Both cases below were real defects.


def _one_ring_geometry(coords: np.ndarray) -> BorderGeometry:
    class _Polygons:
        def __init__(self) -> None:
            self.xmin = np.array([coords[0].min()], dtype=np.int32)
            self.xmax = np.array([coords[0].max()], dtype=np.int32)
            self.ymin = np.array([coords[1].min()], dtype=np.int32)
            self.ymax = np.array([coords[1].max()], dtype=np.int32)

        def __len__(self) -> int:
            return 1

        def coords_of(self, index: int) -> np.ndarray:
            return coords

    return BorderGeometry(_Polygons())


@pytest.mark.unit
def test_a_ring_just_across_the_antimeridian_is_still_measured() -> None:
    # the box test compares longitudes, and +179.9999 against -179.9999 is
    # 360 degrees apart in arithmetic and 20 metres apart on the globe. The
    # distance function has always wrapped; the filter feeding it did not, so
    # this ring was pruned before anything measured it
    geometry = _one_ring_geometry(
        _ring(
            (179.9990, 10.0), (179.9999, 10.0), (179.9999, 10.001), (179.9990, 10.001)
        )
    )
    measured = dict(geometry.distances_to_rings(-179.9999, 10.0005, 1000.0))
    assert measured, "the ring across the seam was pruned"
    assert measured[0] < 50.0

    # ... and the consequence that matters: a point 20 m from a border must not
    # be accepted as a sample of what a kilometre from a border looks like
    assert geometry.verify(-179.9999, 10.0005, 1000.0) is None


@pytest.mark.unit
def test_the_longitude_pad_holds_at_the_highest_latitude_in_reach() -> None:
    """A pad taken at the point's own latitude is too small near a pole.

    A degree of longitude shortens towards the pole, so metres-to-degrees taken
    at the point understates what a ring slightly nearer the pole needs. It only
    bites where the cosine changes sharply over the latitude band in reach,
    which is the last fraction of a degree - the ring below is ~5.3 km away and
    150 degrees of longitude from the probe, and a pad taken at the probe's own
    latitude reaches only 103 of them.
    """
    geometry = _one_ring_geometry(
        _ring((149.99, 89.99), (150.01, 89.99), (150.01, 89.995), (149.99, 89.995))
    )
    # what is asserted is that the ring survives the prune, not what its
    # distance comes out as: 150 degrees of longitude is far outside the local
    # equirectangular frame the measurement is valid in, and the prune's job is
    # to hand the measurement everything that could be in range, not to be
    # right about things that are not
    assert dict(geometry.distances_to_rings(0.0, 89.95, 10_000.0)), (
        "the pad was computed as if the point's own latitude were the worst "
        "case, and pruned a ring nearer the pole than that"
    )


@pytest.mark.slow
def test_the_prune_agrees_with_brute_force_over_the_packaged_borders() -> None:
    """No ring in range is ever pruned, checked against every ring there is.

    The superset argument above is a proof, and this is the thing that would
    catch a hole in it: for each probe, every ring in the dataset is measured
    and any that came out inside the search radius must have survived the box
    test. Points are drawn along the antimeridian and up to the poles as well
    as at random, because that is where the pad arithmetic is delicate.
    """
    from tests.auxiliaries import boundaries

    geometry = BorderGeometry(boundaries)
    rng = np.random.default_rng(11)
    probes = [
        (
            float(rng.uniform(-180.0, 180.0)),
            float(np.degrees(np.arcsin(rng.uniform(-1, 1)))),
        )
        for _ in range(12)
    ]
    probes += [
        (179.9999, 10.0),
        (-179.9999, 10.0),
        (179.99, -16.5),
        (-179.99, -16.5),
        (0.0, 89.99),
        (100.0, -89.99),
        (180.0, 65.0),
        (-180.0, 65.0),
    ]

    for search_m in (100.0, 10_000.0):
        for lng, lat in probes:
            cos_lat = max(math.cos(math.radians(lat)), 1e-9)
            kept = dict(geometry.distances_to_rings(lng, lat, search_m))
            in_range = {
                ring_id
                for ring_id in range(geometry.ring_count)
                if geometry._distance_to_ring(ring_id, lng, lat, cos_lat) <= search_m
            }
            missed = in_range - set(kept)
            assert not missed, (
                f"({lng}, {lat}) within {search_m} m: the box test pruned rings "
                f"{sorted(missed)}, which brute force finds in range"
            )


@pytest.mark.slow
def test_a_wider_search_never_changes_the_verdict() -> None:
    """Why the search radius is the target distance and not a multiple of it.

    The search is centred on the *probe*, not on the border site it was offset
    from, so anything nearer than the target distance is inside a radius of the
    target distance by definition. Widening can only add rings that are further
    away than the question is about. The intuition that it should be twice the
    distance - out to the point, then around it - anchors the query at the
    border site instead, and is answered here rather than argued: at ten times
    the radius, well past twice, neither the nearest ring nor the set of rings
    at the target distance moves.
    """
    from tests.auxiliaries import boundaries

    geometry = BorderGeometry(boundaries)
    rng = np.random.default_rng(5)
    for distance_m in (1.0, 100.0, 1_000.0):
        tight = distance_m * (1 + DISTANCE_TOLERANCE)
        for _ in range(40):
            lng, lat = geometry.draw(rng, distance_m)
            if not (-180.0 <= lng <= 180.0 and -90.0 <= lat <= 90.0):
                continue
            near = dict(geometry.distances_to_rings(lng, lat, tight))
            wide = dict(geometry.distances_to_rings(lng, lat, 10 * distance_m))

            widest = min(wide.values(), default=float("inf"))
            if widest <= tight:
                assert min(near.values()) == pytest.approx(widest), (
                    f"({lng}, {lat}): the nearest ring within {tight:.3f} m "
                    "disagrees with the nearest found by a ten times wider search"
                )

            def at_target(found: dict[int, float]) -> set[int]:
                return {
                    ring_id
                    for ring_id, measured in found.items()
                    if abs(measured - distance_m) <= DISTANCE_TOLERANCE * distance_m
                }

            assert at_target(near) == at_target(wide), (
                f"({lng}, {lat}): a wider search changes which rings sit at "
                f"{distance_m} m, so the multiplicity correction would differ"
            )
