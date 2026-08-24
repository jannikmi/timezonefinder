#!/usr/bin/env python3

"""How far from a timezone border this package and ``tzfpy`` stop agreeing.

What this answers
-----------------

``docs/alternatives.rst`` states that ``tzfpy`` ships simplified polygons and
trades accuracy near borders for size and speed. Nothing in this repository
said what that trade *costs*, which is the question `issue #542
<https://github.com/jannikmi/timezonefinder/issues/542>`__ has to answer before
the polygon encoding can be chosen: this package spends ~1.1 cm of coordinate
resolution and there is no evidence anywhere about what that resolution buys.

Ask it the obvious way - run both packages over a uniform sample of the globe
and count - and the answer is zero disagreements, which is true and useless. A
uniformly drawn coordinate is hundreds of kilometres from the nearest timezone
border, so such a sample measures how much of the world is nowhere near a
border. The committed point fixtures have the same problem in a milder form:
even ``ambiguous_shortcut_points``, the closest thing to a near-border sample
this repository has, only guarantees that a point's H3 cell holds more than one
candidate zone - and a resolution 4 cell is tens of kilometres across.

So the measurement is taken at a *stated distance from a border*, sweeping the
distance, over points drawn without bias in where on the globe they land. How
those points are produced - and the two ways an obvious implementation of it
goes wrong - is :mod:`scripts.border_sampling`.

Reading the curve
-----------------

The number is what it says: of points exactly this far from a border, the share
that get a different zone from the two packages. It levels off just under half
rather than at 100 %, because the points sit on both sides of this package's
border and only the side the other package's boundary has moved away from can
disagree.

``tzfpy``'s maintainer gives that boundary's maximum displacement as roughly
111 m, which is what the far end of the sweep is checking rather than
discovering - and why nothing beyond 200 m is measured.

The overlapping-zone rate in the last column is near-flat across distances by
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
import sys
from pathlib import Path
from typing import Callable, Iterable, NamedTuple, Sequence

import numpy as np

from scripts.benchmark_utils import TZFPY_DISTRIBUTION, tzfpy_version
from scripts.border_sampling import BorderGeometry, Candidate
from scripts.configs import DOC_ROOT, read_data_version
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder
from timezonefinder.utils import is_ocean_timezone

# The distances swept, in metres: one decade apart, starting at this package's
# own coordinate resolution. ~1.1 cm is the quantization step of the stored
# int32 coordinates, so a point nearer than that to a border is not a thing
# this package can represent, and nothing above 200 m is shown because the
# other package's simplification is bounded well below it - see the module
# docstring.
DEFAULT_DISTANCES_M: tuple[float, ...] = (0.01, 0.1, 1.0, 10.0, 100.0)

# Accepted points per distance. At 33 % this is a standard error of ~1 point,
# which is finer than anything read off the curve.
DEFAULT_POINTS = 2_000

# Fixed so that two runs are comparable; there is nothing to tune here, and a
# wandering sample would be mistaken for a `tzfpy` release.
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
MAX_EXAMPLES = 4

# Where the rendered chart goes. Declared here because this module writes it;
# docs/alternatives.rst is the only reader, and the Makefile passes `--chart`
# with no argument rather than retyping the path.
CHART_PATH = DOC_ROOT / "tzfpy_agreement_by_distance.svg"


class AgreementCounts(NamedTuple):
    """One group of points, counted three ways, with a few cases named."""

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


class DistanceResult(NamedTuple):
    """One column of the sweep."""

    distance_m: float
    drawn: int
    all_borders: AgreementCounts
    land_borders: AgreementCounts

    @property
    def acceptance_rate(self) -> float:
        return 100.0 * self.all_borders.total / self.drawn if self.drawn else 0.0


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


def borders_a_land_zone(candidate: Candidate, ocean_ring: np.ndarray) -> bool:
    """Whether the border this point sits by belongs to a real timezone.

    The ocean zones are lunes of longitude and the border between two of them
    is a meridian - a definition, which no simplification can move and which
    both packages therefore reproduce exactly. They are a large share of the
    packaged boundary length, so a curve over every border is diluted by them.
    Reported both ways rather than filtered, since "any border" is the honest
    global answer and "a border of a land zone" is the one users are near.

    A coastline qualifies: it is stored in the land polygon as well as in the
    ocean polygon around it, so one of the rings at the point is a land one.
    """
    return any(not ocean_ring[ring_id] for ring_id in candidate.rings_at_distance)


class Measurement(NamedTuple):
    """One run: which data both sides answered from, and the counts."""

    data_version: str
    tzfpy_version: str | None
    by_distance: tuple[DistanceResult, ...]
    by_point_class: dict[str, AgreementCounts]

    def as_json(self) -> dict:
        return {
            "data_version": self.data_version,
            "tzfpy_version": self.tzfpy_version,
            "by_distance_m": [
                {
                    "distance_m": result.distance_m,
                    "drawn": result.drawn,
                    "all_borders": result.all_borders._asdict(),
                    "land_borders": result.land_borders._asdict(),
                }
                for result in self.by_distance
            ],
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
    points: int = DEFAULT_POINTS,
    seed: int = DEFAULT_SEED,
    include_point_classes: bool = True,
) -> Measurement:
    import tzfpy

    from tests.auxiliaries import boundaries

    data_version = _require_matching_dataset(tzfpy)
    rng = np.random.default_rng(seed)
    geometry = BorderGeometry(boundaries)

    with TimezoneFinder(in_memory=True) as finder:
        ocean_ring = np.array(
            [
                is_ocean_timezone(finder.zone_name_from_boundary_id(ring_id))
                for ring_id in range(geometry.ring_count)
            ]
        )

        def ours(lng: float, lat: float) -> str | None:
            return finder.timezone_at(lng=lng, lat=lat)

        by_distance = []
        for distance in distances_m:
            accepted, drawn = geometry.sample(rng, distance, points)
            land = [c for c in accepted if borders_a_land_zone(c, ocean_ring)]
            by_distance.append(
                DistanceResult(
                    distance_m=distance,
                    drawn=drawn,
                    all_borders=count_agreement(
                        [(c.lng, c.lat) for c in accepted],
                        ours,
                        tzfpy.get_tz,
                        tzfpy.get_tzs,
                    ),
                    land_borders=count_agreement(
                        [(c.lng, c.lat) for c in land],
                        ours,
                        tzfpy.get_tz,
                        tzfpy.get_tzs,
                    ),
                )
            )

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
        by_distance=tuple(by_distance),
        by_point_class=by_point_class,
    )


def _example_lines(label: str, counts: AgreementCounts) -> list[str]:
    return [
        f"  {label}: ({lng:.5f}, {lat:.5f}) -> {ours!r}, "
        f"{TZFPY_DISTRIBUTION} holds {list(theirs)}"
        for lng, lat, ours, theirs in counts.examples
    ]


def format_distance(distance_m: float) -> str:
    """A distance as a reader would say it, not as a float.

    The sweep starts at this package's own ~1.1 cm coordinate resolution, and
    "0.01 m" on an axis is a number rather than a length.
    """
    if distance_m >= 1000.0:
        return f"{distance_m / 1000:g} km"
    if distance_m >= 1.0:
        return f"{distance_m:g} m"
    return f"{round(distance_m * 100, 6):g} cm"


def format_report(measurement: Measurement) -> str:
    lines = [
        f"boundary release {measurement.data_version} on both sides "
        f"({TZFPY_DISTRIBUTION} {measurement.tzfpy_version})",
        "",
        "a different zone returned, by distance from the nearest timezone border",
        "(just under half is the most this can reach: the points sit on both sides",
        " of our border and only one of them can be the side tzfpy moved away from)",
        "",
        f"{'distance':>10}{'points':>8}{'accepted':>10}"
        f"{'any border':>16}{'land zone border':>20}{'overlap-policy':>17}",
    ]
    for result in measurement.by_distance:
        every = result.all_borders
        land = result.land_borders
        lines.append(
            f"{format_distance(result.distance_m):>10}{every.total:>8}"
            f"{result.acceptance_rate:>9.0f}%"
            f"{every.substantive:>8} {every.rate(every.substantive):>5.2f}%"
            f"{land.substantive:>12} {land.rate(land.substantive):>5.2f}%"
            f"{every.overlap_policy:>10} {every.rate(every.overlap_policy):>5.2f}%"
        )
    for result in measurement.by_distance:
        lines += _example_lines(format_distance(result.distance_m), result.all_borders)

    if measurement.by_point_class:
        lines += [
            "",
            "for contrast, the committed query fixtures - workload-shaped rather than",
            "border-shaped, so they say what a query stream sees and nothing about the",
            "geometry",
            "",
            f"{'point class':<26}{'n':>7}{'substantive':>18}{'overlap-policy':>18}",
        ]
        for name, counts in measurement.by_point_class.items():
            lines.append(
                f"{name:<26}{counts.total:>7}"
                f"{counts.substantive:>11} {counts.rate(counts.substantive):>5.3f}%"
                f"{counts.overlap_policy:>11} {counts.rate(counts.overlap_policy):>5.3f}%"
            )
    return "\n".join(lines)


# --- the chart docs/alternatives.rst embeds ---------------------------------
# Hand-written SVG rather than a plotting library: this is one line chart of
# five points, and the alternative is a dependency heavy enough that nothing
# else in this repository carries it. The output is text, so a regeneration
# shows up in a diff as the numbers that moved.

CHART_WIDTH = 780
CHART_HEIGHT = 420
CHART_MARGIN_LEFT = 76
CHART_MARGIN_RIGHT = 30
CHART_MARGIN_TOP = 96
CHART_MARGIN_BOTTOM = 62
CHART_Y_MAX = 50.0
CHART_INK = "#28323a"
CHART_MUTED = "#6b7a85"
CHART_GRID = "#dde3e8"
CHART_SERIES_ALL = "#1f6feb"
CHART_SERIES_LAND = "#c2570f"


class ChartSeries(NamedTuple):
    label: str
    colour: str
    dashes: str
    # where the value label goes relative to its marker, so the two series do
    # not print over each other where the curves converge
    label_offset: float
    counts: Callable[[DistanceResult], AgreementCounts]


CHART_SERIES = (
    ChartSeries(
        "any timezone border", CHART_SERIES_ALL, "", 20.0, lambda r: r.all_borders
    ),
    ChartSeries(
        "border of a land zone",
        CHART_SERIES_LAND,
        "7 5",
        -13.0,
        lambda r: r.land_borders,
    ),
)


def _chart_x(distance_m: float, low: float, high: float) -> float:
    span = CHART_WIDTH - CHART_MARGIN_LEFT - CHART_MARGIN_RIGHT
    position = (np.log10(distance_m) - low) / (high - low) if high > low else 0.5
    return CHART_MARGIN_LEFT + span * float(position)


def _chart_y(rate: float) -> float:
    span = CHART_HEIGHT - CHART_MARGIN_TOP - CHART_MARGIN_BOTTOM
    return CHART_MARGIN_TOP + span * (1.0 - min(rate, CHART_Y_MAX) / CHART_Y_MAX)


def render_chart(measurement: Measurement) -> str:
    """The sweep as an SVG line chart, ready to be written next to the docs."""
    distances = [result.distance_m for result in measurement.by_distance]
    low, high = float(np.log10(min(distances))), float(np.log10(max(distances)))
    right = CHART_WIDTH - CHART_MARGIN_RIGHT
    baseline = _chart_y(0.0)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CHART_WIDTH} '
        f'{CHART_HEIGHT}" width="{CHART_WIDTH}" height="{CHART_HEIGHT}" '
        f'font-family="Helvetica, Arial, sans-serif" role="img" '
        f'aria-label="How often timezonefinder and tzfpy return a different zone, '
        f'against distance from the nearest timezone border">',
        f'<rect width="{CHART_WIDTH}" height="{CHART_HEIGHT}" fill="#ffffff"/>',
        f'<text x="{CHART_MARGIN_LEFT}" y="32" font-size="17" font-weight="600" '
        f'fill="{CHART_INK}">Where timezonefinder and tzfpy stop agreeing</text>',
        f'<text x="{CHART_MARGIN_LEFT}" y="52" font-size="12.5" fill="{CHART_MUTED}">'
        f"boundary release {measurement.data_version} on both sides, "
        f"{TZFPY_DISTRIBUTION} {measurement.tzfpy_version}, "
        f"{measurement.by_distance[0].all_borders.total} points per distance</text>",
    ]

    # legend, above the plot so it cannot collide with the axis titles
    for index, series in enumerate(CHART_SERIES):
        swatch = CHART_MARGIN_LEFT + index * 210
        dash = f' stroke-dasharray="{series.dashes}"' if series.dashes else ""
        parts.append(
            f'<line x1="{swatch}" y1="{CHART_MARGIN_TOP - 24}" x2="{swatch + 26}" '
            f'y2="{CHART_MARGIN_TOP - 24}" stroke="{series.colour}" '
            f'stroke-width="2.4"{dash}/>'
        )
        parts.append(
            f'<text x="{swatch + 34}" y="{CHART_MARGIN_TOP - 20}" font-size="12.5" '
            f'fill="{CHART_INK}">{series.label}</text>'
        )

    for percent in (0, 10, 20, 30, 40, 50):
        y = _chart_y(float(percent))
        parts.append(
            f'<line x1="{CHART_MARGIN_LEFT}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" '
            f'stroke="{CHART_GRID}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{CHART_MARGIN_LEFT - 10}" y="{y + 4:.1f}" font-size="12" '
            f'text-anchor="end" fill="{CHART_MUTED}">{percent}%</text>'
        )

    for result in measurement.by_distance:
        x = _chart_x(result.distance_m, low, high)
        parts.append(
            f'<line x1="{x:.1f}" y1="{baseline:.1f}" x2="{x:.1f}" '
            f'y2="{baseline + 5:.1f}" stroke="{CHART_MUTED}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{baseline + 22:.1f}" font-size="12.5" '
            f'text-anchor="middle" fill="{CHART_INK}">'
            f"{format_distance(result.distance_m)}</text>"
        )

    for series in CHART_SERIES:
        rates = [
            series.counts(result).rate(series.counts(result).substantive)
            for result in measurement.by_distance
        ]
        points = " ".join(
            f"{_chart_x(result.distance_m, low, high):.1f},{_chart_y(rate):.1f}"
            for result, rate in zip(measurement.by_distance, rates)
        )
        dash = f' stroke-dasharray="{series.dashes}"' if series.dashes else ""
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{series.colour}" '
            f'stroke-width="2.4" stroke-linejoin="round"{dash}/>'
        )
        for index, (result, rate) in enumerate(zip(measurement.by_distance, rates)):
            x = _chart_x(result.distance_m, low, high)
            parts.append(
                f'<circle cx="{x:.1f}" cy="{_chart_y(rate):.1f}" r="4" '
                f'fill="{series.colour}"/>'
            )
            if rate >= 1.0:
                # the end labels are anchored inwards, or half of the first one
                # sits outside the plot and over the percentage axis
                anchor = (
                    "start"
                    if index == 0
                    else "end"
                    if index == len(rates) - 1
                    else "middle"
                )
                parts.append(
                    f'<text x="{x:.1f}" y="{_chart_y(rate) + series.label_offset:.1f}" '
                    f'font-size="12" text-anchor="{anchor}" fill="{series.colour}">'
                    f"{rate:.1f}%</text>"
                )

    parts.append(
        f'<text x="{(CHART_MARGIN_LEFT + right) / 2:.0f}" y="{baseline + 46:.1f}" '
        f'font-size="12.5" text-anchor="middle" fill="{CHART_MUTED}">distance from '
        f"the nearest timezone border (logarithmic)</text>"
    )
    parts.append(
        f'<text x="20" y="{(CHART_MARGIN_TOP + baseline) / 2:.0f}" font-size="12.5" '
        f'text-anchor="middle" fill="{CHART_MUTED}" transform="rotate(-90 20 '
        f'{(CHART_MARGIN_TOP + baseline) / 2:.0f})">a different zone returned</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--distances",
        type=float,
        nargs="+",
        default=list(DEFAULT_DISTANCES_M),
        metavar="METRES",
        help="distances from a border to sample at",
    )
    parser.add_argument(
        "--points",
        type=int,
        default=DEFAULT_POINTS,
        help="accepted points per distance",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--no-point-classes",
        action="store_true",
        help="skip the committed query fixtures and report the sweep alone",
    )
    parser.add_argument(
        "--chart",
        nargs="?",
        const=str(CHART_PATH),
        metavar="PATH",
        help=f"write the sweep as an SVG line chart (default: {CHART_PATH})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the counts as JSON instead of a table",
    )
    args = parser.parse_args(argv)

    measurement = measure(
        distances_m=args.distances,
        points=args.points,
        seed=args.seed,
        include_point_classes=not args.no_point_classes,
    )
    if args.chart:
        Path(args.chart).write_text(render_chart(measurement), encoding="utf-8")
        print(f"wrote {args.chart}", file=sys.stderr)
    print(
        json.dumps(measurement.as_json(), indent=2)
        if args.json
        else format_report(measurement)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
