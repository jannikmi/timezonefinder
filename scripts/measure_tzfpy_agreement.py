#!/usr/bin/env python3

"""How far from a timezone border the two packages stop agreeing.

What this answers
-----------------

``docs/alternatives.rst`` states that ``tzfpy`` ships simplified polygons and
trades accuracy near borders for size and speed. Nothing in this repository
said what that trade *costs*, which is the question `issue #542
<https://github.com/jannikmi/timezonefinder/issues/542>`__ has to answer before
the polygon encoding can be chosen: this package spends ~1.1 cm of coordinate
resolution and there is no evidence anywhere about what that resolution buys.

Ask it the obvious way - run both packages over a uniform sample of the globe
and count - and the answer is zero disagreements, which is true and useless.
A uniformly drawn coordinate is hundreds of kilometres from the nearest
timezone border, so such a sample measures how much of the world is nowhere
near a border, not how the two packages behave where the answer is actually
contested. The committed point fixtures have the same problem in a milder form:
even ``ambiguous_shortcut_points``, which is the closest thing to a near-border
sample this repository has, only guarantees that a point's H3 cell holds more
than one candidate zone - and a resolution 4 cell is tens of kilometres across.

So the primary measurement here does not sample points at all. It samples the
**border itself** - a position drawn along the boundary polygons this package
ships, weighted by length - and then probes at a controlled distance to either
side of it. Sweeping that distance turns a single rate into a curve, and the
curve is the answer: it says how far `tzfpy`'s boundary sits from this one.

Reading the curve
-----------------

**50 % is the ceiling, not 100 %.** Each site contributes two probes, one on
each side of this package's border. If the other package's border is merely
displaced rather than absent, both probes land on the same side of *it*, so
exactly one of the two disagrees. A rate of `r` therefore says that roughly
`r / 50 %` of the border length has moved by more than the probe distance.

The overlapping-zone rate in the last column is flat across distances by
construction - it is about zone naming, not geometry - and is a useful check
that the sweep is working.

Two things make the numbers attributable, and without either they would not be
-----------------------------------------------------------------------------

**The boundary release has to match.** Both packages compile
timezone-boundary-builder output, and a disagreement between two *releases*
says nothing about geometry - a border genuinely moved. So this refuses to
report unless ``tzfpy.data_version()`` equals the release this repository
packages. When they match, this package answers from the source polygons and
``tzfpy`` from a simplification of the same polygons, which is what makes a
disagreement attributable to the simplification.

**Overlapping zones have to be separated out.** The dataset ships genuinely
overlapping polygons - ``Asia/Urumqi`` inside ``Asia/Shanghai`` is the large
one - and each package picks one answer from the overlap by its own rule.
Comparing ``timezone_at`` against ``tzfpy.get_tz`` counts every such point as a
disagreement, and on a uniform sample they are *all* of them, while saying
nothing about geometry. Asking instead whether our answer appears in
``tzfpy.get_tzs`` - the full set of zones it holds over that point - is the
rate that describes the geometry, and it is the one to quote.

Usage::

    make tzfpy-agreement
    uv run --group compare python -m scripts.measure_tzfpy_agreement --help
"""

import argparse
import json
import math
import sys
from typing import Callable, Iterable, NamedTuple, Sequence

import numpy as np

from scripts.benchmark_utils import TZFPY_DISTRIBUTION, tzfpy_version
from scripts.configs import read_data_version
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder
from timezonefinder.configs import COORD2INT_FACTOR
from timezonefinder.utils import is_ocean_timezone

# Metres per degree, at the equator for longitude and mean for latitude. A
# spherical approximation is the right tool here: it converts a probe distance
# into a coordinate offset over a span of metres, where the difference against
# a proper geodesic is far below the simplification being measured.
METRES_PER_DEGREE_LATITUDE = 110_574.0
METRES_PER_DEGREE_LONGITUDE = 111_320.0

# The distances probed either side of a border, in metres. Chosen to bracket
# the answer rather than to sample it evenly: the interesting decade turned out
# to be 10 m to 100 m, and both ends are there to show the curve reaching its
# ceiling and its floor.
DEFAULT_DISTANCES_M: tuple[float, ...] = (1.0, 10.0, 100.0, 1_000.0, 10_000.0)

# Border positions drawn per distance. Every distance probes the *same* sites,
# so the columns of the report differ only in the offset and not in which piece
# of border they describe - which is what makes the curve readable as one
# measurement rather than five.
DEFAULT_SITES = 2_000

# Fixed so that two runs of this script are comparable; there is nothing to
# tune here and a wandering sample would be mistaken for a `tzfpy` release.
DEFAULT_SEED = 20260824

# The committed point fixtures, in the order the secondary report prints them.
POINT_CLASSES: tuple[str, ...] = (
    RANDOM_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
)

# How a single point's two answers relate. `OVERLAP_POLICY` is the case the
# module docstring exists for: both packages hold our zone over the point and
# merely disagree about which of the overlapping zones to name.
AGREE = "agree"
OVERLAP_POLICY = "overlap_policy"
SUBSTANTIVE = "substantive"

# How many substantive disagreements to keep per group. A bare count is
# unattributable - three points out of five thousand could be a coastline, a
# pole, or a bug in this script - so the report names some of them.
MAX_EXAMPLES = 5


class AgreementCounts(NamedTuple):
    """One group of probes, counted three ways, with a few cases named."""

    total: int
    overlap_policy: int
    substantive: int
    examples: tuple[tuple[float, float, str | None, tuple[str, ...]], ...] = ()

    @property
    def first_answer_disagreements(self) -> int:
        """What comparing ``timezone_at`` against ``get_tz`` alone would report."""
        return self.overlap_policy + self.substantive

    def rate(self, count: int) -> float:
        return 100.0 * count / self.total if self.total else 0.0


class BorderSite(NamedTuple):
    """A position on a boundary edge, and the direction across it.

    ``normal_east``/``normal_north`` are a unit vector in metres, perpendicular
    to the edge, so a probe at distance ``d`` is the site offset by ``d`` times
    this - converted back into degrees at the site's own latitude.
    """

    lng: float
    lat: float
    normal_east: float
    normal_north: float


def classify(
    ours: str | None, theirs_first: str | None, theirs_all: Sequence[str]
) -> str:
    """Relate one point's two answers.

    Split out from the measurement loops because it is the whole of the
    interpretation, and it needs no ``tzfpy`` to test: everything else here is
    counting.
    """
    if ours == theirs_first:
        return AGREE
    if ours is not None and ours in theirs_all:
        # they hold our zone over this point too, and picked a different one of
        # the zones overlapping there
        return OVERLAP_POLICY
    return SUBSTANTIVE


def count_agreement(
    points: Iterable[tuple[float, float]],
    ours: Callable[[float, float], str | None],
    theirs_first: Callable[[float, float], str | None],
    theirs_all: Callable[[float, float], Sequence[str]],
) -> AgreementCounts:
    total = overlap = substantive = 0
    examples: list[tuple[float, float, str | None, tuple[str, ...]]] = []
    for lng, lat in points:
        total += 1
        our_answer = ours(lng, lat)
        their_zones = tuple(theirs_all(lng, lat))
        verdict = classify(our_answer, theirs_first(lng, lat), their_zones)
        if verdict == OVERLAP_POLICY:
            overlap += 1
        elif verdict == SUBSTANTIVE:
            substantive += 1
            if len(examples) < MAX_EXAMPLES:
                examples.append((lng, lat, our_answer, their_zones))
    return AgreementCounts(
        total=total,
        overlap_policy=overlap,
        substantive=substantive,
        examples=tuple(examples),
    )


def edge_vectors(
    coordinates: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Per-edge start point, metric displacement and length for one ring.

    ``coordinates`` is the ``(2, n)`` int32 array the packaged data stores, and
    the ring is closed, so edge ``i`` runs from vertex ``i`` to ``i + 1``
    modulo ``n``. Lengths are metres under the spherical approximation above.

    Edges spanning more than 180 degrees of longitude are given zero length
    rather than a length of half the planet: they are the seam of a ring that
    wraps the antimeridian, not a piece of border anyone can stand next to.
    """
    lng = coordinates[0].astype(np.float64) / COORD2INT_FACTOR
    lat = coordinates[1].astype(np.float64) / COORD2INT_FACTOR
    next_lng = np.roll(lng, -1)
    next_lat = np.roll(lat, -1)

    delta_lng = next_lng - lng
    mean_lat = np.radians((lat + next_lat) / 2.0)
    east = delta_lng * np.cos(mean_lat) * METRES_PER_DEGREE_LONGITUDE
    north = (next_lat - lat) * METRES_PER_DEGREE_LATITUDE
    length = np.hypot(east, north)
    length[np.abs(delta_lng) > 180.0] = 0.0
    return lng, lat, east, north, length


def land_boundary_ids(finder: TimezoneFinder, polygons) -> list[int]:
    """Boundary polygons that belong to a real timezone rather than the sea.

    The ocean zones are rectangles of longitude, and the border between two of
    them is a meridian - a definition, which no simplification can move and
    which both packages therefore reproduce exactly. They are 39 % of the
    packaged boundary length, so leaving them in would dilute the measurement
    with border that cannot disagree. Nothing is lost by dropping them:
    coastlines remain, as the boundaries of the land polygons themselves.
    """
    return [
        boundary_id
        for boundary_id in range(len(polygons))
        if not is_ocean_timezone(finder.zone_name_from_boundary_id(boundary_id))
    ]


def sample_border_sites(
    finder: TimezoneFinder,
    polygons,
    count: int,
    rng: np.random.Generator,
) -> list[BorderSite]:
    """Draw ``count`` positions along the packaged borders, weighted by length.

    Length-weighted rather than vertex-weighted on purpose. Vertices cluster on
    intricate coastlines, which is exactly where a simplification loses the
    most, so drawing uniformly over vertices would report a rate for the worst
    border rather than for the average one.
    """
    boundary_ids = land_boundary_ids(finder, polygons)
    rings = {
        boundary_id: edge_vectors(polygons.coords_of(boundary_id))
        for boundary_id in boundary_ids
    }
    perimeters = np.array([rings[i][4].sum() for i in boundary_ids])
    ring_weights = perimeters / perimeters.sum()

    sites: list[BorderSite] = []
    for boundary_id in rng.choice(boundary_ids, size=count, p=ring_weights):
        lng, lat, east, north, length = rings[int(boundary_id)]
        edge = int(rng.choice(len(length), p=length / length.sum()))
        along = float(rng.random())
        next_edge = (edge + 1) % len(length)
        sites.append(
            BorderSite(
                lng=float(lng[edge] + along * (lng[next_edge] - lng[edge])),
                lat=float(lat[edge] + along * (lat[next_edge] - lat[edge])),
                # rotate the edge a quarter turn to get its normal
                normal_east=float(-north[edge] / length[edge]),
                normal_north=float(east[edge] / length[edge]),
            )
        )
    return sites


def probes_at(site: BorderSite, distance_m: float) -> list[tuple[float, float]]:
    """The two probe points ``distance_m`` either side of ``site``."""
    cos_lat = max(math.cos(math.radians(site.lat)), 1e-6)
    east_degrees = site.normal_east / (METRES_PER_DEGREE_LONGITUDE * cos_lat)
    north_degrees = site.normal_north / METRES_PER_DEGREE_LATITUDE
    points = []
    for sign in (1.0, -1.0):
        lng = site.lng + sign * distance_m * east_degrees
        lat = site.lat + sign * distance_m * north_degrees
        if -180.0 <= lng <= 180.0 and -90.0 <= lat <= 90.0:
            points.append((lng, lat))
    return points


class Measurement(NamedTuple):
    """One run: which data both sides answered from, and the counts."""

    data_version: str
    tzfpy_version: str | None
    sites: int
    by_distance: dict[float, AgreementCounts]
    by_point_class: dict[str, AgreementCounts]

    def as_json(self) -> dict:
        return {
            "data_version": self.data_version,
            "tzfpy_version": self.tzfpy_version,
            "sites": self.sites,
            "by_distance_m": {
                str(distance): counts._asdict()
                for distance, counts in self.by_distance.items()
            },
            "by_point_class": {
                name: counts._asdict() for name, counts in self.by_point_class.items()
            },
        }


def _require_matching_dataset(tzfpy) -> str:
    """The guard the whole measurement rests on - see the module docstring."""
    ours = read_data_version()
    theirs = tzfpy.data_version()
    if ours != theirs:
        raise SystemExit(
            f"{TZFPY_DISTRIBUTION} {tzfpy_version()} packages boundary release "
            f"{theirs!r}, this repository packages {ours!r}. A disagreement "
            "between two releases is a border that moved, not geometry that was "
            "simplified, so there is no measurement to take until the two match."
        )
    return ours


def measure(
    distances_m: Sequence[float] = DEFAULT_DISTANCES_M,
    sites: int = DEFAULT_SITES,
    seed: int = DEFAULT_SEED,
    include_point_classes: bool = True,
) -> Measurement:
    import tzfpy

    from tests.auxiliaries import boundaries

    data_version = _require_matching_dataset(tzfpy)
    rng = np.random.default_rng(seed)

    with TimezoneFinder(in_memory=True) as finder:

        def ours(lng: float, lat: float) -> str | None:
            return finder.timezone_at(lng=lng, lat=lat)

        border_sites = sample_border_sites(finder, boundaries, sites, rng)
        by_distance = {
            distance: count_agreement(
                [point for site in border_sites for point in probes_at(site, distance)],
                ours,
                tzfpy.get_tz,
                tzfpy.get_tzs,
            )
            for distance in distances_m
        }
        by_point_class = (
            {
                name: count_agreement(
                    load_benchmark_points(name), ours, tzfpy.get_tz, tzfpy.get_tzs
                )
                for name in POINT_CLASSES
            }
            if include_point_classes
            else {}
        )

    return Measurement(
        data_version=data_version,
        tzfpy_version=tzfpy_version(),
        sites=len(border_sites),
        by_distance=by_distance,
        by_point_class=by_point_class,
    )


def _example_lines(label: str, counts: AgreementCounts) -> list[str]:
    return [
        f"  {label}: ({lng:.5f}, {lat:.5f}) -> {ours!r}, "
        f"{TZFPY_DISTRIBUTION} holds {list(theirs)}"
        for lng, lat, ours, theirs in counts.examples
    ]


def format_report(measurement: Measurement) -> str:
    lines = [
        f"boundary release {measurement.data_version} on both sides "
        f"({TZFPY_DISTRIBUTION} {measurement.tzfpy_version})",
        "",
        f"disagreement by distance from a border, {measurement.sites} sites drawn "
        "along the packaged boundaries",
        "(50% is the ceiling: one probe of each pair is on the side both packages agree on)",
        "",
        f"{'distance':>10}{'probes':>9}{'substantive':>20}{'overlap-policy':>19}",
    ]
    for distance, counts in measurement.by_distance.items():
        lines.append(
            f"{distance:>8.0f} m{counts.total:>9}"
            f"{counts.substantive:>13} {counts.rate(counts.substantive):>5.2f}%"
            f"{counts.overlap_policy:>12} {counts.rate(counts.overlap_policy):>5.2f}%"
        )
    for distance, counts in measurement.by_distance.items():
        lines += _example_lines(f"{distance:.0f} m", counts)

    if measurement.by_point_class:
        lines += [
            "",
            "for contrast, the committed query fixtures - which are workload-shaped,",
            "not border-shaped, and say what a query stream sees rather than what the",
            "geometry does",
            "",
            f"{'point class':<26}{'n':>7}{'substantive':>18}{'overlap-policy':>18}",
        ]
        for name, counts in measurement.by_point_class.items():
            lines.append(
                f"{name:<26}{counts.total:>7}"
                f"{counts.substantive:>11} {counts.rate(counts.substantive):>5.3f}%"
                f"{counts.overlap_policy:>11} {counts.rate(counts.overlap_policy):>5.3f}%"
            )
        for name, counts in measurement.by_point_class.items():
            lines += _example_lines(name, counts)
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--distances",
        type=float,
        nargs="+",
        default=list(DEFAULT_DISTANCES_M),
        metavar="METRES",
        help="distances either side of a border to probe",
    )
    parser.add_argument(
        "--sites",
        type=int,
        default=DEFAULT_SITES,
        help="border positions drawn; every distance probes the same ones",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--no-point-classes",
        action="store_true",
        help="skip the committed query fixtures and report the sweep alone",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the counts as JSON instead of a table",
    )
    args = parser.parse_args(argv)

    measurement = measure(
        distances_m=args.distances,
        sites=args.sites,
        seed=args.seed,
        include_point_classes=not args.no_point_classes,
    )
    print(
        json.dumps(measurement.as_json(), indent=2)
        if args.json
        else format_report(measurement)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
