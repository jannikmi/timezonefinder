#!/usr/bin/env python3

"""Draw points that sit an exact distance from the nearest timezone border.

Why this is not "sample points and keep the ones near a border"
---------------------------------------------------------------

That is the unbiased method and it is unusable: the band within 10 m of a
border is about one part in 20,000 of the planet's surface, so a uniform sample
of the globe would spend a hundred thousand distance computations per accepted
point, and at 1 m it is ten times worse.

So the sample is drawn *from the border outwards* instead, and the bias that
introduces is removed rather than tolerated. The set of points exactly ``d``
from a ring is that ring's **offset locus**, and it has two parts:

- one parallel curve per edge, offset ``d`` along the edge normal, on each side
- one circular arc of radius ``d`` per vertex, on whichever side the ring turns
  *away* from - spanning the turning angle, and joining the two parallel curves
  that would otherwise leave a gap there

Sampling the edges alone - the obvious implementation - silently drops every
arc, and the arcs are not a rounding error. Over the packaged boundaries the
mean edge is ~300 m and the total absolute turning is ~2.3 million radians, so
the arcs are 0.05 % of the locus at 1 m, 4.6 % at 100 m, 33 % at 1 km and
**83 % at 10 km**. An edge-only sampler is therefore fine for a metre and
describes almost none of the right locus for a kilometre.

Two corrections after the draw, both necessary
----------------------------------------------

**A drawn point is verified, never assumed.** Offsetting from one ring says
nothing about the rest of the world: the perpendicular can overshoot a short
edge, a concave stretch shadows itself, and another border can simply be
nearer. So every candidate's true distance to the *nearest* border is computed
and the point is dropped unless it matches what was asked for. That rejection
is the whole difference between "10 km from this edge" and "10 km from any
border": at 10 km only about a fifth of candidates survive, and the median
survivor-less candidate sits at ~0.77 of the nominal distance.

**A shared border is drawn twice.** Every border between two zones is stored in
both zones' rings - a coastline in the land polygon and in the ocean polygon
around it - so offsetting from each produces the same locus, and it would be
over-represented two-to-one against a border that only one ring describes.
Each accepted point is therefore kept with probability ``1 / m``, where ``m``
counts the rings that are at the target distance from it.

What stays approximate
----------------------

Distances are computed in a local equirectangular frame - degrees of latitude
and longitude converted to metres at the point's own latitude. Over the spans
this samples (a metre to ten kilometres) the difference against a geodesic is
far below the geometry being measured, and the alternative would be to make
every point-to-segment distance a spherical construction for no readable gain.
"""

import math
from functools import lru_cache
from typing import Iterator, NamedTuple, TypeVar

import numpy as np

from timezonefinder.configs import COORD2INT_FACTOR

# Metres per degree: mean for latitude, equatorial for longitude, the latter
# scaled by the cosine of the working latitude at every use.
METRES_PER_DEGREE_LATITUDE = 110_574.0
METRES_PER_DEGREE_LONGITUDE = 111_320.0

# Below this the cosine correction stops being a correction; only reachable
# within a few metres of a pole, where no timezone border runs anyway.
MIN_COS_LATITUDE = 1e-9

# A candidate is accepted when its measured distance is within this fraction of
# the distance asked for. Loose enough to absorb the equirectangular
# approximation and the float error in a point-to-segment projection, tight
# enough that "10 km" cannot quietly mean 9 km.
DISTANCE_TOLERANCE = 0.02


class Ring:
    """One boundary polygon, in the derived forms the sampler needs.

    Built once per polygon and cached, because a single accepted point costs a
    distance computation against every ring whose bounding box is in range, and
    the same handful of rings comes up repeatedly along one border.
    """

    __slots__ = ("lng", "lat", "east", "north", "length", "heading", "turning")

    def __init__(self, coordinates: np.ndarray) -> None:
        lng = coordinates[0].astype(np.float64) / COORD2INT_FACTOR
        lat = coordinates[1].astype(np.float64) / COORD2INT_FACTOR
        next_lng = np.roll(lng, -1)
        next_lat = np.roll(lat, -1)

        delta_lng = next_lng - lng
        # the seam of a ring that wraps the antimeridian: the two vertices are
        # neighbours on the globe and 360 degrees apart in the stored numbers
        seam = np.abs(delta_lng) > 180.0
        mean_lat = np.radians((lat + next_lat) / 2.0)
        east = delta_lng * np.cos(mean_lat) * METRES_PER_DEGREE_LONGITUDE
        north = (next_lat - lat) * METRES_PER_DEGREE_LATITUDE
        east[seam] = 0.0
        north[seam] = 0.0

        length = np.hypot(east, north)
        heading = np.arctan2(north, east)
        # the turn taken at vertex i, between the edge arriving and the edge
        # leaving; wrapped into (-pi, pi] so a heading crossing due west is a
        # small turn rather than an almost complete one
        turning = (heading - np.roll(heading, 1) + np.pi) % (2 * np.pi) - np.pi
        # a vertex next to a zero-length edge has no defined turn
        turning[(length == 0.0) | (np.roll(length, 1) == 0.0)] = 0.0

        self.lng = lng
        self.lat = lat
        self.east = east
        self.north = north
        self.length = length
        self.heading = heading
        self.turning = turning


class Candidate(NamedTuple):
    """A drawn point, and what the verification found out about it."""

    lng: float
    lat: float
    distance_m: float
    rings_at_distance: tuple[int, ...]

    @property
    def multiplicity(self) -> int:
        return len(self.rings_at_distance)


class CandidatePair(NamedTuple):
    """Two verified probes on opposite sides of one sampled border site."""

    positive: Candidate
    negative: Candidate
    rings_at_distance: tuple[int, ...]

    @property
    def multiplicity(self) -> int:
        """How many stored rings describe the sampled physical border."""
        return len(self.rings_at_distance)


# scalar for one ring, array for all of them at once - the formula is the same
# and the sampler needs both, so it is written once and applied elementwise
Measure = TypeVar("Measure", float, np.ndarray)


def offset_locus_measure(
    edge_length_m: Measure, absolute_turning: Measure, distance_m: float
) -> Measure:
    """The length of the offset locus of a ring, both sides taken together.

    Two parallel curves of the ring's own length, plus one arc per vertex whose
    radius is the offset distance and whose angle is the turn taken there.
    """
    return 2.0 * edge_length_m + distance_m * absolute_turning


class BorderGeometry:
    """Every packaged boundary ring, and the two operations the sweep needs."""

    def __init__(self, polygons, ring_cache_size: int = 256) -> None:
        self._polygons = polygons
        self.ring_count = len(polygons)
        self.lng_min = polygons.xmin.astype(np.float64) / COORD2INT_FACTOR
        self.lng_max = polygons.xmax.astype(np.float64) / COORD2INT_FACTOR
        self.lat_min = polygons.ymin.astype(np.float64) / COORD2INT_FACTOR
        self.lat_max = polygons.ymax.astype(np.float64) / COORD2INT_FACTOR

        self._cached_ring = lru_cache(maxsize=ring_cache_size)(self._build_ring)
        self.edge_length = np.empty(self.ring_count)
        self.absolute_turning = np.empty(self.ring_count)
        for ring_id in range(self.ring_count):
            ring = self._build_ring(ring_id)
            self.edge_length[ring_id] = ring.length.sum()
            self.absolute_turning[ring_id] = np.abs(ring.turning).sum()

    def _build_ring(self, ring_id: int) -> Ring:
        return Ring(self._polygons.coords_of(ring_id))

    def ring(self, ring_id: int) -> Ring:
        return self._cached_ring(ring_id)

    def draw(self, rng: np.random.Generator, distance_m: float) -> tuple[float, float]:
        """A point on some ring's offset locus at ``distance_m``.

        Uniform over the locus, which is what keeps the sample from clustering
        where vertices are dense: an intricate coastline carries no more weight
        per kilometre of border than a straight one does.
        """
        weights = offset_locus_measure(
            self.edge_length, self.absolute_turning, distance_m
        )
        ring_id = int(rng.choice(self.ring_count, p=weights / weights.sum()))
        ring = self.ring(ring_id)

        edge_measure = 2.0 * self.edge_length[ring_id]
        arc_measure = distance_m * self.absolute_turning[ring_id]
        if rng.random() * (edge_measure + arc_measure) < edge_measure:
            base_lng, base_lat, bearing = self._draw_on_edge(rng, ring)
        else:
            base_lng, base_lat, bearing = self._draw_on_arc(rng, ring)

        return self._offset(base_lng, base_lat, bearing, distance_m)

    def draw_pair(
        self, rng: np.random.Generator, distance_m: float
    ) -> tuple[int, tuple[float, float], tuple[float, float]]:
        """One border site and probes ``distance_m`` along both edge normals.

        This population is deliberately different from :meth:`draw`. A paired
        question is about uniformly sampled *border locations*, so rings and
        edges are weighted only by border length. Vertex arcs belong to the
        offset-locus point population; a vertex itself has zero border length
        and no unique opposite normal to pair with it.
        """
        ring_id = int(
            rng.choice(self.ring_count, p=self.edge_length / self.edge_length.sum())
        )
        ring = self.ring(ring_id)
        base_lng, base_lat, heading = self._draw_edge_site(rng, ring)
        normal = heading + math.pi / 2.0
        return (
            ring_id,
            self._offset(base_lng, base_lat, normal, distance_m),
            self._offset(base_lng, base_lat, normal + math.pi, distance_m),
        )

    @staticmethod
    def _offset(
        base_lng: float, base_lat: float, bearing: float, distance_m: float
    ) -> tuple[float, float]:
        cos_lat = max(math.cos(math.radians(base_lat)), MIN_COS_LATITUDE)
        return (
            base_lng
            + distance_m * math.cos(bearing) / (METRES_PER_DEGREE_LONGITUDE * cos_lat),
            base_lat + distance_m * math.sin(bearing) / METRES_PER_DEGREE_LATITUDE,
        )

    @staticmethod
    def _draw_on_edge(
        rng: np.random.Generator, ring: Ring
    ) -> tuple[float, float, float]:
        """A point along an edge, and the normal pointing to one of its sides."""
        base_lng, base_lat, heading = BorderGeometry._draw_edge_site(rng, ring)
        side = 1.0 if rng.random() < 0.5 else -1.0
        return base_lng, base_lat, heading + side * math.pi / 2.0

    @staticmethod
    def _draw_edge_site(
        rng: np.random.Generator, ring: Ring
    ) -> tuple[float, float, float]:
        """A border location drawn uniformly by edge length and its heading."""
        edge = int(rng.choice(len(ring.length), p=ring.length / ring.length.sum()))
        along = rng.random()
        following = (edge + 1) % len(ring.length)
        return (
            float(ring.lng[edge] + along * (ring.lng[following] - ring.lng[edge])),
            float(ring.lat[edge] + along * (ring.lat[following] - ring.lat[edge])),
            float(ring.heading[edge]),
        )

    @staticmethod
    def _draw_on_arc(
        rng: np.random.Generator, ring: Ring
    ) -> tuple[float, float, float]:
        """A point on the arc a vertex contributes, on the side it turns away from.

        A left turn leaves a wedge open on the right and shadows the left, so
        the arc runs from the arriving edge's right normal to the leaving
        edge's right normal - and mirrored for a right turn. Sweeping the
        bearing uniformly across that wedge is uniform along the arc, since the
        radius is the same everywhere on it.
        """
        turns = np.abs(ring.turning)
        vertex = int(rng.choice(len(turns), p=turns / turns.sum()))
        turn = float(ring.turning[vertex])
        arriving = float(ring.heading[(vertex - 1) % len(ring.heading)])
        start = arriving - math.copysign(math.pi / 2.0, turn)
        return (
            float(ring.lng[vertex]),
            float(ring.lat[vertex]),
            start + rng.random() * turn,
        )

    def distances_to_rings(
        self, lng: float, lat: float, search_m: float
    ) -> Iterator[tuple[int, float]]:
        """Distance in metres to every ring that could be within ``search_m``.

        Bounding boxes do the pruning, over **every** ring in the dataset - the
        H3 shortcut index is deliberately not consulted here. It answers "which
        polygons might *contain* this point", which is a different question: a
        border a few metres away can belong to a polygon that overlaps a
        neighbouring cell and not this one, and at a cell edge the nearest
        border is routinely in the neighbour. Anything built on the index would
        have to widen it by a ring of cells and would still be arguing about
        the right width. A box test over 1,322 rings is one vectorised
        comparison and needs no such argument.

        The prune is a superset by construction, and two things are needed to
        keep it one:

        - the longitude gap is measured **the short way round**, or a ring 20 m
          away across the antimeridian is pruned as if it were 360 degrees away.
          The distance function below wraps; before this the filter feeding it
          did not, so that ring was never measured at all
        - the longitude pad is computed at the **highest latitude in reach**,
          not at the point's own. A degree of longitude shortens towards the
          pole, so a pad derived from the point's latitude is too small for a
          ring slightly nearer the pole, and would prune a ring that is inside
          the radius
        """
        pad_lat = search_m / METRES_PER_DEGREE_LATITUDE
        # the worst case within reach: a degree of longitude is shortest at the
        # highest |latitude| a ring within `search_m` could occupy
        worst_lat = min(abs(lat) + pad_lat, 90.0)
        cos_lat = max(math.cos(math.radians(lat)), MIN_COS_LATITUDE)
        pad_cos = max(math.cos(math.radians(worst_lat)), MIN_COS_LATITUDE)
        pad_lng = min(search_m / (METRES_PER_DEGREE_LONGITUDE * pad_cos), 180.0)

        # zero when the point's longitude is inside the box, otherwise the
        # shorter of the two ways round to the nearer edge of it
        inside = (self.lng_min <= lng) & (lng <= self.lng_max)
        to_min = np.abs((lng - self.lng_min + 180.0) % 360.0 - 180.0)
        to_max = np.abs((lng - self.lng_max + 180.0) % 360.0 - 180.0)
        lng_gap = np.where(inside, 0.0, np.minimum(to_min, to_max))

        in_range = np.nonzero(
            (lng_gap <= pad_lng)
            & (self.lat_min - pad_lat <= lat)
            & (lat <= self.lat_max + pad_lat)
        )[0]
        for ring_id in in_range:
            yield int(ring_id), self._distance_to_ring(int(ring_id), lng, lat, cos_lat)

    def _distance_to_ring(
        self, ring_id: int, lng: float, lat: float, cos_lat: float
    ) -> float:
        """Shortest distance from the point to any edge of one ring."""
        ring = self.ring(ring_id)
        # wrapped, so a ring on the far side of the antimeridian is measured
        # the short way round rather than across the whole globe
        delta_lng = (ring.lng - lng + 180.0) % 360.0 - 180.0
        start_east = delta_lng * cos_lat * METRES_PER_DEGREE_LONGITUDE
        start_north = (ring.lat - lat) * METRES_PER_DEGREE_LATITUDE
        edge_east = np.roll(start_east, -1) - start_east
        edge_north = np.roll(start_north, -1) - start_north

        squared = edge_east * edge_east + edge_north * edge_north
        with np.errstate(invalid="ignore", divide="ignore"):
            # where along the edge the perpendicular from the point lands,
            # clamped so a foot beyond either end falls back to that endpoint
            along = np.clip(
                -(start_east * edge_east + start_north * edge_north) / squared, 0.0, 1.0
            )
        along = np.where(squared > 0.0, along, 0.0)
        nearest = np.hypot(
            start_east + along * edge_east, start_north + along * edge_north
        )
        nearest[ring.length == 0.0] = np.inf
        return float(nearest.min())

    def verify(self, lng: float, lat: float, distance_m: float) -> Candidate | None:
        """Measure a drawn point, or reject it.

        ``None`` means the point is not where it was meant to be - the nearest
        border is closer than asked for, which is the usual outcome once the
        offset exceeds the length of the edge it came from.
        """
        if not (-180.0 <= lng <= 180.0 and -90.0 <= lat <= 90.0):
            return None
        tolerance = DISTANCE_TOLERANCE * distance_m
        measured = list(self.distances_to_rings(lng, lat, distance_m + tolerance))
        if not measured:
            return None
        nearest = min(distance for _, distance in measured)
        if abs(nearest - distance_m) > tolerance:
            return None
        return Candidate(
            lng=lng,
            lat=lat,
            distance_m=nearest,
            rings_at_distance=tuple(
                ring_id
                for ring_id, distance in measured
                if abs(distance - distance_m) <= tolerance
            ),
        )

    def sample(
        self, rng: np.random.Generator, distance_m: float, count: int
    ) -> tuple[list[Candidate], int]:
        """``count`` accepted points at ``distance_m``, and how many were drawn.

        The draw count is reported because the acceptance rate is itself a
        result: it says how much of a ring's offset locus is shadowed by the
        rest of the world at that distance.
        """
        accepted: list[Candidate] = []
        drawn = 0
        while len(accepted) < count:
            drawn += 1
            candidate = self.verify(*self.draw(rng, distance_m), distance_m)
            if candidate is None:
                continue
            # a border described by several rings would otherwise be drawn once
            # per ring; keep one draw in `multiplicity` of them
            if rng.random() * candidate.multiplicity >= 1.0:
                continue
            accepted.append(candidate)
        return accepted, drawn

    def verify_pair(
        self,
        source_ring: int,
        positive: tuple[float, float],
        negative: tuple[float, float],
        distance_m: float,
    ) -> CandidatePair | None:
        """Verify both sides and identify the rings describing their border."""
        positive_candidate = self.verify(*positive, distance_m)
        negative_candidate = self.verify(*negative, distance_m)
        if positive_candidate is None or negative_candidate is None:
            return None

        negative_rings = set(negative_candidate.rings_at_distance)
        shared_rings = tuple(
            ring_id
            for ring_id in positive_candidate.rings_at_distance
            if ring_id in negative_rings
        )
        # The sampled source ring must remain the nearest border to both probes.
        # Otherwise the pair belongs to a different or shadowing border and no
        # longer answers the question asked at the sampled site.
        if source_ring not in shared_rings:
            return None
        return CandidatePair(
            positive=positive_candidate,
            negative=negative_candidate,
            rings_at_distance=shared_rings,
        )

    def sample_pairs(
        self, rng: np.random.Generator, distance_m: float, count: int
    ) -> tuple[list[CandidatePair], int]:
        """``count`` verified two-sided border locations and raw draw count."""
        accepted: list[CandidatePair] = []
        drawn = 0
        while len(accepted) < count:
            drawn += 1
            candidate = self.verify_pair(*self.draw_pair(rng, distance_m), distance_m)
            if candidate is None:
                continue
            # The same physical border is stored once in each adjacent zone.
            if rng.random() * candidate.multiplicity >= 1.0:
                continue
            accepted.append(candidate)
        return accepted, drawn
