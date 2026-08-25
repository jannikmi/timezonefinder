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

``tzfpy``'s maintainer gives that boundary's maximum *displacement* as roughly
111 m. The far end of the sweep is not there to confirm it but to show what it
does not cover: a displacement bound governs how far a boundary that survives
simplification may move, and says nothing about features the simplification
removes or merges outright. Those keep the curve above zero a full kilometre
from any border, which is the reason for both the sample size and the log axis
below.

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
from scripts.configs import DOC_ROOT, PROJECT_ROOT, read_data_version
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
# int32 coordinates, so a point nearer than that to a border is not something
# this package can represent.
#
# The far end is not there to show the curve reaching zero. It does not reach
# zero: `tzfpy`'s maintainer states a maximum *displacement* of ~111 m, and a
# displacement bound says nothing about features a simplification removes or
# merges outright - which is why a kilometre out, well past that bound, the two
# packages still disagree about roughly one point in three thousand.
DEFAULT_DISTANCES_M: tuple[float, ...] = (
    0.01,
    0.05,
    0.1,
    0.5,
    1.0,
    5.0,
    10.0,
    50.0,
    100.0,
    500.0,
    1_000.0,
)

# Accepted points per distance. Large because of the tail above, not for
# precision at the near end: the rate at 100 m is ~0.16 % and at 1 km ~0.03 %,
# so a run of 2,000 finds nothing at either and reports a zero - which reads as
# "beyond here the two agree" and is the one conclusion this sweep exists to
# refuse. At this size the far end is a couple of dozen observations rather than
# an absence. A full sweep costs around half an hour, which is why the run is
# saved and the chart can be redrawn from it without measuring again.
DEFAULT_POINTS = 20_000

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

# Where a run is kept so the chart can be redrawn without re-measuring, the
# same arrangement `make benchmarks` has with tmp/benchmark.json. Untracked:
# the chart is the committed artifact, this is the input that produced it.
MEASUREMENT_PATH = PROJECT_ROOT / "tmp" / "tzfpy_agreement.json"


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

    @property
    def substantive_rate(self) -> float:
        return self.rate(self.substantive)

    @property
    def upper_bound_rate(self) -> float:
        """What "none observed" is worth as a number, by the rule of three.

        Seeing nothing in ``n`` tries does not mean the rate is zero, it means
        it is below roughly ``3 / n`` with 95 % confidence. Reporting the zero
        instead is what would let a reader conclude that beyond some distance
        the two packages simply agree - and they do not.
        """
        return 300.0 / self.total if self.total else 0.0


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

    @classmethod
    def from_json(cls, payload: dict) -> "Measurement":
        """Rebuild a run from what :meth:`as_json` wrote.

        Measuring and rendering are decoupled here for the same reason they are
        for the benchmark reports (``CONTRIBUTING.md``): a full sweep takes
        around twenty minutes, and changing how the chart *looks* should not
        cost that - nor should it arrive buried in a fresh set of numbers.
        """
        return cls(
            data_version=payload["data_version"],
            tzfpy_version=payload["tzfpy_version"],
            by_distance=tuple(
                DistanceResult(
                    distance_m=result["distance_m"],
                    drawn=result["drawn"],
                    all_borders=_counts_from_json(result["all_borders"]),
                    land_borders=_counts_from_json(result["land_borders"]),
                )
                for result in payload["by_distance_m"]
            ),
            by_point_class={
                name: _counts_from_json(counts)
                for name, counts in payload["by_point_class"].items()
            },
        )


def _counts_from_json(payload: dict) -> AgreementCounts:
    return AgreementCounts(
        total=payload["total"],
        overlap_policy=payload["overlap_policy"],
        substantive=payload["substantive"],
        examples=tuple(
            (lng, lat, ours, tuple(theirs))
            for lng, lat, ours, theirs in payload["examples"]
        ),
    )


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

CHART_WIDTH = 880
CHART_HEIGHT = 495
CHART_MARGIN_LEFT = 84
CHART_MARGIN_RIGHT = 56
CHART_MARGIN_TOP = 142
CHART_MARGIN_BOTTOM = 62
# The y axis is logarithmic, because the interesting part of this measurement
# spans four orders of magnitude: about half of the points a centimetre from a
# border get a different zone, and a few hundredths of a percent still do a
# kilometre away. On a linear axis the second number is the axis itself, which
# is exactly the reading to avoid - "no disagreements out here" is the thing
# that is not true.
# The y axis is logarithmic, because the interesting part of this measurement
# spans four orders of magnitude: about half of the points a centimetre from a
# border get a different zone, and a few hundredths of a percent still do a
# kilometre away. On a linear axis the second number is the axis itself, which
# is exactly the reading to avoid - "no disagreements out here" is the thing
# that is not true.
#
# Its ends are the nearest 1-or-5 step outside the data rather than a fixed
# decade, so the top of the axis is a value the measurement reaches. A 100 %
# ceiling above a 47 % maximum spends a third of the plot on empty space and
# invites the reader to scale the curve against a number nothing produced.
CHART_AXIS_STEPS = (1.0, 5.0)
CHART_Y_MIN_FLOOR_PERCENT = 0.001
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
        -16.0,
        lambda r: r.land_borders,
    ),
)


def escape_svg_text(text: str) -> str:
    """Text destined for an SVG text node.

    The upper-bound labels start with "<", which an XML parser reads as the
    start of an element - so the chart renders as a parse error rather than as
    a chart, in a file nothing else validates.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class ChartPoint(NamedTuple):
    """One plotted value, and whether anything was actually observed."""

    percent: float
    is_upper_bound: bool

    @property
    def label(self) -> str:
        return (
            f"<{self.percent:.3g}%" if self.is_upper_bound else f"{self.percent:.3g}%"
        )


def chart_point(counts: AgreementCounts) -> ChartPoint:
    """What to plot for one group - never a zero, which a log axis cannot show.

    A group with no disagreement in it is plotted at its 95 % upper bound and
    drawn hollow. That is the honest reading and it is also the one this chart
    exists to give: the curve does not reach zero anywhere it was measured.
    """
    if counts.substantive:
        return ChartPoint(counts.substantive_rate, is_upper_bound=False)
    return ChartPoint(counts.upper_bound_rate, is_upper_bound=True)


def _chart_x(distance_m: float, low: float, high: float) -> float:
    span = CHART_WIDTH - CHART_MARGIN_LEFT - CHART_MARGIN_RIGHT
    position = (np.log10(distance_m) - low) / (high - low) if high > low else 0.5
    return CHART_MARGIN_LEFT + span * float(position)


def axis_bound(value: float, upwards: bool) -> float:
    """The nearest 1-or-5 step at or beyond ``value``.

    ``axis_bound(47, upwards=True)`` is 50 and ``axis_bound(0.0265, False)`` is
    0.01, so both ends of the axis are round numbers the reader can hold onto
    without being further from the data than one step.
    """
    exponent = int(np.floor(np.log10(value)))
    candidates = [
        step * 10.0**power
        for power in (exponent - 1, exponent, exponent + 1)
        for step in CHART_AXIS_STEPS
    ]
    if upwards:
        return min(c for c in candidates if c >= value * (1 - 1e-12))
    return max(c for c in candidates if c <= value * (1 + 1e-12))


def axis_ticks(floor_percent: float, top_percent: float) -> list[float]:
    """Every 1-or-5 step from the floor to the top, inclusive."""
    ticks = [floor_percent]
    while ticks[-1] < top_percent * (1 - 1e-12):
        ticks.append(axis_bound(ticks[-1] * 1.0000001, upwards=True))
    return ticks


def _chart_y(percent: float, floor_percent: float, top_percent: float) -> float:
    span = CHART_HEIGHT - CHART_MARGIN_TOP - CHART_MARGIN_BOTTOM
    low, high = np.log10(floor_percent), np.log10(top_percent)
    position = (np.log10(min(max(percent, floor_percent), top_percent)) - low) / (
        high - low
    )
    return CHART_MARGIN_TOP + span * (1.0 - float(position))


# Legend metrics. The text width is estimated rather than measured - there is
# no font metric available here - which is fine because the only thing it has
# to get right is that the row ends at the right margin.
LEGEND_SWATCH = 34
LEGEND_GAP = 26
LEGEND_CHAR_WIDTH = 6.6


def _legend_entry_width(label: str) -> float:
    return LEGEND_SWATCH + LEGEND_CHAR_WIDTH * len(label)


def _percent_axis_label(percent: float) -> str:
    return f"{percent:.3g}%"


def is_decade(distance_m: float) -> bool:
    """Whether a swept distance is a power of ten - 1 cm, 1 m, 100 m.

    ``bool`` rather than whatever numpy hands back: this is a plain predicate
    and a ``np.bool_`` leaking out of it fails an ``is True`` on the far side.
    """
    exponent = np.log10(distance_m)
    return bool(abs(exponent - round(float(exponent))) < 1e-9)


def render_chart(measurement: Measurement) -> str:
    """The sweep as an SVG line chart, ready to be written next to the docs."""
    distances = [result.distance_m for result in measurement.by_distance]
    low, high = float(np.log10(min(distances))), float(np.log10(max(distances)))
    right = CHART_WIDTH - CHART_MARGIN_RIGHT

    plotted = {
        series.label: [
            chart_point(series.counts(result)) for result in measurement.by_distance
        ]
        for series in CHART_SERIES
    }
    values = [point.percent for points in plotted.values() for point in points]
    floor_percent = max(
        CHART_Y_MIN_FLOOR_PERCENT, axis_bound(min(values), upwards=False)
    )
    top_percent = axis_bound(max(values), upwards=True)
    any_upper_bound = any(
        point.is_upper_bound for points in plotted.values() for point in points
    )

    def y_of(percent: float) -> float:
        return _chart_y(percent, floor_percent, top_percent)

    baseline = y_of(floor_percent)

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
        f"boundary release {escape_svg_text(measurement.data_version)} on both "
        f"sides, {TZFPY_DISTRIBUTION} "
        f"{escape_svg_text(str(measurement.tzfpy_version))}, "
        f"{measurement.by_distance[0].all_borders.total} points per distance; "
        f"both axes logarithmic</text>",
    ]

    # Legend above the plot and pushed to the right. Above, so it cannot
    # collide with the axis titles; right, because the leftmost data label is
    # anchored at the left margin and the axis now tops out just over the
    # largest value, which puts that label exactly where a left-aligned legend
    # would be.
    entries = [(series.label, series.colour, series.dashes) for series in CHART_SERIES]
    if any_upper_bound:
        # only explained when one is actually on the chart - a legend entry for
        # a marker that is not there is a puzzle rather than a key
        entries.append(("hollow: none found, so at most this", CHART_MUTED, "hollow"))
    widths = [_legend_entry_width(label) for label, _, _ in entries]
    cursor = right - sum(widths) - LEGEND_GAP * (len(entries) - 1)
    legend_y = CHART_MARGIN_TOP - 26
    for (label, colour, dashes), width in zip(entries, widths):
        if dashes == "hollow":
            parts.append(
                f'<circle cx="{cursor + 13:.0f}" cy="{legend_y}" r="4.5" '
                f'fill="#ffffff" stroke="{colour}" stroke-width="1.8"/>'
            )
        else:
            dash = f' stroke-dasharray="{dashes}"' if dashes else ""
            parts.append(
                f'<line x1="{cursor:.0f}" y1="{legend_y}" x2="{cursor + 26:.0f}" '
                f'y2="{legend_y}" stroke="{colour}" stroke-width="2.4"{dash}/>'
            )
        parts.append(
            f'<text x="{cursor + LEGEND_SWATCH:.0f}" y="{legend_y + 4}" '
            f'font-size="12.5" fill="{CHART_INK}">{escape_svg_text(label)}</text>'
        )
        cursor += width + LEGEND_GAP

    for tick in axis_ticks(floor_percent, top_percent):
        y = y_of(tick)
        parts.append(
            f'<line x1="{CHART_MARGIN_LEFT}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" '
            f'stroke="{CHART_GRID}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{CHART_MARGIN_LEFT - 10}" y="{y + 4:.1f}" font-size="12" '
            f'text-anchor="end" fill="{CHART_MUTED}">'
            f"{_percent_axis_label(tick)}</text>"
        )

    for result in measurement.by_distance:
        x = _chart_x(result.distance_m, low, high)
        parts.append(
            f'<line x1="{x:.1f}" y1="{baseline:.1f}" x2="{x:.1f}" '
            f'y2="{baseline + 5:.1f}" stroke="{CHART_MUTED}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{baseline + 22:.1f}" font-size="11.5" '
            f'text-anchor="middle" fill="{CHART_INK}">'
            f"{format_distance(result.distance_m)}</text>"
        )

    for series in CHART_SERIES:
        points = plotted[series.label]
        polyline = " ".join(
            f"{_chart_x(result.distance_m, low, high):.1f},{y_of(point.percent):.1f}"
            for result, point in zip(measurement.by_distance, points)
        )
        dash = f' stroke-dasharray="{series.dashes}"' if series.dashes else ""
        parts.append(
            f'<polyline points="{polyline}" fill="none" stroke="{series.colour}" '
            f'stroke-width="2.4" stroke-linejoin="round"{dash}/>'
        )
        for index, (result, point) in enumerate(zip(measurement.by_distance, points)):
            x = _chart_x(result.distance_m, low, high)
            y = y_of(point.percent)
            if point.is_upper_bound:
                parts.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#ffffff" '
                    f'stroke="{series.colour}" stroke-width="1.8"/>'
                )
            else:
                parts.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{series.colour}"/>'
                )
            # only the decade positions carry a number. Every point would be 22
            # labels over 11 markers, and the page prints the whole table anyway
            if not is_decade(result.distance_m) and not point.is_upper_bound:
                continue
            # the end labels are anchored inwards, or half of the first one
            # sits outside the plot and over the percentage axis
            anchor = (
                "start"
                if index == 0
                else "end"
                if index == len(points) - 1
                else "middle"
            )
            # a label below a point near the floor would land under the axis
            offset = series.label_offset
            if offset > 0 and y + offset > baseline - 4:
                offset = -16.0
            parts.append(
                f'<text x="{x:.1f}" y="{y + offset:.1f}" font-size="12" '
                f'text-anchor="{anchor}" fill="{series.colour}">'
                f"{escape_svg_text(point.label)}</text>"
            )

    parts.append(
        f'<text x="{(CHART_MARGIN_LEFT + right) / 2:.0f}" y="{baseline + 46:.1f}" '
        f'font-size="12.5" text-anchor="middle" fill="{CHART_MUTED}">distance from '
        f"the nearest timezone border</text>"
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
    parser.add_argument(
        "--json-out",
        nargs="?",
        const=str(MEASUREMENT_PATH),
        metavar="PATH",
        help=f"save the run so --from-json can redraw it (default: {MEASUREMENT_PATH})",
    )
    parser.add_argument(
        "--from-json",
        metavar="PATH",
        help=(
            "re-report and re-draw a saved run instead of measuring again; "
            "every other option except --chart and --json is then ignored"
        ),
    )
    args = parser.parse_args(argv)

    measurement = (
        Measurement.from_json(json.loads(Path(args.from_json).read_text("utf-8")))
        if args.from_json
        else measure(
            distances_m=args.distances,
            points=args.points,
            seed=args.seed,
            include_point_classes=not args.no_point_classes,
        )
    )
    if args.json_out:
        destination = Path(args.json_out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(measurement.as_json(), indent=2), encoding="utf-8"
        )
        print(f"wrote {destination}", file=sys.stderr)
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
